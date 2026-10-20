"""Speech-first Japanese dialogue. Captions supply context, never audio boundaries."""
from fast_mode import enabled as one_pass

import hashlib
import json
import math
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

REVISION = 'speech-first-7-chinese-window-coverage'
MODEL_REV = 'edaa852ec7e145841d8ffdb056a99866b5f0a478'
MODEL_SHA = '69f74147e3334731bc3a76048724833325d2ec74642fb52620eda87352e3d4f1'


def install(root, emit, variant=None):
    from model_catalog import install as download,selected
    ident=variant or selected(root,'speech');path=download(root,ident)
    from faster_whisper import WhisperModel
    WhisperModel(str(path),device='cpu',compute_type='int8',local_files_only=True)
    (Path(root)/'speech-ready.json').write_text(json.dumps({'variant':ident}))
    emit('完成','所選日語辨識模型已部署。',1)


def normalized(text):
    return ''.join(c for c in text if c.isalnum()).lower()


def similar(a,b):
    a,b = normalized(a),normalized(b)
    if a==b: return True
    if min(len(a),len(b)) < 8: return False
    if SequenceMatcher(None,a,b).ratio() >= .86: return True
    # OCR can swap two rows without the underlying subtitle changing.
    aa,bb=Counter(a[i:i+2] for i in range(len(a)-1)),Counter(b[i:i+2] for i in range(len(b)-1))
    return 2*sum((aa & bb).values())/max(1,sum(aa.values())+sum(bb.values())) >= .86


def caption_context(captions):
    result=[]
    for c in sorted(captions,key=lambda c:c['start']):
        if not c.get('text','').strip(): continue
        if result and c['start']-result[-1]['end'] <= .65 and similar(c['text'],result[-1]['text']):
            previous=result[-1];previous['end']=max(previous['end'],c['end'])
            key=c['text'];previous['variants'][key]=previous['variants'].get(key,0)+c['end']-c['start']
            previous['text']=max(previous['variants'],key=previous['variants'].get)
        else:
            result.append(dict(start=c['start'],end=c['end'],text=c['text'],variants={c['text']:c['end']-c['start']}))
    return [{k:v for k,v in c.items() if k!='variants'} for c in result]


def build_cues(segments, spans, captions, duration, offset=0):
    """Split at word pauses and ASR sentence boundaries, independently of OCR."""
    captions=caption_context(captions)
    groups=[]
    for segment in segments:
        current=[]
        source_words=[w for w in segment.get('words',[]) if all(math.isfinite(w[k]) for k in ('start','end')) and w['end']>=w['start'] and w['word'].strip()]
        timed=[i for i,w in enumerate(source_words) if w['end']>w['start']]
        if not timed: continue
        for i,w in enumerate(source_words):
            # Whisper sometimes assigns several subword tokens the same instant.
            # Retain internal tokens as text; dropping them changes names/meaning.
            if w['end']==w['start'] and not (timed[0]<=i<=timed[-1]): continue
            # VAD is corroborating evidence, not a knife through Japanese words.
            # Cartoon voices over music are often rejected by conversational VAD.
            w=dict(w,start=max(0,w['start']),end=min(duration,w['end']))
            if w['end']<w['start'] or w['start']>=duration: continue
            if current and (w['start']-current[-1]['end']>1.2 or (w['start']-current[-1]['end']>.32 and current[-1]['word'].rstrip().endswith(('。','！','？','!','?'))) or (w['end']-current[0]['start']>7 and w['start']-current[-1]['end']>.25)):
                groups.append(current);current=[]
            current.append(w)
        if current: groups.append(current)
    cues=[]
    for words in groups:
        a,b=words[0]['start'],words[-1]['end']
        coverage=sum(max(0,min(b,s['end'])-max(a,s['start'])) for s in merge_spans(spans))
        # A short recognition stretched over seconds of silence is unreliable.
        text=''.join(w['word'] for w in words).strip()
        if not text: continue
        relevant=[c for c in captions if c['end']>a and c['start']<b]
        hints=[]
        for c in relevant:
            if not any(similar(c['text'],h) for h in hints): hints.append(c['text'])
        score=sum(w.get('probability',1) for w in words)/len(words)
        # Low VAD coverage alone cannot veto high-pitched anime speech. Only
        # reject weak uncorroborated noise, or typical closing-credit ASR filler
        # with almost no acoustic support and no matching subtitle evidence.
        boilerplate=any(t in text for t in ('ご視','チャンネル登録'))
        if coverage/max(.001,b-a)<.35 and boilerplate and not any('視聴' in h or '收看' in h or '观看' in h or '訂閱' in h or '订阅' in h for h in hints): continue
        if coverage==0 and score<.65 and not hints: continue
        note=[]
        if coverage/max(.001,b-a)<.35: note.append('動畫聲線未被人聲偵測器完整捕捉；保留原聲辨識，時間以日語音訊為準。')
        fragment = len(normalized(text)) == 1 and '\u4e00' <= normalized(text) <= '\u9fff'
        if fragment: note.append('只辨識到單個漢字，可能係截斷字／雜聲；保留配音並標記覆核，請聽原聲確認。')
        if score < .55: note.append('日語辨識信心較低，請比較原声同中文字幕參考。')
        if b-a > max(2.5,len(normalized(text))*.65): note.append('辨識文字同聲音長度唔相稱，可能係叫聲／笑聲；請核對。')
        start=max(0,a-.06);end=min(duration,b+.10)
        cues.append(dict(start=round(start,3),end=round(end,3),text=text,japanese=text,
                         subtitleHint=' ／ '.join(hints[:3]),asrConfidence=round(score,3),
                         reviewNote=' '.join(note),timingSource='japanese-audio',cantonese='',
                         enabled=True,sourceReviewReasons=note.copy()))
    cues.sort(key=lambda c:c['start'])
    merged=[]
    for c in cues:
        small=normalized(c['japanese'])
        if merged and c['end']-c['start']<.55 and c['start']-merged[-1]['end']<=.12 and small and all(x in 'ぁぃぅぇぉっゃゅょァィゥェォッャュョ' for x in small):
            previous=merged[-1]
            previous['end']=c['end']
            previous['reviewNote']+=' 已將辨識器拆開嘅短尾音合返前句。'
        else: merged.append(c)
    cues=rescue_caption_speech(merged,captions,spans,duration)
    for i,c in enumerate(cues):
        if i+1<len(cues): c['end']=min(c['end'],cues[i+1]['start'])
        # A modest following pause is available for natural Cantonese delivery.
        # Never borrow from the next spoken line or move its start.
        next_start=cues[i+1]['start'] if i+1<len(cues) else duration
        c['speechStart']=c['start'];c['speechEnd']=c['end']
        c['deliveryEnd']=round(min(duration,next_start,c['end']+.35),3)
        c['sourceStart']=c['start']+offset;c['sourceEnd']=c['end']+offset
    return [c for c in cues if c['end']>c['start']]


def consolidate_fragments(cues):
    """Join grammatical continuations sharing one caption, before voice clustering.

    Caption timing never creates a voice or sets an audio boundary. Both pieces
    must already have independent ASR evidence, with a bounded intervening pause.
    """
    joined=[]
    for c in cues:
        c=dict(c)
        previous=joined[-1] if joined else None
        same_caption=previous and c.get('subtitleHint') and c.get('subtitleHint')==previous.get('subtitleHint')
        continuation=previous and re.search(r'(?:[はをにのともがへ]|と思い)[、。\s]*$',previous.get('japanese',''))
        if same_caption and continuation and previous.get('enabled',True) and c.get('enabled',True) and 0<=c['start']-previous['end']<=1.8 and c['end']-previous['start']<=10:
            previous.setdefault('recognitionParts',[dict(start=previous['start'],end=previous['end'],japanese=previous['japanese'])])
            previous['recognitionParts'].append(dict(start=c['start'],end=c['end'],japanese=c['japanese']))
            previous['japanese']+=' '+c['japanese'];previous['text']=previous['japanese']
            previous['japaneseAlt']=' '.join(x for x in (previous.get('japaneseAlt',''),c.get('japaneseAlt','')) if x)
            for key in ('end','speechEnd','deliveryEnd','sourceEnd'):previous[key]=c.get(key,c['end'])
            previous['reviewNote']='同一字幕對應嘅日語未完句，已合成完整語意再分析聲線及翻譯。'
        else:joined.append(c)
    return joined


def merge_spans(spans):
    merged=[]
    for s in sorted(spans,key=lambda s:s['start']):
        if merged and s['start']<=merged[-1]['end']:
            merged[-1]['end']=max(merged[-1]['end'],s['end'])
        else: merged.append(dict(s))
    return merged


def uncovered_spans(spans, segments, minimum=.8):
    covered=merge_spans([dict(start=s['start'],end=s['end']) for s in segments])
    missing=[]
    for span in merge_spans(spans):
        cursor=span['start']
        for s in covered:
            if s['end']<=cursor or s['start']>=span['end']: continue
            if s['start']-cursor>=minimum: missing.append(dict(start=cursor,end=s['start']))
            cursor=max(cursor,s['end'])
        if span['end']-cursor>=minimum: missing.append(dict(start=cursor,end=span['end']))
    return missing


def timed_segments(segments,duration,emit):
    """Progress measures completed decoder output, not time waiting for a batch."""
    duration=max(0,float(duration));done=0.0
    def report():
        emit('日語原聲',f'已辨識 {done:.1f} / {duration:.1f} 秒日語。',
             .21+.07*done/max(1,duration),workID='japanese-transcription',workCompleted=done,workTotal=duration)
    report()
    for segment in segments:
        done=max(done,min(duration,max(0,float(segment.end))))
        report()
        yield segment
    # An exhausted iterator has also inspected any trailing silence. Exceptions
    # and interrupted iterators must never report completion.
    done=duration;report()


def analyze(cfg,job,captions,run,emit):
    if cfg.get('sourceLanguage','ja')!='ja':
        original_emit=emit
        def emit(stage,message,progress=None,**extra):
            label='英語' if cfg.get('sourceLanguage')=='en' else '原聲語音'
            return original_emit(stage.replace('日語',label),message.replace('日語',label).replace('日文',label),progress,**extra)
    import numpy as np
    from faster_whisper import WhisperModel
    from faster_whisper.vad import get_speech_timestamps,VadOptions
    from worker import atomic_json
    from model_catalog import resolve,selected,choice
    variant=cfg.get('speechModel') or selected(cfg['storage'],'speech')
    model_path=resolve(cfg['storage'],variant)
    if not (Path(cfg['storage'])/'speech-ready.json').exists():
        raise ValueError('請先喺環境頁部署「日語原聲時間辨識」。')
    # The original mix is the timing authority: separation can remove quiet voices.
    path=job/'japanese-original.wav'
    if not path.exists():
        run([cfg['ffmpeg'],'-v','error','-y','-ss',str(cfg.get('startOffset',0)),'-i',cfg['video'],'-map',f"0:{cfg['sourceAudioStream']}" if cfg.get('sourceAudioStream') is not None else '0:a:0','-t',str(cfg['duration']),'-vn','-ac','1','-ar','16000',path])
    from source_evidence import chinese_captions,merge_ranges
    chinese=chinese_captions(captions,cfg)
    caption_windows=merge_ranges([dict(start=max(0,c['start']-.8),end=min(cfg['duration'],c['end']+.8)) for c in chinese])
    key=hashlib.sha256(json.dumps([REVISION,cfg.get('productionMode','standard'),variant,choice(variant)['revision'],cfg['video'],cfg.get('startOffset',0),cfg['duration'],caption_windows]).encode()).hexdigest()
    cache=job/'japanese-analysis.json'
    saved=json.loads(cache.read_text()) if cache.exists() else {}
    if saved.get('key')!=key:
        emit('日語原聲','按原裝中文字幕時段辨識日語同逐字時間。' if chinese else '未有中文字幕；按原片音軌辨識日語同逐字時間。',.21)
        raw=run([cfg['ffmpeg'],'-v','error','-i',path,'-f','f32le','pipe:1'])
        audio=np.frombuffer(raw,dtype=np.float32)
        options=dict(threshold=.3,min_speech_duration_ms=100,min_silence_duration_ms=220,speech_pad_ms=120)
        spans=get_speech_timestamps(audio,VadOptions(**options))
        spans=[dict(start=s['start']/16000,end=s['end']/16000) for s in spans]
        voice_audio=None
        if cfg.get('dialoguePath'):
            voice=run([cfg['ffmpeg'],'-v','error','-i',cfg['dialoguePath'],'-ar','16000','-ac','1','-f','f32le','pipe:1'])
            voice_audio=np.frombuffer(voice,dtype=np.float32)
            voice_spans=get_speech_timestamps(voice_audio,VadOptions(**dict(options,threshold=.15)))
            spans=merge_spans(spans+[dict(start=s['start']/16000,end=s['end']/16000) for s in voice_spans])
        if chinese:
            # Do not repeatedly re-listen to songs/effects without source captions.
            spans=merge_spans([dict(start=max(s['start'],c['start']),end=min(s['end'],c['end'])) for s in spans for c in chinese if min(s['end'],c['end'])>max(s['start'],c['start'])])
        model=WhisperModel(str(model_path),device='cpu',compute_type='int8',local_files_only=True,cpu_threads=8)
        # Preserve the whole original waveform. Filtering first discarded the
        # first 13 seconds of voiced dialogue in the anime regression sample.
        transcribe_options=dict(clip_timestamps=[t for r in caption_windows for t in (r['start'],r['end'])]) if caption_windows else {}
        segments,_=model.transcribe(audio,language=cfg.get('sourceLanguage','ja'),word_timestamps=True,vad_filter=False,
                                    condition_on_previous_text=False,beam_size=5,**transcribe_options)
        rows=[]
        for s in timed_segments(segments,cfg['duration'],emit):
            rows.append(dict(start=float(s.start),end=float(s.end),text=s.text,
                words=[dict(start=float(w.start),end=float(w.end),word=w.word,probability=float(w.probability)) for w in (s.words or [])]))
        # Recheck locally when separation exposes a voiced passage missed in the
        # original music-heavy mix. Caption text is only an existence hint here.
        if spans and not one_pass(cfg):
            recovery_audio=voice_audio if voice_audio is not None else audio
            gaps=uncovered_spans(spans,rows)
            if gaps: emit('日語原聲','覆核原聲遺漏片段。',.28,workID='japanese-coverage',workCompleted=0,workTotal=len(gaps))
            for gap_index,gap in enumerate(gaps):
                a=max(0,gap['start']-1.2);b=min(cfg['duration'],gap['end']+.3)
                emit('日語原聲',f'覆核原聲遺漏片段 {a:.1f}–{b:.1f} 秒。',.28)
                recovered,_=model.transcribe(recovery_audio[round(a*16000):round(b*16000)],language=cfg.get('sourceLanguage','ja'),word_timestamps=True,vad_filter=False,condition_on_previous_text=False,beam_size=5)
                for s in recovered:
                    words=[dict(start=float(w.start+a),end=float(w.end+a),word=w.word,probability=float(w.probability)) for w in (s.words or []) if w.end>w.start]
                    if not words: continue
                    mid=(words[0]['start']+words[-1]['end'])/2
                    if mid<gap['start']-1.2 or mid>=gap['end']+.1: continue
                    # Context can contain an already recognized phrase followed
                    # by a missed short reply. Keep the uncovered words, not a
                    # duplicate context phrase or an all-or-nothing segment.
                    groups=[];current=[]
                    for w in words:
                        if any(min(w['end'],r['end'])-max(w['start'],r['start'])>.001 for r in rows):
                            if current: groups.append(current);current=[]
                        else: current.append(w)
                    if current: groups.append(current)
                    for group in groups:
                        rows.append(dict(start=group[0]['start'],end=group[-1]['end'],text=''.join(w['word'] for w in group),words=group,recovered=True))
                emit('日語原聲',f'已覆核 {gap_index+1}/{len(gaps)} 段遺漏候選。',.28,workID='japanese-coverage',workCompleted=gap_index+1,workTotal=len(gaps))
            rows.sort(key=lambda s:s['start'])
        saved=dict(key=key,segments=rows,spans=spans);atomic_json(cache,saved)
        del model
    cues=build_cues(saved['segments'],saved['spans'],captions,cfg['duration'],cfg.get('startOffset',0))
    if not cues: raise ValueError('原片未辨識到有效日語，請檢查音軌同開始位置；未改用 OCR 碎句配音。')
    atomic_json(job/'subtitle-context.json',caption_context(captions))
    emit('日語原聲',f'{len(captions)} 段字幕取樣只作參考；按日語原聲建立 {len(cues)} 句對白。',.29)
    return cues


def coverage_report(cfg,job,cues):
    """VAD gaps are candidates for review, not proof of speech or lip movement."""
    path=Path(job)/'japanese-analysis.json'
    analysis=json.loads(path.read_text()) if path.exists() else {}
    import opening
    exclusions=opening.local_ranges(cfg)
    active=[dict(start=c['start'],end=c['end']) for c in cues if c.get('enabled',True)]
    spans=analysis.get('spans',[])
    uncovered=uncovered_spans(spans,active+exclusions,minimum=.6)
    disabled=[dict(index=i+1,start=c['start'],end=c['end'],text=c.get('japanese',c.get('text','')),reason=c.get('reviewNote','')) for i,c in enumerate(cues) if not c.get('enabled',True) and not c.get('captionPolicyExcluded')]
    report=dict(status='needs-review' if uncovered or disabled else ('checked' if analysis else 'not-checked'),uncovered=uncovered,disabled=disabled,method='Japanese source VAD versus enabled dialogue; singing/noise may require exclusion',sourceStart=cfg.get('startOffset',0))
    (Path(job)/'source-coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report


def rescue_caption_speech(cues,captions,spans,duration):
    """Recover a wholly missed caption only with independent speech activity.

    This is VAD + caption corroboration, not caption timing as invented speech.
    Existing/partially covered dialogue stays owned by its original ASR turn.
    """
    import re
    result=list(cues)
    for caption in captions:
        text=caption.get('text','')
        if not any('\u3400'<=c<='\u9fff' for c in text) or re.search(r'(?:作詞|作曲|編曲|字幕組|制作|製作|片頭|片尾|演唱|提供|翻譯[:：]|♪|♫)',text):continue
        a,b=caption['start'],caption['end']
        if any(min(b,c['end'])-max(a,c['start'])>.12 for c in result):continue
        activity=[(max(a,s['start']),min(b,s['end'])) for s in spans if min(b,s['end'])-max(a,s['start'])>=.12]
        if not activity:continue
        start=max(0,activity[0][0]-.04);end=min(duration,activity[-1][1]+.04)
        if not .18<=end-start<=12:continue
        result.append(dict(start=round(start,3),end=round(end,3),text='',japanese='',cantonese='',subtitleHint=text,asrConfidence=0,enabled=True,captionSpeechRescue=True,timingSource='speech-activity-with-caption',speechRegions=[dict(start=x,end=y) for x,y in activity],reviewNote='字幕有對白而日語辨識漏句；以原聲活動時段及本身中文字幕補稿，保留覆核線索。'))
    return sorted(result,key=lambda c:c['start'])
