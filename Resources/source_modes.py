"""Four source modes for new jobs. Keep historical jobs on their frozen revision."""
REVISION = 'four-source-modes-298'
CHOICES = ('auto', 'subtitles-speech', 'speech-subtitles', 'speech-ocr')
LABELS = {'subtitles-speech':'字幕優先','speech-subtitles':'語音優先','speech-ocr':'語音 / OCR'}


def current(cfg):
    return cfg.get('sourceWorkflowRevision') == REVISION


def choice(value):
    # The removed OCR-first choice migrates only when a NEW job is submitted.
    return 'speech-ocr' if value == 'ocr-speech' else value if value in CHOICES else 'auto'


def prepare_request(cfg):
    if not current(cfg):return cfg
    cfg['sourceWorkflow'] = choice(cfg.get('sourceWorkflow','auto'))
    cfg.setdefault('sourceProofreadMaxAttempts',1)
    cfg.setdefault('sourceProofreadBudgetSeconds',600)
    if cfg['sourceWorkflow'] == 'speech-ocr':
        cfg.update(subtitleSource='burned',subtitle=None,subtitleStream=None,ocr=True,
                   translationSource='audio-and-ocr',batchAutoSubtitles=False,
                   batchExplicitSubtitle=False,batchExplicitStream=False)
        cfg.pop('subtitleSnapshot',None)
    return cfg


def configure(cfg, meta, select_track, emit=None):
    import source_workflow, subtitle_preference
    from pathlib import Path
    prepare_request(cfg)
    requested = cfg.get('sourceWorkflow','auto') if cfg.get('interfaceMode') == 'expert' else 'auto'
    tracks = [s for s in meta.get('streams',[]) if subtitle_preference.is_text_stream(s)]
    explicit_ocr = requested == 'speech-ocr'
    external = not explicit_ocr and bool(cfg.get('subtitle') and Path(cfg['subtitle']).is_file())
    track = None
    if not explicit_ocr and not external:
        track = next((s for s in tracks if s['index'] == cfg.get('subtitleStream')),None) if cfg.get('batchExplicitStream') else select_track(tracks,cfg.get('subtitleLanguage'),cfg.get('subtitleTitle'),source_workflow.dub_language(cfg))
        if cfg.get('batchExplicitStream') and track is None:
            raise ValueError('The selected subtitle track is no longer available.')
    if track is not None and not cfg.get('sourceCaptionLanguageSelected'):
        cfg['sourceCaptionLanguageSelected']=__import__('subtitle_choice').language(track)
    has_text = external or track is not None
    effective = requested if requested != 'auto' else ('subtitles-speech' if has_text else 'speech-subtitles')
    if effective == 'subtitles-speech' and not has_text:effective = 'speech-subtitles'
    cfg.update(sourceWorkflowEffective=effective,sourceContentPriority='subtitles' if effective=='subtitles-speech' else 'speech',speechTiming=True)
    if explicit_ocr:
        cfg.update(translationSource='audio-and-ocr',subtitleSource='burned',subtitle=None,ocr=True,ocrAutoRegion=True)
    elif has_text:
        cfg.update(translationSource='audio-and-subtitles',subtitleSource='external' if external else 'embedded',ocr=False)
        if not external:cfg.update(subtitle=None,subtitleStream=track['index'])
    else:
        cfg.update(translationSource='audio-only',subtitleSource='none',subtitle=None,subtitleStream=None,ocr=False)
    cfg['sourceSelectionMode']=requested
    cfg['sourceProofreadRevision']=REVISION if effective in ('speech-subtitles','speech-ocr') else None
    cfg.setdefault('sourceProofreadMaxAttempts',1)
    cfg.setdefault('sourceProofreadBudgetSeconds',600)
    cfg['sourceWorkflowResolution']=dict(revision=REVISION,requested=requested,effective=effective,
        hasTextSubtitles=has_text,ocrUsed=explicit_ocr,automatic=requested=='auto',clocks='original-speech',
        targetLanguage=source_workflow.dub_language(cfg),proofreadAfterSpeechDraft=effective!='subtitles-speech',
        authoredSubtitlesIgnored=explicit_ocr,
        trackFamily=subtitle_preference.reason(track) if track else 'external-file' if external else None,
        trackPreferenceRevision=subtitle_preference.REVISION if track else None,
        selectedSubtitleLanguage=cfg.get('sourceCaptionLanguageSelected'),
        subtitleLanguageChoice=cfg.get('subtitleLanguageSelection'))
    reason = '僅以 OCR 讀取畫面字幕，忽略內置及外掛字幕' if explicit_ocr else '使用外掛字幕檔案' if external else ('使用內置字幕軌 '+str(track['index']) if track else '沒有可用文字字幕，使用語音，不自動啟用 OCR')
    cfg['sourceFlow']=dict(revision=REVISION,flow=effective,label=LABELS[effective],reason=reason,manual=requested!='auto',automatic=requested=='auto',track=track['index'] if track else None)
    if emit is not None:emit('來源流程',source_workflow._flow_message(cfg['sourceFlow']),sourceFlow=cfg['sourceFlow'])
    return cfg
