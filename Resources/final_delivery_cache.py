"""Resume final packaging from immutable measured audio, never refill TTS."""
import hashlib,json
from pathlib import Path
from export_retry import digest_file
from repair_limits import read

def identity(cfg,cues):
 settings={k:v for k,v in cfg.items() if not k.startswith('_') and k not in ('submission','executable','port','boundedRepairs')}
 if __import__('basic_flow').enabled(cfg):settings.pop('outputDuration',None)
 rows=[dict({k:v for k,v in c.items() if not k.startswith('_')},termRequirements=c.get('termRequirements',[])) for c in cues]
 return hashlib.sha256(json.dumps([settings,rows],ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def load(cfg,job,cues):
 if not __import__('delivery_policy').bounded_delivery(cfg) or cfg.get('editorRender'):return None
 saved=read(Path(job)/'final-audio-checkpoint.json')
 if saved.get('identity')!=identity(cfg,cues):return None
 audio=Path(saved.get('audio') or '/nonexistent')
 from normal_mode import audio_present
 if not audio_present(audio) or digest_file(audio)!=saved.get('sha256'):return None
 if __import__('basic_flow').enabled(cfg):cfg['outputDuration']=saved.get('outputDuration',cfg['duration'])
 return audio,saved.get('warnings',[])

def save(cfg,job,cues,audio,warnings):
 if not __import__('delivery_policy').bounded_delivery(cfg) or cfg.get('editorRender'):return
 from worker import atomic_json
 atomic_json(Path(job)/'final-audio-checkpoint.json',dict(identity=identity(cfg,cues),audio=str(audio),sha256=digest_file(audio),warnings=warnings,qualityCertified=False,phase='ready-for-packaging',outputDuration=cfg.get('outputDuration',cfg['duration'])))
