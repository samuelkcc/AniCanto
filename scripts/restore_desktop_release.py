#!/usr/bin/env python3
"""Prepare an isolated desktop rebuild from checked public release materials.

The public binary supplies unchanged third-party tools. Application code is built
from the matching source archive. Xcode, Rust and cargo-xwin are prerequisites.
Never replace an installed App or read owner projects.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import tarfile
import urllib.request
import zipfile

TAG = 'v0.25.54-beta'
ASSETS = {
    'AniCanto-macOS-0.25.54.zip': '8486f8111667e5cd6ab843c370c2c561605a1cd9fcd12da7576237bb7347c0f4',
    'AniCanto.exe': '49d26c619c163f9a2a98d071e86df32a5c5eb3d123c827e1d8a57ef42fa2a79d',
    'AniCanto-0.25.54-source-materials-reviewed.tar.gz': 'bb808cba5a5db8ffd6c99d5c87ff7c23913137b960b60e04d65c4b7cede83160',
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_rows(root, rows):
    for row in rows:
        rel = Path(row['path'])
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('Unsafe manifest path.')
        path = root/rel
        if not path.is_file() or path.is_symlink() or digest(path) != row['sha256']:
            raise ValueError('Source checksum mismatch: '+str(rel))
    return len(rows)


def safe_zip(archive, destination):
    for info in archive.infolist():
        rel = Path(info.filename)
        # AppleDouble entries describe file metadata. They are not bundle files.
        if any(part == '__MACOSX' or part.startswith('._') for part in rel.parts):
            continue
        if rel.is_absolute() or '..' in rel.parts or stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError('Unsafe release ZIP member.')
        target = destination/rel
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
            mode = info.external_attr >> 16
            if mode:
                target.chmod(stat.S_IMODE(mode))


def pe_payload(path):
    """Locate the checked ZIP embedded in the launcher, independently of PE offsets."""
    raw = path.read_bytes()
    end = raw.rfind(b'PK\x05\x06')
    if end < 0:
        raise ValueError('No embedded Windows payload.')
    size, offset = struct.unpack_from('<II', raw, end+12)
    comment = struct.unpack_from('<H', raw, end+20)[0]
    start = end-size-offset
    archive = zipfile.ZipFile(io.BytesIO(raw[start:end+22+comment]))
    if archive.testzip() is not None:
        raise ValueError('Windows payload CRC check failed.')
    version = json.loads(archive.read('VERSION.json'))
    if version['version'] != '0.25.54' or str(version['build']) != '446':
        raise ValueError('Wrong Windows payload version.')
    return archive


def vendor_crates(materials, destination):
    vendor = destination/'vendor';vendor.mkdir()
    count = 0
    for source in sorted((materials/'desktop-crates').glob('*.crate')):
        with tarfile.open(source) as archive:
            archive.extractall(vendor, filter='data')
        folder = vendor/source.name.removesuffix('.crate')
        files = {p.relative_to(folder).as_posix(): digest(p) for p in folder.rglob('*') if p.is_file()}
        (folder/'.cargo-checksum.json').write_text(json.dumps(dict(package=digest(source), files=files)))
        count += 1
    cargo_home = destination/'cargo-home';cargo_home.mkdir()
    (cargo_home/'config.toml').write_text('[source.crates-io]\nreplace-with = "recovery-vendor"\n'
                                         '[source.recovery-vendor]\ndirectory = '+json.dumps(str(vendor))+'\n')
    # Package notices use the selected Cargo home. Keep original crate archives there.
    cache = cargo_home/'registry/cache/recovery';cache.mkdir(parents=True)
    for source in (materials/'desktop-crates').glob('*.crate'):
        shutil.copy2(source, cache/source.name)
    return count, cargo_home


def adapt_notice_cache(app):
    """Apply the checked Cargo-home correction to the older published recipe."""
    path=app/'scripts/package_shared_studio.py';before=path.read_text()
    old_import='import hashlib,json,plistlib,shutil,subprocess,sys'
    old_line="            archive=next((Path.home()/'.cargo/registry/cache').glob('*/'+package['name']+'-'+package['version']+'.crate'))"
    new_line="            cargo_home=Path(os.environ.get('CARGO_HOME',str(Path.home()/'.cargo')))\n            archive=next((cargo_home/'registry/cache').glob('*/'+package['name']+'-'+package['version']+'.crate'))"
    if before.count(old_import)!=1 or before.count(old_line)!=1:
        raise ValueError('The published notice recipe changed. Review the recovery adapter.')
    saved=app/'.recovery/originals/scripts/package_shared_studio.py';saved.parent.mkdir(parents=True)
    shutil.copy2(path,saved)
    path.write_text(before.replace(old_import,'import hashlib,json,os,plistlib,shutil,subprocess,sys').replace(old_line,new_line))
    return dict(path='scripts/package_shared_studio.py',originalSHA256=digest(saved),adaptedSHA256=digest(path),
                reason='Use the isolated Cargo home for required notice archives.')


def prepare(destination, assets, download=False):
    if destination.exists():
        raise ValueError('Use a new recovery directory.')
    assets.mkdir(parents=True, exist_ok=True)
    for name, expected in ASSETS.items():
        path = assets/name
        if not path.is_file() and download:
            temporary = path.with_suffix(path.suffix+'.partial')
            urllib.request.urlretrieve('https://github.com/samuelkcc/AniCanto/releases/download/'+TAG+'/'+name, temporary)
            if digest(temporary) != expected:
                raise ValueError('Downloaded asset checksum mismatch.')
            temporary.replace(path)
        if not path.is_file() or digest(path) != expected:
            raise ValueError('Missing or changed public release asset: '+name)
    destination.mkdir(parents=True)
    materials = destination/'materials';materials.mkdir()
    with tarfile.open(assets/'AniCanto-0.25.54-source-materials-reviewed.tar.gz') as archive:
        archive.extractall(materials, filter='data')
    manifest = json.loads((materials/'SOURCE-MATERIALS.json').read_text())
    source_count = verify_rows(materials, manifest['files'])
    app = materials/'AniCanto'
    app_count = verify_rows(app, json.loads((app/'SOURCE-MANIFEST.json').read_text())['files'])
    dist = app/'dist';dist.mkdir()
    with zipfile.ZipFile(assets/'AniCanto-macOS-0.25.54.zip') as archive:
        safe_zip(archive, dist)
    base = dist/'AniCanto.app/Contents/Resources'
    shutil.copy2(base/'bin/drama3-small-server', app/'Resources/drama3-small-server')
    # The old source allowlist omitted this required build asset. Its checked
    # release copy permits recovery without the original development computer.
    shutil.copy2(base/'app-icon-art-framed.png', app/'Resources/app-icon-art-framed.png')
    shutil.copytree(base/'wheels', app/'Resources/wheels', dirs_exist_ok=True)
    with pe_payload(assets/'AniCanto.exe') as archive:
        payload = destination/'windows-payload';payload.mkdir()
        safe_zip(archive, payload)
    shutil.copytree(payload/'tools', app/'windows/tools', dirs_exist_ok=True)
    installer = materials/'installer'
    for wheel in installer.glob('*.whl'):
        shutil.copy2(wheel, app/'Resources/wheels'/wheel.name)
    crates, cargo_home = vendor_crates(materials, destination)
    adapter=adapt_notice_cache(app)
    receipt = dict(languageStandard='English; ASD-STE100 style', task='Prepare desktop recovery from public release assets.',
                   sourceCommit='2bec8592ea83a6e26e63dee9aad9581bd479bd71', version='0.25.54', build=446,
                   sourceMaterialsVerified=source_count, applicationFilesVerified=app_count,
                   vendoredCrates=crates, assetHashes=ASSETS, sourceRoot=str(app), cargoHome=str(cargo_home),
                   buildRecipeAdapters=[adapter],
                   thirdPartyBinaryToolsFromMatchingRelease=True, ownerDataRead=False,
                   restoredMissingSourceAssets={'Resources/app-icon-art-framed.png': digest(app/'Resources/app-icon-art-framed.png')},
                   fullThirdPartyToolRecompile=False, buildPassed=False)
    (destination/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return app, cargo_home, receipt


def build(destination, app, cargo_home, receipt):
    env=dict(os.environ,CARGO_HOME=str(cargo_home),CARGO_BUILD_JOBS='2',XWIN_VERSION='17',XWIN_SDK_VERSION='10.0.22621')
    logs=destination/'logs';logs.mkdir(exist_ok=True)
    steps=[('native',['scripts/stage_release.py']),
           ('host-mac',['scripts/build_shared_host.py','--target','native']),
           ('host-windows',['scripts/build_shared_host.py','--target','x86_64-pc-windows-msvc']),
           ('package-mac',['scripts/package_shared_studio.py']),
           ('package-windows',['scripts/build_portable_windows.py'])]
    for name,args in steps:
        with (logs/(name+'.log')).open('w') as stream:
            subprocess.run(['python3',*args],cwd=app,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    for name,script,overrides in [
        ('verify-mac','tests/verify_mac_desktop.py',dict(CANTOSYNC_VERIFY_APP=str(app/'.build/shared-release/0.25.54/AniCanto.app'))),
        ('verify-windows','tests/verify_windows_portable.py',dict(CANTOSYNC_VERIFY_EXE=str(app/'dist/AniCanto.exe')))]:
        with (logs/(name+'.log')).open('w') as stream:
            subprocess.run(['python3',script],cwd=app,env=dict(env,**overrides),stdout=stream,stderr=subprocess.STDOUT,check=True)
    receipt.update(buildPassed=True,macProductVerifierPassed=True,windowsProductVerifierPassed=True,
                   ownerInstallationChanged=False,windowsHardwareExecuted=False)
    (destination/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--assets', required=True, type=Path)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--build', action='store_true', help='build and verify both desktop packages inside the new directory')
    args = parser.parse_args()
    app, cargo_home, receipt = prepare(args.destination.resolve(), args.assets.resolve(), args.download)
    if args.build:
        build(args.destination.resolve(),app,cargo_home,receipt)
    print(json.dumps(receipt, indent=2))
    print('Prepared source: '+str(app))
    print('Use CARGO_HOME='+str(cargo_home)+' for the isolated builds.')


if __name__ == '__main__':
    main()
