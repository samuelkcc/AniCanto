"""GGUF Drama provider. Production uses the backend that passed native setup."""
import base64,io,json,os,re,socket,subprocess,sys,threading,time,urllib.request
from pathlib import Path
_active=None
_emitter=None

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
  if self.backend=='cuda':
   if not small:raise ValueError('This CUDA adapter is for Drama3-small only.')
   from drama_cuda import ready
   if not ready(root):raise ValueError('Drama3-small CUDA runtime needs repair in Welcome setup.')
   binary=root/'tools/drama-small-cuda/audiocpp_server.exe'
  if not binary.is_file():raise ValueError('Native Drama server is missing from this package.')
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));self.port=sock.getsockname()[1]
  job=Path(cfg.get('job',root/'checks'));job.mkdir(parents=True,exist_ok=True)
  settings=dict(host='127.0.0.1',port=self.port,backend=self.backend,device=int(cfg.get('gpuIndex',0)),threads=min(8,max(1,(os.cpu_count() or 4)//2)),lazy_load=True,max_loaded_models=1,ui=False,models=[dict(id='drama3',family='fish_drama3',path=str(model),task='tts',mode='streaming',session_options={'fish_drama3.context_length':4096,'fish_drama3.cpu_expert_layers':0},default_request_options=dict(max_tokens=512))])
  file=job/'native-drama-server.json';file.write_text(json.dumps(settings));log_path=job/'native-drama-server.log';self.progressPosition=log_path.stat().st_size if log_path.exists() else 0;self.log=log_path.open('a');self.emit=_emitter
  self.variant=variant;self.cfg=cfg;self.silence=folder/'silence_codes.json'
  environment=dict(os.environ)
  if self.backend=='cuda':environment['PATH']=str(binary.parent)+os.pathsep+environment.get('PATH','')
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
 stop=threading.Event()
 def monitor():
  path=Path(model.log.name);position=getattr(model,'progressPosition',0)
  while not stop.wait(.25):
   try:
    with path.open(errors='replace') as stream:stream.seek(position);lines=stream.readlines();position=stream.tell();model.progressPosition=position
   except OSError:continue
   for line in lines:
    match=re.search(r'(.+?)\.weights\.upload_progress\s+([\d.]+)',line)
    phase=re.search(r'runtime.load.phase (\S+)',line)
    if emit and match:
     label=match[1].split(']')[-1].strip();value=min(1,max(0,float(match[2])))
     emit('模型載入',f'Drama3-small · {label} · {value:.0%}',componentProgress=dict(label='Drama3-small · '+label,fraction=value,phase='loading'))
    elif emit and phase:emit('模型載入','Drama3-small · '+phase[1],componentProgress=dict(label='Drama3-small',phase=phase[1]))
 thread=threading.Thread(target=monitor,daemon=True);thread.start()
 try:return wav_request(model.port,body)
 finally:stop.set();thread.join(timeout=2)

def generate(model,item,cfg):
 import numpy as np
 import soundfile as sf
 from drama3 import complete_clauses,generation_budget,GenerationLimit,RATE,SAMPLING
 text=item['text'];profile=item['profile'];chunks=[]
 pieces=complete_clauses(text) if item.get('deliveryStyle') in ('complete-clauses','plain-clauses','cantonese-strict-clauses') else [text]
 trace=dict(policy='native-gguf-complete-text-2-explicit-sampling',nativeFormat='gguf',backend=model.backend,modelVariant=model.variant,sampling=dict(SAMPLING),status='generating',parts=[],requestedText=text,plannedParts=len(pieces),reference=profile['reference'],targetLanguage=cfg.get('targetLanguage','yue'),seed=int(item.get('seed',42)))
 cfg['_dramaLastGeneration']=trace
 for piece in pieces:
  maximum=generation_budget(piece,item.get('targetSeconds'))
  cue=('用香港廣東話講，唔好普通話，保留原聲情緒' if item.get('deliveryStyle') in ('cantonese-strict','cantonese-strict-clauses') else '用香港廣東話講，自然語氣') if cfg.get('targetLanguage','yue')=='yue' else 'Speak natural English'
  prompted=piece if item.get('deliveryStyle') in ('plain-clauses','plain-whole') else '['+cue+'] '+piece
  body=dict(model='drama3',input=prompted,voice_ref=profile['reference'],reference_text=profile.get('promptText',''),max_tokens=maximum,seed=int(item.get('seed',42)),response_format='wav',**SAMPLING)
  if model.variant=='drama3-small-iq3':body['options']=dict(max_pause_frames='10',silence_codes=str(model.silence))
  audio,sr=sf.read(io.BytesIO(monitored_request(model,body,getattr(model,'emit',None))),dtype='float32',always_2d=True);audio=audio.mean(axis=1)
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
