"""Pinned complete Drama3 CUDA host. Q2 weights are shared with the CPU path."""
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
TOOLS=('drama-full-cuda12','drama-full-cudart12','drama-full-cuda13','drama-full-cudart13')
MARKER='drama-full-cuda-ready.json'

def cuda_version(hardware):
 if hardware.get('nativeDramaRuntimeVersion') in ('12','13'):return hardware['nativeDramaRuntimeVersion']
 # CUDA 12.4 predates Blackwell. The matching 13.3 bundle includes that architecture.
 names=' '.join([str(hardware.get('acceleratorName',''))]+[str(a.get('name',a.get('Name',''))) for a in hardware.get('displayAdapters',[])])
 if hardware.get('gpuRuntime',{}).get('torchIndex')=='cu130':return '13'
 return '13' if re.search(r'Blackwell|\bRTX\s*(?:50\d\d|PRO\s*\d+)|\b[BR]200\b',names,re.I) else '12'

def deployment_hardware(root,hardware):
 # Torch and the native GGML server run in separate processes. A Torch
 # preference does not invalidate a verified native CUDA runtime pair.
 if hardware.get('nativeDramaRuntimeVersion') in ('12','13'):return hardware
 record=read(Path(root)/MARKER,{})
 version=record.get('cudaVersion')
 if version not in ('12','13') or not ready(root,require_speech=True):return hardware
 cc=hardware.get('cudaComputeCapability')
 if version=='12':
  names=' '.join([str(hardware.get('acceleratorName',''))]+[str(a.get('name','')) for a in hardware.get('displayAdapters',[])])
  if isinstance(cc,(int,float)) and cc>=10:return hardware
  if re.search(r'Blackwell|\bRTX\s*(?:50\d\d|PRO\s*\d+)|\b[BR]200\b',names,re.I):return hardware
 return dict(hardware,nativeDramaRuntimeVersion=version)

def components(root,hardware):
 rows=json.loads((HERE/'native-tools.json').read_text());version=cuda_version(deployment_hardware(root,hardware));result=[]
 for key in ('drama-full-cuda'+version,'drama-full-cudart'+version):
  row=rows[key];path=Path(root)/'tools'/key;receipt=read(path/'verified.json',{})
  present=receipt.get('sha256')==row['sha256'] and bool(receipt.get('files')) and all((path/n).is_file() and (path/n).stat().st_size==meta['bytes'] for n,meta in receipt.get('files',{}).items())
  result.append(dict(id=key,title='Drama 3 · NVIDIA CUDA '+row['cudaVersion'] if 'cudart' not in key else 'NVIDIA CUDA '+row['cudaVersion']+' libraries',kind='tool',bytes=row['size'],installed=present,purpose='Drama 3 NVIDIA acceleration',required=True))
 return result

def read(path,default):
 try:return json.loads(Path(path).read_text(encoding='utf-8'))
 except (OSError,ValueError):return default

def ready(root,require_speech=False):
 root=Path(root);record=read(root/MARKER,{})
 if require_speech and record.get('speechInferencePassed') is not True:return False
 if record.get('runtimeTool') not in ('drama-full-cuda12','drama-full-cuda13') or record.get('cudartTool')!='drama-full-cudart'+str(record.get('cudaVersion','')) or record.get('runtimeTool')!='drama-full-cuda'+str(record.get('cudaVersion','')):return False
 if record.get('deviceProbePassed') is not True or record.get('runtimeTool') not in TOOLS or record.get('cudartTool') not in TOOLS:return False
 rows=json.loads((HERE/'native-tools.json').read_text())
 for key in (record['runtimeTool'],record['cudartTool']):
  base=root/'tools'/key;r=read(base/'verified.json',{})
  if r.get('sha256')!=rows[key]['sha256'] or not r.get('files'):return False
  for name in rows[key]['requiredFiles']:
   p=base/name;meta=r['files'].get(name,{})
   if not p.is_file() or p.stat().st_size!=meta.get('bytes') or not meta.get('sha256'):return False
   with p.open('rb') as stream:
    if hashlib.file_digest(stream,'sha256').hexdigest()!=meta['sha256']:return False
 return True

def runtime(root):
 root=Path(root)
 if not ready(root):raise ValueError('The full Drama 3 CUDA runtime needs deployment or repair.')
 record=read(root/MARKER,{});a=root/'tools'/record['runtimeTool'];b=root/'tools'/record['cudartTool']
 return a/'audiocpp_server.exe',os.pathsep.join([str(a),str(b)]),record['memory']

def prepare(root,hardware,memory,emit):
 from native_setup import tool
 root=Path(root);version=cuda_version(hardware);runtime_id='drama-full-cuda'+version;cudart_id='drama-full-cudart'+version
 # Both archives are independently hash-verified; never mix GGML builds or CUDA majors.
 a=tool(runtime_id);b=tool(cudart_id);marker=root/MARKER;marker.unlink(missing_ok=True)
 shared=HERE/'shared' if (HERE/'shared').is_dir() else HERE.parent/'Resources'
 notices=shared/'licenses/tools/drama-full-cuda'
 if not notices.is_dir() and (HERE.parent/'licenses/tools/drama-full-cuda').is_dir():notices=HERE.parent/'licenses/tools/drama-full-cuda'
 if not notices.is_dir():raise ValueError('The full Drama CUDA distribution notices are missing from this app.')
 shutil.copytree(notices,a/'notices',dirs_exist_ok=True)
 emit('Checking the full Drama 3 NVIDIA CUDA device',setupStep='verify')
 env=dict(os.environ,PATH=os.pathsep.join([str(a),str(b),os.environ.get('PATH','')]))
 result=subprocess.run([str(a/'audiocpp_server.exe'),'--list-devices'],capture_output=True,text=True,timeout=90,env=env)
 output=result.stdout+'\n'+result.stderr
 details=dict(returnCode=result.returncode,returnCodeHex=hex(result.returncode&0xffffffff),stdout=result.stdout[-16000:],stderr=result.stderr[-16000:],cudaVersion=version,executable=str(a/'audiocpp_server.exe'))
 (a/'device-probe.log').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
 if result.returncode or not any(re.match(r'^CUDA:\d+\b',line.strip(),re.I) for line in output.splitlines()):
  reason='process-exit' if result.returncode else 'no-cuda-device-row'
  emit('Drama 3 CUDA '+version+' device check failed: '+reason+'; exit='+details['returnCodeHex']+'; '+output.strip()[-1800:],setupStep='verify',cudaProbe=details)
  raise RuntimeError('CUDA device check failed: '+reason+'; exit='+details['returnCodeHex']+'. '+output.strip()[-1000:])
 from atomic_files import write_json
 write_json(marker,dict(runtimeTool=runtime_id,cudartTool=cudart_id,deviceProbePassed=True,speechInferencePassed=False,memory=memory,cudaVersion=version))
 return dict(runtimeTool=runtime_id,cudartTool=cudart_id,memory=memory)


def checked_deployment(root,hardware,memory,worker,backend,emit):
 """Try registered native runtimes, then CPU, with actual loading each time."""
 import copy
 from native_setup import call
 checks=HERE/'setup_checks.py';errors=[]
 if backend=='cuda':
  hardware=deployment_hardware(root,hardware)
  choices=[dict(hardware)]
  cc=hardware.get('cudaComputeCapability');name=str(hardware.get('acceleratorName','')).upper()
  # The registered CUDA12 native bundle includes Pascal through Ada; it is
  # never offered as a Blackwell substitute merely because CUDA13 failed.
  older_compatible=(isinstance(cc,(int,float)) and 6.1<=cc<10) or ('RTX 40' in name and 'BLACKWELL' not in name)
  if cuda_version(hardware)=='13' and older_compatible:choices.append(dict(hardware,nativeDramaRuntimeVersion='12'))
  for candidate in choices:
   version=cuda_version(candidate)
   try:
    prepare(root,candidate,memory,emit)
    call([worker,checks,'drama3',root,'cuda'])
    return 'cuda','; '.join(errors) or None
   except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
    errors.append('CUDA '+version+': '+str(error)[-1600:]);emit('Drama 3 CUDA '+version+' did not pass: '+str(error)[-1800:])
  emit('Drama 3 GPU checks did not pass. Verifying the same full model on CPU.')
 call([worker,checks,'drama3',root,'cpu'])
 return 'cpu','; '.join(errors) or None
