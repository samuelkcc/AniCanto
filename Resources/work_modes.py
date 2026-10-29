"""Frozen desktop work modes. Model deployment quality is a separate setting."""
REVISION='desktop-work-modes-2'
REVISION_1='desktop-work-modes-1'
LEGACY_MODES=('performance','balanced','quality')
# Revision 2 has one mode. Samuel asked to remove the performance/balanced/quality
# choice: every new job runs the frozen performance policy, and each behaviour
# behind it became a separate switch. The stored value stays 'performance' so the
# frozen performance gates in other modules keep their existing names.
MODES=('performance',)
def enabled(cfg):return cfg.get('workModeRevision') in (REVISION_1,REVISION)
def collapsed(cfg):return cfg.get('workModeRevision')==REVISION
def mode(cfg):return 'performance' if collapsed(cfg) else cfg.get('workMode','balanced')
def ai_repair(cfg):
    """The AI repair switch is user-owned, and default off in the collapsed mode."""
    return bool(cfg.get('aiAutoFix',False))
def timing_passes(cfg):
    if __import__('speech_duration').enabled(cfg):return 1 if __import__('speech_duration').strict(cfg) else 0
    if collapsed(cfg):return 0
    return {'performance':0,'balanced':1,'quality':2}[cfg.get('workMode','balanced')] if enabled(cfg) else 2
def configure(cfg):
 if not enabled(cfg):return cfg
 if collapsed(cfg):
  cfg['workMode']='performance'
  if not isinstance(cfg.get('fullAIReview',False),bool):raise ValueError('Full AI review must be on or off.')
  if not isinstance(cfg.get('aiAutoFix',False),bool):raise ValueError('AI repair must be on or off.')
  full=cfg.get('fullAIReview',False);repair=cfg.get('aiAutoFix',False)
  requested_alternate=bool(cfg.get('automaticAlternateVoice',True));requested_native=bool(cfg.get('automaticSystemVoice',False))
  cfg.update(productionMode='standard' if full else 'fast',normalRepairPolicy='missing-only',
   automaticDurationRewrite=False,continueOnError=True,autoApprove=True,aiAutoFix=repair,
   visualRoleAnalysisEnabled=bool(full),maximumMissingRepairAttempts=2,
   maximumTimingRewritePasses=0 if not full else 1,
   automaticAlternateVoice=bool(repair) and bool(cfg.get('automaticAlternateVoice',True)),
   automaticSystemVoice=bool(repair) and bool(cfg.get('automaticSystemVoice',False)),
   sourceMatchedScriptRevision=__import__('source_mora').REVISION)
  if full:cfg.update(roleAnalysisMode='audiovisual',autoSpeakers=True,autoValidate=True)
  elif cfg.get('roleAnalysisMode')=='audiovisual':cfg['roleAnalysisMode']='audio'
  __import__('speech_duration').configure(cfg)
  if __import__('speech_duration').enabled(cfg):
   cfg.update(autoContentRepair=repair,autoVoiceRepair=repair,automaticAlternateVoice=requested_alternate,
              automaticSystemVoice=requested_native,fallbackToRoleVoice=repair,allowCrossEngineRepair=repair and requested_alternate)
  return cfg
 if cfg.get('workMode') not in LEGACY_MODES:raise ValueError('Unknown work mode.')
 if not isinstance(cfg.get('fullAIReview',False),bool):raise ValueError('Full AI review must be on or off.')
 selected=cfg.get('workMode');full=cfg.get('fullAIReview',False)
 cfg.update(productionMode='standard' if full else 'fast' if selected=='performance' else 'normal',normalRepairPolicy='verified' if selected=='quality' else 'missing-only',
  automaticDurationRewrite=selected!='performance',continueOnError=True,autoApprove=True,
  visualRoleAnalysisEnabled=bool(full),maximumMissingRepairAttempts=2 if selected=='quality' or (selected=='performance' and __import__('delivery_policy').forced_tts(cfg)) else 0 if __import__('delivery_policy').bounded_delivery(cfg) else 1,
  maximumTimingRewritePasses=timing_passes(cfg),
  automaticAlternateVoice=False if selected=='performance' and __import__('delivery_policy').forced_tts(cfg) else cfg.get('automaticAlternateVoice',True),
  automaticSystemVoice=False if selected=='performance' and __import__('delivery_policy').forced_tts(cfg) else cfg.get('automaticSystemVoice',False))
 if full:cfg.update(roleAnalysisMode='audiovisual',autoSpeakers=True,autoValidate=True,aiAutoFix=True)
 elif cfg.get('roleAnalysisMode')=='audiovisual':cfg['roleAnalysisMode']='audio'
 return cfg
