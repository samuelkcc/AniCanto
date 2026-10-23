"""Bounded automatic lower-screen subtitle region detection.

One small discovery pass, followed by the existing timestamped OCR pass. A
weak/empty discovery uses a wide lower-screen band; it never asks for a crop.
No language model or second ASR pass is involved.
"""
import json
import math
from pathlib import Path

SEARCH=dict(x=.01,y=.55,width=.98,height=.445)


def sample_times(duration,speech=(),limit=18):
    if not math.isfinite(duration) or duration<=0:raise ValueError('Invalid OCR duration')
    heard=sorted({round((max(0,float(r['start']))+min(duration,float(r['end'])))/2,3)
                  for r in speech if float(r['end'])>float(r['start'])})
    # Spread speech samples across the episode rather than sampling just OP.
    points=[heard[min(len(heard)-1,int(i*len(heard)/12))] for i in range(min(12,len(heard)))]
    points += [duration*(i+.5)/6 for i in range(6)]
    return sorted({round(min(max(0,t),max(0,duration-.05)),3) for t in points})[:limit]


def choose_region(rows):
    clusters=[]
    for row in rows:
        for box in row.get('boxes',[]):
            try:
                x,y,w,h=(float(box[k]) for k in ('x','y','width','height'))
                text=str(box['text']).strip();confidence=float(box.get('confidence',1))
            except (KeyError,TypeError,ValueError):continue
            if not all(math.isfinite(v) for v in (x,y,w,h,confidence)):continue
            if confidence<.45 or not(0<=x<x+w<=1.001 and 0<=y<y+h<=1.001):continue
            if len(''.join(c for c in text if c.isalnum()))<2 or w<.06 or h>.3:continue
            # Reject corner logos, but keep off-centre dialogue captions.
            if x+w<.20 or x>.80:continue
            center=y+h/2
            cluster=next((c for c in clusters if abs(c['center']-center)<.07),None)
            if cluster is None:
                cluster=dict(center=center,hits=set(),texts=set(),bounds=[]);clusters.append(cluster)
            cluster['hits'].add(row['index']);cluster['texts'].add(text);cluster['bounds'].append((y,y+h))
    candidates=[c for c in clusters if len(c['hits'])>=2 and len(c['texts'])>=2]
    if not candidates:return dict(SEARCH),False
    best=max(candidates,key=lambda c:(len(c['hits']),len(c['texts']),c['center']))
    # Include nearby second-line subtitles and allow breathing room for outlines.
    lines=[c for c in candidates if abs(c['center']-best['center'])<=.22]
    top=max(0,min(a for c in lines for a,b in c['bounds'])-.065)
    bottom=min(1,max(b for c in lines for a,b in c['bounds'])+.065)
    return dict(x=SEARCH['x'],y=SEARCH['y']+top*SEARCH['height'],width=SEARCH['width'],
                height=max(.05,(bottom-top)*SEARCH['height'])),True


def discover(w,cfg,job):
    if cfg.get('ocrRect') is not None and not cfg.get('ocrAutoRegion'):return
    folder=Path(job)/'ocr-discovery';folder.mkdir(exist_ok=True)
    points=sample_times(float(cfg['duration']),cfg.get('_ocrSpeechWindows',()))
    w.emit('字幕位置偵測','冇可用文字字幕軌；自動檢查畫面下方字幕，唔需要手動畫框。',.27,
           workID='ocr-discovery',workCompleted=0,workTotal=len(points))
    scan=dict(cfg,ocrRect=SEARCH,ocrColor='original')
    # Only our bounded discovery images are passed to the helper.
    for old in folder.glob('*.jpg'):old.unlink()
    for i,point in enumerate(points):
        w.run([cfg['ffmpeg'],'-v','error','-y','-ss',str(cfg.get('startOffset',0)+point),
               '-i',cfg['video'],'-frames:v','1','-vf',w.ocr_filter(scan,False),folder/f'{i:03d}.jpg'])
    rows=run_ocr(w,cfg,folder)
    region,detected=choose_region(rows)
    cfg.update(ocrRect=region,ocrEvidenceOnly=True)
    w.atomic_json(Path(job)/'ocr-region.json',dict(revision=1,region=region,detected=detected,
        sampledSeconds=points,searchRegion=SEARCH,source='automatic-lower-screen',
        fallback=None if detected else 'wide-lower-screen-band'))
    w.emit('字幕位置偵測','已定位畫面下方字幕；按日文聽寫時間整合。' if detected else
           '未確認固定字幕位置；繼續掃描下方範圍，冇字幕時沿用日文原聲。',.28,
           workID='ocr-discovery',workCompleted=len(points),workTotal=len(points))


SCAN_REVISION=3


def select_speech_frames(files,speech,duration):
    """Retain adjacent samples per heard turn, plus pairs within long turns.

    OCR corroborates ASR; never infer missing dialogue from unscanned video.
    Files carry real millisecond PTS. No fabricated ordinal-frame timestamps.
    """
    from bisect import bisect_left,bisect_right
    files=sorted(files);times=[int(p.stem)/1000 for p in files];selected=set()
    for cue in speech:
        try:start=max(0,float(cue['start']));end=min(duration,float(cue['end']))
        except (KeyError,ValueError,TypeError):continue
        if not math.isfinite(start+end) or end<=start:continue
        lo=bisect_left(times,max(0,start-.12));hi=bisect_right(times,end+.12)
        if lo==hi:continue
        # A pair is checked near the middle of each <= 2 s part of a turn.
        parts=max(1,math.ceil((end-start)/2))
        for n in range(parts):
            point=start+(n+.5)*(end-start)/parts
            center=min(hi-1,max(lo,bisect_left(times,point)))
            left=max(lo,min(center-1,hi-2)) if hi-lo>=2 else lo
            selected.update(range(left,min(hi,left+2)))
    return [files[i] for i in sorted(selected)]


def run_ocr(w,cfg,folder):
    """One helper/model instance; a private atomic sidecar carries progress."""
    import threading,time
    folder=Path(folder);progress=folder/'ocr-progress.json';progress.unlink(missing_ok=True)
    done=threading.Event();seen=[-1]
    def report():
        while not done.wait(.5):
            try:
                event=json.loads(progress.read_text())
                completed=int(event['completed']);total=int(event['total'])
                if 0<=completed<=total and completed!=seen[0]:
                    seen[0]=completed
                    w.emit('OCR',f"OCR: {completed}/{total} · {float(event.get('seconds',0)):.1f}s",.28,
                           workID='ocr-scan',workCompleted=completed,workTotal=total,
                           ocrProgress=event)
            except (OSError,ValueError,KeyError,TypeError):pass
    thread=threading.Thread(target=report,daemon=True);thread.start()
    try:return json.loads(w.run([cfg['executable'],'--ocr',folder]).decode())
    finally:done.set();thread.join(timeout=2)


def scan(w,cfg,job):
    """Speech-guided auxiliary OCR; legacy pure-OCR keeps its dense clock."""
    import hashlib,time,sys
    job=Path(job);video=Path(cfg['video']);stat=video.stat()
    speech=cfg.get('_ocrSpeechWindows',())
    if cfg.get('ocrRect') is None:cfg['ocrAutoRegion']=True
    guided=bool(speech) and bool(cfg.get('ocrEvidenceOnly'))
    identity=dict(revision=SCAN_REVISION,video=str(video.resolve()),bytes=stat.st_size,
        modified=stat.st_mtime_ns,duration=cfg['duration'],offset=cfg.get('startOffset',0),
        region=None if cfg.get('ocrAutoRegion') else cfg.get('ocrRect'),auto=bool(cfg.get('ocrAutoRegion')),colour=cfg.get('ocrColor','original'),
        stable=cfg.get('ocrStable',True),speech=speech if guided else [],platform=sys.platform)
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    cache=job/'ocr-scan.json'
    try:
        previous=json.loads(cache.read_text())
        if previous.get('identity')==key and isinstance(previous.get('cues'),list):
            cfg.update(ocrRect=previous['region'],ocrEvidenceOnly=previous['evidenceOnly'])
            w.emit('OCR','沿用已完成嘅畫面字幕辨識，唔需要重複掃描。',.28,ocrCacheReused=True)
            return previous['cues']
    except (OSError,ValueError,KeyError,TypeError):pass
    started=time.monotonic();discover(w,cfg,job)
    interval=.4 if guided else .2
    folder=job/'frames-pts';folder.mkdir(exist_ok=True)
    # This directory is owned by this job. Remove old PTS images before a
    # changed sampling plan, rather than mixing two clocks after a resume.
    for old in folder.glob('*.jpg'):old.unlink()
    w.emit('OCR','按原聲對白位置抽樣畫面字幕。' if guided else '精細畫面字幕掃描：每 0.2 秒取樣。',.28,
           ocrSampling='speech-guided' if guided else 'dense')
    w.run([cfg['ffmpeg'],'-v','error','-y','-ss',str(cfg.get('startOffset',0)),
           '-i',cfg['video'],'-t',str(cfg['duration']),'-vf',
           f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{interval})',"+w.ocr_filter(cfg),
           '-fps_mode','vfr','-enc_time_base','1:1000','-frame_pts','1',folder/'%012d.jpg'])
    files=sorted(folder.glob('*.jpg'));extracted=len(files)
    if guided:
        retained=select_speech_frames(files,speech,float(cfg['duration']))
        keep=set(retained)
        for path in files:
            if path not in keep:path.unlink()
        files=retained
    extraction_seconds=time.monotonic()-started
    rows=run_ocr(w,cfg,folder) if files else []
    if len(rows)!=len(files) or any(row.get('index')!=i for i,row in enumerate(rows)):
        raise ValueError('OCR helper returned incomplete frame coverage')
    if guided:rows=subtitle_rows(rows)
    for row in rows:row['time']=int(files[row['index']].stem)/1000
    # Sparse auxiliary samples may be single hits in a fast utterance. They
    # remain evidence, never independent dialogue or a reason to delete ASR.
    cues=w.merge_ocr_rows(rows,cfg['duration'],False if guided else cfg.get('ocrStable',True),interval=interval)
    metrics=dict(mode='speech-guided' if guided else 'dense',sampleInterval=interval,
        extractedFrames=extracted,recognisedFrames=len(files),
        extractionSeconds=round(extraction_seconds,3),totalSeconds=round(time.monotonic()-started,3),
        denseBaselineFrames=math.ceil(float(cfg['duration'])/.2),captionCount=len(cues),
        model='RapidOCR 1.4.4 / ONNX CPU' if sys.platform=='win32' else 'Apple Vision',
        speechCueCount=len(speech),revision=SCAN_REVISION)
    try:
        helper=json.loads((folder/'ocr-progress.json').read_text())
        metrics['helper']={k:helper[k] for k in ('inferences','reused','backend','engine','seconds') if k in helper}
    except (OSError,ValueError,TypeError):pass
    w.atomic_json(job/'ocr-metrics.json',metrics)
    w.atomic_json(cache,dict(identity=key,cues=cues,region=cfg.get('ocrRect'),
                            evidenceOnly=bool(cfg.get('ocrEvidenceOnly')),metrics=metrics))
    w.emit('OCR',f"OCR: {len(files)}/{len(files)} · {metrics['totalSeconds']:.1f}s",.29,
           workID='ocr-scan',workCompleted=len(files),workTotal=len(files),ocrMetrics=metrics)
    return cues


def subtitle_rows(rows):
    """Prefer centered subtitle-size lines over scene text.

    Lower-confidence outlined captions remain auxiliary evidence with their
    confidence; high-confidence Japanese page text must not win by confidence.
    No box is turned into a speech turn or an authoritative transcript.
    """
    import re
    result=[]
    for row in rows:
        if not row.get('boxes'):result.append(row);continue
        choices=[];japanese_choices=[]
        for box in row['boxes']:
            text=str(box.get('text','')).strip();x=float(box.get('x',0));y=float(box.get('y',0));w=float(box.get('width',0));h=float(box.get('height',0));confidence=float(box.get('confidence',0))
            chinese=bool(re.search(r'[\u3400-\u9fff]',text)) and not re.search(r'[\u3040-\u30ff]',text)
            english=bool(re.search(r'[A-Za-z]{2,}',text)) and not re.search(r'[\u3040-\u30ff]',text)
            if confidence<.1 or w<.12 or not .18<x+w/2<.82 or y+h/2<.2:continue
            if chinese or english:choices.append(box)
            elif re.search(r'[\u3040-\u30ff]',text) and .32<x+w/2<.68 and w>=.24 and h>=.12:
                japanese_choices.append(box)
        # Keep large centered Japanese-only subtitles if no Chinese/English
        # caption exists. Small off-centre Japanese page writing stays excluded.
        if not choices:choices=japanese_choices
        if choices:
            height=max(float(b['height']) for b in choices)
            choices=[b for b in choices if float(b['height'])>=height*.65]
            choices.sort(key=lambda b:(round(float(b['y'])/.12),float(b['x'])))
        result.append(dict(row,text=' '.join(b['text'] for b in choices),selectedBoxes=choices,subtitleConfidence=min((float(b['confidence']) for b in choices),default=0),excludedSceneBoxes=len(row['boxes'])-len(choices)))
    return result
