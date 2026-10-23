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


def audio_label(cfg,input_index=0):
    return f"{input_index}:{cfg['sourceAudioStream']}" if cfg.get('sourceAudioStream') is not None else f'{input_index}:a:0'


def iso_code(language):
    return dict(ja='jpn',en='eng',zh='zho',yue='yue',ko='kor',fr='fra',es='spa',de='deu',it='ita',pt='por',ru='rus',ar='ara',hi='hin',th='tha',vi='vie',id='ind',nl='nld',uk='ukr',tr='tur').get(language,'und')


def audio_stream(meta):
    streams=[s for s in meta.get('streams',[]) if s.get('codec_type')=='audio']
    return next((s for s in streams if s.get('disposition',{}).get('default')),streams[0] if streams else {})


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
    """CPU-only language ID; no translation or TTS is started before consent."""
    import os
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    from faster_whisper import WhisperModel
    import numpy as np
    from model_catalog import resolve,selected
    model=WhisperModel(str(resolve(request['storage'],request.get('speechModel') or selected(request['storage'],'speech'))),device='cpu',compute_type='int8',local_files_only=True,cpu_threads=4)
    votes=[];duration=request['duration']
    for fraction in (.2,.5,.75):
        start=max(0,min(duration-8,duration*fraction))
        raw=subprocess.check_output([request['ffmpeg'],'-v','error','-ss',str(start),'-i',request['video'],'-map',f"0:{request['stream']}",'-t','12','-ar','16000','-ac','1','-f','f32le','pipe:1'],stderr=subprocess.PIPE,timeout=30)
        samples=np.frombuffer(raw,dtype=np.float32)
        if len(samples)<16000 or np.max(np.abs(samples),initial=0)<.003:continue
        lang,confidence,_=model.detect_language(audio=samples)
        votes.append(dict(language=lang,confidence=float(confidence),start=start))
    confident=[v['language'] for v in votes if v['confidence']>=.85]
    winner=max(set(confident),key=confident.count) if confident else None
    return dict(language=winner if winner and confident.count(winner)>=2 else None,method='three-audio-samples',samples=votes,stream=request['stream'])


def preflight(root,video,tools,settings):
    path=Path(video);stat=path.stat()
    identity=[str(path.resolve()),stat.st_size,stat.st_mtime_ns,'source-audio-1']
    key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()
    folder=Path(root)/'source-language'/key;folder.mkdir(parents=True,exist_ok=True)
    saved=folder/'result.json'
    try:
        result=json.loads(saved.read_text())
        if not result.get('language'):raise ValueError('Retry unconfirmed probe after repair')
    except (OSError,ValueError):
        if sys.platform=='win32':
            from source_access import accessible
            media_source,raw=accessible(video,tools['ffprobe'],root)
            meta=json.loads(raw)
        else:
            media_source=path
            meta=json.loads(subprocess.check_output([tools['ffprobe'],'-v','error','-show_streams','-show_format','-of','json',video],stderr=subprocess.PIPE,timeout=15))
        result=metadata(meta)
        if not result['language'] and result['stream'] is not None:
            from runtime_paths import python_for
            request=folder/'request.json'
            request.write_text(json.dumps(dict(storage=str(root),video=str(media_source),stream=result['stream'],duration=float(meta['format']['duration']),ffmpeg=tools['ffmpeg'],speechModel=settings.get('speechModel'))))
            python=python_for(root,'speech-runtime' if sys.platform=='win32' else 'runtime')
            try:
                output=subprocess.check_output([str(python),str(Path(__file__).resolve()),str(request)],stderr=subprocess.PIPE,timeout=150)
                result=json.loads(output)
            except (OSError,ValueError,subprocess.SubprocessError):result.update(language=None,method='unconfirmed-audio',reason='Source language could not be confirmed. Check the audio language or repair speech recognition setup.')
        from atomic_files import write_json
        write_json(saved,result)
    engines=settings.get('selectedEngines') or [settings.get('ttsBackend','drama3')]
    language=result.get('language');available=supported(language,engines)
    token=hashlib.sha256(json.dumps([key,language,engines],sort_keys=True).encode()).hexdigest()
    return dict(result,name=NAMES.get(language,language or 'Unconfirmed'),supported=available,cacheKey=key,
                needsConfirmation=language!='ja',token=token,
                reason=result.get('reason') or ('' if available else 'The detected source language is not supported by the selected voice engine.'))


if __name__=='__main__':print(json.dumps(probe(json.loads(Path(sys.argv[1]).read_text()))))
