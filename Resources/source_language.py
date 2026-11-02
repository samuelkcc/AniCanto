"""Audio-language preflight and explicit consent for experimental source languages."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

NAMES={'ja':'Japanese','en':'English','zh':'Chinese','yue':'Cantonese','ko':'Korean',
       'fr':'French','es':'Spanish','de':'German','it':'Italian','pt':'Portuguese',
       'ru':'Russian','ar':'Arabic','hi':'Hindi','th':'Thai','vi':'Vietnamese',
       'id':'Indonesian','nl':'Dutch','uk':'Ukrainian','tr':'Turkish'}
ALIASES={'jpn':'ja','eng':'en','chi':'zh','zho':'zh','kor':'ko','fra':'fr','fre':'fr',
         'spa':'es','deu':'de','ger':'de','ita':'it','por':'pt','rus':'ru','ara':'ar',
         'hin':'hi','tha':'th','vie':'vi','ind':'id','nld':'nl','dut':'nl','tur':'tr','ukr':'uk'}
# The subtitle track families from subtitle_preference-1, read as written-language codes.
SUBTITLE_FAMILIES={'cantonese':'yue','traditional':'zh','simplified':'zh','chinese':'zh'}


def text_subtitle_tracks(meta):
    """Subtitle streams that carry readable words, not images."""
    import subtitle_preference
    return [s for s in meta.get('streams',[]) if subtitle_preference.is_text_stream(s)]


def track_language(stream):
    """Language code stated by one subtitle track tag or track title."""
    import subtitle_preference
    tags=stream.get('tags',{}) or {}
    tag=subtitle_preference.canonical(tags.get('language'))
    code=ALIASES.get(tag,tag)
    if code in NAMES:return code
    family=subtitle_preference.family(stream)
    if family in SUBTITLE_FAMILIES:return SUBTITLE_FAMILIES[family]
    return None


def subtitle_snippet(video,tools,index,preparation):
    """Read the first words of one text track. Used only to identify the script."""
    if 'ffmpeg' not in tools:return ''
    command=[tools['ffmpeg'],'-v','error','-i',str(video),'-map',f'0:{index}','-c:s','srt','-f','srt','-t','600','pipe:1']
    raw=preparation.capture(command,timeout=60) if preparation else subprocess.run(command,capture_output=True,timeout=60).stdout
    return (raw or b'').decode('utf-8','ignore')[:4000]


def subtitle_evidence(video,tools,meta,preparation):
    """Record the language of the words inside this file, and how that was read.

    This is content evidence, not audio evidence. It never changes the language
    used for speech recognition, because that language must match the recording.
    """
    import subtitle_preference
    tracks=text_subtitle_tracks(meta)
    if not tracks:return {}
    for stream in tracks:
        language=track_language(stream)
        if language:return dict(language=language,method='subtitle-track-tag',track=stream.get('index'),
                                family=subtitle_preference.family(stream),tracks=len(tracks))
    # No track states a language, so read the words and identify the script.
    for stream in tracks:
        try:text=subtitle_snippet(video,tools,stream['index'],preparation)
        except __import__('source_preparation').SourcePreparationCancelled:raise
        except (OSError,ValueError,subprocess.SubprocessError):continue
        code=__import__('primary_source').language(text)
        if code in NAMES:return dict(language=code,method='subtitle-script-reading',track=stream.get('index'),
                                     family=subtitle_preference.family(stream),tracks=len(tracks))
    return dict(language=None,method='subtitle-unreadable',track=None,family=None,tracks=len(tracks))


def majority_language(samples,minimum=.55):
    """Use the one language every audio sample heard, even under the strict bar.

    The strict gate needs two samples at 0.85, or agreeing samples plus a matching
    file label. With auto-approve on, a failed strict gate used to fall back to
    Japanese even when all three samples named the same language. One shared answer
    across samples, each above this floor, is a real reading, not a guess.
    """
    heard=[s for s in samples or [] if isinstance(s,dict) and s.get('language') in NAMES]
    if len(heard)<2 or len({s['language'] for s in heard})!=1:return None
    if min(float(s.get('confidence') or 0) for s in heard)<minimum:return None
    return heard[0]['language']


def audio_label(cfg,input_index=0):
    return f"{input_index}:{cfg['sourceAudioStream']}" if cfg.get('sourceAudioStream') is not None else f'{input_index}:a:0'


def iso_code(language):
    return dict(ja='jpn',en='eng',zh='zho',yue='yue',ko='kor',fr='fra',es='spa',de='deu',it='ita',pt='por',ru='rus',ar='ara',hi='hin',th='tha',vi='vie',id='ind',nl='nld',uk='ukr',tr='tur').get(language,'und')


def audio_stream(meta):
    streams=[s for s in meta.get('streams',[]) if s.get('codec_type')=='audio']
    return streams[0] if streams else {}


def metadata(meta):
    stream=audio_stream(meta);tag=str(stream.get('tags',{}).get('language','')).casefold()
    language=ALIASES.get(tag,tag)
    return dict(language=language if language in NAMES else None,stream=stream.get('index'),method='audio-stream-metadata')


def supported(language,engines):
    if language not in NAMES:return False
    for engine in engines:
        if engine.startswith('gpt-sovits') and language not in ('ja','en','zh','yue','ko'):return False
        if engine=='wsyue' and language not in ('ja','en','zh','yue'):return False
        if engine not in ('drama3','cosyvoice3','voxcpm2','qwen-tts','wsyue') and not engine.startswith('gpt-sovits'):return False
    return True


def apply(cfg,language):
    cfg['sourceLanguage']=language
    if language!='ja':
        # Full AI's scene/character prompts are Japanese-specific. Experimental
        # sources use the independent source-voice path, with no visual grouping.
        cfg.update(productionMode='normal',roleAnalysisMode='independent',visualRoleAnalysisEnabled=False)
    return cfg


def instruction(cfg):
    if __import__('primary_source').enabled(cfg):return __import__('primary_source').rules(cfg)
    language=cfg.get('sourceLanguage','ja')
    if language=='ja':return ''
    return (' The actual source audio language is '+NAMES.get(language,language)+'. '
            'Legacy fields named japanese, independent_japanese or isolated_japanese contain that source language, not Japanese. '
            'Recognise and translate this language directly; never convert the transcript into Japanese first. '
            'Preserve names and meaning. The source audio transcript has priority over mismatched captions. ')


def speech_name(cfg):
    """User-facing source name, independent of legacy ``japanese`` field names."""
    return NAMES.get(cfg.get('sourceLanguage', 'ja'), 'Source')


def probe(request):
    """Use the installed speech backend for language ID; no translation/TTS starts."""
    import os
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    from whisper_accel import load as load_whisper
    import numpy as np
    from model_catalog import resolve,selected
    model=load_whisper(request)
    votes=[];duration=request['duration']
    positions=sorted({max(0,min(duration-12,duration*f)) for f in (.2,.5,.75)})
    for relative in positions:
        start=float(request.get('startOffset',0))+relative
        raw=subprocess.check_output([request['ffmpeg'],'-v','error','-ss',str(start),'-i',request['video'],'-map',f"0:{request['stream']}",'-t','12','-ar','16000','-ac','1','-f','f32le','pipe:1'],stderr=subprocess.PIPE,timeout=30)
        samples=np.frombuffer(raw,dtype=np.float32)
        if len(samples)<16000 or np.max(np.abs(samples),initial=0)<.003:continue
        lang,confidence,_=model.detect_language(audio=samples)
        votes.append(dict(language=lang,confidence=float(confidence),start=start))
    confident=[v['language'] for v in votes if v['confidence']>=.85]
    winner=max(set(confident),key=confident.count) if confident else None
    language=winner if winner and confident.count(winner)>=2 else None
    method='three-audio-samples'
    # Shared rule "Automatic queue source selection248": a probe can carry a valid
    # consensus without a second dialog. When the samples agree with each other and
    # with the audio stream label, two agreeing samples are a consensus even if one
    # sits under the confidence bar. The rule is recorded, never hidden.
    heard=[v['language'] for v in votes]
    label=str(request.get('metadataLanguage') or '').casefold()
    label=ALIASES.get(label,label)
    if language is None and len(heard)>=2 and len(set(heard))==1 and heard[0] in NAMES and heard[0]==label:
        language=heard[0];method='three-audio-samples+stream-metadata'
    return dict(language=language,method=method,samples=votes,stream=request['stream'])


def _preflight(root,video,tools,settings,preparation=None):
    path=Path(video);stat=path.stat();chosen=settings.get('sourceAudioStream')
    identity=[str(path.resolve()),stat.st_size,stat.st_mtime_ns,'source-audio-4-first-track',chosen,settings.get('startOffset',0),settings.get('limit',0),settings.get('speechModel')]
    key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()
    folder=Path(root)/'source-language'/key;folder.mkdir(parents=True,exist_ok=True);saved=folder/'result.json'
    try:
        result=json.loads(saved.read_text())
        # An older build stored a failed listen as an unconfirmed language, which keeps
        # asking even after the rule is fixed. Recompute those records.
        if result.get('method')=='unconfirmed-audio':raise ValueError('stale unconfirmed listen record')
    except (OSError,ValueError):
        if sys.platform=='win32':
            from source_access import accessible
            media_source,raw=accessible(video,tools['ffprobe'],root);meta=json.loads(raw)
        else:
            media_source=path
            from source_access import probe as media_probe
            command=[tools['ffprobe'],'-v','error','-show_streams','-show_format','-of','json',video]
            meta=json.loads(preparation.capture(command,timeout=45) if preparation else media_probe(video,tools['ffprobe']))
        streams=[x for x in meta.get('streams',[]) if x.get('codec_type')=='audio']
        if chosen is not None:
            stream=next((x for x in streams if x['index']==chosen),None)
            if stream is None:raise ValueError('Selected source audio stream no longer exists.')
            info=metadata(dict(streams=[stream]))
        else:info=metadata(meta)
        result=dict(info,metadataLanguage=info.get('language'),streams=[dict(index=x['index'],language=x.get('tags',{}).get('language','und'),title=x.get('tags',{}).get('title',''),channels=x.get('channels')) for x in streams])
        total=float(meta.get('format',{}).get('duration',0));start=max(0,float(settings.get('startOffset',0)));duration=max(0,total-start)
        if settings.get('limit',0):duration=min(duration,float(settings['limit']))
        # A file label is evidence, never a substitute for available listening.
        if duration>0 and result.get('stream') is not None:
            from runtime_paths import python_for
            request=folder/'request.json';request.write_text(json.dumps(dict(storage=str(root),video=str(media_source),stream=result['stream'],duration=duration,startOffset=start,ffmpeg=tools['ffmpeg'],speechModel=settings.get('speechModel'),metadataLanguage=info.get('language'))))
            python=python_for(root,'speech-runtime' if sys.platform=='win32' else 'runtime')
            try:
                command=[str(python),str(Path(__file__).resolve()),str(request)]
                if preparation:preparation.update(phase='language')
                heard=json.loads(preparation.capture(command,timeout=150) if preparation else subprocess.check_output(command,stderr=subprocess.PIPE,timeout=150));result.update(heard);result['metadataConflict']=bool(heard.get('language') and heard['language']!=info.get('language') and info.get('language'))
            except __import__('source_preparation').SourcePreparationCancelled:raise
            except (OSError,ValueError,subprocess.SubprocessError) as failure:
                # A listen step that could not run says nothing about the speech. Keep the
                # file label, exactly as an empty listen result does, and record the fault
                # so the interface can state why no listening evidence exists.
                raw=getattr(failure,'stderr',None)
                detail=(raw.decode('utf-8','replace') if isinstance(raw,bytes) else str(raw or ''))[-300:].strip()
                result.update(listenFailure=detail or type(failure).__name__,
                              reason='Language listening could not run on this computer. '+(detail or type(failure).__name__))
        # Subtitle words are a second, separate source of evidence. Read them only when
        # the audio path produced nothing, and never let a caption fault stop the preflight.
        if not result.get('language'):
            try:
                result['subtitle']=subtitle_evidence(media_source,tools,meta,preparation)
            except __import__('source_preparation').SourcePreparationCancelled:raise
            except (OSError,ValueError,subprocess.SubprocessError) as failure:
                result['subtitle']=dict(language=None,method='subtitle-unreadable',track=None,family=None,
                                        tracks=len(text_subtitle_tracks(meta)),
                                        detail=(str(getattr(failure,'stderr','') or failure).__class__.__name__))
        from atomic_files import write_json
        write_json(saved,result)
    override=settings.get('sourceLanguageOverride')
    if override:
        if override not in NAMES:raise ValueError('Unknown source language.')
        result=dict(result,detectedLanguage=result.get('language'),language=override,method='user-selected-source',explicitOverride=True)
    engines=settings.get('selectedEngines') or [settings.get('ttsBackend','drama3')]
    language=result.get('language')
    # One switch decides whether the app asks again. With the switch on the app never asks
    # for a language it can work with: it uses the language it detected, and when nothing
    # was heard and the file carries no label it works in Japanese, the source language this
    # product is built for. That assumption is recorded and shown in the preview column, so
    # the user can still change it before export.
    auto_approve=settings.get('autoApproveSourceLanguage',True) is not False
    # The switch is on and nothing cleared the strict gate. Take the one language all the
    # audio samples heard before falling back to a language nobody heard at all.
    relaxed=majority_language(result.get('samples')) if (auto_approve and not language and not override) else None
    if relaxed:language=relaxed
    language_evidence=result.get('method') or ''
    if relaxed:language_evidence='audio-samples-majority'
    assumed=bool(auto_approve and not language and not override)
    if assumed:language='ja'
    available=supported(language,engines)
    token=hashlib.sha256(json.dumps([key,language,engines,override],sort_keys=True).encode()).hexdigest()
    # One case still asks with the switch on: the selected voice engine cannot read the
    # detected language. The dubbing worker refuses that pairing and stops the run, so a
    # silent start would only move the failure from here into the middle of a conversion.
    confirm=bool(language!='ja') and not bool(language and available and auto_approve)
    confirm_reason=('' if not confirm else 'switch-off' if not auto_approve else 'engine-language-mismatch')
    # Detected Japanese continues without a second confirmation. Record what was
    # detected and how it was detected, so the request carries the decision
    # source. Other languages and an uncertain detection still ask the user.
    detected=result.get('detectedLanguage') or (None if override or assumed else language)
    heard=[s for s in result.get('samples') or [] if isinstance(s,dict) and s.get('language')==detected]
    detection=dict(language=language,detectedLanguage=detected,method=result.get('method') or '',
                   stream=result.get('stream'),explicitOverride=bool(override),
                   confidence=max([s.get('confidence',0) for s in heard] or [0]),
                   confirmationSkipped=not confirm,autoApproveSetting=bool(auto_approve),
                   assumedSourceLanguage=assumed,
                   languageEvidence=language_evidence,
                   confirmReason=confirm_reason,listenFailure=bool(result.get('listenFailure')))
    # Content language from the words inside the file, kept separate from the audio language.
    subtitle=result.get('subtitle') or {}
    detection.update(subtitleLanguage=subtitle.get('language'),subtitleMethod=subtitle.get('method') or '',
                     subtitleTrack=subtitle.get('track'),subtitleFamily=subtitle.get('family'))
    return dict(result,name=NAMES.get(language,language or 'Unconfirmed'),supported=available,cacheKey=key,
                language=language,
                needsConfirmation=confirm,confirmReason=confirm_reason,
                assumedSourceLanguage=assumed,
                listenFailure=result.get('listenFailure') or '',token=token,detection=detection,
                detectedLanguage=detected,detectionSource=detection['method'],
                languageEvidence=language_evidence,
                subtitleLanguage=subtitle.get('language'),subtitleMethod=subtitle.get('method') or '',
                reason=result.get('reason') or ('' if available else 'Select a supported source language.'))


def preflight(root,video,tools,settings,operation_id=None,row_id=None):
    from source_preparation import Preparation,SourcePreparationCancelled,CLOUD_ERROR,READ_ERROR,STALLED_ERROR,ProviderNotReady,ProviderReadInterrupted,MediaUnreadable
    preparation=Preparation(root,video,operation_id,row_id)
    def report(error,message):
        # One message per fault: provider not ready, provider stalled, or unreadable media.
        preparation.fail(RuntimeError(message))
        from atomic_files import write_json
        import source_preparation
        try:reason=source_preparation.hydration_reason(video)
        except OSError:reason='source-unreadable'
        write_json(preparation.folder/'diagnostic.json',dict(kind=type(error).__name__,detail=str(error)[:1200],readerError=(getattr(error,'stderr',b'') or b'').decode('utf-8',errors='replace')[-4000:] if isinstance(getattr(error,'stderr',None),bytes) else str(getattr(error,'stderr',''))[-4000:],source=str(video),phase=preparation.state['phase'],provider=source_preparation.provider(video),hydrationReason=reason))
        raise RuntimeError(message) from error
    try:
        preparation.ensure_local();preparation.update(phase='probing')
        result=_preflight(root,video,tools,settings,preparation)
        preparation.finish();return result
    except SourcePreparationCancelled as error:
        preparation.fail(error);raise
    except ProviderNotReady as error:report(error,CLOUD_ERROR)
    except ProviderReadInterrupted as error:report(error,STALLED_ERROR)
    except MediaUnreadable as error:report(error,READ_ERROR)
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        report(error,CLOUD_ERROR if preparation.state['phase']=='reading' and __import__('source_preparation').cloud(video) else READ_ERROR)
    except RuntimeError as error:
        preparation.fail(error);raise


if __name__=='__main__':print(json.dumps(probe(json.loads(Path(sys.argv[1]).read_text()))))
