"""Versioned first-audible baseline. Saved requests are never restamped here."""
REVISION='basic-first-audible-253'
def enabled(cfg):return cfg.get('basicFlowRevision')==REVISION
def relaxed(cfg):return enabled(cfg) and not cfg.get('limitSpeechDuration',False)
def validate(cfg):
 for key in ('repairExcessiveAudibleOverlap',):
  if key in cfg and not isinstance(cfg[key],bool):raise ValueError('Invalid on/off setting: '+key)
 value=cfg.get('contentChecks',0)
 if isinstance(value,bool) or type(value) is not int or not 0<=value<=2:raise ValueError('Content checks must be 0, 1, or 2.')
 return cfg

def finish(cfg,job,cues,paths,run,emit):
 """Mandatory presence first. Optional work never enables whole-film review."""
 from normal_mode import repair_missing_only,audio_present,inspect
 from worker import atomic_json
 from pathlib import Path
 from track_control import UserSkipped
 import repair_permissions
 selected=list(paths);repair_permissions.capture(cfg,job,cues,selected)
 # One same-reference retry leaves room for one selected-engine generic fill.
 selected=repair_missing_only(dict(cfg,maximumMissingRepairAttempts=1,_generationGuardRoot=str(job)),job,cues,selected,run,emit)
 if any(not audio_present(p) for p in selected):
  from normal_voice_fallback import repair
  from natural_schedule import prepare
  local=dict(cfg,productionMode='normal',_mandatoryPresence=True,_objectiveFallbackOnly=True,_sourceVoiceRepairsExhausted=True)
  selected=repair(local,job,cues,selected,prepare(local,job,cues,selected,run,emit),run,emit)
 # Content checking is an explicit cap. It does not authorize a retake.
 if cfg.get('contentChecks',0)>0:
  try:
   checks=inspect(dict(cfg,_forceIndependentListening=True,_allowBasicContentCheck=True),job,cues,selected,emit)
   atomic_json(Path(job)/'basic-content-checks.json',dict(checks=checks,reportOnly=not cfg.get('aiAutoFix'),qualityCertified=False))
   if cfg.get('aiAutoFix') and checks:
    from normal_mode import repair_paths
    selected=repair_paths(dict(cfg,productionMode='normal',normalRepairPolicy='verified',_allowBasicContentCheck=True,_generationPurpose='content',_initialContentChecks=checks,_contentCheckRoot=str(job)),job,cues,selected,run,emit)
  except UserSkipped:raise
  except (ValueError,RuntimeError,OSError) as error:emit('核對提示','額外內容核對未完成，保留有聲錄音：'+str(error)[:200])
 if cfg.get('limitSpeechDuration'):
  from natural_delivery import repair
  selected=repair(dict(cfg,preferFirstAudibleTake=False,_maximumTimingOperations=1,_generationPurpose='timing'),job,cues,selected,run,emit)
 elif cfg.get('repairExcessiveAudibleOverlap'):
  from audible_overlap import repair
  selected=repair(cfg,job,cues,selected,run,emit)
 from draft_length import observe
 observe(cfg,job,cues,selected)
 return selected,None
