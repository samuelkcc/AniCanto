"""Source-performance review stays separate from TTS repair targets."""
import hashlib,json
from pathlib import Path

def read(path,default):
 try:return json.loads(Path(path).read_text())
 except (OSError,ValueError):return default

def project(root,folders,cfg):
 root=Path(root).resolve();result={};kept=set();unsupported=set()
 for folder in sorted({Path(folder).resolve() for folder in folders}):
  report=read(folder/'nonverbal-report.json',{})
  unsupported.update(report.get('unsupportedCategories',[]))
  # Parent and current child often hold the same report. Count source
  # intervals once, irrespective of how many output tracks retained them.
  for event in report.get('events',[])+report.get('originalSoundRanges',[]):
   try:a,b=(float(event['start']),float(event['end'])) if isinstance(event,dict) else (float(event[0]),float(event[1]))
   except (KeyError,ValueError,TypeError,IndexError):continue
   if __import__('math').isfinite(a+b) and 0<=a<b:kept.add((a,b))
  # Folder configuration and audio availability are invariant for every event.
  # A short-lived UI poll must not decode the full review once per note.
  auditions={}
  if report.get('reviewEvents'):
   local=read(folder/'review.json',{}).get('config',cfg)
   source=root/'japanese-original.wav';stem=Path(local.get('dialoguePath') or '/nonexistent')
   if source.is_file():auditions['original']=dict(path=str(source))
   storage=Path(cfg.get('storage') or root).resolve()
   if stem.is_file() and (stem.resolve().is_relative_to(root) or stem.resolve().is_relative_to(storage/'separations')):auditions['separated']=dict(path=str(stem))
  for event in report.get('reviewEvents',[]):
   a=float(event['start']);b=float(event['end']);label=event.get('label','performance')
   ident=hashlib.sha256(json.dumps([a,b,label],sort_keys=True).encode()).hexdigest()[:20]
   row=result.setdefault(ident,dict(id=ident,start=a,end=b,label=label,status='unconfirmed',reason=event.get('reason',''),confidence=event.get('confidence'),tracks=[]))
   row['tracks'].append(str(folder.relative_to(root)))
   row['auditions']={key:dict(value,start=a,end=b) for key,value in auditions.items()}
  if report.get('status')=='unavailable':
   ident=hashlib.sha256(str(folder).encode()).hexdigest()[:20]
   result[ident]=dict(id=ident,start=0,end=min(float(cfg.get('duration',0)),5),label='unavailable',status='unavailable',reason=report.get('error',''),tracks=[str(folder.relative_to(root))],auditions={})
 rows=sorted(result.values(),key=lambda x:x['start']);merged=[]
 for row in rows:
  if merged and row['label']==merged[-1]['label'] and row['start']<=merged[-1]['end']+.1:
   merged[-1]['end']=max(merged[-1]['end'],row['end'])
   for value in merged[-1].get('auditions',{}).values():value['end']=merged[-1]['end']
  else:merged.append(row)
 return dict(keptRanges=len(kept),notes=merged[:200],remainingNotes=max(0,len(merged)-200),qualityCertified=False,unsupportedCategories=sorted(unsupported))
