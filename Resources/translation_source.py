"""Translation input policy, independent of speed mode and output subtitles.

Audio-only means no caption evidence in generation OR subsequent recovery. The
original media and requested output subtitle tracks are never edited here.
"""
import copy

AUDIO_ONLY='audio-only'
COMBINED='audio-and-subtitles'
SCREEN='audio-and-ocr'
CAPTION_FIELDS=('subtitleHint','captionRecords','captionAllocation','hybridEvidence',
                'hybridNeedsReview','captionPolicyExcluded',
                'captionAllocationIssue','sourceCaptionRecords','preHybridCantonese','captionEvidenceOnly')

AUDIO_PRIORITY_PROMPT=' Japanese speech is the primary source. OCR captions are fallible auxiliary evidence for names and context. If OCR is missing, garbled or contradicts the Japanese, translate the Japanese transcript. Never copy a contradictory caption or discard a heard turn because OCR missed it. If the hearing itself is uncertain, preserve that uncertainty rather than inventing speech.'


def priority_prompt(cfg):
    if cfg.get('sourceLanguage')=='en':
        return (' English speech is the primary source. Captions are fallible auxiliary evidence for names and context. '
                'Translate the English transcript directly into the requested target language, one spoken turn at a time. '
                'Never echo an English sentence as Cantonese dialogue, copy a contradictory caption, or import neighbouring speech.')
    return AUDIO_PRIORITY_PROMPT


def audio_only(cfg):return cfg.get('translationSource',COMBINED)==AUDIO_ONLY


def audio_primary(cfg=None,cue=None):
    """Persist the policy on cues so render/recovery cannot lose OCR provenance."""
    return bool((cfg or {}).get('ocr') or (cfg or {}).get('ocrEvidenceOnly')
                or (cfg or {}).get('translationSource')==SCREEN
                or (cue or {}).get('captionEvidenceOnly'))


def configure(cfg):
    mode=cfg.get('translationSource',COMBINED)
    if mode not in (COMBINED,AUDIO_ONLY,SCREEN):raise ValueError('Unknown translation source: '+str(mode))
    if audio_only(cfg):
        cfg.update(subtitleSource='none',subtitle=None,ocr=False,batchAutoSubtitles=False,
                   speechTiming=True,translate=True,sourceCaptionLanguage='')
        for key in ('captionSourceReview','captionPolicy','_captionPreserveRanges'):
            cfg.pop(key,None)
    elif mode==SCREEN:
        cfg.update(subtitleSource='burned',subtitle=None,ocr=True,batchAutoSubtitles=False,
                   speechTiming=True,translate=True,ocrAutoRegion=True)
        for key in ('captionSourceReview','captionPolicy','_captionPreserveRanges','ocrRect'):
            cfg.pop(key,None)
    return cfg


def analyze_sources(w,cfg,job,meta):
    """Screen captions corroborate full Japanese ASR, never gate its coverage.

    Reuse the saved word timestamps to add OCR context without another model
    pass. Soft/external subtitle jobs retain their existing compatibility path.
    """
    import json
    import dialogue
    screen=bool(cfg.get('ocr')) and not audio_only(cfg)
    if not screen:
        if cfg.get('captionSourceReview'):
            from pathlib import Path
            captions=json.loads((Path(cfg['captionSourceReview']).parent/'cues.json').read_text())
        else:captions=[] if audio_only(cfg) or cfg.get('subtitleSource')=='none' else w.extract_cues(cfg,job,meta)
        return dialogue.analyze(cfg,job,captions,w.run,w.emit)
    cfg['ocrEvidenceOnly']=True
    cfg.pop('sourceCaptionLanguage',None)
    from source_language import speech_name
    name='英文' if cfg.get('sourceLanguage')=='en' else '日文' if cfg.get('sourceLanguage')=='ja' else speech_name(cfg)
    w.emit('原聲辨識',f'先聽完整{name}原聲；畫面字幕只作翻譯參考。',.10)
    cues=dialogue.analyze(cfg,job,[],w.run,w.emit)
    cfg['_ocrSpeechWindows']=[dict(start=c['start'],end=c['end']) for c in cues]
    failure=None
    try:captions=w.extract_cues(cfg,job,meta)
    except (RuntimeError,OSError,ValueError) as error:
        captions=[];failure=str(error)
        w.emit('OCR 提示',f'畫面字幕未能辨識；繼續按{name}原聲聽寫翻譯廣東話／英文。',.28,
               warningCode='ocr-unavailable-audio-used',ocrError=failure)
    finally:cfg.pop('_ocrSpeechWindows',None)
    context=dialogue.caption_context(captions)
    # OCR may enrich a heard turn, but cannot change its clock, create caption-
    # only dialogue, merge turns or remove a turn when a screen word is wrong.
    result=[dict(cue) for cue in cues]
    for cue in result:
        local=[c for c in context if c['end']>cue['start'] and c['start']<cue['end']]
        seen=set();hints=[]
        for caption in local:
            text=caption['text'].strip();key=''.join(c for c in text if c.isalnum()).casefold()
            if key and key not in seen:seen.add(key);hints.append(text)
        cue['subtitleHint']=' ／ '.join(hints[:3])
        cue['captionEvidenceOnly']=True
    w.atomic_json(job/'subtitle-context.json',context)
    w.atomic_json(job/'input-source.json',dict(primary=cfg.get('sourceLanguage','ja')+'-audio',captions='screen-ocr',
        policyRevision='source-primary-ocr-auxiliary-3',
        captionCount=len(captions),audioCueCount=len(cues),cueCount=len(result),ocrError=failure,
        order=[cfg.get('sourceLanguage','ja')+'-asr','screen-ocr','integrated-translation'],region=cfg.get('ocrRect')))
    w.emit('字幕整合',f'{name}原聲 {len(cues)} 句；OCR {len(captions)} 段只作參考，之後整合翻譯。' if captions else f'畫面未辨識到字幕；繼續按完整{name}原聲翻譯，唔需要手動畫框。',.29)
    return result


def remove_caption_evidence(cfg,cues):
    if not audio_only(cfg):
        for cue in cues:
            if audio_primary(cfg,cue):cue['captionEvidenceOnly']=True
        return cues
    for cue in cues:
        for key in CAPTION_FIELDS:cue.pop(key,None)
        # Prior glossary/scene hints must not reintroduce caption-derived facts.
        for key in ('scenePlan','requiredNames','intent'):cue.pop(key,None)
        if cue.get('nonlexicalTail'):cue['captionPolicyExcluded']='nonlexical-asr-tail'
    return cues


def translation_cues(cfg,cues):
    return remove_caption_evidence(cfg,copy.deepcopy(cues)) if audio_only(cfg) else cues
