"""Explicit append/replace plans retain exact prior channels and old versions."""
import copy,hashlib,json,uuid
from pathlib import Path

def digest(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def family(path):
 root=Path(path).resolve()
 while root.parent.name=='versions':root=root.parent.parent
 return root

def build(review_path,draft,operation,engine=None,language=None,replaced=None):
 from multitrack import ENGINES,saved_track_reports
 from engine_policy import pairs
 from dub_languages import selected
 path=Path(review_path).resolve();review=json.loads(path.read_text());root=family(path.parent)
 result=copy.deepcopy(draft);cfg=result.setdefault('settings',{});cfg.pop('_retainedTracks',None);cfg.pop('_trackPairs',None);cfg.pop('_generationGuardRoot',None);cfg.pop('_explicitRetakeToken',None)
 if operation=='all':cfg['audioRerunToken']=uuid.uuid4().hex;return result
 if operation not in ('append','replace'):raise ValueError('Unknown recording update operation.')
 if (language,engine) not in pairs([engine],[language]):raise ValueError('This engine does not support the selected language.')
 target=(language,engine);old=saved_track_reports(path);available={(x.get('language','yue'),x['engine']):x for x in old}
 if operation=='append' and target in available:raise ValueError('This language/engine track already exists. Choose Replace track.')
 remove=tuple(replaced or ()) if operation=='replace' else None
 if remove is not None and remove not in available:raise ValueError('Select an existing track to replace.')
 if target in available and target!=remove:raise ValueError('The requested track already exists.')
 donors={}
 for pair,row in available.items():
  if pair==remove:continue
  manifest=Path(row['report']).resolve()
  if not manifest.is_relative_to(root) or not manifest.is_file():raise ValueError('A retained track report is missing.')
  prior=json.loads(manifest.read_text());output=Path(prior.get('deliveredOutput') or prior.get('output','')).resolve()
  if not output.is_relative_to(root) or not output.is_file():raise ValueError('A retained track output is missing.')
  donors[':'.join(pair)]=dict(folder=str(manifest.parent),reportSHA256=digest(manifest),output=str(output),outputSHA256=digest(output))
 track_pairs=[list(p) for p in available if p!=remove]+[list(target)]
 cfg.update(_trackPairs=track_pairs,_retainedTracks=donors,selectedEngines=list(dict.fromkeys(p[1] for p in track_pairs)),dubLanguages=list(dict.fromkeys(p[0] for p in track_pairs)),ttsBackend=engine,defaultAudioEngine=engine,defaultDubLanguage=language,audioRerunToken=uuid.uuid4().hex,aiAutoFix=False)
 cfg['updateRecordingPlan']=dict(operation=operation,target=list(target),replaced=list(remove) if remove else None,retained=[list(p) for p in available if p!=remove])
 return result

def retained(cfg,root):
 result={};root=family(root)
 for key,row in cfg.get('_retainedTracks',{}).items():
  language,engine=key.split(':',1);folder=Path(row['folder']).resolve();manifest=folder/'report.json';output=Path(row['output']).resolve()
  if not folder.is_relative_to(root) or not output.is_relative_to(root) or not manifest.is_file() or not output.is_file() or digest(manifest)!=row['reportSHA256'] or digest(output)!=row['outputSHA256']:raise ValueError('Retained track changed. Refresh the update plan.')
  result[(language,engine)]=(folder,json.loads(manifest.read_text()),output)
 return result
