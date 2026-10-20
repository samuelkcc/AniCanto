"""Preserve words: trim measured silent edges, place, then bounded, pitch-preserving tempo.

Only automatic Normal jobs. Never change source clocks or manual audio, cut
words, cross protected boundaries, or imply a language/quality approval.
"""
import hashlib,json,math,wave
from pathlib import Path

REVISION='natural-finish-2-short-near-miss'
MAX_RATE=1.05
MAX_SAVED_SECONDS=.18
SHORT_MAX_RATE=1.10
SHORT_MAX_SECONDS=2.
SHORT_MAX_OVERRUN=.12


def tempo_limits(length,available):
    near_miss=length<=SHORT_MAX_SECONDS and 0<length-available<=SHORT_MAX_OVERRUN+1e-8
    return (SHORT_MAX_RATE,SHORT_MAX_OVERRUN) if near_miss else (MAX_RATE,MAX_SAVED_SECONDS)


def read(path,default):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return default



def bounded_tempo(cfg,job,cue,path,lengths,placement,i,simulate,run,prior_rate=1.,failures=None):
    """Try complete measured output before rejecting a near-miss candidate.

    Uses the same cumulative tempo/time-saved limits for every reference type;
    never commits a failed trial or sacrifices an already fitting neighbour.
    """
    from natural_delivery import seconds
    from audio_fallback import healthy
    from track_control import UserSkipped
    if not cfg.get('automaticMicroTempo',True):return None
    job=Path(job);length=lengths[i]
    if length is None:return None
    original_length=length*prior_rate
    max_rate,max_saved=tempo_limits(original_length,placement[i]['deadline']-placement[i]['start'])
    for percent in range(1,11):
        rate=1+percent/100;total_rate=prior_rate*rate
        if total_rate>max_rate+1e-8 or original_length-length/rate>max_saved+1e-8:continue
        # Use measured output to decide the fit. A blanket 25 ms margin
        # previously rejected short near-misses before trying FFmpeg.
        trial=list(lengths);trial[i]=length/rate
        predicted=simulate(trial)
        if not predicted[i]['fit'] or any(row['fit'] and not predicted[n]['fit'] for n,row in enumerate(placement)):continue
        # Complete atempo output is measured again; no truncation to a slot.
        key=hashlib.sha256(Path(path).read_bytes()+str(rate).encode()+REVISION.encode()).hexdigest()[:24]
        output=job/'natural-finishing'/key/'micro-tempo.wav';output.parent.mkdir(parents=True,exist_ok=True)
        from track_control import check,UserSkipped
        try:
            check(cfg)
            if not output.is_file():
                run([cfg['ffmpeg'],'-v','error','-i',path,'-af',f'atempo={rate:.4f}','-c:a','pcm_s16le','-y',output])
            if not healthy(output):raise ValueError('Empty tempo candidate')
            measured=seconds(output,cfg,run)
            if measured<length/rate:
                with wave.open(str(output)) as audio:params=audio.getparams();raw=audio.readframes(params.nframes)
                frames=math.ceil(length/rate*params.framerate)
                with wave.open(str(output),'wb') as audio:audio.setparams(params);audio.writeframes(raw+b'\0'*(max(0,frames-params.nframes)*params.nchannels*params.sampwidth))
                measured=seconds(output,cfg,run)
            trial[i]=measured
            actual=simulate(trial)
            if not actual[i]['fit'] or any(row['fit'] and not actual[n]['fit'] for n,row in enumerate(placement)):continue
            # FFmpeg can differ by a few samples; reject large shortening.
            if measured<original_length/max_rate-1e-6 or original_length-measured>max_saved+1e-6:continue
            record=dict(index=cue.get('reviewIndex',i)+1,action='micro-tempo',input=str(path),output=str(output),status='adopted',rate=rate,totalRate=total_rate,allowedMaximumRate=max_rate,originalSeconds=original_length,beforeSeconds=length,candidateSeconds=measured)
            return output,trial,actual,record
        except UserSkipped:raise
        except (OSError,RuntimeError,ValueError) as error:
            if failures is not None:failures.append(dict(index=cue.get('reviewIndex',i)+1,action='micro-tempo',status='failed',rate=rate,error=str(error)[:300]))
            continue
    return None

def finish(cfg,job,cues,paths,run,emit,allow_tempo=True):
    from normal_recovery import padding
    from natural_schedule import prepare,plan
    from natural_delivery import seconds
    from audio_fallback import healthy
    from dubbing import is_vocalization
    from worker import atomic_json
    from speech_timing import natural_window
    if cfg.get('editorRender') or cfg.get('productionMode')!='normal':return paths,None
    job=Path(job);selected=list(paths);audit=read(job/'natural-finishing.json',{}).get('operations',[])
    protected=lambda c: c.get('editorAudio') or c.get('preserveOriginalSpeech') or not c.get('enabled',True) or is_vocalization(c)
    for i,(cue,p) in enumerate(zip(cues,selected)):
        path=Path(p)
        if protected(cue) or not path.is_file() or path.name.startswith('skipped-'):continue
        measured=padding(path)
        if not measured:continue
        params,samples,a,b=measured;key=hashlib.sha256(path.read_bytes()+REVISION.encode()).hexdigest()[:24]
        target=job/'natural-finishing'/key/'silent-edges.wav';target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            with wave.open(str(target),'wb') as f:f.setparams(params);f.writeframes(samples[a*params.nchannels:b*params.nchannels].tobytes())
        selected[i]=target
        previous=next((x for x in reversed(audit) if x.get('output')==str(path) and x.get('status')=='adopted'),{})
        record=dict(totalRate=previous.get('totalRate',previous.get('rate',1.)),index=cue.get('reviewIndex',i)+1,action='trim-padding',input=str(path),output=str(target),status='adopted',beforeSeconds=params.nframes/params.framerate,candidateSeconds=(b-a)/params.framerate,rate=1.,preservedPaddingSeconds=.08)
        if not any(x.get('output')==str(target) for x in audit):audit.append(record)
    placement=prepare(cfg,job,cues,selected,run,emit)
    if placement is None:return selected,None
    def save():atomic_json(job/'natural-finishing.json',dict(revision=REVISION,maximumTempo=MAX_RATE,maximumTimeSavedSeconds=MAX_SAVED_SECONDS,shortNearMiss=dict(maximumTempo=SHORT_MAX_RATE,maximumRecordingSeconds=SHORT_MAX_SECONDS,maximumOverrunSeconds=SHORT_MAX_OVERRUN),sourceClocksUnchanged=True,qualityCertified=False,operations=audit))
    save()
    if allow_tempo and cfg.get('automaticMicroTempo',True):
        planning=read(job/'natural-placement.json',{});base=job.parent.parent if job.parent.name=='tracks' else job
        boundaries=read(base/'natural-scene-boundaries.json',{})
        use_cuts=planning.get('sceneBoundaryStatus')=='detected' and cfg.get('naturalTimingPolicy','micro-shift')=='micro-shift'
        lengths=[row.get('seconds') for row in placement]
        def simulate(lengths):
            if use_cuts:return plan(cfg,cues,lengths,boundaries.get('cuts',[]))
            result=[]
            for c,length in zip(cues,lengths):
                a,b=natural_window(c,cues,cfg['duration'],cfg)
                result.append(dict(start=a,deadline=b,fit=length is not None and length<=b-a))
            return result
        for i,(cue,path) in enumerate(zip(cues,selected)):
            if placement[i]['fit'] or protected(cue) or lengths[i] is None:continue
            length=lengths[i]
            previous=next((x for x in reversed(audit) if x.get('output')==str(path) and x.get('status')=='adopted'),{})
            prior_rate=previous.get('totalRate',previous.get('rate',1.))
            fitted=bounded_tempo(cfg,job,cue,path,lengths,placement,i,simulate,run,prior_rate,failures=audit)
            if fitted:
                output,lengths,_,record=fitted;selected[i]=output;audit.append(record)
                placement=prepare(cfg,job,cues,selected,run,emit);save()
    for i,p in enumerate(selected):
        record=next((x for x in reversed(audit) if x.get('output')==str(p) and x.get('status')=='adopted'),{})
        placement[i]['tempoRate']=record.get('totalRate',record.get('rate',1.))
    save()
    from project_store import resolve_issues
    resolve_issues(cfg,job,{cues[i].get('reviewIndex',i)+1 for i,p in enumerate(placement) if p['fit']},kinds={'timing-overrun'})
    return selected,placement
