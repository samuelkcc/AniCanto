"""Separate source preservation from a positively verified vocal timing barrier.

Only automatic subtitle gaps with no ASR words AND a near-digital-silent vocal
stem may be borrowed. Unknown/noSpeech/keepOriginal alone are never permission.
Background music stays in its existing mix exactly once.
"""
import hashlib,json
from pathlib import Path
from repair_limits import read,root
REVISION='verified-vocal-capacity-1'
REASONS=('subtitle-content-only-gap','subtitle-continuation')

def configure(cfg,job,cues):
 if cfg.get('repairGroupsRevision')=='repair-groups-263' and not cfg.get('analyzeBackgroundGaps'):
  cfg.pop('_nonVocalCueIDs',None);cfg.pop('_nonVocalClockSHA',None);return cfg
 if not __import__('delivery_policy').safe_capacity(cfg) or cfg.get('editorRender'):return cfg
 import numpy as np,soundfile as sf
 from worker import atomic_json
 source=Path(cfg.get('dialoguePath') or '/nonexistent')
 if not source.is_file():return cfg
 stat=source.stat();identity=[str(source),stat.st_size,stat.st_mtime_ns]
 prior=cfg.get('_vocalCapacityFingerprint')
 if not isinstance(prior,list) or prior[:3]!=identity:
  digest=hashlib.sha256(source.read_bytes()).hexdigest();cfg['_vocalCapacityFingerprint']=identity+[digest]
 else:digest=prior[3]
 marker=root(cfg,job)/'source-vocal-capacity.json';saved=read(marker)
 if saved.get('audioSHA256')!=digest:saved=dict(revision=REVISION,audioSHA256=digest,records={})
 records=saved.setdefault('records',{});allowed=set(cfg.get('_nonVocalCueIDs',[])) if cfg.get('_nonVocalClockSHA')==digest else set()
 with sf.SoundFile(source) as audio:
  sr=audio.samplerate;quantum=1/32768 if audio.subtype=='PCM_16' else 1e-7
  for i,c in enumerate(cues):
   index=c.get('reviewIndex',i)+1;allowed.discard(index)
   if not c.get('preserveOriginalSpeech') or c.get('originalSpeechReason') not in REASONS or c.get('editorAudio') or str(c.get('japanese') or c.get('text') or '').strip():continue
   index=c.get('reviewIndex',i)+1;a=float(c.get('speechStart',c['start']));b=float(c.get('speechEnd',c['end']))
   key=json.dumps([index,a,b]);record=records.get(key)
   if record is None:
    start=max(0,round(a*sr));end=min(len(audio),round(b*sr));audio.seek(start);x=audio.read(max(0,end-start),dtype='float32',always_2d=True)
    peak=float(np.max(abs(x))) if len(x) else None;rms=float(np.sqrt(np.mean(x.astype('float64')**2))) if len(x) else None
    ok=bool(len(x) and end-start>=sr*.08 and np.isfinite(x).all() and peak<=quantum and rms<=quantum*.25)
    record=dict(index=index,start=a,end=b,verifiedNoVocal=ok,peak=peak,rms=rms,reason='digital-quiet-vocal-stem-and-no-asr-words' if ok else 'not-proven-no-vocal',backgroundMixUnchanged=True)
    records[key]=record
   if record['verifiedNoVocal']:allowed.add(index)
 cfg['_nonVocalClockSHA']=digest;cfg['_nonVocalCueIDs']=sorted(allowed);atomic_json(marker,saved)
 return cfg

def is_barrier(cue,cues,cfg):
 if not cfg or not __import__('delivery_policy').safe_capacity(cfg):return True
 if not cfg.get('_nonVocalClockSHA'):return True
 index=cue.get('reviewIndex',next((i for i,c in enumerate(cues) if c is cue),-1))+1
 return not (cue.get('preserveOriginalSpeech') and cue.get('originalSpeechReason') in REASONS and not cue.get('editorAudio') and not str(cue.get('japanese') or cue.get('text') or '').strip() and index in cfg.get('_nonVocalCueIDs',[]))
