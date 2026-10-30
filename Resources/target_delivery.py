"""Keep target delivery separate from source-clock uncertainty and source retention."""
REVISION='caption-clock-target-255'

def enabled(cfg):return cfg.get('targetDeliveryRevision')==REVISION

def required_clock(cue):
 return bool(cue.get('enabled',True) and cue.get('originalSpeechReason')=='uncertain-source-clock'
             and (any(str(cue.get(k,'')).strip() for k in ('cantonese','english','mandarin'))
                  or cue.get('primarySource',{}).get('text','').strip()))

def prepare(cfg,cues):
 if not enabled(cfg):return cues
 for cue in cues:
  if not required_clock(cue) or cue.get('editorAudio') or cue.get('sourcePolicyBlocked'):continue
  # Keep the actual saved clock and its uncertainty. Do not claim new ASR word times.
  cue['sourcePreservationReview']='uncertain-source-clock'
  cue['sourceClockFallback']='unconfirmed-source-window'
  cue['sourceClockOriginalNote']=cue.get('reviewNote','')
  cue['reviewNote']=cue.get('reviewNote','').replace('此段保留原聲，請核對','配音沿用現有時段，請核對時間')
  cue['preserveOriginalSpeech']=False
  cue.pop('originalSpeechReason',None)
 return cues

def source_windows(cues,timing):
 rows=[]
 for n,cue in enumerate(cues):
  index=cue.get('reviewIndex',n)+1;row=timing.get(index,{})
  if cue.get('captionOnly'):continue
  if not (cue.get('preserveOriginalSpeech') or row.get('originalPreserved') or row.get('originalFallback')):continue
  rows.append(dict(index=index,start=cue['start'],end=cue['end'],reason=cue.get('originalSpeechReason') or row.get('failureKind') or 'source-fallback',script=cue.get('cantonese',''),sourceCaption=cue.get('subtitleHint',''),captionIDs=[r['id'] for r in cue.get('captionRecords',[]) if 'id' in r],targetDelivered=False,meaningCoverageCertified=False))
 return rows

def trace_issues(folder,review,timing,generic=()):
 from pathlib import Path
 import json
 from drama_prompt import file_defects
 try:request=json.loads((Path(folder)/'drama3-request.json').read_text())
 except (OSError,ValueError):return {}
 found={};cues=review.get('cues',[])
 for item in request.get('items',[]):
  n=item.get('reviewIndex')
  if type(n) is not int or not 0<=n<len(cues):continue
  index=n+1;row=timing.get(index,{});cue=cues[n]
  if index in generic or cue.get('editorAudio') or row.get('originalPreserved') or row.get('originalFallback'):continue
  if item.get('approvedText',item.get('text'))!=cue.get('cantonese'):continue
  trace=row.get('generationTrace') or str(Path(item['output']).with_suffix('.generation.json'))
  if file_defects(trace):found[index]=dict(kind='generation-input',generationTrace=trace,message='A delivery instruction was generated without spoken dialogue. Generate a new take; audio presence does not confirm target-language delivery.')
 return found
