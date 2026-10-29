"""Language-aware first-request timing guidance, never an editing permission."""
import hashlib,json,math,re
from pathlib import Path
REVISION='language-aware-first-draft-budget-1'
RATES={'yue':3.9,'zh':4.2,'en':2.3}
def units(text,language):
 if language=='en':return len(re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*",str(text)))
 return len(re.findall(r'[\u3400-\u9fff]|[A-Za-z]+|\d',str(text)))
def instruction(cfg,language):
 if not __import__('basic_flow').enabled(cfg):return ''
 return (' FIRST-DRAFT LENGTH: use durationGuidance as a SOFT spoken-length estimate in this target language. '
  'Aim at the original speech time; a following free gap or permitted overlap is tolerance, not space for more text. '
  'Keep all meaning, names, negation, numbers, relationships and emotion. Prefer direct natural clauses and contractions in English. '
  'Do not expand short reactions into explanations. Expand number/name readings mentally when judging length. '
  'Never delete meaning or clip words to hit a count. Chinese characters are only syllable proxies; English words vary in syllables. '
  'No extra explanation or stage directions. This is the first translation, not a request for a second pass.')
def reference_identity(cfg,cue,language):
 try:
  from dubbing import profile_for
  profile=profile_for(cue,dict(cfg,targetLanguage=language))
  path=Path(profile['reference'])
  return hashlib.sha256(path.read_bytes()+str(profile.get('promptText','')).encode()).hexdigest()
 except (OSError,ValueError,KeyError,TypeError):return None

def apply(cfg,job,cues,rows,language):
 if not __import__('basic_flow').enabled(cfg):return rows
 from worker import atomic_json
 path=Path(job)/'draft-length-guidance.json'
 try:audit=json.loads(path.read_text())
 except (OSError,ValueError):audit={}
 try:history=json.loads((Path(job)/'draft-length-observed.json').read_text()).get('rows',[])
 except (OSError,ValueError):history=[]
 for key,row in rows.items():
  index=int(key);cue=cues[index];seconds=max(.15,float(cue.get('speechEnd',cue['end']))-float(cue.get('speechStart',cue['start'])))
  engine=cfg.get('ttsBackend','drama3');speaker=cue.get('speakerId','');reference=reference_identity(cfg,cue,language)
  rates=[r['units']/r['seconds'] for r in history if r.get('language')==language and r.get('engine')==engine and r.get('speaker')==speaker and reference and r.get('referenceIdentity')==reference and r.get('seconds',0)>.2 and r.get('units',0)>0]
  rates=[r for r in rates if RATES[language]*.5<=r<=RATES[language]*1.5]
  rate=sorted(rates)[len(rates)//2] if len(rates)>=3 else RATES[language]
  value=dict(revision=REVISION,language=language,engine=engine,referenceIdentity=reference,clockSource='source-speech' if 'speechStart' in cue and 'speechEnd' in cue else 'cue-clock fallback; speech timing unconfirmed',sourceSeconds=round(seconds,3),spokenUnit='words with syllable-aware phrasing' if language=='en' else 'spoken syllable estimate; characters are a proxy',suggestedRange=[max(1,round(seconds*rate*.8)),max(2,round(seconds*rate*1.15))],rate=round(rate,3),rateSource='same-engine/reference observed complete takes' if len(rates)>=3 else 'conservative language prior; uncertain',preserveCompleteMeaning=True)
  row['durationGuidance']=value;audit[language+':'+str(index)]=value
 atomic_json(path,dict(audit))
 return rows

def observe(cfg,job,cues,paths):
 from normal_mode import audio_present
 from natural_delivery import seconds
 from worker import atomic_json
 rows=[]
 for cue,path in zip(cues,paths):
  if not audio_present(path) or cue.get('preserveOriginalSpeech'):continue
  try:duration=seconds(path,cfg,None)
  except (OSError,ValueError,TypeError):continue
  language=cfg.get('targetLanguage','yue')
  rows.append(dict(language=language,engine=cfg.get('ttsBackend'),speaker=cue.get('speakerId',''),referenceIdentity=reference_identity(cfg,cue,language),units=units(cue.get('cantonese',''),language),seconds=duration,qualityCertified=False))
 atomic_json(Path(job)/'draft-length-observed.json',dict(revision=REVISION,rows=rows))
