"""Verify the delivered PE embeds the exact current, hashed desktop payload."""
import hashlib,json,mmap,struct,subprocess,zipfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from pe_icons import verify_icon
version=json.loads((ROOT/'VERSION.json').read_text())['version']
folder=ROOT/'.build/windows/release'/version
exe=Path(os.environ.get('CANTOSYNC_VERIFY_EXE',str(ROOT/'dist/AniCanto.exe')));payload=folder/'payload.zip';manifest=json.loads(payload.with_suffix('.manifest.json').read_text())
with exe.open('rb') as source,mmap.mmap(source.fileno(),0,access=mmap.ACCESS_READ) as pe:
 assert pe[:2]==b'MZ'
 offset=struct.unpack_from('<I',pe,0x3c)[0]
 assert pe[offset:offset+4]==b'PE\0\0'
 assert struct.unpack_from('<H',pe,offset+4)[0]==0x8664
 optional=offset+24;assert struct.unpack_from('<H',pe,optional)[0]==0x20b
 assert struct.unpack_from('<H',pe,optional+68)[0]==2 # Windows GUI subsystem
 launcher_icon=verify_icon(pe,(ROOT/'studio/src-tauri/icons/icon.ico').read_bytes())
 embedded=pe.find(payload.read_bytes());assert embedded>=0,'EXE does not embed this exact package'
with zipfile.ZipFile(payload) as archive:
 assert set(archive.namelist())==set(manifest)
 assert len({name.casefold() for name in manifest})==len(manifest),'Windows case-insensitive path collision'
 for name,row in manifest.items():
  data=archive.read(name)
  assert len(data)==row['size'] and hashlib.sha256(data).hexdigest()==row['sha256'],name
  assert '..' not in Path(name).parts and not Path(name).is_absolute()
  assert ':' not in name and '\\' not in name and all(part and part not in ('.','..') and not part.endswith((' ','.')) for part in name.split('/')),'Launcher rejects this Windows package path: '+name
  assert not name.endswith(('.dylib','.safetensors','.mkv','.mp4'))
  assert '__pycache__' not in name
  if name.endswith('.whl'):assert name.endswith('-none-any.whl'),name
  if (name.endswith('.py') and name.count('/')==0) or name=='bootstrap.ps1':
   assert data==(ROOT/'windows'/name).read_bytes(),'Stale production module: '+name
 assert not any(Path(name).name.lower() in ('uv','uv.exe','uvx.exe') for name in manifest),'Retired installer found'
 assert 'app.py' not in manifest and 'jobs.py' not in manifest and 'studio.py' not in manifest
 for name in ('tools/AniCanto-Studio.exe','studio/backend.py','tools/AniCanto-helper.exe','tools/audiocpp_server.exe','shared/python-installer.json','shared/python-bootstrap.ps1','shared/runtime_installer.py','shared/bin/anicanto-core.exe',
              'shared/normal_mode.py','shared/model_switch.py','shared/license-inventory.json',
              'shared/worker.py','shared/take_reuse.py','shared/secondary_speech.py','shared/project_edit.py',
              'shared/fonts/NotoSansCJKtc-Regular.otf','shared/natural-voices/catalog.json'):
  assert name in manifest,name
 assert archive.read('studio/backend.py')==(ROOT/'studio/backend.py').read_bytes()
 host=archive.read('tools/AniCanto-Studio.exe')
 host_icon=verify_icon(host,(ROOT/'studio/src-tauri/icons/icon.ico').read_bytes())
 assert host==(ROOT/'studio/src-tauri/target/x86_64-pc-windows-msvc/release/anicanto-studio.exe').read_bytes()
 assert (ROOT/'studio/web/assets/interface-manifest.json').read_bytes() in host,'Windows host does not embed the current common interface manifest'
 assert len([name for name in manifest if name.startswith('shared/welcome-art/welcome-')])==36
 # The production code in the package is the current shared Mac baseline.
 for name,row in manifest.items():
  if name.startswith('shared/') and name.endswith('.py') and name.count('/')==1:
   assert hashlib.sha256((ROOT/'Resources'/name.split('/',1)[1]).read_bytes()).hexdigest()==row['sha256'],name
receipts=dict(singleFile=str(exe),sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),bytes=exe.stat().st_size,
 peMachine='x86_64',subsystem='Windows GUI',embeddedPayloadOffset=embedded,verifiedFiles=len(manifest),
 exactCurrentDesktop=True,exactSharedMacWorker=True,macNativeWheelsExcluded=True,legacyPipelineExcluded=True,
 welcomeCovers=36,launcherIcon=launcher_icon,studioIcon=host_icon,modelsBundled=False,windowsExecuted=False,gpuInferenceTested=False)
(folder/'package-verification.json').write_text(json.dumps(receipts,indent=2)+'\n')
print(json.dumps(receipts,indent=2))
