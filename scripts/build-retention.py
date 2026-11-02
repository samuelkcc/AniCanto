#!/usr/bin/env python3
"""Enforce the .build retention rule: keep at most 5 build versions, remove the rest.

Samuel set this rule on 2026-11-01. .build held 1.35 TB across 1,038 entries and the volume
had 31 GB free. .build is scratch space. Source lives in the repo, shipped output lives in
dist/, and evidence lives in docs/ and mobile/Validation/.

The rule, in order:

  1. Protected entries are never touched. That covers live trees, build toolchains, model
     caches, runtimes, entries named in the newest handover records, and entries written in
     the optional --active-days interval. The default interval is zero.
  2. Desktop release containers share one budget of 5 versions. The current version and
     recorded published version stay protected. Unmanaged version folders keep 5 groups.
  3. Other work folders keep their 5 newest versions. Protected source and evidence are
     separate. A Git checkout or a preservation failure prevents removal.
  4. Recognized model assets move to .build/_retained-models at every size. A move keeps
     downloads. Exact SHA-256 matches can share storage while both paths remain available.
  5. Source files that exist only inside a deleted app snapshot copy to
     .build/_retention-archive, up to --archive-cap-mb.
  6. Each run writes one manifest: .build/_retention-log-<stamp>-<action>.txt.

Dry run is the default and removes nothing. Pass --apply to remove.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import stat
import uuid
import plistlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / '.build'

# Entries that hold a live tree, a toolchain, or a model download that is slow to rebuild.
PROTECTED = {
    'compliance': 'Pinned third-party source inputs and binary verification archives required for matching source delivery.',
    'qa249': 'Required Python 3.11 test runtime. Do not remove its environment.',
    'audit822245': 'Retained user-film evidence. Do not remove recordings.',
    'iphone201': 'Active iPhone source workspace (.build/iphone201/workspace/mobile).',
    'windows': 'Windows cross-build toolchain: xwin cache, portable target, release tree.',
    'Licenses': 'Licence inputs used by the packaging path.',
    'ModuleCache': 'Compiler module cache.',
    'ModuleCache-AniCanto': 'Compiler module cache.',
    'dubbing-data': 'Voice model downloads, GPT-SoVITS runtime and its ready marker.',
    'embedded-resources': 'Bundled runtimes used by the packaging path.',
    'anicanto-demo-runtime': 'Python virtualenv for the demo runtime.',
    '_retained-models': 'Model assets kept by this script.',
    '_retention-archive': 'Source rescued by this script.',
}

# Model weight files only. Packaging payloads such as .zip and .whl are build output, not models.
MODEL_SUFFIXES = {'.gguf', '.safetensors', '.mlx', '.pt', '.pth', '.ckpt', '.onnx', '.bin',
                  '.litertlm', '.tflite', '.mlmodel', '.h5', '.pb', '.npy', '.npz', '.weights'}
SOURCE_SUFFIXES = {'.swift', '.py', '.mjs', '.sh', '.json', '.md', '.m', '.h', '.js',
                   '.rs', '.c', '.cc', '.cpp', '.hpp', '.toml', '.lock', '.css', '.html',
                   '.pbxproj', '.xcconfig', '.plist', '.xcscheme', '.entitlements'}
SOURCE_MAX_BYTES = 5 * 1024 * 1024
SIZES_CACHE = BUILD / '_retention-sizes.json'

# Protected toolchains that still hold old version output one level down.
NESTED_VERSION_FOLDERS = ['windows/release']

SEMVER = re.compile(r'^\d+\.\d+(?:\.\d+)?$')
SEMVER_IN_NAME = re.compile(r'(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)')
VERSION_CONTAINERS = {'previous','releases','shared-release','replaced','backups',
                      'previous-dist','installed-backups','public-review'}
DATE_DIR = re.compile(r'20\d{2}[-_]?\d{2}[-_]?\d{2}')
DIGIT_RUN = re.compile(r'\d+')


def version_key(name: str):
    """Rank a folder by version. Return None when the name carries no version mark.

    Digit runs are build numbers. A run of five digits or more is a timestamp. A four-digit
    run in 1900-2100 without a leading zero is a year. Neither counts as a build number.
    """
    embedded = SEMVER_IN_NAME.search(name)
    if embedded:
        parts = [int(x) for x in embedded.groups()]
    elif SEMVER.match(name):
        parts = [int(part) for part in name.split('.')]
    else:
        numbers = []
        for run in DIGIT_RUN.findall(name):
            if len(run) >= 5:
                continue
            value = int(run)
            if len(run) == 4 and not run.startswith('0') and 1900 <= value <= 2100:
                continue
            numbers.append(value)
        if not numbers and not DATE_DIR.search(name):
            return None
        parts = [max(numbers)] if numbers else [0]
    parts += [0] * (3 - len(parts))
    return tuple(parts[:3])


def du_mb(depth: int, refresh: bool = False) -> dict:
    """One du pass. Return megabytes for each path under .build, to the given depth."""
    if SIZES_CACHE.is_file() and not refresh and time.time() - SIZES_CACHE.stat().st_mtime < 6 * 3600:
        print(f'using cached size scan: {SIZES_CACHE}')
        return json.loads(SIZES_CACHE.read_text(encoding='utf-8'))
    result = subprocess.run(['du', '-m', '-d', str(depth), str(BUILD)],
                            capture_output=True, text=True, check=False)
    sizes = {}
    for line in result.stdout.splitlines():
        tab = line.find('\t')
        if tab < 0:
            continue
        try:
            size = int(line[:tab])
        except ValueError:
            continue
        path = Path(line[tab + 1:])
        if path == BUILD:
            continue
        sizes[path.relative_to(BUILD).as_posix()] = size
    SIZES_CACHE.write_text(json.dumps(sizes), encoding='utf-8')
    return sizes


def protected_names() -> dict:
    """Names in PROTECTED plus any .build entry named in the newest handover records."""
    keep = dict(PROTECTED)
    # Active projects can link native libraries outside their own source tree.
    # A handover window is not a complete inventory of those build inputs.
    for source in (ROOT/'mobile', BUILD/'iphone201/workspace/mobile'):
        for project in source.glob('*.xcodeproj/project.pbxproj'):
            for name in re.findall(r'\.build/([A-Za-z0-9_.-]+)',project.read_text(encoding='utf-8')):
                keep.setdefault(name,'Referenced by an active native project.')
    handover = ROOT / 'docs' / 'CODEX-HANDOVER.md'
    if handover.is_file():
        text = handover.read_text(encoding='utf-8')
        head = text.split('\n## Work Records', 1)[-1]
        # The first records are the newest. Read the nine most recent blocks.
        for block in re.split(r'\n### ', head)[1:10]:
            for match in re.finditer(r'\.build/([A-Za-z0-9_.\-]+)', block):
                keep.setdefault(match.group(1), 'Named in the newest handover records.')
    return keep


def live_source_names() -> dict:
    """Index source paths by name. A name alone never proves equal content."""
    roots = [ROOT / 'mobile', ROOT / '.build/iphone201/workspace/mobile', ROOT / 'scripts',
             ROOT / 'core', ROOT / 'docs', ROOT / 'tests', ROOT / 'Sources',
             ROOT / 'Resources', ROOT / 'studio', ROOT / 'windows']
    present = {}
    for root in roots:
        if not root.exists():
            continue
        for base, dirs, files in os.walk(root):
            dirs[:] = [n for n in dirs if n not in {'target', 'DerivedData', 'Dependencies',
                '.git', '__pycache__', 'node_modules', 'SourcePackages'}]
            for name in files:
                if Path(name).suffix.lower() in SOURCE_SUFFIXES:
                    present.setdefault(name, []).append(Path(base, name))
    return present


def digest(path):
    """Read every byte before treating two files as duplicates."""
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def looks_like_snapshot(path: Path) -> bool:
    """True when one folder holds one work tree, so it counts as one version."""
    if path.name.endswith('-device-project'):
        return True
    for marker in ('workspace', 'AniCantoApp', 'mobile', 'DerivedData', 'dd'):
        if (path / marker).is_dir():
            return True
    return False


def version_children(folder: Path) -> list:
    def artifact(child):
        name=child.name.lower()
        return child.is_file() and not child.is_symlink() and SEMVER_IN_NAME.search(name) and \
            ('anicanto' in name or 'cantosync' in name or 'source-materials' in name) and \
            name.endswith(('.exe','.zip','.tar.gz'))
    return [child for child in folder.iterdir() if not child.is_symlink() and
            (child.is_dir() or artifact(child)) and version_key(child.name) is not None]


def is_version_folder(folder: Path) -> bool:
    """True when most children are version output, such as .build/previous or .build/releases."""
    kids = sub_dirs(folder)
    versioned = version_children(folder)
    kids += [child for child in versioned if child.is_file()]
    return len(versioned) >= 2 and len(versioned) * 10 >= len(kids) * 6


def release_identity(path):
    match=SEMVER_IN_NAME.search(path.name)
    if match:return tuple(int(x) for x in match.groups())
    if path.is_dir():
        for plist in [path/'Contents/Info.plist', *path.glob('*.app/Contents/Info.plist')]:
            try:
                match=SEMVER_IN_NAME.search(str(plistlib.loads(plist.read_bytes()).get('CFBundleShortVersionString','')))
                if match:return tuple(int(x) for x in match.groups())
            except (OSError,ValueError,plistlib.InvalidFileException):pass
    return None


def desktop_release_budget(retain):
    """Use one desktop release budget across containers. Pin the published baseline."""
    versions=set();required=set()
    for label in sorted(VERSION_CONTAINERS|set(NESTED_VERSION_FOLDERS)):
        folder=BUILD/label
        if folder.is_dir():versions.update(v for p in version_children(folder) if (v:=release_identity(p)))
    version=ROOT/'VERSION.json'
    if version.is_file():
        match=SEMVER_IN_NAME.search(str(json.loads(version.read_text()).get('version','')))
        if match:required.add(tuple(int(x) for x in match.groups()))
    downloads=ROOT/'docs/DESKTOP-DOWNLOADS.json'
    if downloads.is_file():
        for value in json.loads(downloads.read_text()).values():
            if isinstance(value,dict):
                match=SEMVER_IN_NAME.search(str(value.get('version','')))
                if match:required.add(tuple(int(x) for x in match.groups()))
    keep=set(required)
    for value in sorted(versions,reverse=True):
        if len(keep)>=retain:break
        keep.add(value)
    return keep or None


def prune_children(folder: Path, retain: int, release_budget=None) -> list:
    """Return the older version children of one folder, keeping the newest `retain`."""
    ordered = sorted(version_children(folder),
                     key=lambda child: (version_key(child.name), child.stat().st_mtime),
                     reverse=True)
    if release_budget is not None:
        return [child for child in ordered if (v:=release_identity(child)) is not None and v not in release_budget]
    # Keep complete releases: a Mac archive and its source archive share a version.
    versions = sorted({version_key(child.name) for child in ordered}, reverse=True)
    latest = set(versions[:retain])
    return [child for child in ordered if version_key(child.name) not in latest]


def rescue(path: Path, live: dict, report: list, model_min_mb: int, archive_left: list,
           model_left: list) -> bool:
    """Move model assets out by rename, and copy source that exists nowhere else."""
    # Check the complete tree before moving any file out of a source checkout.
    for base, dirs, files in os.walk(path):
        parts = Path(base).relative_to(path).parts
        if '.git' in dirs or '.git' in files:
            if 'SourcePackages' in parts and 'checkouts' in parts:
                if '.git' in dirs:dirs.remove('.git')
            else:
                report.append(f'protected {path.name}: contains a Git checkout')
                return False
    for base, dirs, files in os.walk(path):
        if '.git' in dirs or '.git' in files:
            parts = Path(base).relative_to(path).parts
            if 'SourcePackages' in parts and 'checkouts' in parts:
                # These are per-build Xcode dependency caches. Preserve changed
                # source below, but do not archive their duplicate Git database.
                if '.git' in dirs:dirs.remove('.git')
            else:
                report.append(f'protected {path.name}: contains a Git checkout')
                return False
        for name in files:
            file = Path(base, name)
            if file.is_symlink():
                continue
            try:
                size = file.lstat().st_size
            except OSError:
                continue
            if file.suffix.lower() in MODEL_SUFFIXES:
                if model_left[1] + size > model_left[0]:
                    report.append(f'protected {path.name}: model rescue cap reached')
                    return False
                target = BUILD / '_retained-models' / path.name / file.relative_to(path)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    if target.stat().st_size == size and digest(target) == digest(file):
                        continue
                    report.append(f'protected {path.name}: retained model path conflict')
                    return False
                try:
                    file.rename(target)
                    try:
                        file.symlink_to(os.path.relpath(target, file.parent))
                    except OSError:
                        target.rename(file)
                        raise
                except OSError as error:
                    report.append(f'skipped model {file.relative_to(path)}: {error}')
                    return False
                model_left[1] += size
                report.append(f'rescued model {file.relative_to(path)} '
                              f'({size // (1024 * 1024)} MB)')
            elif file.suffix.lower() in SOURCE_SUFFIXES and size <= SOURCE_MAX_BYTES:
                fingerprint = digest(file)
                if any(p.is_file() and p.stat().st_size == size and digest(p) == fingerprint
                       for p in live.get(name, [])):
                    continue
                target = BUILD / '_retention-archive' / fingerprint / name
                if target.exists() and target.stat().st_size == size and digest(target) == fingerprint:
                    continue
                if size > archive_left[0]:
                    report.append(f'protected {path.name}: source archive cap reached')
                    return False
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(file, target)
                except OSError as error:
                    report.append(f'skipped source {file.relative_to(path)}: {error}')
                    return False
                archive_left[0] -= size
                report.append(f'rescued source {file.relative_to(path)}')
    return True


def sub_dirs(folder: Path) -> list:
    return [child for child in folder.iterdir() if child.is_dir() and not child.is_symlink()]


def model_identities() -> set:
    """(name, size) pairs already inside .build/_retained-models."""
    root = BUILD / '_retained-models'
    found = set()
    if not root.is_dir():
        return found
    for base, _dirs, files in os.walk(root):
        for name in files:
            try:
                found.add((name, Path(base, name).lstat().st_size))
            except OSError:
                continue
    return found


def dedupe_retained(report: list, apply=True) -> int:
    """Share exact model duplicates. Preserve every old path through a relative link."""
    root = BUILD / '_retained-models'
    if not root.is_dir():
        return 0
    newest = {}
    freed = 0
    for base, _dirs, files in os.walk(root):
        for name in files:
            file = Path(base, name)
            if file.is_symlink():
                continue
            try:
                stamp = file.lstat().st_mtime
                size = file.lstat().st_size
            except OSError:
                continue
            # Equal names and lengths can identify different model revisions.
            key = (size, digest(file))
            rank=(int(file.stat().st_nlink > 1),stamp)
            holder = newest.get(key)
            if holder is None:
                newest[key] = (rank, file)
                continue
            if rank > holder[0]:
                keep, drop = file, holder[1]
                newest[key] = (rank, file)
            else:
                keep, drop = holder[1], file
            try:
                drop_links=drop.stat().st_nlink
                if apply:
                    link = drop.with_name(drop.name + '.retention-link')
                    if link.exists() or link.is_symlink():
                        raise FileExistsError(str(link))
                    link.symlink_to(os.path.relpath(keep, drop.parent))
                    os.replace(link, drop)
                freed += size if drop_links == 1 else 0
                report.append(f'exact duplicate model {"shared" if apply else "planned"} {drop.relative_to(root)}; '
                              f'kept {keep.relative_to(root)}')
            except OSError as error:
                report.append(f'duplicate model left {drop.relative_to(root)}: {error}')
    for base, dirs, _files in os.walk(root, topdown=False) if apply else []:
        for name in dirs:
            folder = Path(base, name)
            try:
                folder.rmdir()
            except OSError:
                pass
    return freed


def share_live_models(plan_path, live_root, report, apply=False):
    """Keep both paths while sharing verified immutable model weights on one volume."""
    live_root = Path(live_root).resolve()
    retained = (BUILD / '_retained-models').resolve()
    plan = json.loads(Path(plan_path).read_text())
    approved = []
    for group in plan['groups']:
        sources = [Path(f['path']).resolve() for f in group['files'] if f['group'] == 'installed']
        if not sources:
            raise ValueError('Missing installed model identity.')
        source = sources[0]
        if not source.is_relative_to(live_root) or not source.is_file() or digest(source) != group['sha256']:
            raise ValueError('Installed model changed. Scan duplicates again.')
        for row in group['files']:
            if row['group'] != 'retained':
                continue
            target = Path(row['path'])
            if target.is_symlink():
                continue
            target = target.resolve()
            if not target.resolve().is_relative_to(retained) or not target.is_file() or digest(target) != group['sha256']:
                raise ValueError('Retained model changed or escaped its folder.')
            if not source.samefile(target):
                approved.append((source,target,target.stat()))
    freed = 0
    for source,target,old in approved:
        if source.stat().st_dev != old.st_dev:
            report.append(f'kept separate volume model {target.relative_to(retained)}')
            continue
        if apply:
            temporary = target.with_name(target.name + '.share-' + uuid.uuid4().hex)
            try:
                os.link(source,temporary)
                os.replace(temporary,target)
            finally:
                temporary.unlink(missing_ok=True)
            if not source.samefile(target):
                raise RuntimeError('Shared model identity verification failed.')
        freed += old.st_size if old.st_nlink == 1 else 0
        report.append(f'{"shared" if apply else "would share"} exact model {target.relative_to(retained)}; both paths retained')
    return freed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retain', type=int, default=5, help='build versions to keep (default 5)')
    parser.add_argument('--active-days', type=int, default=0,
                        help='optional age guard; default 0 enforces the version limit')
    parser.add_argument('--model-min-mb', type=int, default=300,
                        help='legacy option; recognized model formats are protected at every size')
    parser.add_argument('--model-cap-gb', type=int, default=60,
                        help='model weight total moved in one run (default 60)')
    parser.add_argument('--archive-cap-mb', type=int, default=700,
                        help='total source copied to _retention-archive (default 700)')
    parser.add_argument('--dedupe-only', action='store_true',
                        help='only remove repeated model shards in _retained-models')
    parser.add_argument('--share-model-plan', type=Path, help='reviewed cross-root SHA-256 model plan')
    parser.add_argument('--live-model-root', type=Path, help='installed model root for the reviewed plan')
    parser.add_argument('--apply', action='store_true', help='remove; default is a dry run')
    parser.add_argument('--refresh', action='store_true',
                        help='ignore the size cache and re-measure .build now')
    args = parser.parse_args()
    if not 1 <= args.retain <= 5:
        print('retain must be between 1 and 5')
        return 2
    if bool(args.share_model_plan) != bool(args.live_model_root):
        parser.error('--share-model-plan and --live-model-root must be used together')
    # One retention run at a time. Two runs delete the same folders and crash each other.
    lock = Path('/tmp/anicanto-build-retention.lock')
    try:
        handle = lock.open('x', encoding='utf-8')
    except FileExistsError:
        print(f'another run holds {lock}. Remove it only when no retention run is alive.')
        return 3
    handle.write(str(time.time())); handle.close()
    try:
        return run(args)
    finally:
        lock.unlink(missing_ok=True)


def run(args) -> int:
    report: list = []
    if getattr(args, 'share_model_plan', None):
        freed = share_live_models(args.share_model_plan,args.live_model_root,report,args.apply)
        action = 'model-sharing-applied' if args.apply else 'model-sharing-plan'
        manifest = BUILD / f'_retention-log-{time.strftime("%Y%m%d-%H%M%S")}-{action}.txt'
        manifest.write_text('\n'.join(report)+'\n',encoding='utf-8')
        print(json.dumps(dict(action=action,duplicateBytes=freed,pathsPreserved=True,manifest=str(manifest))))
        return 0
    if args.dedupe_only:
        freed = dedupe_retained(report, apply=args.apply)
        action = 'dedupe applied' if args.apply else 'dedupe dry run'
        manifest = BUILD / f'_retention-log-{time.strftime("%Y%m%d-%H%M%S")}-{action}.txt'
        manifest.write_text('\n'.join(report) + '\n', encoding='utf-8')
        print(f'.build model dedupe: {freed // (1024 * 1024)} MB ({freed / (1024 ** 3):.2f} GB) '
              f'freed. manifest: {manifest}')
        return 0
    sizes = du_mb(3, args.refresh)
    keep = protected_names()
    release_budget=desktop_release_budget(args.retain)
    if release_budget:
        (BUILD/'_retention-release-budget.json').write_text(json.dumps(dict(
            schemaVersion=1,retainedDesktopVersions=['.'.join(map(str,x)) for x in sorted(release_budget)],
            scope='One desktop budget across release containers. Current and published releases are protected.'),indent=2)+'\n')
    now = time.time()
    recent_window = args.active_days * 86400
    entries = [entry for entry in BUILD.iterdir() if entry.is_dir() and not entry.is_symlink()]

    victims = []
    kept = {}
    for entry in entries:
        if entry.name in keep:
            kept[entry.name] = keep[entry.name]
            if entry.name in VERSION_CONTAINERS:
                victims.extend(prune_children(entry, args.retain,release_budget))
            continue
        # An app snapshot is one version, not a folder of versions.
        if not looks_like_snapshot(entry):
            if is_version_folder(entry):
                # Version folder: keep its newest children and remove the older ones.
                kept[entry.name] = 'Version folder; keeps its newest children.'
                victims.extend(prune_children(entry, args.retain,release_budget if entry.name in VERSION_CONTAINERS else None))
                continue
        if now - entry.stat().st_mtime <= recent_window:
            kept[entry.name] = f'Written within {args.active_days} days.'
            continue
        victims.append(entry)

    # A protected toolchain can still hold old version output inside it.
    for label in NESTED_VERSION_FOLDERS:
        folder = BUILD / label
        if folder.is_dir():
            victims.extend(prune_children(folder, args.retain,release_budget))

    # The newest work folders are the five retained versions. Everything older goes.
    work = [entry for entry in victims if entry.parent == BUILD]
    work.sort(key=lambda entry: (version_key(entry.name) or (0,0,0), entry.stat().st_mtime), reverse=True)
    for entry in work[:args.retain]:
        victims.remove(entry)
        kept[entry.name] = 'One of the five newest work folders.'

    live = live_source_names()
    archive_left = [args.archive_cap_mb * 1024 * 1024]
    model_left = [args.model_cap_gb * 1024 * 1024 * 1024, 0]
    freed = 0
    removed_count = 0
    for entry in sorted(victims, key=lambda item: str(item.relative_to(BUILD))):
        label = entry.relative_to(BUILD).as_posix()
        size_mb = sizes.get(label, (entry.stat().st_size + 1024*1024 - 1)//(1024*1024) if entry.is_file() else 0)
        if not args.apply:
            freed += size_mb
            report.append(f'would remove {label} ({size_mb} MB)')
            continue
        if entry.is_file() and not entry.is_symlink():
            size=entry.stat().st_size
            entry.unlink()
            freed += size // (1024*1024)
            report.append(f'removed release artifact {label} ({size // (1024*1024)} MB)')
            removed_count += 1
            continue
        # Version children also contain unique source, models, or Git checkouts.
        models_before=model_left[1];archive_before=archive_left[0]
        if not rescue(entry, live, report, args.model_min_mb, archive_left, model_left):
            kept[label] = 'Preservation check did not permit removal.'
            continue
        # Bazel snapshots can contain owner-read-only generated directories.
        # Change only owned directories inside the reviewed build victim.
        for base, dirs, _files in os.walk(entry, followlinks=False):
            dirs[:] = [n for n in dirs if not (Path(base) / n).is_symlink()]
            folder = Path(base)
            st = folder.stat()
            if hasattr(os, 'getuid') and st.st_uid == os.getuid() and not st.st_mode & stat.S_IWUSR:
                folder.chmod(stat.S_IMODE(st.st_mode) | stat.S_IWUSR | stat.S_IXUSR)
        # ignore_errors keeps one vanished file from stopping the whole clean-up.
        shutil.rmtree(entry, ignore_errors=True)
        if entry.exists():
            leftovers = sum(1 for _ in entry.rglob('*'))
            report.append(f'partial {label}: {leftovers} items remain')
            kept[label] = 'Removal incomplete; no full-folder saving is claimed.'
            continue
        preserved_bytes=(model_left[1]-models_before)+(archive_before-archive_left[0])
        freed += max(0,size_mb-(preserved_bytes+1024*1024-1)//(1024*1024))
        report.append(f'removed {label} ({size_mb} MB)')
        removed_count += 1
        if removed_count % 50 == 0:
            print(f'removed {removed_count} of {len(victims)} entries, '
                  f'{freed / 1024:.1f} GB freed so far', flush=True)

    for name, reason in sorted(kept.items()):
        report.append(f'kept {name}: {reason}')
    # Repeated model shards from several snapshots must not pile up.
    if args.apply:
        extra = dedupe_retained(report)
        freed += extra // (1024 * 1024)
        report.append(f'model dedupe freed {extra // (1024 * 1024)} MB')
        # Sizes changed. The next run must re-measure instead of trusting this cache.
        SIZES_CACHE.unlink(missing_ok=True)
    # Show where the space still sits, so the next run has a starting point.
    remaining = sorted(((sizes.get(name, 0), name) for name in kept), reverse=True)
    for size_mb, name in remaining[:12]:
        report.append(f'largest kept {name}: {size_mb} MB')
    action = 'applied' if args.apply else 'dry run'
    print(f'.build retention ({action}): {len(entries)} entries read; {len(victims)} to remove; '
          f'{freed} MB ({freed / 1024:.2f} GB); {len(kept)} kept.')
    print('largest kept: ' + ', '.join(f'{name} {mb // 1024} GB' for mb, name in remaining[:8]))
    manifest = BUILD / f'_retention-log-{time.strftime("%Y%m%d-%H%M%S")}-{action}.txt'
    manifest.write_text('\n'.join(report) + '\n', encoding='utf-8')
    print(f'manifest: {manifest}')
    print(json.dumps({'action': action, 'retain': args.retain, 'entries': len(entries),
                      'to_remove': len(victims), 'kept': len(kept), 'freed_mb': freed}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
