"""Build an actual single-file Windows x64 launcher with its desktop payload embedded.

Models/runtimes download on first use. The embedded desktop uses the shared
production worker. Native Windows/GPU acceptance still requires a Windows PC.
No installed Mac application is modified.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
from build_core import build as build_core,notices

ROOT=Path(__file__).resolve().parents[1]

def validate_payload_paths(files):
    """Reject names the Windows launcher cannot verify before embedding an EXE."""
    seen={}
    for name,path in files.items():
        parts=name.split('/')
        if (not name or '\\' in name or ':' in name or any(part in ('','.','..') or part.endswith((' ','.')) for part in parts)
                or any(part.upper().split('.')[0] in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))} for part in parts)):
            raise ValueError('invalid-package-path: '+name)
        folded=name.casefold()
        if folded in seen:
            raise ValueError('windows-package-path-collision: '+seen[folded]+' / '+name)
        seen[folded]=name
        if not path.is_file():raise ValueError('missing-package-file: '+name)

def build():
    from python_installer_assets import prepare as installer_assets
    installer_assets()
    from sanitize_build_paths import prepare as native_paths
    native_paths()
    version=json.loads((ROOT/'VERSION.json').read_text())['version']
    output=ROOT/'.build/windows/release'/version;output.mkdir(parents=True,exist_ok=True)
    core=build_core('x86_64-pc-windows-msvc')
    from build_environment import rust_environment
    helper_env=rust_environment('x86_64-pc-windows-msvc',CARGO_TARGET_DIR=str(ROOT/'.build/windows/portable-target'),
                    XWIN_CACHE_DIR=str(ROOT/'.build/windows/xwin-cache'))
    helper_env.pop('CANTOSYNC_EMBEDDED_PACKAGE',None)
    subprocess.run(['cargo']+(['xwin'] if os.name!='nt' else [])+['build','--release','--locked','--offline',
        '--manifest-path',str(ROOT/'windows/launcher/Cargo.toml'),'--bin','AniCanto-helper','--target','x86_64-pc-windows-msvc'],env=helper_env,check=True)
    shutil.copy2(ROOT/'.build/windows/portable-target/x86_64-pc-windows-msvc/release/AniCanto-helper.exe',ROOT/'windows/tools/AniCanto-helper.exe')
    files={}
    for p in (ROOT/'windows').rglob('*'):
        if p.is_file() and not p.is_symlink() and p.name.lower() not in ('uv','uv.exe','uvx.exe') and 'notices/uv' not in p.relative_to(ROOT/'windows').as_posix() and not p.name.startswith('CantoSync-') and p.name not in ('app.py','studio.py','jobs.py','build-exe.ps1','Setup-NVIDIA.cmd','Setup-AMD.cmd','Setup-Intel.cmd') and not any(part in ('__pycache__','target','.cargo') for part in p.relative_to(ROOT/'windows').parts):
            files[p.relative_to(ROOT/'windows').as_posix()]=p
    shared_host=ROOT/'studio/src-tauri/target/x86_64-pc-windows-msvc/release/anicanto-studio.exe'
    if shared_host.is_file():
        files['tools/AniCanto-Studio.exe']=shared_host
        for name in ('backend.py','bootstrap-windows.ps1'):files['studio/'+name]=ROOT/'studio'/name
    for p in (ROOT/'Resources').iterdir():
        if p.is_file() and p.suffix in ('.py','.json','.yaml','.txt','.png','.ps1'):files['shared/'+p.name]=p
    for directory in ('tts-vendor','fonts','natural-voices','welcome-art'):
        for p in (ROOT/'Resources'/directory).rglob('*'):
            if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts:
                files['shared/'+p.relative_to(ROOT/'Resources').as_posix()]=p
    for p in (ROOT/'licenses').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and not p.relative_to(ROOT/'licenses').as_posix().startswith('tools/uv'):files['shared/licenses/'+p.relative_to(ROOT/'licenses').as_posix()]=p
    files['shared/NOTICE.txt']=ROOT/'NOTICE.txt'
    if any(Path(n).name.lower() in ('uv','uv.exe','uvx.exe') or n.startswith(('shared/licenses/tools/uv','tools/notices/uv')) for n in files):raise ValueError('Retired uv installer must not enter the payload.')
    # Pure Python wheel fallbacks avoid requiring a compiler on the target PC.
    # macOS/ARM native wheels must never enter a Windows package.
    for p in (ROOT/'Resources/wheels').glob('*.whl'):
        if p.name.endswith('-none-any.whl'):files['shared/wheels/'+p.name]=p
    files['shared/bin/anicanto-core.exe']=core
    notice_root=output/'notices';shutil.rmtree(notice_root,ignore_errors=True);records=notices(notice_root)
    if shared_host.is_file():
        from package_shared_studio import notices as studio_notices
        records+=studio_notices(notice_root,'x86_64-pc-windows-msvc')
    from release_notices import install as install_release_notices
    records+=install_release_notices(notice_root)
    (notice_root/'license-inventory.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    for p in notice_root.rglob('*'):
        if p.is_file():
            relative=p.relative_to(notice_root).as_posix()
            if relative.startswith('Licenses/'):
                relative='licenses/'+relative[len('Licenses/'):]
            name='shared/'+relative
            if name in files:
                if files[name].read_bytes()!=p.read_bytes():raise ValueError('conflicting-package-notice: '+name)
            else:files[name]=p
    files['LICENSE']=ROOT/'LICENSE';files['VERSION.json']=ROOT/'VERSION.json'
    validate_payload_paths(files)
    manifest={name:dict(size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for name,p in sorted(files.items())}
    payload=output/'payload.zip'
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,p in sorted(files.items()):
            # Cargo archives can retain epoch timestamps. Use deterministic ZIP metadata.
            entry=zipfile.ZipInfo(name,(2026,1,1,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED
            entry.external_attr=0o100644 << 16
            archive.writestr(entry,p.read_bytes())
    payload.with_suffix('.manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2))
    env=rust_environment('x86_64-pc-windows-msvc',CANTOSYNC_EMBEDDED_PACKAGE=str(payload),CARGO_TARGET_DIR=str(ROOT/'.build/windows/portable-target'),
             XWIN_CACHE_DIR=str(ROOT/'.build/windows/xwin-cache'))
    command=['cargo']+(['xwin'] if os.name!='nt' else [])+['build','--release','--locked','--offline','--manifest-path',str(ROOT/'windows/launcher/Cargo.toml'),'--bin','AniCanto-Windows','--target','x86_64-pc-windows-msvc']
    subprocess.run(command,env=env,check=True)
    binary=ROOT/'.build/windows/portable-target/x86_64-pc-windows-msvc/release/AniCanto-Windows.exe'
    dest=Path(os.environ['CANTOSYNC_OUTPUT_EXE']) if os.environ.get('CANTOSYNC_OUTPUT_EXE') else ROOT/'dist/AniCanto.exe';dest.parent.mkdir(parents=True,exist_ok=True)
    temporary=dest.with_suffix('.exe.partial');shutil.copy2(binary,temporary);temporary.replace(dest)
    receipt=dict(file=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),bytes=dest.stat().st_size,
                 embeddedFiles=len(files),singleExecutable=True,modelsBundled=False,windowsExecutionTested=False,
                 gpuInferenceTested=False,fullWorkflowParity=False,stage='windows-native-acceptance-pending',
                 nativeDramaSmall=False,legacySmallReadback=True,nvidiaCUDA='pinned dynamic backend; on-device speech verification required',
                 entry='tools/AniCanto-Studio.exe' if shared_host.is_file() else 'desktop.py',sharedWorker='native_worker.py -> shared/worker.py',
                 features=['welcome','basic-expert-shared-settings','batch-queue','automatic-repair','pause-resume',
                 'video-preview','timeline','script-editor','role-references','per-line-retakes','recording-history',
                 'versioned-exports','local-terminal','hardware-aware-setup','bilingual-guide','about-mit-notices'])
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':build()
