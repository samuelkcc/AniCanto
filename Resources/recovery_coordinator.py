"""One automatic delivery coordinator for all new desktop modes and errors."""
import json
from pathlib import Path
from repair_limits import bounded,check

@bounded('initial-missing-and-readback')
def initial(cfg,job,cues,paths,run,emit):
 from normal_mode import repair_missing_only,inspect,audio_present
 from worker import atomic_json
 # Three INITIAL attempts in quality; one otherwise. Healthy takes stop here.
 prior=__import__('repair_limits').read(Path(job)/'normal-checks.json')
 paths=repair_missing_only(dict(cfg,maximumMissingRepairAttempts=2 if cfg.get('workMode')=='quality' or __import__('delivery_policy').forced_tts(cfg) else 0),job,cues,paths,run,emit)
 if cfg.get('workMode')=='performance':
  if prior.get('checks'):atomic_json(Path(job)/'normal-checks.json',prior)
  return paths
 proof=inspect(dict(cfg,_forceIndependentListening=True),job,cues,paths,emit)
 for old in prior.get('repairs',[]):
  if old.get('originalAudio') in [str(p) for p in paths] and old.get('check'):proof.setdefault(old['index'],old['check'])
 old=__import__('repair_limits').read(Path(job)/'normal-checks.json')
 rows=[];pending=[]
 for i,(cue,path) in enumerate(zip(cues,paths)):
  if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not cue.get('enabled',True) or not cue.get('cantonese','').strip():continue
  index=cue.get('reviewIndex',i)+1;evidence=proof.get(index,{})
  bad=not audio_present(path) or bool(evidence.get('languageFailure') or evidence.get('contentFailure'))
  if bad:pending.append(index)
  rows.append(dict(index=index,originalAudio=str(path),repaired=False,check=evidence,reason='confirmed-content' if evidence.get('languageFailure') or evidence.get('contentFailure') else 'missing' if not audio_present(path) else 'uncertain-or-usable',attempts=[]))
 atomic_json(Path(job)/'normal-checks.json',dict(revision='bounded-content-listen-2',checks=proof,repairs=rows,unresolved=pending,initialAttempts=1 if cfg.get('workMode')!='quality' else 3,qualityCertified=False,missingRepairHistory=old))
 return paths

@bounded('same-actor-timing')
def actor(cfg,job,cues,paths,run,emit,placement):
 from natural_delivery import repair
 return repair(cfg,job,cues,paths,run,emit,placement=placement)

def fallback(cfg,job,cues,paths,run,emit,placement):
 from normal_voice_fallback import repair as generic
 from natural_schedule import prepare
 from generic_delivery import repair as measured
 from normal_engine_fallback import repair as alternate
 permissions=__import__('repair_permissions')
 if permissions.enabled(cfg) and not permissions.generic(cfg):return paths
 count=1 if permissions.enabled(cfg) else 2 if cfg.get('workMode')=='quality' else 1
 for attempt in range(count):
  paths=generic(dict(cfg,productionMode='normal',_sourceVoiceRepairsExhausted=True,_genericAttempt=attempt),job,cues,paths,placement,run,emit)
  placement=prepare(cfg,job,cues,paths,run,emit)
 if cfg.get('workMode')!='performance' and not permissions.enabled(cfg):
  paths=measured(dict(cfg,_skipAlternate=True,maximumTimingRewritePasses=1,_maximumTimingOperations=1),job,cues,paths,placement,run,emit)
  placement=prepare(cfg,job,cues,paths,run,emit)
 if permissions.enabled(cfg) and not permissions.alternate(cfg):return paths
 return alternate(dict(cfg,productionMode='normal',_genericTargetVoice=True,_forceIndependentListening=True,_maximumAlternateEngines=1),job,cues,paths,placement,run,emit)

def recover_v2(cfg,job,cues,paths,run,emit):
 from natural_finish import finish
 from normal_policy import finish_requested
 from track_control import UserSkipped
 from delivery_policy import confirmed_indices
 from worker import atomic_json
 cfg=dict(cfg,productionMode='fast' if cfg.get('workMode')=='performance' else 'normal')
 paths=list(paths)
 def stage(name,fn,*args,**kwargs):
  try:return fn(*args,**kwargs)
  except UserSkipped:raise
  except (OSError,RuntimeError,ValueError) as error:
   if __import__('export_retry').storage_failure(error):raise
   file=Path(job)/'recovery-warnings.json';saved=__import__('repair_limits').read(file);saved.setdefault('warnings',[]).append(dict(stage=name,error=str(error)[:1200],qualityCertified=False));atomic_json(file,saved)
   emit('修復提示',name+' 未完成；保留已完成錄音，繼續後備交付。',.90)
   return paths
 paths=stage('initial-and-readback',initial,cfg,job,cues,paths,run,emit)
 paths,placement=finish(cfg,job,cues,paths,run,emit,allow_tempo=False)
 timing=0 if cfg.get('workMode')=='performance' or cfg.get('workMode')=='balanced' and cfg.get('failedVoicePolicy','first-take')=='first-take' else 2 if cfg.get('workMode')=='quality' else 1
 if timing and not finish_requested(cfg):
  paths=stage('same-actor',actor,dict(cfg,preferFirstAudibleTake=False,automaticDurationRewrite=True,_maximumTimingOperations=timing),job,cues,paths,run,emit,placement)
  paths,placement=finish(cfg,job,cues,paths,run,emit,allow_tempo=True)
 if cfg.get('failedVoicePolicy')!='source' and not finish_requested(cfg):
  paths=stage('generic-alternate',fallback,dict(cfg,failedVoicePolicy='generic'),job,cues,paths,run,emit,placement)
  paths,placement=finish(cfg,job,cues,paths,run,emit,allow_tempo=True)
  from system_voice import repair as native
  paths=stage('native',native,cfg,job,cues,paths,placement,run,emit)
  paths,placement=finish(cfg,job,cues,paths,run,emit,allow_tempo=True)
 return paths,placement

@bounded('physical-missing')
def physical(cfg,job,cues,paths,run,emit):
 from normal_mode import repair_missing_only
 from repair_limits import read
 import delivery_policy
 prior=read(Path(job)/'normal-checks.json')
 selected=repair_missing_only(dict(cfg,maximumMissingRepairAttempts=2 if cfg.get('workMode')=='quality' or delivery_policy.forced_tts(cfg) else 0),job,cues,paths,run,emit)
 if prior.get('checks') or prior.get('repairs'):
  # Missing-only inspection must not erase persisted content evidence on resume.
  fresh=read(Path(job)/'normal-checks.json')
  prior['missingRepairHistory']=fresh
  __import__('worker').atomic_json(Path(job)/'normal-checks.json',prior)
 return selected

@bounded('optional-content-listening',phase='listening')
def listen(cfg,job,cues,paths,run,emit):
 """Inspect a bounded suspect subset in Balanced; broader selection in Quality.

 Evidence is tied to the selected audio fingerprint. Uninspected and undecided
 recordings remain unverified, never implicitly passed or confirmed wrong.
 """
 import hashlib
 from normal_mode import inspect,audio_present
 from natural_delivery import seconds
 from worker import atomic_json
 from repair_limits import read
 old=read(Path(job)/'normal-checks.json');by_index={r.get('index'):r for r in old.get('repairs',[])}
 selected=[];mode=cfg.get('workMode','balanced');baseline=cfg.get('_initialRecordingPaths',[])
 for i,(cue,path) in enumerate(zip(cues,paths)):
  if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not cue.get('enabled',True) or not cue.get('cantonese','').strip() or not audio_present(path):continue
  index=cue.get('reviewIndex',i)+1
  changed=i<len(baseline) and str(path)!=baseline[i]
  try:short=seconds(path,cfg,run)<.65 and sum(c.isalnum() for c in cue['cantonese'])>=5
  except (OSError,ValueError,EOFError,__import__('wave').Error):short=True
  risky=changed or short or bool(cue.get('translationWarnings') or cue.get('reviewNote') or by_index.get(index,{}).get('check'))
  if mode=='quality' or risky:selected.append(i)
 if mode=='balanced':selected=selected[:24]
 emit('局部覆聽',f'補聲／對時後額外核對 {len(selected)} 句；覆聽有獨立預算，未確認只留報告。',.91)
 proof=inspect(dict(cfg,_deferContentReadback=False,_forceIndependentListening=True),job,[dict(cues[i],reviewIndex=cues[i].get('reviewIndex',i)) for i in selected],[paths[i] for i in selected],emit) if selected else {}
 rows=[];pending=[];checks={}
 for i,(cue,path) in enumerate(zip(cues,paths)):
  if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not cue.get('enabled',True) or not cue.get('cantonese','').strip():continue
  index=cue.get('reviewIndex',i)+1;sha=hashlib.sha256(Path(path).read_bytes()).hexdigest() if audio_present(path) else None
  previous=by_index.get(index,{})
  evidence=proof.get(index,previous.get('check',{}) if sha and previous.get('audioSHA256')==sha else {})
  if evidence:checks[str(index)]=evidence
  bad=bool(evidence.get('languageFailure') or evidence.get('contentFailure') or evidence.get('confirmedContentFailure'))
  if bad or not sha:pending.append(index)
  rows.append(dict(index=index,originalAudio=str(path),audioSHA256=sha,repaired=False,check=evidence,reason='confirmed-content' if bad else 'missing' if not sha else 'uncertain-or-usable',attempts=[]))
 atomic_json(Path(job)/'normal-checks.json',dict(revision='repair-first-content-listen-3',checks=checks,repairs=rows,unresolved=pending,requestedIndices=[cues[i].get('reviewIndex',i)+1 for i in selected],completedIndices=list(proof),qualityCertified=False,priorHistory=old.get('missingRepairHistory',{})))
 return paths

def recover(cfg,job,cues,paths,run,emit):
 from delivery_policy import repair_first,confirmed_indices
 if not repair_first(cfg):return recover_v2(cfg,job,cues,paths,run,emit)
 from natural_finish import finish
 from normal_policy import finish_requested
 from track_control import UserSkipped
 from worker import atomic_json
 from repair_limits import read,root
 paths=__import__('speech_duration').prepare(cfg,job,cues,paths);baseline=[str(p) for p in paths]
 permissions=__import__('repair_permissions');permissions.capture(cfg,job,cues,paths)
 # Normal placement is required even in Performance; content readback stays off.
 cfg=dict(cfg,productionMode='normal',_deferContentReadback=True,_initialRecordingPaths=baseline)
 __import__('safe_vocal_capacity').configure(cfg,job,cues)
 __import__('recovery_plan').prepare(cfg,job,cues,paths)
 __import__('production_progress').phase(root(cfg,job),'repair')
 def stage(name,fn,*args,**kwargs):
  try:return fn(*args,**kwargs)
  except UserSkipped:raise
  except (OSError,RuntimeError,ValueError) as error:
   if __import__('export_retry').storage_failure(error):raise
   file=Path(job)/'recovery-warnings.json';saved=read(file);saved.setdefault('warnings',[]).append(dict(stage=name,error=str(error)[:1200],qualityCertified=False));atomic_json(file,saved)
   emit('修復提示',name+' 未完成；保留已完成錄音，繼續後備交付。',.90)
   return paths
 paths=stage('physical-missing',physical,cfg,job,cues,paths,run,emit)
 permissions.capture(cfg,job,cues,paths)
 paths,placement=finish(cfg,job,cues,paths,run,emit,allow_tempo=True)
 timing=__import__('work_modes').timing_passes(cfg) if __import__('speech_duration').enabled(cfg) else {'performance':0,'balanced':1,'quality':2}[cfg.get('workMode','balanced')]
 if timing and not finish_requested(cfg):
  paths=stage('same-actor-timing',actor,dict(cfg,preferFirstAudibleTake=False,automaticDurationRewrite=True,_durationFitRequired=True,_maximumTimingOperations=timing),job,cues,paths,run,emit,placement)
  paths,placement=finish(cfg,job,cues,paths,run,emit,allow_tempo=True)
 if permissions.enabled(cfg) and permissions.alternate(cfg) and not finish_requested(cfg):
  paths=stage('alternate-actor',__import__('normal_engine_fallback').repair,dict(cfg,_genericTargetVoice=False,_maximumAlternateEngines=1),job,cues,paths,placement,run,emit)
  paths,placement=finish(cfg,job,cues,paths,run,emit,allow_tempo=True)
 def deliver():
  nonlocal paths,placement
  if permissions.enabled(cfg) and not permissions.generic(cfg):return
  if cfg.get('failedVoicePolicy')=='source' or finish_requested(cfg):return
  paths=stage('generic-alternate',fallback,dict(cfg,failedVoicePolicy='generic'),job,cues,paths,run,emit,placement)
  paths,placement=finish(cfg,job,cues,paths,run,emit,allow_tempo=True)
  if not permissions.enabled(cfg) or permissions.native(cfg):
   paths=stage('native',__import__('system_voice').repair,cfg,job,cues,paths,placement,run,emit)
   paths,placement=finish(cfg,job,cues,paths,run,emit,allow_tempo=True)
 # Required delivery has first use of the repair clock. Optional listening has
 # another clock and cannot consume the money/time reserved for target speech.
 deliver()
 if cfg.get('workMode')!='performance' and not finish_requested(cfg):
  paths=stage('optional-content-listening',listen,cfg,job,cues,paths,run,emit)
  if confirmed_indices(cfg,job):deliver() # SAME ledgers and remaining allowance.
 required=__import__('dubbing').required_dialogue(cfg,cues)
 confirmed=confirmed_indices(cfg,job)
 position={c.get('reviewIndex',i)+1:i for i,c in enumerate(cues)}
 unresolved=[n for n,c in required if n in confirmed or not placement or not placement[position[n]].get('fit') or not __import__('normal_mode').audio_present(paths[position[n]])]
 # This is a recovery summary, not a semantic/whole-film listening certificate.
 atomic_json(Path(job)/'recovery-summary.json',dict(revision='safe-capacity-4' if __import__('delivery_policy').safe_capacity(cfg) else 'repair-first-3',mode=cfg.get('workMode','balanced'),required=len(required),unresolvedIndices=unresolved,unresolvedCount=len(unresolved),sourcePolicy=cfg.get('failedVoicePolicy')=='source',unresolvedAction='continue-to-delivery-policy-and-export',qualityCertified=False,budget=read(root(cfg,job)/'repair-time-budget.json')))
 emit('配音交付',f'必要補聲／對時已收尾；仍有 {len(unresolved)} 句未能以目前錄音交付，按後備規則完成輸出並留報告。',.92)
 return paths,placement
