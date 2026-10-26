"""Owned Whisper acceleration, with real word clocks and one CPU fallback.

MLX remains in the dedicated ASR runtime. Windows CUDA uses the installed Torch
DLLs in its analysis runtime; CUDA is never claimed from an adapter name alone.
"""
import contextlib,json,math,os,platform,queue,subprocess,sys,tempfile,threading,time,uuid
from pathlib import Path
from types import SimpleNamespace


def selection(cfg):
 from model_catalog import selected,resolve
 ident=cfg.get('speechModel') or selected(cfg['storage'],'speech');mode=cfg.get('speechAcceleration','auto')
 if mode not in ('auto','cpu'):raise ValueError('Invalid speech acceleration preference.')
 base=dict(backend='cpu',id=ident,path=str(resolve(cfg['storage'],ident)),reason='CPU compatibility')
 if mode=='cpu':return base
 if sys.platform=='darwin' and platform.machine() in ('arm64','aarch64') and ident=='whisper-large-v3':
  try:return dict(backend='mlx',id='whisper-large-v3-mlx',path=str(resolve(cfg['storage'],'whisper-large-v3-mlx')),reason='Installed Apple MLX large-v3')
  except ValueError:return dict(base,reason='Apple MLX Whisper is not installed; use CPU until deployment completes')
 if sys.platform=='win32':
  try:ready=json.loads((Path(cfg['storage'])/'native-ready.json').read_text())
  except (OSError,ValueError):ready={}
  if ready.get('backend') in ('nvidia','cuda') or ready.get('hardware',{}).get('backend')=='cuda':return dict(base,backend='cuda',reason='CUDA candidate; model inference must succeed')
 return base


def identity(cfg):
 chosen=selection(cfg)
 return dict(revision='word-clock-device-1',model=chosen['id'],backend=chosen['backend'],decoding='greedy-mlx' if chosen['backend']=='mlx' else 'beam-search-ctranslate2')


def validate_segments(rows,seconds,word_timestamps):
 if not isinstance(rows,list):raise ValueError('Whisper did not return timed segments')
 previous=-.01
 for row in rows:
  a=row.get('start');b=row.get('end')
  if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (a,b)) or a<0 or b<a or b>seconds+.25 or a<previous-.01:raise ValueError('Whisper returned an invalid source clock')
  previous=a
  if word_timestamps and row.get('text','').strip() and not row.get('words'):raise ValueError('Accelerated Whisper did not return real word timestamps')
  for word in row.get('words',[]):
   left=word.get('start');right=word.get('end')
   if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (left,right)) or not 0<=left<=right<=seconds+.25:raise ValueError('Whisper returned an invalid word clock')
 return rows


def cpu_model(cfg):
 from faster_whisper import WhisperModel
 from model_catalog import resolve,selected
 return WhisperModel(str(resolve(cfg['storage'],cfg.get('speechModel') or selected(cfg['storage'],'speech'))),device='cpu',compute_type='int8',local_files_only=True,cpu_threads=8)


class AcceleratedWhisper:
 def __init__(self,cfg,job,emit):
  self.cfg=dict(cfg);self.job=Path(job);self.job.mkdir(parents=True,exist_ok=True);self.emit=emit;self.chosen=selection(cfg);self.process=None;self.cpu=None;self.events=queue.Queue();self.log=None
  self.record(dict(state='candidate',**self.chosen))
 def record(self,data):
  from atomic_files import write_json
  write_json(self.job/'whisper-compute.json',dict(revision='word-clock-device-1',**data))
  from compute_policy import record
  record(self.cfg.get('storage'),'primary-whisper',dict(data,modelInferencePassed=data.get('state')=='inference-passed'))
 def close(self):
  p=self.process;self.process=None
  if p:
   if p.poll() is None:
    p.terminate()
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
   if p.stdin:p.stdin.close()
   if p.stdout:p.stdout.close()
  if self.log:self.log.close();self.log=None
 def __del__(self):self.close()
 def start(self):
  if self.process:return
  from runtime_paths import python_for
  runtime='asr-runtime' if self.chosen['backend']=='mlx' else 'separator-runtime'
  python=python_for(self.cfg['storage'],runtime)
  if not python.is_file():raise ValueError('Accelerated Whisper runtime is unavailable.')
  request=self.job/'whisper-compute-request.json'
  from atomic_files import write_json
  write_json(request,dict(self.chosen,storage=self.cfg['storage'],gpuIndex=self.cfg.get('gpuIndex',0)))
  self.log=(self.job/'whisper-compute.log').open('a')
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONUNBUFFERED='1')
  self.process=subprocess.Popen([str(python),'-B',str(Path(__file__).resolve()),str(request)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,env=env)
  stream=self.process.stdout;events=self.events
  def reader():
   try:
    for line in stream:events.put(line)
   finally:events.put(None)
  threading.Thread(target=reader,daemon=True).start()
  self.receive('ready',180)
  self.emit('語音硬件加速',self.chosen['backend'].upper()+' · 原聲辨識模型已載入；保留真實字音時間。')
 def receive(self,kind,timeout):
  start=time.monotonic();heartbeat=start
  while time.monotonic()-start<timeout:
   from track_control import check
   check(self.cfg)
   try:line=self.events.get(timeout=.2)
   except queue.Empty:line=''
   if line is None:raise RuntimeError('Whisper acceleration process exited; see whisper-compute.log')
   if line:
    try:value=json.loads(line)
    except ValueError:continue
    if value.get('event')=='error':raise RuntimeError(value.get('error','Whisper inference failed'))
    if value.get('event')==kind:return value
   if time.monotonic()-heartbeat>=10:
    self.emit('語音硬件加速',self.chosen['backend'].upper()+' · 模型仍在處理；未提供新字句進度。');heartbeat=time.monotonic()
  raise TimeoutError('Whisper acceleration timed out; preserved completed source evidence.')
 def request(self,action,audio,options):
  import numpy as np
  from whisper_audio import load
  self.start();path=self.job/('whisper-input-'+uuid.uuid4().hex+'.npy');np.save(path,load(audio),allow_pickle=False)
  try:
   self.process.stdin.write(json.dumps(dict(action=action,audio=str(path),options=options))+'\n');self.process.stdin.flush()
   result=self.receive('result',float(self.cfg.get('speechInferenceTimeout',1200)))
   self.record(dict(state='inference-passed',**self.chosen,seconds=result.get('seconds'),decoding='greedy-mlx' if self.chosen['backend']=='mlx' else 'beam-search-ctranslate2'))
   return result
  finally:path.unlink(missing_ok=True)
 def fallback(self,error):
  from track_control import UserSkipped
  if isinstance(error,UserSkipped):self.close();raise error
  self.close();self.chosen=dict(backend='cpu',id=self.cfg.get('speechModel','whisper-large-v3'),reason=str(error)[:700]);self.cpu=cpu_model(self.cfg)
  self.record(dict(state='fallback',**self.chosen));self.emit('語音硬件加速','加速路徑未完成，保留來源資料並改用 CPU 一次：'+str(error)[:180])
 def transcribe(self,audio,**options):
  if self.chosen['backend']=='cpu':
   if self.cpu is None:self.cpu=cpu_model(self.cfg)
   return self.cpu.transcribe(audio,**options)
  try:
   result=self.request('transcribe',audio,options)
   segments=[SimpleNamespace(**dict(row,words=[SimpleNamespace(**w) for w in row.get('words',[])])) for row in result['segments']]
   return iter(segments),SimpleNamespace(language=result['language'])
  except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
   self.fallback(error);return self.cpu.transcribe(audio,**options)
 def detect_language(self,audio):
  if self.chosen['backend']=='cpu':
   if self.cpu is None:self.cpu=cpu_model(self.cfg)
   return self.cpu.detect_language(audio=audio)
  try:
   result=self.request('language',audio,{})
   return result['language'],result['probability'],result.get('probabilities',[])
  except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
   self.fallback(error);return self.cpu.detect_language(audio=audio)


def load(cfg,job=None,emit=lambda *a,**k:None):
 if selection(cfg)['backend']=='cpu':return cpu_model(cfg)
 folder=Path(job) if job else Path(cfg['storage'])/'cache/whisper-device'/uuid.uuid4().hex
 return AcceleratedWhisper(cfg,folder,emit)


def serve(path):
 import numpy as np
 cfg=json.loads(Path(path).read_text());backend=cfg['backend']
 parent=os.getppid()
 def parent_watch():
  while os.getppid()==parent:time.sleep(1)
  os._exit(1)
 threading.Thread(target=parent_watch,daemon=True).start()
 with contextlib.redirect_stdout(sys.stderr):
  if backend=='mlx':
   import mlx.core as mx
   from mlx_audio.stt import load as load_mlx
   from compute_policy import mlx_device
   mlx_device(cfg.get('storage'),'primary-whisper')
   model=load_mlx(cfg['path'])
  else:
   import torch,ctranslate2
   if not torch.cuda.is_available():raise ValueError('CUDA runtime is unavailable')
   dll=Path(torch.__file__).parent/'lib'
   if hasattr(os,'add_dll_directory'):dll_handle=os.add_dll_directory(str(dll))
   from compute_policy import torch_device
   device=torch_device(torch,cfg.get('storage'),'primary-whisper',requested='cuda',minimum_gb=3.5)
   if device=='cpu':raise ValueError('Not enough free CUDA memory for Whisper; retain CPU path')
   from faster_whisper import WhisperModel
   model=WhisperModel(cfg['path'],device='cuda',device_index=int(cfg.get('gpuIndex',0)),compute_type='int8_float16',local_files_only=True)
 print(json.dumps(dict(event='ready',backend=backend)),flush=True)
 for raw in sys.stdin:
  request=json.loads(raw);audio=np.load(request['audio'],allow_pickle=False);options=request.get('options',{});start=time.monotonic()
  try:
   with contextlib.redirect_stdout(sys.stderr):
    if request['action']=='language':
     if backend=='mlx':
      mel,_=model._prepare_audio(audio,padding=0)
      from mlx_audio.stt.models.whisper.audio import pad_or_trim,N_FRAMES
      _,probabilities=model.detect_language(pad_or_trim(mel,N_FRAMES,axis=-2).astype(model.dtype));language=max(probabilities,key=probabilities.get);probability=float(probabilities[language])
     else:language,probability,_=model.detect_language(audio=audio);probabilities={language:probability}
     response=dict(language=language,probability=probability,probabilities=list(probabilities.items()))
    elif backend=='mlx':
     # This pinned MLX implementation has no beam search. Record the decoding
     # difference; never pass unsupported beam_size or fabricate word clocks.
     options.pop('beam_size',None);options.pop('vad_filter',None)
     if 'max_new_tokens' in options:options['sample_len']=options.pop('max_new_tokens')
     output=model.generate(audio,verbose=None,**options)
     rows=validate_segments(output.segments,len(audio)/16000,bool(options.get('word_timestamps')))
     response=dict(segments=rows,language=output.language)
    else:
     rows,info=model.transcribe(audio,**options)
     response=dict(segments=[dict(start=s.start,end=s.end,text=s.text,words=[dict(start=w.start,end=w.end,word=w.word,probability=w.probability) for w in (s.words or [])]) for s in rows],language=info.language)
   print(json.dumps(dict(event='result',seconds=round(time.monotonic()-start,3),**response),ensure_ascii=False),flush=True)
  except Exception as error:print(json.dumps(dict(event='error',error=str(error))),flush=True)

if __name__=='__main__':
 try:serve(sys.argv[1])
 except Exception as error:print(json.dumps(dict(event='error',error=str(error))),flush=True);raise
