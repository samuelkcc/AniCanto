"""Remove older AniCanto products. Keep all source and owner media outside bundles."""
import json
import hashlib
import io
import os
import plistlib
import shutil
import struct
import zipfile
from pathlib import Path
from generated_cache_retention import inventory, live_inputs, live_ancestors


def preserve_code(root, paths):
    """Keep copied program text before removing obsolete bundles."""
    suffixes={'.py','.swift','.js','.mjs','.rs','.c','.h','.cpp','.hpp','.m','.mm',
              '.sh','.ps1','.cmd','.json','.toml','.lock','.html','.css','.strings','.yaml','.yml'}
    archive=root/'.build/_retention-archive/product-sources';archive.mkdir(parents=True,exist_ok=True)
    count=0
    with (archive/'origins.jsonl').open('a') as record:
        for path in paths:
            if not path.is_dir():continue
            for base, dirs, files in os.walk(path,followlinks=False):
                dirs[:]=[n for n in dirs if not (Path(base)/n).is_symlink()]
                for name in files:
                    source=Path(base,name)
                    if source.is_symlink() or source.suffix.lower() not in suffixes:continue
                    raw=source.read_bytes();sha=hashlib.sha256(raw).hexdigest()
                    dest=archive/sha/name
                    if dest.exists():
                        if dest.read_bytes()!=raw:raise ValueError('Source preservation conflict.')
                    else:
                        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
                    record.write(json.dumps(dict(source=str(source.relative_to(root)),archive=str(dest.relative_to(root)),sha256=sha))+'\n')
                    count+=1
    return count


def product(path):
    """Read product identity from package metadata, never from a film or work-folder name."""
    data = None
    if path.suffix in {'.zip','.exe'}:
        if path.suffix == '.exe':
            raw=path.read_bytes();end=raw.rfind(b'PK\x05\x06')
            if end < 0 or end+22 > len(raw):
                version=path.parent/'VERSION.json'
                if (raw.startswith(b'MZ') and path.name in {'AniCanto-Windows.exe','AniCanto.exe'}
                        and version.is_file() and (path.parent/'native_worker.py').is_file()):
                    return dict(platform='desktop',build=int(json.loads(version.read_text())['build']))
                return None
            size,offset=struct.unpack_from('<II',raw,end+12)
            comment=struct.unpack_from('<H',raw,end+20)[0]
            if end-size-offset < 0 or end+22+comment > len(raw):return None
            source=io.BytesIO(raw[end-size-offset:end+22+comment])
        else:source=path
        with zipfile.ZipFile(source) as archive:
            names=archive.namelist()
            if 'VERSION.json' in names and 'shared/worker.py' in names:
                version=json.loads(archive.read('VERSION.json'))
                return dict(platform='desktop',build=int(version['build']))
            plists=[n for n in names if n.endswith('.app/Contents/Info.plist') and n.count('/') == 2]
            if len(plists)!=1:return None
            data=plistlib.loads(archive.read(plists[0]))
            if not any(s in str(data.get('CFBundleIdentifier','')).lower() for s in ('anicanto','cantosync','com.sckc.')):
                return None
            return dict(platform='desktop',build=int(data['CFBundleVersion']))
    if path.suffix == '.ipa':
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if n.startswith('Payload/') and n.count('/') == 2 and n.endswith('.app/Info.plist')]
            if len(names) != 1:
                return None
            data = plistlib.loads(archive.read(names[0]))
    else:
        for rel in ('Info.plist', 'Contents/Info.plist'):
            p = path/rel
            if p.is_file():
                data = plistlib.loads(p.read_bytes());break
    if not data:
        return None
    data = data.get('ApplicationProperties', data)
    bundle = str(data.get('CFBundleIdentifier', data.get('ApplicationBundlePath', '')))
    name = str(data.get('CFBundleName', path.name))
    if not any(s in (bundle+' '+name).lower() for s in ('anicanto', 'cantosync', 'com.sckc.')):
        return None
    try:
        build = int(data['CFBundleVersion'])
    except (ValueError, KeyError):
        return None
    desktop = (path/'Contents/Info.plist').is_file() or 'macos' in str(data.get('SupportedPlatforms', '')).lower()
    # Mac archives have a Mac application under Products/Applications.
    if path.suffix == '.xcarchive':
        desktop = any((p/'Contents/Info.plist').is_file() for p in (path/'Products/Applications').glob('*.app'))
    return dict(platform='desktop' if desktop else 'mobile', build=build)


def latest(root):
    desktop = int(json.loads((root/'VERSION.json').read_text())['build'])
    builds = []
    for path in (root/'.build').glob('testflight*/AniCanto.xcarchive'):
        try:
            row = product(path)
            if row and row['platform'] == 'mobile':builds.append(row['build'])
        except (OSError, ValueError, plistlib.InvalidFileException):
            continue
    if not builds:
        raise ValueError('Cannot identify the latest mobile build. Stop.')
    return dict(desktop=desktop, mobile=max(builds))


def checked(root, relative, current):
    rel = Path(relative)
    allowed=(rel.parts[:1] == ('.build',) or rel.parts[:2] == ('dist','windows')
             or len(rel.parts)>1 and rel.parts[0]=='dist' and rel.parts[1].startswith('pending-')
             or len(rel.parts)>1 and rel.parts[0]=='mobile' and rel.parts[1].startswith('DerivedData'))
    if rel.is_absolute() or '..' in rel.parts or not allowed:
        raise ValueError('Product removal must stay inside reviewed generated-product roots.')
    p = root/rel
    for parent in [p, *p.parents]:
        if parent == root:break
        if parent.is_symlink():raise ValueError('Product path contains a link.')
    if p.suffix not in {'.app', '.xcarchive', '.ipa', '.zip', '.exe'}:
        raise ValueError('Not a generated application product.')
    row = product(p)
    if row is None or row['build'] >= current[row['platform']]:
        raise ValueError('Unknown, current or newer product. Keep it.')
    return p, row


def scan(root, destination):
    current = latest(root);targets, _ = live_inputs(root);rows=[];blocked=live_ancestors(targets)
    skip = {'.git', 'Dependencies', 'SourcePackages', 'node_modules', 'target', 'compliance', '_retention-archive'}
    roots=[root/'.build',root/'dist/windows',*root.glob('dist/pending-*'),*root.glob('mobile/DerivedData*')]
    for base, dirs, files in (row for start in roots for row in os.walk(start, followlinks=False)):
        parent=Path(base)
        dirs[:] = [n for n in dirs if n not in skip and not (parent/n).is_symlink()]
        paths=[]
        for name in list(dirs):
            if Path(name).suffix in {'.app', '.xcarchive'}:
                paths.append(parent/name);dirs.remove(name)
        paths += [parent/n for n in files if Path(n).suffix in {'.ipa','.zip','.exe'} and not (parent/n).is_symlink()]
        for path in paths:
            try:p, identity=checked(root,path.relative_to(root),current)
            except (ValueError,OSError,plistlib.InvalidFileException,zipfile.BadZipFile):continue
            resolved=p.resolve()
            if resolved in blocked:continue
            rows.append(dict(path=str(p.relative_to(root)), **identity, **inventory(p)))
    plan=dict(schemaVersion=1,languageStandard='English; ASD-STE100 style',workspace=str(root),
              task='Keep only the latest generated build version for each platform.',latest=current,files=rows)
    destination.write_text(json.dumps(plan,indent=2)+'\n');return plan


def execute(root, plan_path, apply=False):
    plan=json.loads(plan_path.read_text());current=latest(root)
    if plan['workspace'] != str(root) or plan['latest'] != current:
        raise ValueError('Product plan is stale.')
    targets,_=live_inputs(root);approved=[];blocked=live_ancestors(targets)
    for row in plan['files']:
        path,identity=checked(root,row['path'],current)
        if identity != {k:row[k] for k in ('platform','build')}:
            raise ValueError('Product identity changed.')
        resolved=path.resolve()
        if resolved in blocked:
            raise ValueError('An active input uses this product.')
        if inventory(path) != {k:row[k] for k in ('treeIdentity','entries','logicalBytes','allocatedBytes')}:
            raise ValueError('Product files changed.')
        if any(path.is_relative_to(p) or p.is_relative_to(path) for p in approved):
            raise ValueError('Product paths overlap.')
        approved.append(path)
    before=shutil.disk_usage(root).free
    saved=preserve_code(root,approved) if apply else 0
    for path in approved:
        if apply:
            if path.is_dir():shutil.rmtree(path)
            else:path.unlink()
    return dict(action='applied' if apply else 'dry-run',latest=current,products=len(approved),
                copiedProgramFilesPreserved=saved,
                logicalBytes=sum(r['logicalBytes'] for r in plan['files']),
                volumeFreeBeforeBytes=before,volumeFreeAfterBytes=shutil.disk_usage(root).free)
