"""Explicit append/replace plans retain exact prior channels and old versions."""
import copy,hashlib,json,uuid
from pathlib import Path
REVISION='retained-source-dubbing-425'

def source_language_changed(review,language):
 cfg=review.get('config',{})
 previous=cfg.get('defaultDubLanguage') or cfg.get('targetLanguage') or (cfg.get('dubLanguages') or ['yue'])[0]
 return language!=previous

def prepare_cues(cfg,cues):
 """Change only the new child. Preserve source clocks, exclusions and other scripts."""
 plan=cfg.get('updateRecordingPlan',{})
 if plan.get('revision')!=REVISION:return cues
 language=(plan.get('target') or [None])[0]
 field={'yue':'cantonese','zh':'mandarin','en':'english'}.get(language)
 for cue in cues:
  source=__import__('primary_source').content(cue).strip()
  intentional=cue.get('preserveOriginalSpeech') and cue.get('originalSpeechReason') not in ('missing-script','missing-target-script','source-recognition-unconfirmed','source-content-unavailable')
  if not intentional and cue.get('enabled',True) and (cue.get('sourcePolicyBlocked') or source in ('','[UNCONFIRMED_SOURCE]','[UNKNOWN_SOURCE]')):
   cue.update(sourcePolicyBlocked=True,preserveOriginalSpeech=True,noSpeech=False)
   cue.setdefault('originalSpeechReason','source-recognition-unconfirmed')
   cue.setdefault('sourceReviewReasons',[])
   if 'unconfirmed-retained-source' not in cue['sourceReviewReasons']:cue['sourceReviewReasons'].append('unconfirmed-retained-source')
  if field and plan.get('translateFromOriginal'):
   cue[field]=''
   cue.pop('captionText',None);cue.pop(field+'CaptionText',None)
   for key in ('editorAudio','editorAudioBackend','editorAudioLanguage','editorAudioVersion','userAcceptedAudio','userAcceptance'):
    cue.pop(key,None)
   if cue.get('originalSpeechReason') in ('missing-script','missing-target-script'):
    cue.pop('originalSpeechReason',None);cue['preserveOriginalSpeech']=False
 return cues

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
 result=copy.deepcopy(draft);cfg=result.setdefault('settings',{});exact_pairs=copy.deepcopy(cfg.get('_trackPairs'));cfg.pop('_retainedTracks',None);cfg.pop('_trackPairs',None);cfg.pop('_generationGuardRoot',None);cfg.pop('_explicitRetakeToken',None)
 if operation=='all':
  if exact_pairs:cfg['_trackPairs']=exact_pairs
  cfg['audioRerunToken']=uuid.uuid4().hex
  cfg['updateRecordingPlan']=dict(operation='all',retainsScripts=True)
  return result
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
 cfg['updateRecordingPlan']=dict(revision=REVISION,operation=operation,target=list(target),replaced=list(remove) if remove else None,retained=[list(p) for p in available if p!=remove],translateFromOriginal=source_language_changed(review,language))
 cfg['targetDraftRevision']=__import__('target_draft').REVISION
 cfg['draftOutputGuardRevision']=__import__('target_script_guard392').REVISION
 __import__('dialogue_policy441').configure(cfg,basic=cfg.get('interfaceMode')=='basic')
 cfg['_dubbingTranslationLanguages']=[language]
 return result

def retained(cfg,root):
 result={};root=family(root)
 for key,row in cfg.get('_retainedTracks',{}).items():
  language,engine=key.split(':',1);folder=Path(row['folder']).resolve();manifest=folder/'report.json';output=Path(row['output']).resolve()
  if not folder.is_relative_to(root) or not output.is_relative_to(root) or not manifest.is_file() or not output.is_file() or digest(manifest)!=row['reportSHA256'] or digest(output)!=row['outputSHA256']:raise ValueError('Retained track changed. Refresh the update plan.')
  result[(language,engine)]=(folder,json.loads(manifest.read_text()),output)
 return result
