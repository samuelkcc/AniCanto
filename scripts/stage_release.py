"""Build a new app beside an existing release without modifying a running app.

Dependencies are cloned from the already bundled release. For a cold dependency
build use build.py with CANTO_BUILD_APP instead.
"""
import json
import os
import plistlib
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def main():
    from python_installer_assets import prepare as installer_assets
    installer_assets()
    # The Swift worker and Rust core must embed the exact same contract.
    subprocess.run(['python3',str(ROOT/'scripts/generate_contract.py'),'--check'],check=True)
    release=json.loads((ROOT/'VERSION.json').read_text())
    source=ROOT/'dist/AniCanto.app'
    if not source.exists():source=ROOT/'dist/CantoSync.app'
    target=ROOT/'.build/releases'/release['version']/'AniCanto.app'
    if target.exists():raise SystemExit(f'Release staging already exists: {target}')
    if not any((source/'Contents/MacOS'/name).is_file() for name in ('AniCanto','CantoSync')):raise SystemExit('A bundled base release is required.')
    target.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['/bin/cp','-cR',str(source),str(target)],check=True)
    resources=target/'Contents/Resources'
    (resources/'bin/uv').unlink(missing_ok=True)
    if os.environ.get('CANTO_BUNDLE_RUNTIMES')!='1':
        from lightweight_mac import prepare
        prepare(resources,ROOT)
    if os.environ.get('CANTO_BUNDLE_RUNTIMES')=='1' and os.environ.get('CANTO_GSV_SOURCE'):
        import sys
        sys.path.insert(0,str(ROOT/'Resources'))
        from dubbing_setup import REV
        from gsv_versions import complete
        models=Path(os.environ['CANTO_GSV_SOURCE'])/REV
        if not all(complete(models,v) for v in ('v2ProPlus','v4')):raise SystemExit('GPT model bundle is incomplete')
        shutil.copytree(models,resources/'gpt-sovits'/REV,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # An installed base release can contain runtime-created Python/Numba caches.
    # Never carry those generated files into a new signed release.
    for cache in (resources/'runtimes').rglob('__pycache__'):
        shutil.rmtree(cache)
    for pattern in ('*.py','*.lock'):
        for path in (ROOT/'Resources').glob(pattern):shutil.copy2(path,resources/path.name)
    shutil.copy2(ROOT/'Resources/drama3-small-server',resources/'bin/drama3-small-server')
    for name in ('hardware-runtimes.json','production-contract.json','voice-models.json','model-options.json','MODEL-NOTICES.txt','visual-requirements.lock','local-tts-requirements.lock'):shutil.copy2(ROOT/'Resources'/name,resources/name)
    shutil.copytree(ROOT/'Resources/tts-vendor',resources/'tts-vendor',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(ROOT/'Resources/wheels',resources/'wheels',dirs_exist_ok=True)
    if os.environ.get('CANTO_BUNDLE_RUNTIMES')=='1' and os.environ.get('CANTO_LOCAL_TTS_RUNTIME'):
        runtime=Path(os.environ['CANTO_LOCAL_TTS_RUNTIME'])
        dest=resources/'runtimes/local-tts-runtime'
        if dest.exists():shutil.rmtree(dest)
        shutil.copytree(runtime,dest,symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        manifest=json.loads((resources/'BUNDLED-RUNTIMES.json').read_text())
        manifest['local-tts-runtime']={'python':'3.11','packages':sorted(p.name for p in (dest/'lib/python3.11/site-packages').glob('*.dist-info'))}
        (resources/'BUNDLED-RUNTIMES.json').write_text(json.dumps(manifest,indent=2))
    shutil.copytree(ROOT/'Resources/natural-voices',resources/'natural-voices',dirs_exist_ok=True)
    for path in (ROOT/'Resources').glob('pet-*.png'):shutil.copy2(path,resources/path.name)
    shutil.copy2(ROOT/'Resources/pet-art-prompts.json',resources/'pet-art-prompts.json')
    shutil.copy2(ROOT/'Resources/PUBLIC-DISTRIBUTION.json',resources/'PUBLIC-DISTRIBUTION.json')
    for lang in ('en','zh-HK'):
        shutil.copytree(ROOT/'Resources'/f'{lang}.lproj',resources/f'{lang}.lproj',dirs_exist_ok=True)
    from build_core import install as install_core
    install_core(resources/'bin/anicanto-core')
    snapshot=target.parent/'sources'
    shutil.copytree(ROOT/'Sources',snapshot,dirs_exist_ok=True)
    subprocess.run(['/usr/bin/swiftc','-swift-version','5','-O','-whole-module-optimization','-target','arm64-apple-macosx14.0','-module-cache-path',str(ROOT/'.build/ModuleCache-AniCanto'),*[str(p) for p in sorted(snapshot.glob('*.swift'))],'-o',str(target/'Contents/MacOS/AniCanto')],check=True)
    info=target/'Contents/Info.plist'
    with info.open('rb') as f:metadata=plistlib.load(f)
    shutil.copy2(ROOT/'Resources/AniCanto.icns',resources/'AniCanto.icns')
    metadata.update(CFBundleShortVersionString=release['version'],CFBundleVersion=release['build'],CFBundleExecutable='AniCanto',CFBundleName='AniCanto',CFBundleDisplayName='AniCanto',CFBundleIconFile='AniCanto.icns',NSHumanReadableCopyright='Copyright © 2026 SCKC')
    with info.open('wb') as f:plistlib.dump(metadata,f)
    from license_inventory import generate
    from release_notices import install as install_release_notices
    extra=install_release_notices(resources)
    inventory=generate(resources)+extra
    (resources/"license-inventory.json").write_text(json.dumps(inventory,ensure_ascii=False,indent=2))
    from resource_assets import prune
    prune(resources)
    subprocess.run(['/usr/bin/codesign','--force','--deep','--sign','-',str(target)],check=True)
    subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(target)],check=True)
    print(target)

if __name__=='__main__':main()
