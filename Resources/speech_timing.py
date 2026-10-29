"""Measured, non-truncating delivery within immutable source speech clocks."""
import math


def text_budget(seconds):
    """A drafting target, never a reason to delete a name or meaningful clause."""
    return max(1, int(max(0., float(seconds))*4.5))


def window(cue, cues, duration):
    if cue.get('preserveOriginalSpeech'):
        start,end=float(cue['start']),float(cue['end'])
        if not (math.isfinite(start+end) and 0<=start<end<=float(duration)+.001):
            raise ValueError('Invalid preserved source timing.')
        return start,end
    if cue.get('_retryRetained'):
        retained=cue['_retryRetained'];start=float(retained['start']);end=float(retained['end'])
        if not (0<=start<end<=float(duration)+.001):raise ValueError('Invalid retained recording timing.')
        return start,end
    start=max(0.,float(cue.get('speechStart',cue['start'])))
    end=min(float(duration),float(cue.get('speechEnd',cue['end'])),float(cue.get('deliveryEnd',cue['end'])))
    # Witnessed simultaneous source speech is allowed. Keeping each source
    # deadline prevents introducing an overlap where none existed originally.
    if not math.isfinite(start+end) or end<=start:raise ValueError('日文發聲時段無效，未用靜音替代。')
    return start,end


def natural_window(cue,cues,duration,cfg=None):
    """Use an empty following gap, without delaying another line or OP/ED."""
    start,end=window(cue,cues,duration)
    if cue.get('_retryRetained') or cue.get('preserveOriginalSpeech'):return start,end
    if __import__('speech_duration').enabled(cfg):return __import__('speech_duration').deadline(cfg,cue,cues,duration)
    following=[window(c,cues,duration)[0] for c in cues
               if c is not cue and __import__('safe_vocal_capacity').is_barrier(c,cues,cfg) and (c.get('enabled',True) or c.get('preserveOriginalSpeech')) and window(c,cues,duration)[0]>start+.001]
    next_start=min(following,default=float(duration))
    # Existing overlapping Japanese turns retain their own source deadline.
    preserved_overlap=any(c is not cue and c.get('preserveOriginalSpeech') and __import__('safe_vocal_capacity').is_barrier(c,cues,cfg) and window(c,cues,duration)[0]<end and window(c,cues,duration)[1]>start for c in cues)
    if next_start>=end and not preserved_overlap:
        end=next_start
        # The collapsed desktop mode keeps the take inside the witnessed Japanese
        # speech window. A spare tail over an untranscribed source line is what
        # Samuel hears as a second voice, so it is not used to absorb an overrun.
        if __import__('source_mora').cap_requested(cfg):
            cap=float(cue.get('speechEnd',cue['end']))+__import__('source_mora').END_GRACE_SECONDS
            # The caption of this same line can run past the witnessed speech span.
            # The take may use that tail, but never past its own caption end, so a
            # Chinese subtitle window is never left without Cantonese audio.
            caption_end=min(float(cue['end']),float(cue.get('deliveryEnd',cue['end'])))
            end=min(end,max(cap,caption_end))
        end=min(end,next_start)
    import opening
    for interval in opening.local_ranges(dict(cfg or {},duration=float(duration))):
        a=float(interval['start']) if isinstance(interval,dict) else float(interval[0])
        if start<a:end=min(end,a)
    return start,min(end,float(duration))


def tempo_filter(rate):
    # Each stage <=2 avoids FFmpeg skipping samples at a large single ratio.
    stages=[]
    while rate>2:
        stages.append('atempo=2');rate/=2
    stages.append(f'atempo={rate:.10f}')
    return ','.join(stages)


def fit_pcm(cfg, raw, target, run):
    """Compress all words; measure samples, do not trim/pad or shift a neighbour."""
    from audio_format import delivery_rate
    sr=delivery_rate(cfg);available=math.floor(target*sr+1e-6)
    if available<1 or not raw:raise ValueError('配音或日文發聲時段係空白。')
    if len(raw)//2<=available:return raw,1.
    from pathlib import Path
    import tempfile,wave
    with tempfile.TemporaryDirectory(prefix='anicanto-slot-') as folder:
        source=Path(folder)/'full.wav'
        with wave.open(str(source),'wb') as audio:
            audio.setparams((1,2,sr,0,'NONE','not compressed'));audio.writeframes(raw)
        rate=(len(raw)//2)/max(1,available-round(.008*sr))
        for _ in range(6):
            result=run([cfg['ffmpeg'],'-v','error','-i',source,'-af',tempo_filter(rate),
                        '-ar',str(sr),'-ac','1','-f','s16le','pipe:1'])
            if not result:raise ValueError('配音調速後係空白，未輸出靜音替代。')
            if len(result)//2<=available:return result,rate
            rate*=max(1.01,(len(result)//2)/max(1,available-round(.012*sr)))
    raise ValueError('完整配音調速後仍超出日文時段；原錄音已保留，未截斷字句。')
