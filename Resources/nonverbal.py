"""Conservatively retain original non-lexical performance; never restore all vocals."""
import json
import hashlib
import math
import sys
import re
from pathlib import Path

LABELS=('laughter','baby_laughter','belly_laugh','crying_sobbing','sigh','breathing','gasp','screaming','shout','yell')

# Keep the validated model context; raw probabilities are not cross-model calibrated.
# The one-second AST trial reduced event confidence on public evaluation clips.
CLASSIFICATION_REVISION='performance-taxonomy-4-validated-context'


def classification_profile(platform=None):
    if (platform or sys.platform)=='win32':
        return dict(backend='ast-audioset-f826b80d',windowSeconds=5.,hopSeconds=2.5)
    return dict(backend='apple-soundanalysis-v1',windowSeconds=1.,hopSeconds=.5)


def validate_classification(rows):
    if not isinstance(rows,list):raise ValueError('Invalid nonverbal classification result')
    for row in rows:
        if not isinstance(row,dict) or any(not isinstance(row.get(k),(int,float)) or isinstance(row.get(k),bool) or not math.isfinite(row[k]) for k in ('start','duration')) or row['start']<0 or row['duration']<=0:
            raise ValueError('Invalid nonverbal classification time range')
        if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or not 0<=v<=1 for k,v in row.items() if k not in ('start','duration')):
            raise ValueError('Invalid nonverbal classification confidence')


def classification(cfg,job,run):
    """Cache source evidence once across language/engine tracks; never trust v2 clocks."""
    source=Path(cfg['dialoguePath'])
    with source.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    profile=classification_profile()
    identity=[CLASSIFICATION_REVISION,digest,profile]
    key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()
    local=Path(job)/'nonverbal-classification-v3.json'
    shared=Path(cfg['storage'])/'cache/nonverbal'/(key+'.json') if cfg.get('storage') else local
    for cache in dict.fromkeys((local,shared)):
        try:saved=json.loads(cache.read_text())
        except (OSError,ValueError):continue
        if isinstance(saved,dict) and saved.get('key')==key:
            try:validate_classification(saved.get('rows'))
            except ValueError:continue
            return saved['rows']
    rows=json.loads(run([cfg['executable'],'--classify-performance',str(source)]))
    if not isinstance(rows,list):raise ValueError('Invalid nonverbal classification result')
    validate_classification(rows)
    from atomic_files import write_json
    saved=dict(key=key,revision=CLASSIFICATION_REVISION,**profile,rows=rows)
    write_json(shared,saved)
    if shared!=local:write_json(local,saved)
    return rows


def source_vocalization(cue):
    source=re.sub(r'[\s、。！？!?…ーっッ〜～・\-]', '',cue.get('japanese',cue.get('text','')))
    return bool(cue.get('nonlexicalTail') or source and (re.fullmatch(r'[あぁアァいぃイィうぅウゥえぇエェおぉオォ]+',source) or source in ('はあ','はぁ','ハア','ハァ')))


def lexical_ranges(cues,words):
    """Use witnessed word spans to retain pauses inside a long speech turn.

    Missing word evidence retains the entire cue as an exclusion. Never infer
    a laugh just from a transcript gap; event_ranges still requires classifier evidence.
    """
    result=[]
    for cue in cues:
        matching=[w for w in words if w.get('word','').strip() and w.get('end',0)>w.get('start',0)
                  and cue['start']<w['end'] and cue['end']>w['start']]
        if not matching:result.append(cue);continue
        # Trust narrower boundaries only when timed words cover the cue's text.
        clean=lambda s:''.join(c for c in s if c.isalnum())
        source=clean(cue.get('japanese',cue.get('text','')))
        heard=clean(''.join(w['word'] for w in matching))
        if not source or source not in heard:
            result.append(cue);continue
        result.extend(dict(start=max(cue['start'],w['start']),end=min(cue['end'],w['end']),japanese=w['word']) for w in matching)
    return result


def event_ranges(rows, dialogue, duration):
    """Classifier evidence is required. Subtract recognized lexical speech, including padding."""
    spans=[]
    for row in rows:
        label=max(LABELS,key=lambda k:row.get(k,0))
        score=row.get(label,0)
        if score<.55 or (row.get('speech',0)>.2 and not (label in ('screaming','shout','yell') and score>=.7)) or row.get('singing',0)>.2: continue
        a=max(0,float(row['start']));b=min(duration,a+float(row['duration']))
        pieces=[(a,b)]
        for c in dialogue:
            utterance=re.sub(r'[\s、。！？!?…ーっッ]', '',c.get('japanese',c.get('text','')))
            if source_vocalization(c):continue
            left=max(0,c['start']-.12);right=c['end']+.15
            pieces=[p for x,y in pieces for p in ((x,min(y,left)),(max(x,right),y)) if p[1]-p[0]>.12]
        spans.extend(dict(start=x,end=y,label=label,confidence=score) for x,y in pieces if y-x>=.20)
    merged=[]
    for row in sorted(spans,key=lambda r:r['start']):
        if merged and row['start']<=merged[-1]['end']:
            merged[-1]['end']=max(row['end'],merged[-1]['end'])
        else:merged.append(dict(row))
    return merged


def duck_events(events, dialogue):
    result=[]
    for event in events:
        boundaries=sorted({event['start'],event['end']} | {max(event['start'],min(event['end'],c[k])) for c in dialogue for k in ('start','end')})
        for a,b in zip(boundaries,boundaries[1:]):
            if b<=a: continue
            overlap=any(a<c['end'] and b>c['start'] for c in dialogue)
            result.append(dict(event,start=a,end=b,gain=.4 if overlap else 1.0))
    return result


def missing_events(rows,events,duration):
    result=[]
    for row in rows:
        label=max(LABELS,key=lambda k:row.get(k,0));score=row.get(label,0)
        if score<.55:continue
        a=max(0,row['start']);b=min(duration,a+row['duration'])
        ranges=sorted((max(a,e['start']),min(b,e['end'])) for e in events if e['start']<b and e['end']>a)
        covered=0;end=a
        for x,y in ranges:covered+=max(0,y-max(x,end));end=max(end,y)
        if b-a-covered>.2:result.append(dict(start=a,end=b,label=label,confidence=score,missingSeconds=round(b-a-covered,3),reason='混合語音／歌聲或未有可安全獨立抽取嘅片段；未自動合成替代聲。'))
    return result


def restore(cfg,job,cues,voice,run,emit):
    if not cfg.get('dialoguePath') or not cfg.get('executable'):return voice
    emit('原聲表演','偵測叫聲、笑聲、呼吸同哭聲；只補回有把握嘅非語言片段。',.92)
    rows=classification(cfg,job,run)
    source=job/'dual-asr-cues.json'
    lexical=json.loads(source.read_text()) if source.exists() else cues
    analysis=job/'japanese-analysis.json'
    if analysis.exists():
        words=[w for s in json.loads(analysis.read_text()).get('segments',[]) for w in s.get('words',[])]
        lexical=lexical_ranges(lexical,words)
    lexical=[c for c in lexical if not source_vocalization(c)]
    original_ranges=original_sound_ranges(rows,lexical,cfg['duration'])
    cfg['_originalSoundRanges']=original_ranges
    from dubbing import is_vocalization
    retained=[(c['start'],c['end']) for c in cues if is_vocalization(c)]
    events=subtract_restored(event_ranges(rows,lexical,cfg['duration']),original_ranges+retained)
    # Also protect the new dubbing from an original breath/laugh over a delayed line.
    audible=[dict(start=c.get('subtitleStart',c['start']),end=c.get('subtitleEnd',c['end'])) for c in cues]
    # Already excluded original lexical speech above. Preserve the performance
    # even if the NEW Cantonese line runs across it; duck only that overlap.
    events=duck_events(events,audible)
    (job/'nonverbal-report.json').write_text(json.dumps(dict(events=events,originalSoundRanges=original_ranges,reviewEvents=missing_events(rows,events+[dict(start=a,end=b) for a,b in original_ranges+retained],cfg['duration']),classificationRevision=CLASSIFICATION_REVISION,**classification_profile(),method='local-sound-classifier; original-lexical-speech-excluded; cantonese-overlap-ducked',limitation='Sounds overlapping original Japanese speech or not confidently classified remain excluded.'),ensure_ascii=False,indent=2))
    if not events:
        emit('原聲表演','未找到可安全獨立補回嘅非語言片段；冇混回整條日語人聲。',.92)
        return voice
    # Build a separate track with short fades at each boundary, at original times.
    pieces=[]
    for i,e in enumerate(events):
        d=e['end']-e['start'];delay=round(e['start']*1000)
        # FFmpeg duration options reject scientific notation (e.g. a floating
        # point remainder of 9e-14 for an exactly 25 ms event).
        pieces.append(f"[1:a]atrim=start={e['start']:.6f}:end={e['end']:.6f},asetpts=PTS-STARTPTS,volume={e.get('gain',1.0)},afade=t=in:d=0.015,afade=t=out:st={max(0,d-.025):.6f}:d=0.025,adelay={delay}:all=1[n{i}]")
    labels=''.join(f'[n{i}]' for i in range(len(events)))
    pieces.append(f'[0:a]{labels}amix=inputs={len(events)+1}:duration=first:normalize=0,alimiter=limit=0.95:level=0:latency=1[out]')
    output=job/'cantonese-performance.wav'
    from audio_format import delivery_rate
    run([cfg['ffmpeg'],'-v','error','-y','-i',voice,'-i',cfg['dialoguePath'],'-filter_complex',';'.join(pieces),'-map','[out]','-ar',str(delivery_rate(cfg)),'-ac','1','-c:a','pcm_s16le',output])
    emit('原聲表演',f'已按原本時間補回 {len(events)} 段叫聲／笑聲／呼吸等非語言表演。',.92)
    return output


def original_sound_ranges(rows, lexical, duration):
    """Only positively analysed non-speech windows; exclude uncertain neighbours.

    ASR silence alone never authorizes restoring the Japanese track.
    """
    safe=[]; blocked=[(max(0,c['start']-.2),min(duration,c['end']+.2)) for c in lexical]
    for row in rows:
        a=max(0,float(row['start'])); b=min(duration,a+float(row['duration']))
        if row.get('speech',1) >= .10 or max(row.get('singing',0),row.get('choir_singing',0),row.get('rapping',0)) >= .10:
            blocked.append((a,b))
        else: safe.append((a,b))
    pieces=[]
    for a,b in safe:
        pending=[(a,b)]
        for left,right in blocked:
            pending=[p for x,y in pending for p in ((x,min(y,left)),(max(x,right),y)) if p[1]>p[0]]
        pieces.extend(pending)
    merged=[]
    for a,b in sorted(pieces):
        if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else:merged.append((a,b))
    return [(a,b) for a,b in merged if b-a>=.25]


def subtract_restored(events,ranges):
    result=[]
    for event in events:
        pieces=[(event['start'],event['end'])]
        for left,right in ranges:
            pieces=[p for a,b in pieces for p in ((a,min(b,left)),(max(a,right),b)) if p[1]-p[0]>.02]
        result.extend(dict(event,start=a,end=b) for a,b in pieces)
    return result


def write_preservation_mask(path, ranges, duration, rate=48000):
    """A bounded-memory stereo gain track, independent of FFmpeg expression depth."""
    import math
    import wave
    import numpy as np
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('音效保留時長無效。')
    spans=[]
    for a,b in ranges:
        if not math.isfinite(a+b) or a < 0 or b <= a or b > duration + .01:
            raise ValueError('音效保留時段無效。')
        spans.append((a,min(b,duration)))
    spans.sort()
    # Merge overlapping spans; never amplify above unity or invert the background.
    merged=[]
    for a,b in spans:
        if merged and a <= merged[-1][1]: merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else: merged.append((a,b))
    path=Path(path);temporary=path.with_suffix('.partial.wav')
    total=math.ceil(duration*rate);cursor=0
    try:
        with wave.open(str(temporary),'wb') as out:
            out.setparams((2,2,rate,0,'NONE','not compressed'))
            for first in range(0,total,rate):
                count=min(rate,total-first)
                t=(np.arange(count,dtype=np.float64)+first)/rate
                gain=np.zeros(count,dtype=np.float64)
                while cursor<len(merged) and merged[cursor][1]<first/rate: cursor+=1
                for a,b in merged[cursor:]:
                    if a>t[-1]:break
                    gain=np.maximum(gain,np.clip(np.minimum((t-a)/.04,(b-t)/.04),0,1))
                pcm=np.rint(gain*32767).astype('<i2')
                out.writeframes(np.repeat(pcm[:,None],2,axis=1).tobytes())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def preserve_background(cfg,job,background,run,emit):
    ranges=cfg.get('_originalSoundRanges',[])
    if not ranges:return background
    job=Path(job)
    mask=job/'background-preservation-mask.wav'
    write_preservation_mask(mask,ranges,float(cfg['duration']))
    # Fixed-size filter graph: stereo gain values are identical in both channels.
    # PCM16 unity is 32767/32768; compensate before forming complementary gains.
    graph=("[2:a]volume=32768/32767,asplit=2[mask][inverseIn];"
           "[inverseIn]aeval=exprs='1-val(0)|1-val(1)'[inverse];"
           "[0:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[base];"
           "[1:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[source];"
           "[base][inverse]amultiply[bg];[source][mask]amultiply[original];"
           "[bg][original]amix=inputs=2:duration=first:normalize=0[out]")
    from source_language import audio_label
    graph=graph.replace('[1:a]',f'[{audio_label(cfg,1)}]')
    script=job/'background-preservation.ffgraph';script.write_text(graph)
    output=job/'background-preserved.wav';temporary=job/'background-preserved.partial.wav'
    try:
        run([cfg['ffmpeg'],'-v','error','-y','-i',background,'-ss',str(cfg.get('startOffset',0)),'-t',str(cfg['duration']),'-i',cfg['video'],'-i',mask,'-/filter_complex',script,'-map','[out]','-t',str(cfg['duration']),'-ar','48000','-ac','2','-c:a','pcm_s16le',temporary])
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    emit('原聲音效',f'已喺 {len(ranges)} 段確認非對白時段保留原片音樂、音效同人聲表演。',.93)
    return output
