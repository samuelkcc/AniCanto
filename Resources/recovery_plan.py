"""Freeze separate repair/listening clocks from measured first-generation work.

The v3/v4 delivery policies use this plan. Resume reads the original plan;
changing the mode, pending count or observed speed never refills its clocks.
"""
import math
from pathlib import Path
from repair_limits import read,root

BASE={'performance':60,'balanced':180,'quality':600}
CAP={'performance':300,'balanced':900,'quality':1800}
LISTEN={'performance':0,'balanced':60,'quality':180}

def prepare(cfg,job,cues,paths):
 from worker import atomic_json
 from normal_mode import audio_present
 from natural_delivery import seconds
 from speech_timing import natural_window
 from delivery_policy import confirmed_indices
 marker=root(cfg,job)/'repair-time-budget.json'
 if read(marker).get('plan'):return
 mode=cfg.get('workMode','balanced');pending=[];confirmed=confirmed_indices(cfg,job)
 for i,(cue,path) in enumerate(zip(cues,paths)):
  if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not cue.get('enabled',True) or not cue.get('cantonese','').strip():continue
  if __import__('dubbing').is_vocalization(cue):continue
  bad=not audio_present(path)
  if not bad:
   try:
    a,b=natural_window(cue,cues,cfg['duration'],cfg)
    # WAV measurement; no model, no subprocess during plan preparation.
    bad=seconds(path,cfg,lambda a: (_ for _ in ()).throw(ValueError('not PCM WAV')))>b-a+.005
   except (OSError,ValueError,EOFError,__import__('wave').Error):bad=True
  if bad or cue.get('reviewIndex',i)+1 in confirmed:pending.append(cue.get('reviewIndex',i)+1)
 observed=cfg.get('_observedGenerationSecondsPerCue')
 if not isinstance(observed,(int,float)) or not math.isfinite(observed) or observed<=0:
  cost=read(Path(job)/'generation-cost.json')
  observed=cost.get('medianSecondsPerCue') if cost.get('engine')==cfg.get('ttsBackend') and cost.get('language')==cfg.get('targetLanguage','yue') else None
 if not isinstance(observed,(int,float)) or not math.isfinite(observed) or observed<=0:observed=None
 # Planning estimate is NOT a promise or an audio/text quality decision.
 per_cue=max(8.,min(90.,2*observed+8)) if observed is not None else 24.
 repair=min(CAP[mode],max(BASE[mode],len(pending)*per_cue))
 if cfg.get('_repairBudgetSeconds') is not None:repair=float(cfg['_repairBudgetSeconds'])
 native_allowed=__import__('repair_permissions').native(cfg) if __import__('repair_permissions').enabled(cfg) else cfg.get('automaticSystemVoice',True)
 native=repair*.25 if native_allowed else 0.
 plan=dict(revision='repair-first-plan-3',mode=mode,pendingIndices=pending,pendingCount=len(pending),observedGenerationSecondsPerCue=observed,estimatedRepairSecondsPerCue=per_cue,repairSeconds=repair,repairCapSeconds=CAP[mode],listeningSeconds=LISTEN[mode],phaseLimits=dict(ai=repair-native,native=native,listening=LISTEN[mode]),qualityCertified=False)
 modern=__import__('delivery_policy').safe_capacity(cfg)
 if modern:
  endpoint={'performance':0,'balanced':60,'quality':180}[mode]
  plan.update(revision='safe-capacity-plan-4',endpointSeconds=endpoint)
  plan['phaseLimits']['endpoint']=endpoint
 marker.parent.mkdir(parents=True,exist_ok=True)
 # Preserve any settled legacy ledger; never reinterpret a consumed v2 clock.
 saved=read(marker)
 if saved and saved.get('revision') not in ('repair-time-budget-3','repair-time-budget-4'):return
 saved.update(revision='repair-time-budget-4' if modern else 'repair-time-budget-3',plan=plan,limitSeconds=repair+LISTEN[mode]+(plan.get('endpointSeconds') or 0),mode=mode,phases=saved.get('phases',{}),softDeadline=True,qualityCertified=False)
 atomic_json(marker,saved)
