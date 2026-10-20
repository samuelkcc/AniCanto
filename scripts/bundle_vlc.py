"""Bundle a local official arm64 VLC distribution; relocate all load commands."""
from pathlib import Path
import os,shutil,subprocess

def bundle(resources,root):
    source=Path(os.environ.get('CANTO_VLC_APP','/Applications/VLC.app'))/'Contents/MacOS'
    if not (source/'lib/libvlc.dylib').exists():raise RuntimeError('Build requires an official arm64 VLC.app (CANTO_VLC_APP). End users do not need VLC installed.')
    target=resources/'vlc'
    for name in ('lib','plugins'):
        if (target/name).exists():shutil.rmtree(target/name)
        shutil.copytree(source/name,target/name,symlinks=True,dirs_exist_ok=True)
    fonts=target/'fonts';fonts.mkdir(parents=True,exist_ok=True)
    shutil.copy2(root/'Resources/fonts/NotoSansCJKtc-Regular.otf',fonts/'NotoSansCJKtc-Regular.otf')
    licenses=resources/'Licenses/VLC';licenses.mkdir(parents=True,exist_ok=True)
    shutil.copy2(root/'Resources/fonts/LICENSE',licenses/'Noto-OFL.txt')
    shutil.copy2(root/'Resources/VLC-COPYING.txt',licenses/'VLC-COPYING.txt')
    (licenses/'SOURCE.txt').write_text('VLC 3.x / libVLC, VideoLAN: https://www.videolan.org/vlc/\nSource: https://code.videolan.org/videolan/vlc\nBinary redistributed from official VLC.app. Noto CJK: https://github.com/notofonts/noto-cjk (SIL OFL).\n')
    for p in target.rglob('*.dylib'):
        if p.is_symlink():continue
        text=subprocess.check_output(['/usr/bin/otool','-L',str(p)],text=True)
        for line in text.splitlines()[1:]:
            dep=line.strip().split(' (')[0]
            if dep.startswith('@rpath/'):
                new='@loader_path/'+('../lib/' if p.parent.name=='plugins' else '')+Path(dep).name
                subprocess.run(['/usr/bin/install_name_tool','-change',dep,new,str(p)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(p)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
