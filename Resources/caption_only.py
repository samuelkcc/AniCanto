"""Keep positively silent screen captions visible without creating a voice take.

ASR absence is not silence. The legacy gate needs completed dual-input VAD,
absent lexical speech, and a near-digital-silent stem. New requests can add a
bounded paired sound check for a music-only VAD candidate and PCM16-quiet stem.
"""
import hashlib,json,math,time
from pathlib import Path

LEGACY_REVISION='caption-only-no-dialogue-260'
REVISION='caption-only-no-dialogue-270'
REASON='confirmed-no-dialogue-caption'
PAD=.25

def enabled(cfg):
 return cfg.get('captionOnlyRevision') in (LEGACY_REVISION,REVISION) and cfg.get('skipNonDialogueCaptions') is True

def lexical(row):
 return any(c.isalnum() for c in str(row.get('text') or row.get('japanese') or ''))

def overlaps(row,a,b):
 try:return min(float(row['end']),b)>max(float(row['start']),a)
 except (KeyError,ValueError,TypeError):return True

def decide(cue,evidence,measure):
 """A testable conservative gate. Measurements are from the full padded window."""
 if cue.get('editorAudio') or cue.get('editorDecisions') or cue.get('preserveOriginalSpeech') or cue.get('opEdKind') or not cue.get('enabled',True):return 'protected-or-manual'
 if lexical(cue):return 'source-words-present'
 if not (cue.get('captionRecords') or cue.get('subtitleClockFallbackID')):return 'no-caption'
 if not evidence.get('complete') or evidence.get('dualInput') is not True:return 'acoustic-evidence-unavailable'
 a,b=float(cue['start']),float(cue['end']);a=max(0,a-PAD);b=min(evidence['duration'],b+PAD)
 if any(lexical(r) and overlaps(r,a,b) for r in evidence['segments']):return 'source-words-present'
 if any(overlaps(r,a,b) for r in evidence['spans']):return 'speech-activity-present'
 if not measure or measure.get('coveredSeconds',0)<b-a-.001:return 'incomplete-audio-window'
 peak=measure.get('peak');rms=measure.get('rms');quantum=measure.get('quantum')
 if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (peak,rms,quantum)) or quantum<=0:return 'invalid-audio-evidence'
 if peak>quantum or rms>quantum*.25:return 'vocal-activity-not-excluded'
 return REASON

def apply(cfg,job,cues,write):
 if not enabled(cfg) or cfg.get('editorRender') or cfg.get('_singleEngine'):return cues
 import numpy as np,soundfile as sf
 job=Path(job);rows=[];budget=dict(started=time.monotonic(),windows=len(list((job/'caption-quiet-proof').glob('*.json'))))
 analysis=job/'japanese-analysis.json';source=job/'japanese-original.wav';stem=Path(cfg.get('dialoguePath') or '/nonexistent')
 try:
  saved=json.loads(analysis.read_text());meta=saved.get('noDialogueEvidence',{})
  # The producer writes completion only after both VAD passes finish. Older
  # saved analyses have no such receipt and cannot authorize suppression.
  evidence=dict(complete=meta.get('complete') is True,dualInput=meta.get('dualInput') is True,duration=float(cfg['duration']),segments=saved['segments'],spans=saved['spans'])
  source_id=hashlib.sha256(source.read_bytes()).hexdigest();stem_id=hashlib.sha256(stem.read_bytes()).hexdigest()
  if meta.get('sourceSHA256')!=source_id or meta.get('stemSHA256')!=stem_id:evidence['complete']=False
  if meta.get('startOffset')!=cfg.get('startOffset',0):evidence['complete']=False
  evidence.update(sourceSHA256=source_id,stemSHA256=stem_id,sourcePath=str(source),stemPath=str(stem))
  with sf.SoundFile(stem) as audio:
   sr=audio.samplerate;quantum=1/32768 if audio.subtype=='PCM_16' else 1e-7
   for n,c in enumerate(cues):
    if not (c.get('captionRecords') or c.get('subtitleClockFallbackID')):continue
    if c.get('captionOnlyRevision') in (LEGACY_REVISION,REVISION) and c.get('originalSpeechReason')==REASON:
     # Recheck only this automatic decision on resume; do not clear any manual
     # recording or source choice. Unavailable proof restores the target need.
     for key in ('captionOnly','captionOnlyRevision','captionOnlyEvidence','preserveOriginalSpeech','originalSpeechReason'):c.pop(key,None)
    a=max(0,float(c['start'])-PAD);b=min(evidence['duration'],float(c['end'])+PAD)
    measure=None
    if math.isfinite(a+b) and 0<=a<b and round(b*sr)<=len(audio):
     audio.seek(round(a*sr));x=audio.read(round(b*sr)-round(a*sr),dtype='float32',always_2d=True)
     if len(x) and np.isfinite(x).all():measure=dict(coveredSeconds=len(x)/sr,peak=float(np.max(abs(x))),rms=float(np.sqrt(np.mean(x.astype('float64')**2))),quantum=quantum)
    reason=decide(c,evidence,measure)
    paired=None
    # A source VAD music false positive is not positive lexical evidence.
    # Only a new frozen policy can request the bounded paired check.
    if cfg.get('captionOnlyRevision')==REVISION and evidence['complete'] and evidence['dualInput'] and reason in ('source-words-present','speech-activity-present','vocal-activity-not-excluded') and not lexical(c) and not any(lexical(r) and overlaps(r,float(c['start']),float(c['end'])) for r in evidence['segments']):
     from caption_quiet_proof import inspect,quiet
     if measure and measure.get('coveredSeconds',0)>=b-a-.001 and quiet(measure):
      paired=inspect(cfg,job,c,evidence,measure,write,budget)
      if paired and paired.get('complete') is True:reason=REASON
    row=dict(index=c.get('reviewIndex',n)+1,start=c['start'],end=c['end'],decision=reason,evidence=measure)
    if paired:row['pairedSoundProof']=dict(complete=paired.get('complete') is True,revision='paired-quiet-caption-270',backend=paired.get('backend'))
    rows.append(row)
    if reason==REASON:
     c.update(captionOnly=True,captionOnlyRevision=cfg['captionOnlyRevision'],preserveOriginalSpeech=True,originalSpeechReason=REASON)
     # Keep enabled, primary text and all target captions. The existing source
     # preservation path bypasses TTS and mandatory missing-audio fallback.
     c['captionOnlyEvidence']=dict(pairedProofIdentity=paired.get('identity') if paired and paired.get('complete') else None,sourceSHA256=source_id,stemSHA256=stem_id,analysisKey=saved.get('key'),startOffset=cfg.get('startOffset',0),windowStart=a,windowEnd=b)
     c['reviewNote']='無對白畫面字幕：保留字幕時間及文字，不生成配音。'
  write(job/'caption-only-report.json',dict(revision=cfg['captionOnlyRevision'],rows=rows,sourceSHA256=source_id,stemSHA256=stem_id,qualityCertified=False))
 except (OSError,ValueError,TypeError,KeyError,RuntimeError) as error:
  write(job/'caption-only-report.json',dict(revision=cfg['captionOnlyRevision'],status='unavailable',reason=str(error)[:240],rows=[],qualityCertified=False))
 return cues
