"""Pinned complete Drama3 CUDA host. Q2 weights are shared with the CPU path."""
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
TOOLS=('drama-full-cuda12','drama-full-cudart12','drama-full-cuda13','drama-full-cudart13')
MARKER='drama-full-cuda-ready.json'

def cuda_version(hardware):
 # CUDA 12.4 predates Blackwell. The matching 13.3 bundle includes that architecture.
 names=' '.join([str(hardware.get('acceleratorName',''))]+[str(a.get('name',a.get('Name',''))) for a in hardware.get('displayAdapters',[])])
 return '13' if re.search(r'Blackwell|\bRTX\s*(?:50\d\d|PRO\s*\d+)|\b[BR]200\b',names,re.I) else '12'

def components(root,hardware):
 rows=json.loads((HERE/'native-tools.json').read_text());version=cuda_version(hardware);result=[]
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
 output=result.stdout+'\n'+result.stderr;(a/'device-probe.log').write_text(output,encoding='utf-8')
 if result.returncode or not any(line.strip().startswith('CUDA:') for line in result.stdout.splitlines()):raise RuntimeError('CUDA device check failed. Update the NVIDIA driver or select CPU. See '+str(a/'device-probe.log'))
 from atomic_files import write_json
 write_json(marker,dict(runtimeTool=runtime_id,cudartTool=cudart_id,deviceProbePassed=True,speechInferencePassed=False,memory=memory,cudaVersion=version))
 return dict(runtimeTool=runtime_id,cudartTool=cudart_id,memory=memory)
