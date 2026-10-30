"""One-click native Windows deployment, pinned models, isolated tools and reuse."""
import argparse,hashlib,json,os,shutil,subprocess,sys,time,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
SHARED=HERE/'shared' if (HERE/'shared').is_dir() else HERE.parent/'Resources'
sys.path.insert(0,str(SHARED))
from gpu import data_root,hardware_snapshot,recommended,adapters,amd_supported,vendor
from install import env_python,install_torch,extract_source
from downloads import download,sha256
from runtime_installer import ensure_env,pip_command,repair_command,clean_environment

def emit(message,**extra):print(json.dumps(dict(stage='Windows setup',message=message,**extra),ensure_ascii=False),flush=True)
def call(args):
 from runtime_progress import stream_command
 return stream_command(args,env=clean_environment(data_root()))
def catalog():
 from model_catalog import catalog as common
 rows=common()
 native=json.loads((HERE/'native-models.json').read_text())
 by_id={r['id']:r for r in rows};by_id.update({r['id']:r for r in native})
 for r in by_id.values():
  if r.get('engine','').startswith('gpt-'):r=dict(r,nativeFormat='pytorch');by_id[r['id']]=r
  if r.get('engine')=='whisper':r=dict(r,nativeFormat='ctranslate2');by_id[r['id']]=r
  if r.get('engine') in ('voxcpm2','wsyue'):
   r=dict(r,nativeFormat='pytorch',legacy=r.get('legacy') or 'models/voice-variants/'+r['id']);by_id[r['id']]=r
 return list(by_id.values())
def folder(root,row):return root/row.get('legacy','models/variants/'+row['id'])
def complete(root,row):
 return all((folder(root,row)/f['path']).is_file() and (folder(root,row)/f['path']).stat().st_size==f['size'] for f in row['files'])
def reuse_roots(row):
 if row.get('engine')!='ollama':return []
 roots=[Path.home()/'.ollama/models']
 if os.environ.get('OLLAMA_MODELS'):roots.insert(0,Path(os.environ['OLLAMA_MODELS']))
 return roots

def available(root,row):return complete(root,row) or any(complete(base.parent.parent,dict(row,legacy=str(base))) for base in reuse_roots(row))

def plan(engine='drama3',hardware=None,allow_cpu_drama=False,backend='auto',requested=None,drama_backend='auto'):
 from studio_core import call as core
 root=data_root();rows=catalog();installed=[r['id'] for r in rows if r.get('nativeFormat') and available(root,r)]
 # Keep a verified model-specific CPU fallback usable after a CUDA speech
 # failure; refreshing the welcome page must not force a redeploy loop.
 requested_drama_backend=drama_backend
 native_version=drama_backend[-2:] if drama_backend in ('cuda12','cuda13') else None
 if native_version:drama_backend='cuda'
 if drama_backend=='auto' and backend not in ('nvidia','cuda'):
  try:
   previous=json.loads((root/'drama3-windows-ready.json').read_text())
   from setup_readiness import verified
   completed=json.loads((root/'native-ready.json').read_text()) if (root/'native-ready.json').is_file() else {}
   cpu_verified=(verified(completed) and completed.get('engine')==engine=='drama3'
                 and completed.get('voiceBackend')=='cpu' and previous.get('variant')==completed.get('roles',{}).get('voice'))
   if previous.get('backend')=='cpu' and previous.get('speechInferencePassed') and (previous.get('cudaFailure') or cpu_verified):drama_backend='cpu'
  except (OSError,ValueError):pass
 from gpu import planning_hardware
 from drama_cuda import capable
 h=hardware or planning_hardware();h=dict(h,nativeDramaCUDA=True,nativeWorkflowVersion=1,nativeDramaSmallCPU=(HERE/'tools/audiocpp_small_server.exe').is_file(),nativeDramaSmallCUDA=capable())
 if hardware is None and backend!='auto':h['backend']=dict(nvidia='cuda',amd='rocm').get(backend,'cpu')
 if native_version:
  from drama_full_cuda import validate_version
  validate_version(h,native_version)
  h['nativeDramaRuntimeVersion']=native_version
 if h.get('backend') in ('unprobed',None):h['backend']='cpu'
 try:selected=json.loads((root/'model-selections.json').read_text())
 except (OSError,ValueError):selected={}
 result=core('deployment',hardware=h,engine=engine,models=rows,installedModels=installed,selectedModels=selected,requestedModels=requested or {},singleModelPerCategory=True,allowDramaCPU=allow_cpu_drama,dramaBackend=drama_backend)
 h=result.get('hardware',h)
 if native_version:
  result['dramaBackend']=requested_drama_backend
  for preset in result.get('qualityPresets',[]):
   if preset.get('plan',{}).get('voiceBackend')=='cuda':preset['plan']['dramaBackend']=requested_drama_backend
 result['setupBackend']={'cuda':'nvidia','rocm':'amd'}.get(h.get('backend'),'cpu')
 result['requestedDramaBackend']=requested_drama_backend
 from memory_plan import pools
 from drama_full_cuda import components,ready as cuda_ready,deployment_hardware
 h=deployment_hardware(root,h) if result.get('engine')=='drama3' and result.get('voiceBackend')=='cuda' else h
 classifier=next(r for r in rows if r['id']=='audio-classifier-native')
 def enrich(value):
  if not value.get('downloads'):return
  if not any(r['id']==classifier['id'] for r in value['downloads']):
   value['downloads'].append(dict(id=classifier['id'],title=classifier['title'],bytes=classifier['bytes'],installed=available(root,classifier),purposeKey='audio-classification'))
  value['modelDownloadBytes']=sum(r.get('bytes',0) for r in value['downloads'] if not r.get('installed'))
  value['tools']=components(root,h) if value.get('engine')=='drama3' and value.get('voiceBackend')=='cuda' else []
  value['toolDownloadBytes']=sum(r['bytes'] for r in value['tools'] if not r['installed'])
  value['totalDownloadBytes']=value['modelDownloadBytes']+value['toolDownloadBytes']
  value['memoryPools']=pools(value)
 enrich(result)
 for preset in result.get('qualityPresets',[]):enrich(preset.get('plan') or {})
 from setup_inventory import inventory
 result['inventory']=inventory(root,rows,result['downloads'])+result.get('tools',[])
 result['storage']=str(root);result['requestedModels']=requested or {}
 ready_file=root/'native-ready.json'
 try:ready=json.loads(ready_file.read_text())
 except (OSError,ValueError):ready={}
 from setup_readiness import keep_verified_visual,status
 keep_verified_visual(result,ready)
 readiness=status(result,ready,(root/'setup-invalidated.json').exists(),not result.get('tools') or cuda_ready(root,require_speech=True))
 result['setupReady']=readiness['ready'];result['setupStatus']=readiness
 try:
  verified=json.loads((root/'drama3-windows-ready.json').read_text())
  if result.get('engine')=='drama3' and verified.get('variant')==result['roles'].get('voice') and verified.get('speechInferencePassed'):
   result['verifiedVoiceBackend']=verified.get('backend','cpu')
   result['voiceFallbackReason']=verified.get('cudaFailure')
   result['warnings']=[w for w in result['warnings'] if w!='native-drama-small-cuda-planned']
 except (OSError,ValueError):pass
 return result
def environment(name,backend=None,cuda_index=None):
 from runtime_progress import step
 run=lambda phase,operation,*args,**kwargs:step(emit,name,phase,operation,*args,**kwargs)
 emit('Checking existing '+name+' runtime',setupStep='runtime')
 python=env_python(name)
 requirements=HERE/f'requirements-{name}.lock'
 # Check the package first. Recreating Python cannot repair missing app files.
 if not requirements.is_file():raise RuntimeError('App runtime requirements are missing. Close the app and reopen the current portable EXE. Keep downloaded models.')
 if not python.is_file():run('Preparing private Python',ensure_env,data_root(),python.parent.parent)
 if backend=='nvidia' and cuda_index is None:
  from gpu import planning_hardware
  from hardware_runtimes import nvidia
  hardware=run('Detecting the GPU runtime',planning_hardware)
  profile=nvidia(hardware.get('acceleratorName',''),hardware.get('cudaComputeCapability'),hardware.get('cudaDriverVersion'),hardware.get('selectedTorchIndex'))
  cuda_index=profile['torchIndex']
  if cuda_index=='cpu':raise ValueError('This NVIDIA GPU is not covered by the pinned CUDA runtimes. Choose CPU.')
 identity=hashlib.sha256(requirements.read_bytes()+str([backend,cuda_index]).encode()).hexdigest()
 stamp=data_root()/f'{name}-runtime-ready.json'
 from runtime_health import missing,probe as imports,damaged,state,backend_matches,backend_version
 stamp.unlink(missing_ok=True)
 try:absent=run('Checking installed package versions',missing,python,requirements)
 except (OSError,subprocess.CalledProcessError):
  run('Repairing private Python',ensure_env,data_root(),python.parent.parent,recreate=True)
  absent=run('Checking installed package versions',missing,python,requirements)
 backend_missing=False
 if backend:
  packages=run('Checking installed GPU packages',state,python)['packages']
  backend_missing=not backend_matches(packages,backend,cuda_index)
  if backend_missing:
   run('Installing GPU or CPU runtime components',install_torch,python,backend,
       repair=any(n in packages for n in ('torch','torchaudio')),
       packages=[n for n in ('torch','torchaudio') if packages.get(n)!=backend_version(backend,cuda_index)],cuda_index=cuda_index)
  versions=json.loads(run('Reading verified runtime versions',subprocess.check_output,
   [str(python),'-c','import importlib.metadata as m,json; print(json.dumps([m.version("torch"),m.version("torchaudio")]))'],
   text=True,timeout=60,env=clean_environment(data_root())))
  constraints=data_root()/f'{name}-torch-constraints.txt';constraints.write_text('torch=='+versions[0]+'\ntorchaudio=='+versions[1]+'\n')
 command=pip_command(python,data_root(),'install','--only-binary',':all:','--find-links',SHARED/'wheels','--find-links',HERE/'wheels')
 if backend:command+=['-c',constraints]
 if name in ('analysis','gpt'):command+=['--no-deps']
 command+=['-r',requirements]
 if absent:
  emit('Installing missing or incompatible '+name+' runtime components',setupStep='runtime',missingPackages=absent,backendChange=bool(backend_missing))
  run('Installing missing runtime packages',call,command)
 else:emit('Reusing installed '+name+' runtime; checking imports',setupStep='verify')
 try:run('Checking runtime imports',imports,python,name)
 except subprocess.CalledProcessError:
  broken=run('Checking damaged package files',damaged,python,requirements,backend)
  if not broken:raise RuntimeError(name+' import check failed but package files are intact. No healthy packages were reinstalled.')
  if backend and any(p in ('torch','torchaudio') for p in broken):
   run('Repairing damaged GPU packages',install_torch,python,backend,repair=True,packages=[p for p in broken if p in ('torch','torchaudio')],cuda_index=cuda_index)
  from mac_runtime import requirements as pins
  expected=pins(requirements);broken=[p for p in broken if p not in ('torch','torchaudio')] if backend else broken
  if broken:run('Repairing damaged runtime packages',call,repair_command(python,data_root(),broken,expected,links=[SHARED/'wheels',HERE/'wheels'],constraints=constraints if backend else None))
  run('Checking runtime imports',imports,python,name)
 if run('Verifying installed package versions',missing,python,requirements):raise ValueError(name+' runtime packages remain incomplete.')
 if name in ('analysis','gpt'):
  from runtime_exclusions import cleanup_command
  cleanup=cleanup_command(data_root(),python,name,run('Checking runtime package inventory',state,python)['packages'])
  if cleanup:run('Removing unused runtime components',call,cleanup)
 stamp.write_text(json.dumps(dict(identity=identity,backend=backend,python=str(python))))
 return python

def extract_zip(archive,target,suffix=None,runtime_only=False):
 target.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for f in z.infolist():
   destination=(target/f.filename).resolve()
   if not destination.is_relative_to(target.resolve()) or (f.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe tool archive path.')
  for f in z.infolist():
   legal=Path(f.filename).name.upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE','EULA','AUTHORS','COPYRIGHT'))
   selected=(Path(f.filename).name==f.filename and (f.filename.endswith('.dll') or f.filename=='audiocpp_server.exe')) if runtime_only else suffix is None or f.filename.endswith(suffix)
   if selected or legal:z.extract(f,target)

def tool(name):
 root=data_root();row=json.loads((HERE/'native-tools.json').read_text())[name]
 target=root/'tools'/name;marker=target/'verified.json'
 if marker.is_file():
  try:receipt=json.loads(marker.read_text())
  except (OSError,ValueError):receipt={}
  files=receipt.get('files',{})
  intact=bool(files) and all((target/n).is_file() and (target/n).stat().st_size==v.get('bytes') and (not row.get('extractRuntime') or v.get('sha256')==sha256(target/n)) for n,v in files.items())
  if receipt.get('sha256')==row['sha256'] and (intact if row.get('requiredFiles') else bool(list(target.rglob(name+'.exe')))):return target
 archive=root/'downloads'/(name+'-'+row['sha256'][:12]+'.zip')
 emit('Download / verify '+name,downloadBytes=row['size']);download(row['url'],archive,row['sha256'],row['size'])
 extract_zip(archive,target,row.get('extractSuffix'),row.get('extractRuntime',False))
 if row.get('requiredFiles') and not all((target/n).is_file() for n in row['requiredFiles']):raise ValueError('Tool archive is incomplete: '+name)
 receipt=dict(row,files={p.relative_to(target).as_posix():dict(bytes=p.stat().st_size,sha256=sha256(p)) for p in target.rglob('*') if p.is_file() and p.suffix in ('.dll','.exe')})
 marker.write_text(json.dumps(receipt));return target

def install_model(row):
 if row.get('retired'):raise ValueError('This model is retired and cannot be downloaded.')
 if row.get('licenseReviewRequired'):raise ValueError('This model conversion has no confirmed license. Choose a reviewed variant.')
 emit('Checking model: '+row['title'],setupStep='models')
 root=data_root();target=folder(root,row)
 from model_licenses import install_notices
 install_notices(row,target)
 for i,f in enumerate(row['files']):
  emit(f"{row['title']} · {i+1}/{len(row['files'])} · {f['path']}")
  p=target/f['path']
  if not p.exists() and row.get('engine')=='ollama' and 'content' not in f:
   for cache in reuse_roots(row):
    old=cache/f['path']
    if old.is_file() and old.stat().st_size==f['size'] and sha256(old)==f['sha']:
     p.parent.mkdir(parents=True,exist_ok=True)
     try:os.link(old,p)
     except OSError:shutil.copy2(old,p)
     emit('Reused verified local model: '+f['path']);break
  if 'content' in f:
   raw=f['content'].encode();assert hashlib.sha256(raw).hexdigest()==f['sha'];p.parent.mkdir(parents=True,exist_ok=True)
   temp=p.with_suffix('.partial');temp.write_bytes(raw);temp.replace(p)
  else:
   url=f.get('url') or f"https://huggingface.co/{row['repo']}/resolve/{row['revision']}/{f['path']}"
   download(url,p,f['sha'],f['size'])
 ready=root/'model-ready';ready.mkdir(exist_ok=True)
 (ready/(row['id'].replace(':','-')+'.json')).write_text(json.dumps(dict(id=row['id'],revision=row['revision'],nativeFormat=row.get('nativeFormat'))))
 from model_ownership import mark_available
 mark_available(root,row)
 emit('Model files verified: '+row['title'],modelComplete=row['id'])

def verify_speech_probe(python,path):
 # Setup runs in the minimal UI environment. Inspect generated audio in the
 # verified worker environment where soundfile is an explicit dependency.
 command=[str(python),'-I','-c',"import json,soundfile as sf,sys; i=sf.info(sys.argv[1]); print(json.dumps(dict(frames=i.frames,sampleRate=i.samplerate,channels=i.channels)))",str(path)]
 raw=subprocess.check_output(command,text=True,timeout=60,env=clean_environment(data_root()))
 info=json.loads(raw)
 if not isinstance(info,dict) or not isinstance(info.get('frames'),int) or info['frames']<2400 or not info.get('sampleRate',0):
  raise ValueError('Native speech probe was not completed.')
 return info

def probe_runtime(python,backend):
 device='cuda' if backend in ('nvidia','amd') else 'cpu'
 result=subprocess.check_output([str(python),str(HERE/'gpu.py'),'--probe','gpt','--device',device],text=True,env=dict(os.environ,PYTHONUTF8='1'))
 return json.loads(result.strip().splitlines()[-1])

def setup(engine='drama3',backend='auto',allow_cpu_drama=False,requested=None,drama_backend='auto'):
 root=data_root();names=['model-selections.json','native-ready.json','setup-invalidated.json','drama3-windows-ready.json','drama-full-cuda-ready.json']
 prior={name:(root/name).read_bytes() if (root/name).is_file() else None for name in names}
 try:return _setup(engine,backend,allow_cpu_drama,requested,drama_backend)
 except BaseException:
  for name,data in prior.items():
   path=root/name
   if data is None:path.unlink(missing_ok=True)
   else:
    temp=path.with_suffix('.restore');temp.write_bytes(data);temp.replace(path)
  raise

def _setup(engine='drama3',backend='auto',allow_cpu_drama=False,requested=None,drama_backend='auto'):
 emit('Checking hardware and existing installation',setupStep='check')
 if sys.platform!='win32':raise RuntimeError('Run native setup on Windows 11 x64.')
 from studio_core import verify
 verify()  # Fail before runtime installation or ready-receipt invalidation.
 root=data_root();root.mkdir(parents=True,exist_ok=True)
 (root/'native-ready.json').unlink(missing_ok=True)
 (root/'setup-invalidated.json').write_text(json.dumps(dict(reason='setup-in-progress')))
 if backend=='auto':
  advice=plan(engine,requested=requested,drama_backend=drama_backend)
  backend=advice.get('setupBackend') or advice.get('hardware',{}).get('suggestedSetupBackend') or recommended(adapters())
  if not advice.get('canDeployModels'):
   alternative=next((p for p in advice.get('qualityPresets',[]) if p.get('available') and p.get('id')==advice.get('recommendedPreset')),None)
   if alternative and not requested:
    emit('Available GPU memory cannot fit the requested combination; applying the compatible recommended model plan.')
    engine=alternative['engine'];requested=alternative['requestedModels'];backend=alternative['plan'].get('setupBackend',backend)
   elif backend!='cpu':
    cpu=plan(engine,backend='cpu',requested=requested,drama_backend='cpu')
    if cpu.get('canDeployModels'):backend='cpu';drama_backend='cpu';emit('Available GPU memory cannot fit this plan. Using the same selected models on CPU.')

 if engine=='cosyvoice3':
  from engine_availability import require
  require(engine,root,sys.platform,backend)
 if backend=='intel':backend='cpu';emit('This native voice stack uses CPU on Intel; hardware video export remains available.')
 if backend=='amd' and not any(vendor(r)=='amd' and amd_supported(r.get('Name','')) for r in adapters()):raise ValueError('Use CPU for this Radeon; the selected native ROCm build does not support this model.')
 worker=environment('worker')
 analysis_fallback=None
 try:
  analysis=environment('analysis',backend);probe=probe_runtime(analysis,backend)
 except (RuntimeError,ValueError,OSError,subprocess.SubprocessError) as error:
  analysis_fallback=str(error)[-1000:]
  if backend=='cpu':raise
  fallback_ok=False
  if backend=='nvidia':
   from gpu import planning_hardware
   from hardware_runtimes import nvidia
   detected=planning_hardware();profile=nvidia(detected.get('acceleratorName',''),detected.get('cudaComputeCapability'),detected.get('cudaDriverVersion'),detected.get('selectedTorchIndex'))
   if profile['torchIndex']=='cu130':
    emit('CUDA 13 runtime check failed; trying the compatible CUDA 12.8 profile.')
    try:
     analysis=environment('analysis','nvidia',cuda_index='cu128');probe=probe_runtime(analysis,'nvidia');fallback_ok=True
    except (RuntimeError,ValueError,OSError,subprocess.SubprocessError) as fallback_error:emit('CUDA 12 runtime check failed: '+str(fallback_error)[-300:])
  if not fallback_ok:
   emit('GPU runtime check failed; continuing with CPU: '+str(error)[-400:])
   backend='cpu';drama_backend='cpu';analysis=environment('analysis','cpu');probe=probe_runtime(analysis,'cpu')
   if 'detected' not in locals():
    from gpu import planning_hardware
    detected=planning_hardware()
   (root/'gpu-runtime-selection.json').write_text(json.dumps(dict(name=detected.get('acceleratorName'),driver=detected.get('cudaDriverVersion'),torchIndex='cpu',kernelPassed=False,fallbackReason=analysis_fallback)))
 h=hardware_snapshot();h.update(backend=probe['backend'],acceleratorMemoryGB=probe['memoryGB'],acceleratorFreeMemoryGB=probe.get('freeMemoryGB'),acceleratorName=probe.get('name',''),nativeWorkflowVersion=1)
 if probe.get('computeCapability'):h['cudaComputeCapability']=probe['computeCapability'][0]+probe['computeCapability'][1]/10
 if probe.get('torchIndex'):
  detected=next((x for x in h.get('cudaCapabilities',[]) if x['name'].upper()==h.get('acceleratorName','').upper()),{})
  h['selectedTorchIndex']=probe['torchIndex'];h['cudaDriverVersion']=detected.get('driverVersion')
  (root/'gpu-runtime-selection.json').write_text(json.dumps(dict(name=h.get('acceleratorName'),driver=h.get('cudaDriverVersion'),torchIndex=probe['torchIndex'],kernelPassed=True,fallbackReason=analysis_fallback)))
 deployment=plan(engine,h,allow_cpu_drama,requested=requested,drama_backend=drama_backend)
 # Use the exact normalized hardware that selected the downloaded tools.
 h=deployment.get('hardware',h)
 if deployment['blockers']:raise ValueError('; '.join(deployment['blockers']))
 emit('Deployment plan',deployment=deployment)
 ffdir=tool('ffmpeg');tool('ollama')
 ffmpeg=next(ffdir.rglob('ffmpeg.exe'));ffprobe=next(ffdir.rglob('ffprobe.exe'))
 os.environ['PATH']=str(ffmpeg.parent)+os.pathsep+os.environ.get('PATH','')
 all_rows={r['id']:r for r in catalog()}
 required=[all_rows[r['id']] for r in deployment['downloads']]
 # Audio classification is independent of transcription and always included.
 classifier=all_rows['audio-classifier-native']
 if classifier not in required:required.append(classifier)
 space=sum(r['bytes'] for r in required if not complete(root,r))
 if shutil.disk_usage(root).free<space+int(deployment.get('toolDownloadBytes',0))*3+8_000_000_000:raise ValueError('Not enough disk space for models plus runtime workspace (8 GB reserve).')
 for index,row in enumerate(required):
  emit('Model '+str(index+1)+' / '+str(len(required))+' · '+row['title'],setupStep='models',modelProgress=dict(index=index+1,total=len(required),title=row['title']))
  install_model(row)
 asr=environment('asr',backend)
 selected=deployment['roles'];selected['asr']='asr-native-1.7b'
 selected[deployment['engine']]=selected['voice']
 text_row=all_rows[selected['text']]
 text_alias=selected['text']+'-canto-'+text_row['manifestSHA256'][:12]
 original=root/'models/ollama/manifests/registry.ollama.ai/library/qwen3.5'/selected['text'].split(':',1)[1]
 shutil.copy2(original,original.with_name(text_alias.split(':',1)[1]))
 (root/'model-selections.json').write_text(json.dumps(selected))
 emit('Loading and verifying installed models. First load can take longer.',setupStep='verify')
 call([analysis,HERE/'setup_checks.py','analysis',root])
 (root/'separator-windows-ready.json').write_text(json.dumps(dict(backend=backend,modelLoadPassed=True)))
 (root/'separator-ready.json').write_text(json.dumps(dict(nativeFormat='pytorch',backend=backend)))
 call([asr,HERE/'setup_checks.py','asr',root])
 (root/'asr-windows-ready.json').write_text(json.dumps(dict(backend=backend,modelLoadPassed=True)))
 (root/'asr-ready.json').write_text(json.dumps(dict(variant='asr-native-1.7b',nativeFormat='pytorch')))
 (root/'speech-ready.json').write_text(json.dumps(dict(variant=selected['speech'],nativeFormat='ctranslate2')))
 chosen=deployment['engine']
 if chosen.startswith('gpt-sovits'):
  gpt=environment('gpt',backend)
  from dubbing_setup import REV,SOURCE_SHA
  extract_source(dict(revision=REV,sha256=SOURCE_SHA,url=f'https://codeload.github.com/RVC-Boss/GPT-SoVITS/tar.gz/{REV}'),root/'gpt-sovits'/REV)
  version='v2ProPlus' if chosen=='gpt-sovits-v2' else 'v4'
  call([gpt,HERE/'native_tts.py','--prepare-gpt',root,'--gsv-version',version])
  call([gpt,HERE/'native_tts.py','--load-check','gpt','--root',root,'--gsv-version',version])
  marker=root/'gpt-windows-ready.json';previous=json.loads(marker.read_text()) if marker.is_file() else {}
  versions=list(dict.fromkeys(previous.get('modelVersions',[])+[version]))
  marker.write_text(json.dumps(dict(engine='gpt',backend=backend,modelVersion=version,modelVersions=versions,speechVersions=previous.get('speechVersions',[]),modelLoadPassed=True,speechInferencePassed=False)))
 elif chosen=='cosyvoice3':
  cosy=environment('cosy',backend)
  sources=json.loads((HERE/'models.json').read_text())
  extract_source(sources['cosy-source'],root/'sources/cosy')
  extract_source(sources['matcha-source'],root/'sources/cosy/third_party/Matcha-TTS')
  call([cosy,HERE/'native_tts.py','--load-check','cosy','--root',root])
  (root/'cosy-windows-ready.json').write_text(json.dumps(dict(backend=backend,modelLoadPassed=True,speechInferencePassed=False)))
 elif chosen in ('voxcpm2','wsyue'):
  local=environment('local',backend)
  call([local,HERE/'setup_checks.py',chosen,root])
  marker=root/'local-windows-ready.json';previous=json.loads(marker.read_text()) if marker.is_file() else {}
  if previous.get('backend')!=backend:previous={} # A different Torch/device runtime needs its own probes.
  (root/'local-windows-ready.json').write_text(json.dumps(dict(backend=backend,engines=list(dict.fromkeys(previous.get('engines',[])+[chosen])),verifiedEngines=[e for e in previous.get('verifiedEngines',[]) if e!=chosen],variants=dict(previous.get('variants',{}),**{chosen:selected['voice']}),modelLoadPassed=True,speechInferencePassed=False)))
 elif chosen=='drama3':
  voice_backend=deployment.get('voiceBackend','cpu');fallback_reason=None
  from drama_full_cuda import checked_deployment
  voice_backend,fallback_reason=checked_deployment(root,h,deployment.get('voiceMemory') or {},worker,voice_backend,emit)
  if voice_backend=='cpu' and fallback_reason:
   drama_backend='cpu';deployment['voiceMemory']=dict(deployment.get('voiceMemory') or {},backend='cpu',gpuGB=0,cpuExpertLayers=0,contextLength=4096)
  (root/'drama3-windows-ready.json').write_text(json.dumps(dict(backend=voice_backend,modelLoadPassed=True,nativeFormat='gguf',variant=selected['voice'],memory=deployment.get('voiceMemory'),cudaFailure=fallback_reason)))
 from native_service import service,request as model_request
 with service(root):
  test=model_request(11445,'/api/generate',dict(model=text_alias,prompt='Reply with OK.',stream=False,think=False,keep_alive=0,options=dict(num_predict=8)),1200)
  if not test.get('response','').strip():raise ValueError('Native text model did not return a test response.')
 # Probe the exact speech adapter used by production, not just its imports.
 engine_runtime=gpt if chosen.startswith('gpt-sovits') else env_python('cosy') if chosen=='cosyvoice3' else env_python('local') if chosen in ('voxcpm2','wsyue') else worker
 from natural_voices import catalog as voices
 voice=next(v for v in voices() if v['language']=='yue')
 checks=root/'checks';checks.mkdir(exist_ok=True)
 probe_cfg=dict(storage=str(root),job=str(checks),device='cuda' if backend in ('nvidia','amd') else 'cpu',drama3Backend=voice_backend if chosen=='drama3' else None,targetLanguage='yue',gsvVersion='v2ProPlus' if chosen=='gpt-sovits-v2' else 'v4',cosyModel='cosy-native-0.5b',drama3Model=selected['voice'] if chosen=='drama3' else 'drama3-native-q2',drama3Memory=deployment.get('voiceMemory'),items=[dict(profile=dict(voice,name='Native probe'),text='今日一齊出發啦。',output=str(checks/'native-voice-probe.wav'),reviewIndex=0,seed=42,targetSeconds=4)])
 if chosen=='voxcpm2':probe_cfg['voxcpmModel']=selected['voice']
 if chosen=='wsyue':probe_cfg.update(wsyueModel=selected['voice'],device='cpu')
 (checks/'native-voice-probe.wav').unlink(missing_ok=True)
 file=checks/'native-voice-probe.json';file.write_text(json.dumps(probe_cfg,ensure_ascii=False))
 call([engine_runtime,HERE/'shared_inference.py','tts' if chosen.startswith('gpt-sovits') else 'cosy' if chosen=='cosyvoice3' else chosen,file])
 verify_speech_probe(worker,checks/'native-voice-probe.wav')
 kind='gpt' if chosen.startswith('gpt-sovits') else 'cosy' if chosen=='cosyvoice3' else 'local' if chosen in ('voxcpm2','wsyue') else 'drama3'
 marker=root/(kind+'-windows-ready.json');verified=json.loads(marker.read_text());verified['speechInferencePassed']=True
 if kind=='gpt':verified['speechVersions']=list(dict.fromkeys(verified.get('speechVersions',[])+[version]))
 if kind=='local':verified['verifiedEngines']=list(dict.fromkeys(verified.get('verifiedEngines',[])+[chosen]))
 marker.write_text(json.dumps(verified))
 if kind=='drama3' and voice_backend=='cuda':
  from drama_full_cuda import MARKER,read
  cuda_receipt=read(root/MARKER,{});cuda_receipt['speechInferencePassed']=True
  (root/MARKER).write_text(json.dumps(cuda_receipt))
 receipt=dict(schemaVersion=1,analysisFallbackReason=analysis_fallback,requestedEngine=engine,engine=chosen,textModel=text_alias,backend=backend,hardware=h,ffmpeg=str(ffmpeg),ffprobe=str(ffprobe),roles=selected,voiceBackend=voice_backend if chosen=='drama3' else backend,dramaBackend=drama_backend,drama3Memory=deployment.get('voiceMemory'),cudaFailure=fallback_reason if chosen=='drama3' else None,allowDramaCPU=chosen=='drama3' and voice_backend=='cpu',modelLoadPassed=True,speechInferencePassed=True,speechQualityCertified=False,warnings=deployment['warnings'])
 (root/'native-ready.json').write_text(json.dumps(receipt,indent=2))
 (root/'setup-invalidated.json').unlink(missing_ok=True)
 emit('Native setup completed. The first conversion will validate speech and output on this PC.',ready=receipt,setupStep='ready')

if __name__=='__main__':
 from process_job import install as own_processes
 own_processes()
 parser=argparse.ArgumentParser();parser.add_argument('--drama-backend',choices=['auto','cuda','cuda12','cuda13','cpu'],default='auto');parser.add_argument('--models-json',default='{}');parser.add_argument('--engine',default='drama3');parser.add_argument('--backend',default='auto');parser.add_argument('--allow-cpu-drama',action='store_true');parser.add_argument('--plan',action='store_true');parser.add_argument('--manage',choices=['repair','redownload','remove']);parser.add_argument('--package');parser.add_argument('--kind',choices=['model','runtime','tool']);args=parser.parse_args()
 try:
  if args.manage:
   from setup_inventory import remove,RUNTIMES
   rows=catalog()
   if args.manage!='repair':remove(data_root(),args.kind,args.package,rows)
   if args.manage!='remove':
    if args.kind=='runtime':
     if args.package not in RUNTIMES:raise ValueError('Unknown runtime')
     environment(args.package,None if args.package=='worker' else (recommended(adapters()) if args.backend=='auto' else args.backend))
    elif args.kind=='tool':
     from drama_full_cuda import TOOLS
     if args.package not in ('drama-cuda','drama-cudart')+TOOLS:raise ValueError('Unknown managed tool')
     tool(args.package)
    else:install_model(next(r for r in rows if r['id']==args.package and r.get('nativeFormat')))
   emit('Component updated. Review the plan before conversion.',deployment=plan(args.engine,allow_cpu_drama=args.allow_cpu_drama,backend=args.backend,drama_backend=args.drama_backend))
  elif args.plan:emit('Deployment plan',deployment=plan(args.engine,allow_cpu_drama=args.allow_cpu_drama,backend=args.backend,drama_backend=args.drama_backend))
  else:setup(args.engine,args.backend,args.allow_cpu_drama,json.loads(args.models_json),args.drama_backend)
 except Exception as error:
  import traceback;traceback.print_exc(file=sys.stderr);emit(str(error),error=True);sys.exit(1)
