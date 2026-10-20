"""Stage the cargo-xwin launcher and source desktop without changing the Mac app."""
import hashlib
import json
import plistlib
from pathlib import Path
import shutil
import struct
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'windows'
VERSION=json.loads((ROOT/'VERSION.json').read_text())
DEST=ROOT/('dist/windows/AniCanto-Windows-'+VERSION['version']+'-architecture')
EXE=ROOT/'.build/windows/launcher-target/x86_64-pc-windows-msvc/release/AniCanto-Windows.exe'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package():
    from python_installer_assets import prepare as installer_assets
    installer_assets()
    binary=EXE.read_bytes()
    offset=struct.unpack_from('<I',binary,0x3c)[0]
    assert binary[offset:offset+4]==b'PE\0\0'
    assert struct.unpack_from('<H',binary,offset+4)[0]==0x8664,'Expected Windows x64'
    assert b'VCRUNTIME140.dll' not in binary,'Launcher should not require a separate Visual C runtime'
    if DEST.exists():shutil.rmtree(DEST)
    shutil.copytree(SOURCE,DEST,ignore=shutil.ignore_patterns('__pycache__','*.pyc','target','uv','uv.exe','uvx.exe'))
    shutil.copy2(EXE,DEST/'AniCanto-Windows.exe')
    shutil.copy2(ROOT/'LICENSE',DEST/'LICENSE')
    shutil.copy2(ROOT/'VERSION.json',DEST/'VERSION.json')
    shared=DEST/'shared';shared.mkdir()
    from build_core import install as install_core
    install_core(shared/'bin/anicanto-core.exe','x86_64-pc-windows-msvc')
    artwork=DEST/'artwork';artwork.mkdir()
    shutil.copy2(ROOT/'Resources/companion-studio.png',artwork/'companion-studio.png')
    for file in (ROOT/'Resources').iterdir():
        if file.is_file() and (file.suffix in ('.py','.json','.yaml','.ps1') or file.name=='MODEL-NOTICES.txt'):
            shutil.copy2(file,shared/file.name)
    (shared/'wheels').mkdir(exist_ok=True)
    for p in (ROOT/'Resources/wheels').glob('pip-*-py3-none-any.whl'):shutil.copy2(p,shared/'wheels'/p.name)
    for file in DEST.glob('*.cmd'):
        file.write_bytes(file.read_text().replace('\r\n','\n').replace('\n','\r\n').encode('utf-8'))
    media=json.loads((ROOT/'.build/windows/media-qa/receipt.json').read_text())
    receipt=dict(version=VERSION['version']+'-architecture',launcher=dict(target='x86_64-pc-windows-msvc',
        format='PE32+ GUI',buildTool='cargo-xwin 0.23.0',crt='static',sha256=sha(DEST/'AniCanto-Windows.exe')),
        desktop='PySide6 / Python 3.12, isolated first-run installation',
        policyTestsPassed=None,desktopConstructionSaveRestorePassed=None,desktopQAPlatform=None,
        studioLayout='Mac-style navigation, browser, monitor, caption editor, inspector, timeline; zh-HK/en light/dark',
        historicalMediaQA=media,windowsExecutionTested=False,gpuInferenceTested=False,
        gptModelVersion='v4',gptNativeSampleRate=48000,gptCPUValidation=str(ROOT/'.build/qa232/v4-inference-receipt.json'),
        nativeMacSourceVersion=json.loads((ROOT/'VERSION.json').read_text()),
        installedMacVersion=plistlib.loads((ROOT/'dist/AniCanto.app/Contents/Info.plist').read_bytes())['CFBundleShortVersionString'],
        incompletePorts=['automatic ASR','separation','visual cast identity','full timeline editor','seven-track export'])
    (DEST/'QA-RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    files={str(file.relative_to(DEST)).replace('\\','/'):dict(size=file.stat().st_size,sha256=sha(file))
           for file in sorted(DEST.rglob('*')) if file.is_file()}
    (DEST/'PACKAGE-MANIFEST.json').write_text(json.dumps(files,indent=2)+'\n')
    archive=DEST.with_name(DEST.name+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as zip:
        for file in sorted(DEST.rglob('*')):
            if file.is_file():zip.write(file,str(file.relative_to(DEST.parent)))
    with zipfile.ZipFile(archive) as zip:
        assert zip.testzip() is None
        assert any(name.endswith('/AniCanto-Windows.exe') for name in zip.namelist())
    info=dict(archive=str(archive),size=archive.stat().st_size,sha256=sha(archive),
              launcher=str(DEST/'AniCanto-Windows.exe'),files=len(files)+1)
    (ROOT/'.build/windows/package-receipt.json').write_text(json.dumps(info,indent=2)+'\n')
    print(json.dumps(info,indent=2))


if __name__=='__main__':package()
