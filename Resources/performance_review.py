"""Source-performance review stays separate from TTS repair targets."""
import hashlib,json
from pathlib import Path

def read(path,default):
 try:return json.loads(Path(path).read_text())
 except (OSError,ValueError):return default

def project(root,folders,cfg):
 root=Path(root).resolve();result={};total_kept=0;unsupported=set()
 for folder in sorted(folders):
  report=read(folder/'nonverbal-report.json',{})
  unsupported.update(report.get('unsupportedCategories',[]))
  total_kept+=len(report.get('events',[]))+len(report.get('originalSoundRanges',[]))
  for event in report.get('reviewEvents',[]):
   a=float(event['start']);b=float(event['end']);label=event.get('label','performance')
   ident=hashlib.sha256(json.dumps([a,b,label],sort_keys=True).encode()).hexdigest()[:20]
   row=result.setdefault(ident,dict(id=ident,start=a,end=b,label=label,status='unconfirmed',reason=event.get('reason',''),confidence=event.get('confidence'),tracks=[]))
   row['tracks'].append(str(folder.relative_to(root)))
   local=read(folder/'review.json',{}).get('config',cfg)
   source=root/'japanese-original.wav';stem=Path(local.get('dialoguePath') or '/nonexistent')
   row['auditions']={}
   if source.is_file():row['auditions']['original']=dict(path=str(source),start=a,end=b)
   storage=Path(cfg.get('storage') or root).resolve()
   if stem.is_file() and (stem.resolve().is_relative_to(root) or stem.resolve().is_relative_to(storage/'separations')):row['auditions']['separated']=dict(path=str(stem),start=a,end=b)
  if report.get('status')=='unavailable':
   ident=hashlib.sha256(str(folder).encode()).hexdigest()[:20]
   result[ident]=dict(id=ident,start=0,end=min(float(cfg.get('duration',0)),5),label='unavailable',status='unavailable',reason=report.get('error',''),tracks=[str(folder.relative_to(root))],auditions={})
 rows=sorted(result.values(),key=lambda x:x['start']);merged=[]
 for row in rows:
  if merged and row['label']==merged[-1]['label'] and row['start']<=merged[-1]['end']+.1:
   merged[-1]['end']=max(merged[-1]['end'],row['end'])
   for value in merged[-1].get('auditions',{}).values():value['end']=merged[-1]['end']
  else:merged.append(row)
 return dict(keptRanges=total_kept,notes=merged[:200],remainingNotes=max(0,len(merged)-200),qualityCertified=False,unsupportedCategories=sorted(unsupported))
