"""Frozen repair permissions and final disposition for new desktop submissions.

A fallback choice does not enable optional inspection or actor repair.
The generic choice authorizes one final selected-engine bank-voice trial.
"""
import hashlib,json
from pathlib import Path
REVISION='repair-fallback-permissions-249'
def enabled(cfg):return cfg.get('repairPermissionsRevision')==REVISION
def ai(cfg):return cfg.get('aiAutoFix') is True
def policy(cfg):return cfg.get('failedVoicePolicy','first-take')
def generic(cfg):return policy(cfg)=='generic'
def alternate(cfg):return ai(cfg) and cfg.get('automaticAlternateVoice') is True
def native(cfg):return generic(cfg) and ai(cfg) and cfg.get('automaticSystemVoice') is True
def unrecognized(check):
 witnesses=[check,check.get('independent',{}),check.get('independentCheck',{})]
 return not any(any(c.isalnum() for c in str(w.get('heard') or '')) for w in witnesses if isinstance(w,dict))
def advisory(check):
 if not unrecognized(check):return check
 return dict(check,confirmedContentFailure=False,contentFailure=False,languageFailure='',contentDecision='retain-with-note',reviewReason='unrecognized-audio-is-not-confirmed-silence')
def read(path):
 try:return json.loads(Path(path).read_text())
 except (OSError,ValueError):return {}
def identity(cfg,cue):
 data=[cfg.get('ttsBackend'),cfg.get('targetLanguage','yue'),cue.get('reviewIndex'),cue.get('speakerId'),cue.get('start'),cue.get('end'),cue.get('cantonese','')]
 return hashlib.sha256(json.dumps(data,ensure_ascii=False).encode()).hexdigest()
def capture(cfg,job,cues,paths):
 if not enabled(cfg):return
 from normal_mode import audio_present
 from worker import atomic_json
 marker=Path(job)/'first-audible-takes.json';saved=read(marker);records=saved.setdefault('records',{})
 for cue,path in zip(cues,paths):
  if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not cue.get('enabled',True) or not cue.get('cantonese','').strip() or not audio_present(path):continue
  key=identity(cfg,cue)
  if key not in records:records[key]=dict(path=str(path),sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())
 saved.update(revision=REVISION,qualityCertified=False);atomic_json(marker,saved)
def first(cfg,job,cue):
 from normal_mode import audio_present
 row=read(Path(job)/'first-audible-takes.json').get('records',{}).get(identity(cfg,cue),{})
 path=row.get('path')
 if path and audio_present(path) and hashlib.sha256(Path(path).read_bytes()).hexdigest()==row.get('sha256'):return Path(path)
 return None
def fits(cfg,job,cue,cues,path):
 from normal_mode import audio_present
 from natural_delivery import seconds
 from speech_timing import natural_window
 if not path or not audio_present(path):return False
 try:
  a,b=natural_window(cue,cues,cfg['duration'],cfg)
  path=__import__('speech_duration').trim(cfg,job,path)
  return seconds(path,cfg,None)<=b-a+.00005
 except (OSError,ValueError,EOFError,__import__('wave').Error):return False
def choose(cfg,job,cues,paths):
 from delivery_policy import confirmed_indices,rejected_audio
 from normal_mode import audio_present
 from worker import atomic_json
 job=Path(job);selected=list(paths);source=set();decisions=[]
 confirmed=confirmed_indices(cfg,job)
 modern=__import__('basic_flow').enabled(cfg)
 for i,(cue,path) in enumerate(zip(cues,paths)):
  if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not cue.get('enabled',True) or not cue.get('cantonese','').strip():continue
  index=cue.get('reviewIndex',i)+1
  if modern and audio_present(path):continue
  if (index not in confirmed or not rejected_audio(cfg,job,index,path)) and fits(cfg,job,cue,cues,path):continue
  choice=policy(cfg);take=first(cfg,job,cue) if choice=='first-take' else None
  if take and fits(cfg,job,cue,cues,take) and not rejected_audio(cfg,job,index,take):
   selected[i]=__import__('speech_duration').trim(cfg,job,take);action='first-audible-take'
  else:
   source.add(i)
   action='source-speech' if choice=='source' else 'source-after-no-usable-first-take' if choice=='first-take' else 'source-after-generic-failed'
  decisions.append(dict(index=index,policy=choice,action=action,missingTargetDub=i in source,qualityCertified=False))
 # Replace this report on final-only export too. Do not retain stale decisions.
 atomic_json(job/'failed-voice-choices.json',dict(revision=REVISION,policy=policy(cfg),decisions=decisions,qualityCertified=False))
 return selected,source
