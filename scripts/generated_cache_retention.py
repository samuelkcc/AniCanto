"""Review generated compiler caches without removing source or dependency inputs."""
import hashlib
import json
import os
import plistlib
import shutil
import time
from pathlib import Path

SKIP = {'.git', 'Dependencies', 'SourcePackages', 'node_modules', '_retained-models',
        '_retention-archive', 'compliance', 'privacy-rights327', '.venv', 'venv'}
PARTS = {'Build', 'Index.noindex', 'ModuleCache.noindex', 'SDKStatCaches.noindex',
         'SDKExplicitPrecompiledModules', 'CompilationCache.noindex'}


def xcode_parent(path):
    if 'derived' in path.name.lower() or path.name.startswith('DD-'):
        return (path/'info.plist').is_file() or (path/'Logs').is_dir()
    try:
        return isinstance(plistlib.loads((path/'info.plist').read_bytes()).get('WorkspacePath'),str)
    except (OSError,ValueError,plistlib.InvalidFileException,AttributeError):
        return False


def checked(root, relative):
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise ValueError('Invalid cache path.')
    path = root / rel
    for parent in [path, *path.parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError('A cache parent is a symbolic link.')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Cache path escapes the workspace.')
    if path.name.startswith('._') and any(p.suffix == '.app' for p in path.parents):
        if path.is_file() and path.read_bytes()[:4] == b'\x00\x05\x16\x07':
            return path
        raise ValueError('Invalid AppleDouble metadata.')
    cargo = (rel.as_posix() == 'studio/src-tauri/target' or
             rel.parts[:1] == ('.build',) and (rel.parts[-3:] == ('studio','src-tauri','target') or
             rel.parts[-3:] == ('.build','windows','portable-target') or rel.parts[-2:] == ('.build','core')))
    xcode = path.name in PARTS and xcode_parent(path.parent)
    if not (cargo or xcode) or any(part in SKIP for part in rel.parts):
        raise ValueError('The path is not an allowed generated compiler cache.')
    return path


def inventory(path):
    if path.is_file():
        s = path.stat()
        return dict(treeIdentity=hashlib.sha256(path.read_bytes()).hexdigest(), entries=1,
                    logicalBytes=s.st_size, allocatedBytes=s.st_blocks*512)
    rows = []
    logical = allocated = 0
    for base, dirs, files in os.walk(path, followlinks=False):
        if '.git' in dirs or '.git' in files:
            raise ValueError('A compiler cache contains a Git checkout.')
        for name in sorted(dirs + files):
            p = Path(base, name)
            s = p.lstat()
            link = os.readlink(p) if p.is_symlink() else ''
            rows.append([p.relative_to(path).as_posix(), s.st_mode, s.st_size, s.st_mtime_ns, link])
            if p.is_file() and not p.is_symlink():
                logical += s.st_size
                allocated += s.st_blocks * 512
    rows.sort()
    return dict(treeIdentity=hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest(),
                entries=len(rows), logicalBytes=logical, allocatedBytes=allocated)


def live_inputs(root):
    """Read links and project paths before selecting nested caches."""
    targets = set()
    roots = [root/'mobile', root/'.build/closure340/delivery350/workspace/mobile',
             root/'.build/iphone201/workspace/mobile', root/'.build/duo251']
    for source in roots:
        for base, dirs, files in os.walk(source, followlinks=False):
            dirs[:] = [n for n in dirs if n not in (SKIP-{'Dependencies'}) and 'derived' not in n.lower() and not n.startswith('DD-')]
            for name in dirs + files:
                p = Path(base, name)
                if p.is_symlink():
                    targets.add(p.resolve())
    # Project settings can name a cache product without a symbolic link.
    projects = []
    for source in roots:
        projects.extend(source.glob('*.xcodeproj/project.pbxproj'))
    texts = [p.read_text(errors='replace') for p in projects]
    return targets, texts


def live_ancestors(targets):
    """Index protected target ancestors once, rather than once per cache file."""
    result=set()
    for target in targets:
        result.add(target);result.update(target.parents)
    return result


def discover(root):
    candidates = [root/'studio/src-tauri/target']
    for start in [root/'mobile', root/'DD-audit-ipad', root/'.build']:
        for base, dirs, _ in os.walk(start, followlinks=False):
            parent = Path(base)
            if parent.parts[-2:] == ('studio','src-tauri') and (parent/'target/.rustc_info.json').is_file():
                candidates.append(parent/'target')
            if parent.name == '.build':
                for name in ('core','windows/portable-target'):
                    p=parent/name
                    if (p/'.rustc_info.json').is_file():candidates.append(p)
            dirs[:] = [n for n in dirs if n not in SKIP and not (parent/n).is_symlink()
                       and n != 'target' and not n.endswith(('.app', '.xcarchive'))]
            if xcode_parent(parent):
                for name in list(dirs):
                    if name in PARTS:
                        candidates.append(parent/name)
                        dirs.remove(name)
    return list(dict.fromkeys(candidates))


def make_plan(root, destination):
    targets, projects = live_inputs(root)
    blocked=live_ancestors(targets)
    rows = []
    skipped = []
    for path in discover(root):
        if not path.is_dir():
            continue
        if path.parts[-3:] == ('studio','src-tauri','target') and not (path/'.rustc_info.json').is_file():
            # This can hold only a frozen delivered host for package verification.
            continue
        checked(root, path.relative_to(root))
        resolved = path.resolve()
        if resolved in blocked:
            skipped.append(str(path.relative_to(root)))
            continue
        if any(str(path) in text or str(path.relative_to(root)) in text for text in projects):
            skipped.append(str(path.relative_to(root)))
            continue
        rows.append(dict(path=str(path.relative_to(root)), **inventory(path)))
    result = dict(schemaVersion=1, languageStandard='English; ASD-STE100 style',
                  task='Remove generated compiler caches only.', createdUnix=time.time(),
                  workspace=str(root), files=rows, skippedLiveInputs=skipped,
                  sourceAndModelsRemoved=False)
    destination.write_text(json.dumps(result, indent=2)+'\n')
    return result


def execute(root, plan_path, apply=False):
    plan = json.loads(plan_path.read_text())
    if plan['workspace'] != str(root):
        raise ValueError('The cache plan belongs to another workspace.')
    names=sorted(row['path'] for row in plan['files'])
    for left,right in zip(names,names[1:]):
        if right == left or right.startswith(left.rstrip('/')+'/'):
            raise ValueError('Cache paths overlap.')
    targets, projects = live_inputs(root)
    blocked=live_ancestors(targets)
    approved = []
    for row in plan['files']:
        path = checked(root, row['path'])
        resolved = path.resolve()
        if resolved in blocked:
            raise ValueError('An active native input uses the cache.')
        if any(str(path) in text or row['path'] in text for text in projects):
            raise ValueError('An active native project uses the cache.')
        if inventory(path) != {k: row[k] for k in ('treeIdentity', 'entries', 'logicalBytes', 'allocatedBytes')}:
            raise ValueError('Cache content changed. Create and review a new plan.')
        approved.append(path)
    free_before = shutil.disk_usage(root).free
    for path in approved:
        if apply:
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
    return dict(action='applied' if apply else 'dry-run', paths=len(approved),
                logicalBytes=sum(r['logicalBytes'] for r in plan['files']),
                volumeFreeBeforeBytes=free_before, volumeFreeAfterBytes=shutil.disk_usage(root).free)
