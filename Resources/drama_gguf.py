"""GGUF Drama provider. Production uses the backend that passed native setup."""
import base64,io,json,os,re,socket,subprocess,sys,threading,time,urllib.request
from pathlib import Path
_active=None
_emitter=None
REQUEST_TIMEOUT_SECONDS=600
HEARTBEAT_SECONDS=10

class NativeDramaUnavailable(RuntimeError):
 """A dead/timed-out owned server must not receive the rest of the track."""
 abortVoiceTrack=True


def native_backend(root,cfg):
 backend=cfg.get('drama3Backend')
 if backend is None and sys.platform=='win32':
  try:
   receipt=json.loads((Path(root)/'drama3-windows-ready.json').read_text())
   if receipt.get('modelLoadPassed'):backend=receipt.get('backend')
  except (OSError,ValueError):pass
 backend=backend or 'cpu'
 if backend not in ('cpu','cuda') or (backend=='cuda' and sys.platform!='win32'):raise ValueError('Unavailable native Drama backend: '+backend)
 return backend

def wav_request(port,body,timeout=600):
 request=urllib.request.Request(f'http://127.0.0.1:{port}/v1/audio/speech',json.dumps(body,ensure_ascii=False).encode(),{'Content-Type':'application/json'})
 with urllib.request.urlopen(request,timeout=timeout) as response:return response.read()
class NativeDrama:
 def __init__(self,cfg):
  from voice_models import resolve
  root=Path(cfg['storage']);variant=cfg.get('drama3Model','drama3-small-iq3');folder=resolve(root,'drama3',variant)
  small=variant=='drama3-small-iq3';model=folder/('drama3-small-IQ3_XXS.gguf' if small else 'drama-3-backbone-8bit-experts-Q2_K.gguf')
  here=Path(__file__).resolve().parent
  binary=(here.parent/'tools'/('audiocpp_small_server.exe' if small else 'audiocpp_server.exe')) if sys.platform=='win32' else here/'bin/drama3-small-server'
  self.backend=native_backend(root,cfg)
  runtime_path=None;memory={}
  if self.backend=='cuda':
   if small:
    from drama_cuda import ready
    if not ready(root):raise ValueError('Drama3-small CUDA runtime needs repair in Welcome setup.')
    binary=root/'tools/drama-small-cuda/audiocpp_server.exe';runtime_path=str(binary.parent)
   else:
    from drama_full_cuda import runtime
    binary,runtime_path,memory=runtime(root)
  session_options={'fish_drama3.context_length':4096,'fish_drama3.cpu_expert_layers':0}
  if memory:
   layers=memory.get('cpuExpertLayers');context=memory.get('contextLength')
   if memory.get('policy')!='full-drama-q2-split-1' or layers not in (0,16,24,32) or context!=2048:
    raise ValueError('The full Drama CUDA memory profile needs redeployment.')
   session_options.update({'fish_drama3.context_length':context,'fish_drama3.cpu_expert_layers':layers,'fish_drama3.codec_encoder_chunk_samples':65536})
  self.memory=memory
  if not binary.is_file():raise ValueError('Native Drama server is missing from this package.')
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
  job=Path(cfg.get('job',root/'checks'));job.mkdir(parents=True,exist_ok=True)
  settings=dict(host='127.0.0.1',port=self.port,backend=self.backend,device=int(cfg.get('gpuIndex',0)),threads=min(8,max(1,(os.cpu_count() or 4)//2)),lazy_load=True,max_loaded_models=1,ui=False,models=[dict(id='drama3',family='fish_drama3',path=str(model),task='tts',mode='streaming',session_options=session_options,default_request_options=dict(max_tokens=512))])
  file=job/'native-drama-server.json';file.write_text(json.dumps(settings));log_path=job/'native-drama-server.log';self.progressPosition=log_path.stat().st_size if log_path.exists() else 0;self.log=log_path.open('a');self.emit=_emitter
  self.variant=variant;self.cfg=cfg;self.threads=settings['threads'];self.silence=folder/'silence_codes.json'
  environment=dict(os.environ)
  if runtime_path:environment['PATH']=runtime_path+os.pathsep+environment.get('PATH','')
  self.process=subprocess.Popen([str(binary),'--config',str(file),'--log','--load-progress','1'],stdout=self.log,stderr=self.log,env=environment,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0) if sys.platform=='win32' else 0)
  try:
   for _ in range(120):
    if self.process.poll() is not None:raise RuntimeError('Native Drama server exited; see native-drama-server.log')
    try:
     with urllib.request.urlopen(f'http://127.0.0.1:{self.port}/health',timeout=1) as response:
      if response.status==200:return
    except OSError:time.sleep(.25)
   raise RuntimeError('Native Drama server did not start.')
  except BaseException:self.close();raise
 def close(self):
  if getattr(self,'process',None) is not None and self.process.poll() is None:
   self.process.terminate()
   try:self.process.wait(timeout=10)
   except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
  if getattr(self,'log',None) is not None:self.log.close()

def load(cfg):
 global _active
 _active=NativeDrama(cfg);return _active

def monitored_request(model,body,emit=None):
 stop=threading.Event();started=time.monotonic();timeout=REQUEST_TIMEOUT_SECONDS
 label='Drama3-small' if model.variant=='drama3-small-iq3' else 'Drama 3'
 path=Path(model.log.name);status_path=path.with_name('native-drama-request.json')
 status=dict(state='waiting',modelVariant=model.variant,backend=model.backend,
             cpuThreads=getattr(model,'threads',None),memory=getattr(model,'memory',{}),timeoutSeconds=timeout,
             inputCharacters=len(body.get('input','')),generatedProgressAvailable=False)
 def record(state,error=None):
  status.update(state=state,elapsedSeconds=round(time.monotonic()-started,2))
  if error:status['error']=str(error)
  try:
   temp=status_path.with_suffix('.partial.json');temp.write_text(json.dumps(status));temp.replace(status_path)
  except OSError:pass
 def heartbeat():
  record('waiting')
  if emit:emit('配音',f'{label} · {model.backend.upper()} · 等待原生生成（未提供逐幀進度） · {int(time.monotonic()-started)}s / {timeout}s',nativeRequest=dict(status))
 def monitor():
  position=getattr(model,'progressPosition',0);last_heartbeat=started
  while not stop.wait(.25):
   if time.monotonic()-last_heartbeat>=HEARTBEAT_SECONDS:
    heartbeat();last_heartbeat=time.monotonic()
   try:
    with path.open(errors='replace') as stream:stream.seek(position);lines=stream.readlines();position=stream.tell();model.progressPosition=position
   except OSError:continue
   for line in lines:
    match=re.search(r'(.+?)\.weights\.upload_progress\s+([\d.]+)',line)
    phase=re.search(r'runtime.load.phase (\S+)',line)
    if emit and match:
     component=match[1].split(']')[-1].strip();value=min(1,max(0,float(match[2])))
     emit('模型載入',f'{label} · {component} · {value:.0%}',componentProgress=dict(label=label+' · '+component,fraction=value,phase='loading'))
    elif emit and phase:emit('模型載入',label+' · '+phase[1],componentProgress=dict(label=label,phase=phase[1]))
 heartbeat();thread=threading.Thread(target=monitor,daemon=True);thread.start()
 try:
  raw=wav_request(model.port,body,timeout=timeout)
  stop.set();thread.join(timeout=2);record('completed');return raw
 except (OSError,TimeoutError) as error:
  # A timed-out HTTP client does not cancel native inference. Kill this owned
  # server before another line can be submitted to its still-running request.
  cause=getattr(error,'reason',error);timed_out=isinstance(cause,TimeoutError)
  failed=timed_out or model.process.poll() is not None
  if failed:
   stop.set();thread.join(timeout=2);model.failed=True;model.close()
   record('timed-out' if timed_out else 'server-exited',error)
   if timed_out:raise NativeDramaUnavailable(f'native-drama-timeout: no complete response within {timeout}s; owned server stopped; remaining lines were not queued behind it. See native-drama-request.json and native-drama-server.log.') from error
   raise NativeDramaUnavailable('Native Drama server exited during a request; remaining lines were not queued. See native-drama-server.log.') from error
  stop.set();thread.join(timeout=2);record('failed',error);raise
 finally:stop.set();thread.join(timeout=2)

def generate(model,item,cfg):
 if getattr(model,'failed',False):raise NativeDramaUnavailable('Native Drama server is unavailable after its previous failed request.')
 import numpy as np
 import soundfile as sf
 from drama3 import complete_clauses,generation_budget,GenerationLimit,RATE,CLAUSE_STYLES,language_hint
 from voice_parameters import drama_sampling
 sampling=drama_sampling(cfg)
 text=item['text'];profile=item['profile'];chunks=[]
 pieces=complete_clauses(text) if item.get('deliveryStyle') in CLAUSE_STYLES else [text]
 trace=dict(policy='native-gguf-complete-text-2-explicit-sampling',nativeFormat='gguf',backend=model.backend,modelVariant=model.variant,sampling=sampling,status='generating',parts=[],requestedText=text,plannedParts=len(pieces),reference=profile['reference'],targetLanguage=cfg.get('targetLanguage','yue'),seed=int(item.get('seed',42)))
 cfg['_dramaLastGeneration']=trace
 for piece in pieces:
  maximum=generation_budget(piece,item.get('targetSeconds'))
  cue=language_hint(cfg.get('targetLanguage','yue'),item.get('deliveryStyle'))
  prompted=piece if item.get('deliveryStyle') in ('plain-clauses','plain-whole') else '['+cue+'] '+piece
  body=dict(model='drama3',input=prompted,voice_ref=profile['reference'],reference_text=profile.get('promptText',''),max_tokens=maximum,seed=int(item.get('seed',42)),response_format='wav',**sampling)
  if model.variant=='drama3-small-iq3':body['options']=dict(max_pause_frames='10',silence_codes=str(model.silence))
  try:raw=monitored_request(model,body,getattr(model,'emit',None))
  except NativeDramaUnavailable as error:
   trace.update(status='native-request-failed',error=str(error));raise
  audio,sr=sf.read(io.BytesIO(raw),dtype='float32',always_2d=True);audio=audio.mean(axis=1)
  if sr!=RATE:raise ValueError('Native Drama returned an unexpected sample rate.')
  chunks.append(audio);trace['parts'].append(dict(promptedText=prompted,maximumFrames=maximum,generatedSamples=len(audio),frameCountMethod='sample-count-bound'))
  trace['submittedText']=''.join(pieces[:len(trace['parts'])])
  if len(audio)>=(maximum-1)*2048:
   trace['status']='generation-limit';raise GenerationLimit(np.concatenate(chunks))
 trace['status']='completed';return np.concatenate(chunks) if chunks else np.array([],dtype=np.float32)

def synthesize(cfg,emit):
 global _active,_emitter
 from drama3 import _synthesize as shared
 _emitter=emit
 try:return shared(cfg,emit)
 finally:
  _emitter=None
  if _active is not None:_active.close();_active=None

def probe(root,variant=None,emit=None,backend=None):
 import soundfile as sf
 from io import BytesIO
 if variant is None:
  try:variant=json.loads((Path(root)/'model-selections.json').read_text()).get('voice')
  except (OSError,ValueError):pass
 cfg=dict(storage=str(root),drama3Model=variant or ('drama3-native-q2' if sys.platform=='win32' else 'drama3-small-iq3'),drama3Backend=backend)
 model=NativeDrama(cfg)
 try:
  raw=monitored_request(model,dict(model='drama3',input='你好。',max_tokens=128,seed=42),emit)
  audio,sr=sf.read(BytesIO(raw),dtype='float32')
  from fast_mode import basic_problems
  if sr!=44100 or basic_problems(audio,sr):raise ValueError('Native Drama test did not produce valid non-silent speech.')
  return dict(backend=model.backend,speechInferencePassed=True)
 finally:model.close()
