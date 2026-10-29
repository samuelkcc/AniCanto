"""Bounded natural-speed timing; source clocks and waveforms stay immutable.

This plans audio placement, not speaker identity or semantic approval. Visual
shot changes are diagnostic only; dialogue and preserved ranges constrain timing.
Infeasible lines remain explicitly unresolved; no speed-up, cropping or filler.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import os
import subprocess
import time

REVISION='natural-dialogue-capacity-6-source-locked'
MAX_SHIFT=.5


def plan(cfg,cues,lengths,cuts=()):
    from speech_timing import window,natural_window
    from dubbing import is_vocalization
    if cfg.get('naturalTimingPolicy','source-locked')!='micro-shift':
        rows=[]
        for i,c in enumerate(cues):
            a,b=natural_window(c,cues,cfg['duration'],cfg);length=lengths[i] if i<len(lengths) else None
            if c.get('preserveOriginalSpeech'):a,b=window(c,cues,cfg['duration'])
            rows.append(dict(index=c.get('reviewIndex',i)+1,sourceStart=a,sourceEnd=c.get('speechEnd',c['end']),start=a,deadline=b,
                seconds=length,shift=0.,method='source-preserved' if c.get('preserveOriginalSpeech') else 'source-locked',originalSource=bool(c.get('preserveOriginalSpeech')),fit=bool(length is not None and math.isfinite(length) and 0<length<=b-a)))
        return rows
    import opening
    duration=float(cfg['duration'])
    # Never move speech into deliberately preserved source/OP/ED ranges.
    protected=opening.local_ranges(cfg)
    for cue in cues:
        if cue.get('preserveOriginalSpeech') and __import__('safe_vocal_capacity').is_barrier(cue,cues,cfg):
            start,end=window(cue,cues,duration)
            protected.append(dict(start=start,end=end))
    # Anime motion/camera cuts do not establish a spoken scene boundary.
    # Hard boundaries require an actual preserved source/OP/ED interval.
    barriers=sorted(set([0.,duration]+[float(r[k]) for r in protected for k in ('start','end')]))
    rows=[];entries=[]
    for i,c in enumerate(cues):
        start,end=window(c,cues,duration);_,deadline=natural_window(c,cues,duration,cfg)
        length=lengths[i] if i<len(lengths) else None
        valid=length is not None and math.isfinite(length) and length>0
        row=dict(index=c.get('reviewIndex',i)+1,sourceStart=start,sourceEnd=end,start=start,
            deadline=deadline,seconds=length,shift=0.,method='source-clock',fit=bool(valid and length<=deadline-start))
        rows.append(row)
        preserved=bool(c.get('preserveOriginalSpeech'))
        if preserved:
            row.update(deadline=end,method='source-preserved',originalSource=True,fit=bool(valid and length<=end-start+.001))
        if preserved and not __import__('safe_vocal_capacity').is_barrier(c,cues,cfg):continue
        if not c.get('enabled',True) and not preserved:continue
        locked=bool(c.get('editorAudio') or c.get('preserveOriginalSpeech') or is_vocalization(c) or not valid)
        if any(start<r['end'] and end>r['start'] for r in protected):locked=True
        left=max(b for b in barriers if b<=start+.001)
        right=min((b for b in barriers if b>=end-.001),default=duration)
        # Keep a fitting take on its source clock. Only bounded redistribution
        # of actual dialogue can borrow free time; a shot cut is not an obstacle.
        measured=end-start if preserved else ((length+.001) if valid else end-start)
        entries.append(dict(i=i,a=start,b=end,length=measured,locked=locked,left=left,right=right))
    entries.sort(key=lambda e:(e['a'],e['b'],e['i']))
    # Original simultaneous speech remains fixed; never serialize it into a
    # changed performance or introduce another voice into its occupied interval.
    overlap=set()
    for n,e in enumerate(entries):
        for other in entries[n+1:]:
            if other['a']>=e['b']-.001:break
            overlap.update((e['i'],other['i']))
    for e in entries:
        if e['i'] in overlap:e['locked']=True
    # Fixed overlapping source groups act as one obstacle for adjacent turns.
    blocks=[]
    for e in entries:
        if blocks and e['a']<max(x['b'] for x in blocks[-1])-.001:blocks[-1].append(e)
        else:blocks.append([e])
    runs=[];active=[];lower=0.
    for n,block in enumerate(blocks):
        if len(block)>1 or block[0]['locked']:
            start=min(e['a'] for e in block)
            if active:runs.append((active,lower,start));active=[]
            occupied=max(max(e['b'],e['a']+e['length']) if rows[e['i']]['fit'] else e['b'] for e in block)
            lower=min(duration,occupied)
            continue
        e=block[0]
        if active:
            prior=active[-1]
            split=(e['a']-prior['b']>2
                   or any(prior['b']-.001<=b<=e['a']+.001 for b in barriers))
            if split:
                # A real silence gap can separate independent runs. An
                # arbitrary 12-second chunk cannot: coupled neighbours may need
                # capacity on both sides of that artificial boundary.
                boundary=(prior['b']+e['a'])/2
                between=[b for b in barriers if prior['b']-.001<=b<=e['a']+.001]
                if between:boundary=between[0]
                runs.append((active,lower,boundary));active=[];lower=between[-1] if between else boundary
        active.append(e)
    if active:runs.append((active,lower,duration))

    def solve(group,left,right):
        if not group:return
        lo=[max(left,e['left'],e['a']-MAX_SHIFT) for e in group]
        hi=[min(e['a']+MAX_SHIFT,right-e['length'],e['right']-e['length']) for e in group]
        latest=list(hi)
        for n in range(len(group)-2,-1,-1):latest[n]=min(latest[n],latest[n+1]-group[n]['length'])
        if any(a>b+1e-8 for a,b in zip(lo,latest)):
            # One impossible utterance must not prevent healthy neighbours from
            # being scheduled. Reserve its original interval, solve both sides.
            bad=max(range(len(group)),key=lambda n:group[n]['length']-(rows[group[n]['i']]['deadline']-group[n]['a']))
            e=group[bad];rows[e['i']]['method']='timing-capacity-exhausted'
            occupied=max(e['b'],e['a']+e['length']) if rows[e['i']]['fit'] else e['b']
            solve(group[:bad],left,e['a']);solve(group[bad+1:],occupied,right)
            return
        previous=left
        for n,e in enumerate(group):
            start=max(lo[n],previous,min(e['a'],latest[n]))
            end=start+e['length'];row=rows[e['i']]
            row.update(start=start,deadline=end,shift=round(start-e['a'],6),fit=True,
                method='bounded-natural-placement' if abs(start-e['a'])>.00001 else 'source-clock')
            previous=end
    for group,left,right in runs:
        # A healthy block needs no redistribution at all.
        if any(not rows[e['i']]['fit'] for e in group):solve(group,left,right)
    return rows


def cut_scan(cfg,args):
    """Bounded, cancellable media scan; do not leave a frozen-looking worker."""
    from track_control import check
    options=dict(stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if os.name=='nt':options['creationflags']=getattr(subprocess,'CREATE_NO_WINDOW',0)
    with subprocess.Popen([str(a) for a in args],**options) as process:
        deadline=time.monotonic()+120
        try:
            while True:
                check(cfg)
                try:
                    out,error=process.communicate(timeout=.5)
                    if process.returncode:raise RuntimeError(error.decode(errors='replace')[-800:])
                    return out
                except subprocess.TimeoutExpired:
                    if time.monotonic()>=deadline:raise RuntimeError('輕量場景檢查已達兩分鐘上限；保留原時間同錄音。')
        finally:
            if process.poll() is None:
                process.kill();process.communicate()


def scene_boundaries(cfg,job,run,emit):
    """One cached, low-resolution local cut scan, shared by output languages.

    No vision model, OCR, saved frames or model downloads. If unavailable, the
    caller keeps fixed timing rather than guessing where a scene ends.
    """
    from worker import atomic_json
    from track_control import check,UserSkipped
    video=Path(cfg.get('video',''))
    if not video.is_file():return dict(status='unavailable',cuts=[],reason='source-video-unavailable')
    info=video.stat()
    identity=[REVISION,str(video.resolve()),info.st_size,info.st_mtime_ns,cfg.get('startOffset',0),cfg['duration']]
    key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()
    job=Path(job);parent=job.parent.parent if job.parent.name=='tracks' else job
    cache=parent/'natural-scene-boundaries.json'
    try:saved=json.loads(cache.read_text())
    except (OSError,ValueError):saved={}
    if saved.get('key')==key:return saved
    check(cfg)
    emit('自然語速編排','有完整錄音超時；一次輕量檢查畫面切換邊界，作診斷參考；實際微調以對白及保留原聲範圍為準。唔載入視覺 AI 模型。',.86)
    try:
        raw=cut_scan(cfg,[cfg['ffmpeg'],'-v','error','-nostats','-ss',str(cfg.get('startOffset',0)),
            '-i',video,'-t',str(cfg['duration']),'-an','-sn','-vf',
            r"scale=160:-2,select=gt(scene\,.35),metadata=print:file=-",'-f','null','-'])
        text=raw.decode(errors='replace') if isinstance(raw,bytes) else str(raw)
        cuts=[float(t) for t in re.findall(r'pts_time:([0-9.]+)',text)]
        saved=dict(key=key,status='detected',cuts=sorted(set(t for t in cuts if 0<t<cfg['duration'])),method='low-resolution-ffmpeg-cut-score',visualUnderstanding=False)
    except UserSkipped:raise
    except (OSError,RuntimeError,ValueError) as error:
        saved=dict(key=key,status='unavailable',cuts=[],reason=str(error)[:300])
        emit('自然語速編排','畫面切換邊界未能確認；保留原本配音時間，唔盲目移動台詞。',.86)
    check(cfg);atomic_json(cache,saved)
    return saved


def prepare(cfg,job,cues,paths,run,emit):
    from worker import atomic_json
    from natural_delivery import seconds
    from speech_timing import natural_window
    from audio_fallback import healthy
    lengths=[]
    for path in paths:
        try:lengths.append(seconds(path,cfg,run) if not Path(path).name.startswith('skipped-') and healthy(path) else None)
        except (OSError,RuntimeError,ValueError):lengths.append(None)
    overlong=[i for i,(c,length) in enumerate(zip(cues,lengths)) if c.get('enabled',True) and length is not None and length>natural_window(c,cues,cfg['duration'],cfg)[1]-natural_window(c,cues,cfg['duration'],cfg)[0]]
    boundaries=dict(status='not-required',cuts=[])
    enabled=cfg.get('naturalTimingPolicy','source-locked')=='micro-shift' and not cfg.get('editorRender')
    # Dialogue clocks and protected audio constrain safe placement directly.
    # The old visual-cut scan could time out after two minutes and disable all
    # placement, creating dozens of overlaps; cuts are not a hard constraint.
    if enabled:rows=plan(cfg,cues,lengths,boundaries.get('cuts',[]))
    else:
        rows=[]
        for i,c in enumerate(cues):
            a,b=natural_window(c,cues,cfg['duration'],cfg);length=lengths[i]
            rows.append(dict(index=c.get('reviewIndex',i)+1,sourceStart=a,sourceEnd=c.get('speechEnd',c['end']),start=a,deadline=b,
                seconds=length,shift=0.,fit=bool(length is not None and length<=b-a),method='source-clock'))
    moved=sum(abs(r['shift'])>.00001 for r in rows)
    report=dict(revision=REVISION,maximumShiftSeconds=MAX_SHIFT if enabled else 0.,timingPolicy=cfg.get('naturalTimingPolicy','source-locked'),sceneBoundaryStatus=boundaries['status'],
        sceneMethod=boundaries.get('method'),moved=moved,overlongBefore=len(overlong),
        unresolved=[r['index'] for r in rows if r['seconds'] is not None and not r['fit']],
        rate=1.,sourceClocksUnchanged=True,qualityCertified=False,rows=rows)
    atomic_json(Path(job)/'natural-placement.json',report)
    if moved:emit('自然語速編排',f'已微調 {moved} 句配音起點（每句最多 {MAX_SHIFT:.1f} 秒）；保留完整錄音、自然語速同原本字幕時間。',.87)
    return rows
