"""Explicit project terms are data; never guess an official franchise dictionary."""
import json,re
from pathlib import Path
FIELDS={'source','yue','zh','en','kind','locked','preserveOriginal'}

def validate(rows):
 if not isinstance(rows,list) or len(rows)>256:raise ValueError('Use at most 256 project terms.')
 result=[];seen=set()
 for raw in rows:
  if not isinstance(raw,dict) or set(raw)-FIELDS:raise ValueError('Invalid terminology entry.')
  row={k:str(raw.get(k,'')).strip() for k in ('source','yue','zh','en')}
  if not row['source'] or any(len(v)>120 or any(ord(c)<32 for c in v) for v in row.values()):raise ValueError('Terms need a source name and up to 120 characters per field.')
  if row['source'] in seen:raise ValueError('Each source term must be unique.')
  seen.add(row['source']);kind=raw.get('kind','name')
  if kind not in ('name','technique','other'):raise ValueError('Unknown terminology type.')
  if any(k in raw and not isinstance(raw[k],bool) for k in ('locked','preserveOriginal')):raise ValueError('Invalid terminology option.')
  row.update(kind=kind,locked=raw.get('locked',True),preserveOriginal=raw.get('preserveOriginal',False));result.append(row)
 return result

def merge(names,cfg):
 result={n['source']:dict(n) for n in names}
 for term in validate(cfg.get('termRules',[])):
  if term['locked']:
   old=result.get(term['source'],{})
   result[term['source']]=dict(old,source=term['source'],cantonese=term['yue'] or old.get('cantonese',''),english=term['en'] or old.get('english',''),mandarin=term['zh'] or old.get('mandarin',''),kind=term['kind'],locked=True)
 return list(result.values())

def apply(cfg,cues):
 rules=validate(cfg.get('termRules',[]))
 for cue in cues:
  if cue.get('originalSpeechReason')=='user-locked-term':
   cue['preserveOriginalSpeech']=False;cue.pop('originalSpeechReason',None)
  own=cue.get('japanese') or cue.get('text','')
  matches=[t for t in rules if t['locked'] and t['source'] in own]
  cue['termRequirements']=[{k:t[k] for k in ('source','yue','zh','en','kind')} for t in matches]
  if any(t['preserveOriginal'] for t in matches):cue.update(preserveOriginalSpeech=True,originalSpeechReason='user-locked-term')
 return cues

def audit(cfg,job,cues):
 from atomic_files import write_json
 rows=[]
 for i,cue in enumerate(cues):
  if cue.get('preserveOriginalSpeech'):continue
  for term in cue.get('termRequirements',[]):
   for lang,field in (('yue','cantonese'),('zh','mandarin'),('en','english')):
    target=term.get(lang,'');text=cue.get(field,'')
    if target and text and target.casefold() not in text.casefold():rows.append(dict(index=cue.get('reviewIndex',i)+1,language=lang,kind='name-term-mismatch',source=term['source'],expected=target,text=text,start=cue['start'],end=cue['end'],message='Locked term is missing from the draft; existing audio was not discarded.'))
 write_json(Path(job)/'terminology-report.json',dict(rules=validate(cfg.get('termRules',[])),issues=rows))
 return rows
