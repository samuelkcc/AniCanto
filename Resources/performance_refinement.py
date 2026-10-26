"""Bounded source-clock tail checks; no transcript spelling grants restoration."""
import hashlib,json,math,sys
from pathlib import Path
from atomic_files import write_json
REVISION='performance-tail-paired-1'

def gaps(rows,lexical,duration,limit=16):
 from nonverbal import event_labels
 blocked=sorted((max(0,float(c['start'])-.20),min(duration,float(c['end'])+.20)) for c in lexical)
 candidates=[]
 for row in rows:
  score=max(row[k] for k in event_labels(row))
  if score<.30:continue
  a=max(0,float(row['start']));b=min(duration,a+float(row['duration']))
  pieces=[(a,b)]
  for left,right in blocked:
   pieces=[p for x,y in pieces for p in ((x,min(y,left)),(max(x,right),y)) if p[1]-p[0]>=.25]
  for x,y in pieces:
   # Look around a witnessed dialogue end, not at arbitrary ASR silence.
   tails=[right for left,right in blocked if right<=y and x-right<=2.5]
   if not tails:continue
   x=max(x,max(tails));y=min(y,x+5.)
   if y-x>=.25:candidates.append((x,y,score))
 merged=[]
 for a,b,score in sorted(candidates):
  if merged and a<=merged[-1][1]+.05 and max(b,merged[-1][1])-merged[-1][0]<=5:
   merged[-1]=(merged[-1][0],max(b,merged[-1][1]),max(score,merged[-1][2]))
  else:merged.append((a,b,score))
 return sorted(sorted(merged,key=lambda x:x[2],reverse=True)[:limit])

def positive(rows,length):
 from nonverbal import event_ranges
 # Silence padding used by adapters is never an authorised source interval.
 return event_ranges([x for x in rows if max(x['choir_singing'],x['rapping'])<=.20],[],length)

def paired_ranges(original,stem,length):
 result=[]
 for a in positive(original,length):
  for b in positive(stem,length):
   left=max(a['start'],b['start']);right=min(a['end'],b['end'])
   if right-left>=.20:result.append(dict(start=left,end=right,label=a['label'],confidence=min(a['confidence'],b['confidence']),evidence='paired-isolated-tail'))
 return result

def refine(cfg,job,rows,lexical,run,emit):
 from nonverbal import classification,classification_profile,validate_classification,missing_events
 job=Path(job);folder=job/'performance-tails';folder.mkdir(exist_ok=True)
 duration=float(cfg['duration']);original=job/'japanese-original.wav'
 if not original.is_file():
  from update_plan import family
  existing=family(job)/'japanese-original.wav'
  if existing.is_file():original=existing
 if not original.is_file():
  original=folder/'original-analysis.wav'
  from source_language import audio_label
  if not original.exists():run([cfg['ffmpeg'],'-v','error','-y','-ss',str(cfg.get('startOffset',0)),'-i',cfg['video'],'-map',audio_label(cfg),'-t',str(duration),'-vn','-ar','16000','-ac','1',original])
 # Original and separated evidence are independently cached, once per source.
 original_rows=classification(dict(cfg,dialoguePath=str(original)),folder,run)
 validate_classification(original_rows)
 windows=gaps(rows+original_rows,lexical,duration)
 digests=[]
 for source in (original,Path(cfg['dialoguePath'])):
  with source.open('rb') as stream:digests.append(hashlib.file_digest(stream,'sha256').hexdigest())
 result=[];checks=[]
 for n,(a,b,score) in enumerate(windows):
  from track_control import check
  check(cfg)
  length=b-a;minimum=classification_profile()['windowSeconds']
  identity=[REVISION,classification_profile(),a,b,score]
  identity.extend(digests)
  key=hashlib.sha256(json.dumps(identity).encode()).hexdigest();local=folder/key;local.mkdir(exist_ok=True)
  cached=local/'result.json'
  try:saved=json.loads(cached.read_text())
  except (OSError,ValueError):saved={}
  if saved.get('identity')!=identity:
   classified=[]
   for label,source in (('original',original),('stem',Path(cfg['dialoguePath']))):
    target=local/(label+'.wav')
    if not target.exists():run([cfg['ffmpeg'],'-v','error','-y','-ss',f'{a:.6f}','-t',f'{length:.6f}','-i',source,'-af',f'apad=whole_dur={max(length,minimum):.6f}','-ar','16000','-ac','1',target])
    evidence=json.loads(run([cfg['executable'],'--classify-performance',str(target)]));validate_classification(evidence);classified.append(evidence)
   saved=dict(identity=identity,original=classified[0],stem=classified[1],events=paired_ranges(*classified,length));write_json(cached,saved)
  for event in saved['events']:result.append(dict(event,start=event['start']+a,end=event['end']+a))
  checks.append(dict(start=a,end=b,coarseScore=score,status='paired-confirmed' if saved['events'] else 'unconfirmed',evidence=str(cached)))
  emit('原聲表演尾段',f'局部核對 {n+1}/{len(windows)}；原片及分離聲雙重確認，未確認唔混回日文。',.92)
 write_json(job/'performance-tail-report.json',dict(revision=REVISION,maximumRegions=16,checked=checks,events=result,originalRows=original_rows))
 return result,original_rows
