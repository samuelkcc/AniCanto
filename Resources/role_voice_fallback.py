"""A stable role-card voice when original-source imitation cannot be delivered.

Uses the same engine, script, language, role and clocks. Only its conditioning
voice changes. The caller must independently verify and mix the resulting take.
"""
import copy


def profile_for(cfg,cue):
    from natural_voices import resolve
    ident=cue.get('speakerId') or cfg.get('defaultSpeaker') or 'unassigned'
    original=next((p for p in cfg.get('voiceProfiles',[]) if p.get('id')==ident),{})
    # Keep the card's explicit natural-voice choice and source pitch, but do not
    # feed the failed original/per-engine reference back into the same engine.
    profile=dict(copy.deepcopy(original),id=ident,name=original.get('name',ident),language='',engineReferences={})
    return resolve(profile,dict(cfg,voiceStyleMode='natural'))


def settings_for(cfg,cue,variant=0):
    profile=profile_for(cfg,cue)
    if variant:
        # A different target-language reference is a distinct recovery strategy,
        # unlike repeatedly sampling a reference that steers the model away
        # from Cantonese. Respect any explicitly chosen card voice.
        original=next((p for p in cfg.get('voiceProfiles',[]) if p.get('id')==profile['id']),{})
        target=cfg.get('targetLanguage','yue')
        if (original.get('naturalVoices') or {}).get(target,'auto')!='auto':
            raise ValueError('角色卡已指定後備聲線；未自動取代用戶選擇。')
        from natural_voices import catalog,resolve
        import math
        choices=[v for v in catalog() if v['language']==target]
        chosen=next(v for v in choices if v['id']==profile['naturalReferenceId'])
        alternatives=sorted((v for v in choices if v['id']!=chosen['id']),key=lambda v:abs(math.log(v['pitchHz']/chosen['pitchHz'])))
        if variant>len(alternatives):raise ValueError('未有其他目標語言角色卡聲線。')
        profile=resolve(dict(original,id=profile['id'],language='',engineReferences={},naturalVoices={target:alternatives[variant-1]['id']}),dict(cfg,voiceStyleMode='natural'))
    settings=dict(cfg,voiceStyleMode='natural',voiceProfiles=[profile],defaultSpeaker=profile['id'],
                  autoSpeakers=False,roleAnalysisMode='audio',aiAutoFix=False,
                  fallbackToRoleVoice=False,editorRender=True,boundedRepairs=True)
    settings.pop('_voiceManifest',None)
    settings.pop('_naturalRolePitch',None)
    return settings,profile


def assign(cfg,cues,reason,emit):
    """Role analysis is optional to speech delivery; keep stable card IDs."""
    if not cfg.get('fallbackToRoleVoice'):raise ValueError(str(reason))
    profiles={}
    for cue in cues:
        if not cue.get('enabled',True):continue
        cue['speakerId']=cue.get('speakerId') or cfg.get('defaultSpeaker') or 'fallback-role'
        ident=cue['speakerId']
        if ident not in profiles:profiles[ident]=profile_for(cfg,cue)
        cue['speakerNote']='人物分析未完成，使用角色卡後備聲線。'
    cfg['voiceProfiles']=list(profiles.values())
    cfg['roleVoiceFallbackReason']=str(reason)
    emit('角色卡後備配音','人物分析未能完成；沿用角色卡後備聲線繼續翻譯及配音，原有台詞同時間保留。',.30)
    return cues
