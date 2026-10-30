"""Two-evidence, non-destructive endpoint repair for v4 generated speech only.

Frame activity nominates a tail; prompt-free complete-word timing must agree.
Neither an energy threshold nor an ASR language label authorizes cutting words.
"""
import hashlib,json,math
from pathlib import Path
from repair_limits import read,bounded,root

REVISION='safe-audio-endpoint-1'

def enabled(cfg):return __import__('delivery_policy').safe_capacity(cfg) and not cfg.get('editorRender') and (cfg.get('repairGroupsRevision')!='repair-groups-263' or cfg.get('safeEndpointCheck') is True)
def token(text):return __import__('speechcheck').text_key(text)
def audio_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def analyze(path):
 import numpy as np,soundfile as sf
 x,sr=sf.read(path,dtype='float32',always_2d=True)
 if not len(x) or sr<=0 or not np.isfinite(x).all():raise ValueError('Invalid endpoint audio')
 duration=len(x)/sr
 if duration>120:return dict(status='uncertain',fileSeconds=duration,reason='recording-too-long-for-local-endpoint-check')
 # Max channel RMS preserves quiet/phase-inverted stereo channels.
 frame=max(1,round(sr*.02));hop=max(1,round(sr*.01));count=max(0,(len(x)-frame)//hop+1)
 if count<8:return dict(status='no-tail-suspect',fileSeconds=duration)
 windows=np.lib.stride_tricks.sliding_window_view(x,frame,axis=0)[::hop]
 rms=np.sqrt(np.mean(windows.astype('float64')**2,axis=-1)).max(axis=1)
 floor=float(np.median(rms[-min(60,len(rms)):]))
 peak=float(np.max(rms));high=max(floor*6,peak*.015,1/32768);low=max(floor*2.8,peak*.001,1/65536)
 active=rms>low
 # Require a real stronger body, not a quiet/noisy file labelled as speech.
 strong=np.flatnonzero(rms>high)
 if len(strong)<8:
  # No sustained energy drop means there is no tail to trim. This is only a
  # timing observation, never a claim that the waveform contains correct words.
  if peak>4/32768 and floor>=peak*.3:return dict(status='no-tail-suspect',fileSeconds=duration,reason='no-low-energy-tail',qualityCertified=False)
  return dict(status='uncertain',fileSeconds=duration,reason='no-clear-voice-body')
 last=np.flatnonzero(active);end=(int(last[-1])*hop+frame)/sr if len(last) else duration
 # Protect sustained quiet endings even when they are well below the loud
 # body's threshold. A whole tail average would hide a late weak syllable.
 weak=rms>max(1/65536,floor*1.3)
 sustained=np.flatnonzero(np.convolve(weak.astype('int16'),np.ones(8,dtype='int16'),'valid')>=7)
 if len(sustained):end=max(end,(int(sustained[-1])+8)*hop/sr)
 tail=max(0.,duration-end)
 suffix=rms[min(len(rms)-1,math.ceil(end*sr/hop)):]
 # Inspect every tail block, not just its average: a quiet final phoneme
 # followed by a long noise floor must not disappear in a global percentile.
 blocks=[suffix[k:k+10] for k in range(0,len(suffix),10) if len(suffix[k:k+10])>=4]
 stationary=bool(len(suffix)>=30 and blocks and all(float(np.quantile(block,.9))<=max(1/32768,floor*1.3) for block in blocks))
 body_end=(int(strong[-1])*hop+frame)/sr
 suspect=duration-body_end>=.6 and body_end>=.25
 return dict(status='tail-suspect' if suspect else 'no-tail-suspect',fileSeconds=duration,activityEnd=min(duration,end),lowEnergyTailSeconds=tail,noiseFloorRMS=floor,strongThreshold=high,lowThreshold=low,stationaryTail=stationary,strongBodyEnd=body_end,qualityCertified=False)

def vocal_end(path):
 """A second acoustic witness using the already-installed local Silero VAD.

 This does not certify complete words. CPU ONNX is small; no new download,
 shared-service mutation or CUDA allocation is involved.
 """
 import numpy as np,soundfile as sf
 from scipy.signal import resample_poly
 from math import gcd
 from faster_whisper.vad import get_speech_timestamps,VadOptions
 x,sr=sf.read(path,dtype='float32',always_2d=True)
 channel=int(np.argmax(np.mean(x.astype('float64')**2,axis=0)));mono=x[:,channel]
 if sr!=16000:
  divisor=gcd(sr,16000);mono=resample_poly(mono,16000//divisor,sr//divisor)
 spans=get_speech_timestamps(np.asarray(mono,dtype='float32'),VadOptions(threshold=.25,neg_threshold=.10,min_speech_duration_ms=60,min_silence_duration_ms=100,speech_pad_ms=120))
 return dict(vocalEvidenceAvailable=True,vocalEnd=max([s['end']/16000 for s in spans]+[0]),vocalSpans=[dict(start=s['start']/16000,end=s['end']/16000) for s in spans],vocalMethod='local-silero-vad-sensitive-with-padding',qualityCertified=False)


def vocal_witness(cfg,job,path):
 try:return vocal_end(path)
 except ImportError:
  # Windows keeps Whisper/ONNX in its speech runtime, not necessarily in the
  # UI worker. Reuse that installed interpreter; never pip/download on this path.
  import subprocess,os
  from runtime_paths import python_for
  from repair_limits import check,remaining
  check();runtime='speech-runtime' if __import__('sys').platform=='win32' else 'runtime'
  python=Path(python_for(cfg['storage'],runtime))
  if not python.is_file():raise ValueError('Local acoustic runtime unavailable')
  left=remaining();timeout=min(15,max(.1,left)) if left is not None else 15
  result=subprocess.run([str(python),'-B',str(Path(__file__).resolve()),'--vocal-end',str(Path(path).resolve())],capture_output=True,text=True,timeout=timeout,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1'))
  if result.returncode:raise ValueError('Local acoustic witness unavailable: '+result.stderr[-180:])
  data=json.loads(result.stdout)
  if data.get('vocalEvidenceAvailable') is not True:raise ValueError('Incomplete acoustic witness')
  return data


def verdict(expected,proof,analysis):
 if analysis.get('status')!='tail-suspect':return dict(status='not-applicable',rewriteAllowed=analysis.get('status')=='no-tail-suspect')
 if not isinstance(proof,dict) or proof.get('method')!=__import__('secondary_speech').ENDPOINT_REVISION or 'No expected text' not in str(proof.get('conditioning','')):return dict(status='unconfirmed',reason='no-independent-word-evidence',rewriteAllowed=False)
 expected_key=token(expected);heard=token(proof.get('heard',''))
 if not expected_key or expected_key!=heard:
  return dict(status='unconfirmed',reason='content-incomplete-or-different',rewriteAllowed=False,heard=proof.get('heard',''))
 words=proof.get('words') or []
 if not isinstance(words,list) or not words or any(not isinstance(w,dict) or not isinstance(w.get('word'),str) for w in words) or token(''.join(w.get('word','') for w in words))!=heard:return dict(status='unconfirmed',reason='word-coverage-not-complete',rewriteAllowed=False)
 last=0.;probabilities=[];word_seconds=0.
 for w in words:
  try:a,b,p=float(w['start']),float(w['end']),float(w.get('probability',0))
  except (KeyError,TypeError,ValueError):return dict(status='unconfirmed',reason='invalid-word-timing',rewriteAllowed=False)
  if not math.isfinite(a+b+p) or not 0<=a<b<=analysis['fileSeconds']+.02 or b<last-.04 or a<last-.12:return dict(status='unconfirmed',reason='invalid-word-timing',rewriteAllowed=False)
  last=b;word_seconds+=b-a;probabilities.append(p)
 if word_seconds<len(heard)*.045:return dict(status='unconfirmed',reason='implausible-word-duration',rewriteAllowed=False)
 if min(probabilities)<.35 or probabilities[-1]<.7 or sum(probabilities)/len(probabilities)<.65:return dict(status='unconfirmed',reason='uncertain-last-word',rewriteAllowed=False)
 # Conservative guard after BOTH the last lexical word and all detected weak
 # activity, including a possible fricative/breath. No original sample is erased.
 if not analysis.get('vocalEvidenceAvailable'):return dict(status='unconfirmed',reason='no-independent-acoustic-vad',rewriteAllowed=False)
 end=max(last,float(analysis['activityEnd']),float(analysis.get('vocalEnd',0)))+.24
 if end>=analysis['fileSeconds']-.35:return dict(status='unconfirmed',reason='no-safe-tail-margin',rewriteAllowed=False)
 return dict(status='trim-candidate',reason='complete-words-and-acoustic-endpoints-agree',end=end,lastWordEnd=last,rewriteAllowed=True,qualityCertified=False)

def expected_text(cfg,cue):
 text=cue.get('cantonese','')
 if cfg.get('targetLanguage','yue')!='en':text=__import__('pronunciation').spoken(cfg,text)
 return text

def canonical_text(cfg,text):
 # The listener also converts heard/word spelling with this installed helper.
 # This is post-inference comparison, never an ASR prompt or forced transcript.
 if cfg.get('executable') and cfg.get('targetLanguage','yue') in ('yue','zh'):
  import subprocess
  return subprocess.check_output([cfg['executable'],'--traditional-text'],input=text.encode(),timeout=10).decode()
 return text


def key_for(cfg,cue,path):
 return hashlib.sha256(json.dumps([REVISION,audio_sha(path),expected_text(cfg,cue),cfg.get('targetLanguage','yue'),cfg.get('ttsBackend'),cfg.get('drama3Model'),cfg.get('gsvVersion')],ensure_ascii=False).encode()).hexdigest()[:32]

def rewrite_allowed(cfg,job,cue,path):
 if not enabled(cfg):return True
 marker=Path(cfg.get('_endpointEvidenceRoot') or job)/'safe-audio-endpoints.json'
 try:record=read(marker).get('records',{}).get(key_for(cfg,cue,path))
 except (OSError,ValueError):return False
 if record:
  if record.get('status')=='adopted':
   from normal_mode import audio_present
   candidate=Path(record.get('selectedAudio',''))
   return bool(record.get('rewriteAllowed') and audio_present(candidate) and audio_sha(candidate)==record.get('selectedSHA256'))
  return bool(record.get('rewriteAllowed'))
 # A caller may reach a previously unanalysed trial. Uncertain activity cannot
 # authorize a wording change merely because its WAV header is long.
 try:return analyze(path).get('status')=='no-tail-suspect'
 except (OSError,ValueError,RuntimeError):return False

@bounded('safe-generated-endpoints',phase='endpoint')
def verify(cfg,job,cues,paths,run,emit):
 """Only suspect items enter one cached prompt-free word-timestamp batch."""
 from worker import atomic_json
 from normal_mode import audio_present
 from recovery_attempts import reserve
 from secondary_speech import transcribe_batch
 from types import SimpleNamespace
 marker=Path(job)/'safe-audio-endpoints.json';saved=read(marker);records=saved.setdefault('records',{});selected=list(paths);pending=[];pending_ids=[]
 mode=cfg.get('workMode','balanced');maximum=2 if mode=='quality' else 1
 for i,(cue,path) in enumerate(zip(cues,paths)):
  if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not cue.get('enabled',True) or not cue.get('cantonese','').strip() or __import__('dubbing').is_vocalization(cue) or not audio_present(path):continue
  # Keep ordinary fitting recordings out of the extra ASR path entirely.
  from speech_timing import natural_window
  from natural_delivery import seconds
  a,b=natural_window(cue,cues,cfg['duration'],cfg)
  available=min(b-a,float(cue.get('_targetSeconds') or b-a))
  if seconds(path,cfg,run)<=available+.005:continue
  key=key_for(cfg,cue,path);record=records.get(key)
  if record and record.get('status')=='adopted':
   target=Path(record.get('selectedAudio',''))
   if audio_present(target) and audio_sha(target)==record.get('selectedSHA256'):selected[i]=target
   else:
    record.update(status='unconfirmed',rewriteAllowed=False,reason='selected-endpoint-candidate-unavailable');atomic_json(marker,saved)
   continue
  if record:continue
  index=cue.get('reviewIndex',i)+1
  try:analysis=analyze(path)
  except (ValueError,RuntimeError,EOFError) as error:
   # A failed optional analysis cannot invalidate another healthy recording.
   # Storage/read failures still propagate to the existing resumable handler.
   analysis=dict(status='uncertain',reason='endpoint-analysis-unavailable',error=str(error)[:200])
  record=dict(index=index,input=str(path),inputSHA256=audio_sha(path),expected=cue['cantonese'],analysis=analysis,rewriteAllowed=analysis.get('status')=='no-tail-suspect',status='no-tail-suspect' if analysis.get('status')=='no-tail-suspect' else 'unconfirmed',qualityCertified=False)
  records[key]=record;atomic_json(marker,saved)
  if analysis.get('status')!='tail-suspect':continue
  try:
   analysis.update(vocal_witness(cfg,job,path))
  except (OSError,ValueError,RuntimeError,ImportError,__import__('subprocess').SubprocessError) as error:
   record.update(reason='acoustic-vad-unavailable',vocalError=str(error)[:200]);atomic_json(marker,saved);continue
  if len(pending)>=(96 if mode=='quality' else 32):
   record['reason']='endpoint-batch-cap';continue
  if not reserve(root(cfg,job),'endpoint:'+str(cfg.get('ttsBackend'))+':'+cfg.get('targetLanguage','yue'),index,maximum):
   record['reason']='endpoint-attempts-exhausted';continue
  record.update(status='checking',reason='tail-awaiting-word-evidence');atomic_json(marker,saved)
  pending.append((Path(job)/'endpoint-witnesses'/key,Path(path)));pending_ids.append((i,key))
 if pending:
  emit('安全時長檢查',f'只核對 {len(pending)} 段疑似尾噪；保護末字，未確認唔裁尾或縮稿。',.82)
  try:
   proof=transcribe_batch(SimpleNamespace(atomic_json=atomic_json,emit=emit,secondaryStage='安全時長檢查'),dict(cfg,_endpointWordTimestamps=True,independentAsrBatchTimeout=min(180,float(__import__('repair_limits').remaining() or 180)),independentAsrItemTimeout=60),pending,auto_language=True)
  except __import__('track_control').UserSkipped:raise
  except (OSError,ValueError,RuntimeError) as error:
   proof=[None]*len(pending);saved['availabilityError']=str(error)[:400]
  for (i,key),evidence in zip(pending_ids,proof):
   record=records[key]
   try:decision=verdict(canonical_text(cfg,expected_text(cfg,cues[i])),evidence,record['analysis'])
   except (OSError,ValueError,__import__('subprocess').SubprocessError) as error:decision=dict(status='unconfirmed',reason='comparison-unavailable',rewriteAllowed=False,error=str(error)[:200])
   record.update(decision,check=evidence or {})
   if decision['status']=='trim-candidate':
    import soundfile as sf
    info=sf.info(paths[i]);x,sr=sf.read(paths[i],dtype='float64',always_2d=True);count=min(len(x),math.ceil(decision['end']*sr));target=Path(job)/'safe-endpoint-takes'/key/'complete-words.wav';target.parent.mkdir(parents=True,exist_ok=True)
    # Keep native delivery rate/channels. No resampling or overwriting raw takes.
    sf.write(target,x[:count],sr,subtype=info.subtype);selected[i]=target
    record.update(status='adopted',selectedAudio=str(target),selectedSHA256=audio_sha(target),selectedSeconds=count/sr,removedSeconds=record['analysis']['fileSeconds']-count/sr,originalRetained=True)
   atomic_json(marker,saved)
 saved.update(revision=REVISION,qualityCertified=False,workMode=mode);atomic_json(marker,saved)
 return selected

def apply(cfg,job,cues,paths,run,emit):
 if not enabled(cfg):return paths
 # Reuse proven, immutable candidates before opening a clock. Exhausted ASR
 # allowance must not discard an already verified result during resume.
 from normal_mode import audio_present
 records=read(Path(job)/'safe-audio-endpoints.json').get('records',{});selected=list(paths)
 for i,(cue,path) in enumerate(zip(cues,paths)):
  if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not audio_present(path):continue
  try:
   record=records.get(key_for(cfg,cue,path),{});candidate=Path(record.get('selectedAudio',''))
   if record.get('status')=='adopted' and audio_present(candidate) and audio_sha(candidate)==record.get('selectedSHA256'):selected[i]=candidate
  except (OSError,ValueError):continue
 # Performance starts no new content ASR; saved evidence is still reusable.
 if cfg.get('workMode')=='performance' and not (cfg.get('repairGroupsRevision')=='repair-groups-263' and cfg.get('safeEndpointCheck') is True):return selected
 return verify(cfg,job,cues,selected,run,emit)


def summary(job):
 records={}
 for path in Path(job).rglob('safe-audio-endpoints.json'):
  for key,row in read(path).get('records',{}).items():
   if key not in records or row.get('status')=='adopted':records[key]=row
 values=list(records.values())
 return dict(revision=REVISION,tailCandidates=sum(r.get('analysis',{}).get('status')=='tail-suspect' for r in values),trimmed=sum(r.get('status')=='adopted' for r in values),unconfirmed=sum(r.get('status') in ('unconfirmed','checking') for r in values),originalsRetained=True,qualityCertified=False)


if __name__=='__main__':
 import sys
 if len(sys.argv)==3 and sys.argv[1]=='--vocal-end':print(json.dumps(vocal_end(sys.argv[2])))
 else:raise SystemExit('Unsupported acoustic operation')
