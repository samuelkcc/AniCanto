"""Stage a signed shared-interface Mac candidate without replacing a live app.

Windows embeds the same web bundle in the native host and then packages that
host inside the existing verified single-file bootstrap launcher.
"""
import hashlib,json,plistlib,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from prepare_shared_studio import prepare

def notices(resources,platform='aarch64-apple-darwin'):
    metadata=json.loads(subprocess.check_output(['cargo','metadata','--locked','--offline','--format-version','1',
        '--filter-platform',platform,'--manifest-path',str(ROOT/'studio/src-tauri/Cargo.toml')]))
    records=[]
    for package in metadata['packages']:
        if not package.get('source'):continue
        folder=Path(package['manifest_path']).parent;dest=resources/'Licenses/shared-studio'/(package['name']+'-'+package['version']);files=[]
        for path in folder.iterdir():
            if path.is_file() and path.name.upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE','UNLICENSE')):
                dest.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest/path.name);files.append(str((dest/path.name).relative_to(resources)))
        if not files:
            fallback=ROOT/'studio/notices'/(package['name']+'-'+package['version'])
            if fallback.is_dir():
                for path in fallback.iterdir():
                    if path.is_file():dest.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest/path.name);files.append(str((dest/path.name).relative_to(resources)))
            if not files:raise RuntimeError('Missing shared UI dependency notice: '+package['name'])
        if package.get('license') and 'MPL' in package['license']:
            archive=next((Path.home()/'.cargo/registry/cache').glob('*/'+package['name']+'-'+package['version']+'.crate'))
            shutil.copy2(archive,dest/archive.name)
        records.append(dict(name=package['name'],version=package['version'],license=package.get('license'),origin=package.get('repository') or 'Rust dependency',files=files))
    return records

def bundle():
    from sanitize_build_paths import prepare as native_paths
    native_paths()
    prepare();version=json.loads((ROOT/'VERSION.json').read_text())
    base=ROOT/'.build/releases'/version['version']/'AniCanto.app'
    target=ROOT/'.build/shared-release'/version['version']/'AniCanto.app'
    refresh='--refresh' in sys.argv
    if target.exists() and not refresh:raise SystemExit('A staged shared candidate exists. Use --refresh to refresh only that build stage.')
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():subprocess.run(['/bin/cp','-cR',str(base),str(target)],check=True)
    contents=target/'Contents';resources=contents/'Resources'
    shutil.copy2(base/'Contents/MacOS/AniCanto',contents/'MacOS/AniCanto-worker')
    shutil.copy2(ROOT/'studio/src-tauri/target/release/anicanto-studio',contents/'MacOS/AniCanto')
    from build_core import install as install_core
    install_core(resources/'bin/anicanto-core')
    (resources/'bin/uv').unlink(missing_ok=True)
    shutil.copy2(ROOT/'Resources/drama3-small-server',resources/'bin/drama3-small-server')
    for name in ('python-installer.json','python-bootstrap.sh','python-bootstrap.ps1'):
        shutil.copy2(ROOT/'Resources'/name,resources/name)
    for path in (ROOT/'Resources').glob('*.py'):shutil.copy2(path,resources/path.name)
    for path in (ROOT/'Resources').glob('pet-*.png'):shutil.copy2(path,resources/path.name)
    for name in ('assistant-rigs.json','assistant-characters.json','assistant-animation.json','pet-art-prompts.json','artwork-provenance.json','theme-art-prompts.json','workflow-localization.json','PUBLIC-DISTRIBUTION.json'):
        shutil.copy2(ROOT/'Resources'/name,resources/name)
    shutil.rmtree(resources/'welcome-art',ignore_errors=True)
    shutil.copytree(ROOT/'Resources/welcome-art',resources/'welcome-art')
    for name in ('model-options.json','voice-models.json','cosy-models.json'):shutil.copy2(ROOT/'Resources'/name,resources/name)
    shutil.copy2(ROOT/'VERSION.json',resources/'VERSION.json')
    (resources/'studio').mkdir(exist_ok=True);shutil.copy2(ROOT/'studio/backend.py',resources/'studio/backend.py')
    (resources/'windows').mkdir(exist_ok=True)
    for path in (ROOT/'windows').iterdir():
        if path.is_file() and path.suffix in ('.py','.json','.lock'):shutil.copy2(path,resources/'windows'/path.name)
    # Actual notices are displayed by the same drawer on both platforms.
    from resource_assets import prune
    prune(resources)
    from release_notices import install as install_release_notices
    extra=install_release_notices(resources)
    shutil.rmtree(resources/'Licenses/cantosync-core',ignore_errors=True)
    from license_inventory import generate
    records=generate(resources);records+=notices(resources);records+=extra
    (resources/'license-inventory.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    with (contents/'Info.plist').open('rb') as f:info=plistlib.load(f)
    info.update(CFBundleIdentifier='com.sckc.cantosync.studio',CFBundleDisplayName='AniCanto',CFBundleName='AniCanto',CFBundleExecutable='AniCanto',CFBundleIconFile='AniCanto.icns',NSHighResolutionCapable=True,NSHumanReadableCopyright='Copyright © 2026 SCKC')
    with (contents/'Info.plist').open('wb') as f:plistlib.dump(info,f)
    for name in ('CantoSync','CantoSync-worker'):(contents/'MacOS'/name).unlink(missing_ok=True)
    for name in ('CantoSync.icns','CantoSync-icon.png'):(resources/name).unlink(missing_ok=True)
    (resources/'bin/cantosync-core').unlink(missing_ok=True)
    shutil.rmtree(resources/'Licenses/cantosync-core',ignore_errors=True)
    shutil.copy2(ROOT/'Resources/AniCanto.icns',resources/'AniCanto.icns')
    from resource_assets import prune
    prune(resources)
    subprocess.run(['/usr/bin/codesign','--force','--deep','--sign','-',str(target)],check=True)
    subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(target)],check=True)
    files={str(p.relative_to(ROOT/'studio/web')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'studio/web').rglob('*') if p.is_file()}
    receipt=dict(version=version['version'],file=str(target),framework='Tauri 2',sharedFrontend=files,
        installedAppReplaced=False,modelWeightsBundled=False,windowsGPUInferenceTested=False)
    (target.parent/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(target)
    return target

if __name__=='__main__':bundle()
