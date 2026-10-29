"""Explicit duration policy for new desktop jobs. Saved jobs keep their clocks."""
import hashlib
import wave
from pathlib import Path

REVISION='speech-duration-246'

def enabled(cfg):return bool(cfg) and cfg.get('speechDurationRevision')==REVISION
def strict(cfg):return enabled(cfg) and cfg.get('limitSpeechDuration') is True
def overlap(cfg):return enabled(cfg) and not strict(cfg)

def configure(cfg):
 if not enabled(cfg):return cfg
 if not isinstance(cfg.get('limitSpeechDuration',False),bool):raise ValueError('Speech duration control must be on or off.')
 cfg.update(sourceSpeechEndCap=strict(cfg),automaticDurationRewrite=strict(cfg),
            maximumTimingRewritePasses=1 if strict(cfg) else 0,naturalTimingPolicy='source-locked',automaticMicroTempo=False)
 return cfg

def deadline(cfg,cue,cues,duration):
 """An optional original-speech limit. OP/ED and manual source keeps stay protected."""
 from speech_timing import window
 start,end=window(cue,cues,duration)
 if strict(cfg):return start,end
 end=float(duration)
 for other in cues:
  if other is cue or not other.get('preserveOriginalSpeech'):continue
  a,b=window(other,cues,duration)
  if a>start+.001:end=min(end,a)
 import opening
 for interval in opening.local_ranges(dict(cfg,duration=float(duration))):
  a=float(interval['start']) if isinstance(interval,dict) else float(interval[0])
  if start<a:end=min(end,a)
 return start,end

def trim(cfg,job,path):
 """Remove exact digital silence at edges only. Preserve 80 ms and the original file."""
 if not enabled(cfg):return Path(path)
 from normal_recovery import padding
 measured=padding(path,digital_only=True)
 if not measured:return Path(path)
 params,samples,a,b=measured
 key=hashlib.sha256(Path(path).read_bytes()+REVISION.encode()).hexdigest()[:24]
 target=Path(job)/'speech-duration'/key/'silent-edges.wav'
 if not target.is_file():
  target.parent.mkdir(parents=True,exist_ok=True)
  # Use a private candidate. Never replace the generated source recording.
  import os,tempfile
  fd,name=tempfile.mkstemp(prefix='edges-',suffix='.wav',dir=target.parent);os.close(fd)
  try:
   with wave.open(name,'wb') as audio:
    audio.setparams(params);audio.writeframes(samples[a*params.nchannels:b*params.nchannels].tobytes())
   os.replace(name,target)
  finally:
   if os.path.exists(name):os.unlink(name)
 return target

def prepare(cfg,job,cues,paths):
 if not enabled(cfg):return list(paths)
 from dubbing import is_vocalization
 from natural_delivery import seconds
 from worker import atomic_json
 import json
 marker=Path(job)/'speech-duration-measure.json'
 try:rows=json.loads(marker.read_text()).get('rows',[])
 except (OSError,ValueError):rows=[]
 selected=[]
 for i,(cue,path) in enumerate(zip(cues,paths)):
  protected=cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not cue.get('enabled',True) or is_vocalization(cue)
  target=Path(path) if protected or not Path(path).is_file() or Path(path).name.startswith('skipped-') else trim(cfg,job,path)
  selected.append(target)
  if target!=Path(path) and not any(r.get('input')==str(path) and r.get('output')==str(target) for r in rows):rows.append(dict(index=cue.get('reviewIndex',i)+1,input=str(path),output=str(target),fileSeconds=seconds(path,cfg,None),measuredSeconds=seconds(target,cfg,None),method='exact-digital-silence-edges',preservedPaddingSeconds=.08,internalPausesRetained=True))
 atomic_json(Path(job)/'speech-duration-measure.json',dict(revision=REVISION,limitSpeechDuration=strict(cfg),allowDialogueOverlap=overlap(cfg),qualityCertified=False,rows=rows))
 return selected
