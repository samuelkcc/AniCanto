"""Local OP/ED detection, independent of the user's audio treatment."""
import hashlib
import json
import math
import re
from pathlib import Path


def candidates(rows, duration=300):
    rows=[r for r in rows if all(math.isfinite(float(r.get(k,0))) for k in ('start','duration','music','singing','speech'))]
    rows=sorted(rows,key=lambda r:r['start'])
    groups=[]
    for r in rows:
        singing=max(r.get('singing',0),r.get('choir_singing',0),r.get('rapping',0))
        if r.get('music',0)<.45 or singing<.18 or r.get('speech',0)>.5: continue
        gap=[x for x in rows if groups and groups[-1][-1]['start']<x['start']<r['start']]
        bridge=len(gap)<=5 or (sum(x.get('music',0) for x in gap)/len(gap)>=.65 and sum(x.get('speech',0) for x in gap)/len(gap)<=.55)
        if groups and bridge and r['start']-(groups[-1][-1]['start']+groups[-1][-1]['duration'])<=15:
            groups[-1].append(r)
        else: groups.append([r])
    found=[]
    for group in groups:
        a=group[0]['start'];b=min(duration,group[-1]['start']+group[-1]['duration'])
        if not 35<=b-a<=240: continue
        span=[r for r in rows if a<=r['start']<b]
        music=sum(r.get('music',0) for r in span)/len(span)
        speech=sum(r.get('speech',0) for r in span)/len(span)
        support=len(group)/len(span)
        score=.35*support+.35*music+.30*(1-speech)
        if music<.6 or speech>.4 or support<.5 or score<.67: continue
        for r in reversed(rows):
            if r['start']>=a or r['start']+r['duration']<a-1.6:continue
            if group[0]['start']-r['start']>8 or r.get('music',0)<.55 or r.get('speech',0)>.4:break
            a=r['start']
        # Include a short instrumental tail, stopping before spoken dialogue.
        for r in rows:
            if r['start']<b or r['start']>b+1.6: continue
            if r['start']>group[-1]['start']+group[-1]['duration']+8 or r.get('music',0)<.55 or r.get('speech',0)>.4: break
            b=min(duration,r['start']+r['duration'])
        found.append(dict(start=round(a,3),end=round(b,3),confidence=round(score,3),source='local-singing-classifier'))
    return sorted(found,key=lambda r:(-r['confidence'],r['start']))[:1]


def detect(cfg,meta,run,emit):
    duration=float(meta['format']['duration'])
    found=[]
    for chapter in meta.get('chapters',[]):
        title=chapter.get('tags',{}).get('title','').lower()
        kind = ('OP' if re.search(r'(^|[\s\W])op(?:\s*\d+)?($|[\s\W])|opening|オープニング|片頭|片头',title)
                else 'ED' if re.search(r'(^|[\s\W])ed(?:\s*\d+)?($|[\s\W])|ending|エンディング|片尾',title) else None)
        if not kind:continue
        try:a,b=float(chapter['start_time']),float(chapter['end_time'])
        except (KeyError,ValueError,TypeError):continue
        if 0<=a<b<=duration and 15<=b-a<=240 and (a<300 if kind=='OP' else b>duration-300):
            found.append(dict(start=a,end=b,confidence=1,source='chapter',kind=kind))
    video=Path(cfg['video']);stat=video.stat()
    normal=cfg.get('productionMode')=='normal'
    key=hashlib.sha256(json.dumps([str(video.resolve()),stat.st_size,stat.st_mtime_ns,'normal-song-4' if normal else 3]).encode()).hexdigest()[:20]
    folder=Path(cfg['storage'])/'openings'/key;folder.mkdir(parents=True,exist_ok=True)
    result=folder/'result.json'
    if result.exists():return json.loads(result.read_text())
    failures=[]
    for kind,offset,length in [('OP',0,min(300,duration)),('ED',max(0,duration-300),min(300,duration))]:
        if any(r['kind']==kind for r in found):continue
        emit('OP／ED 分析',f'分析{kind}區域嘅歌唱、音樂同對白；單有配樂唔會當成歌曲。',.01)
        audio=folder/(kind+'.wav')
        run([cfg['ffmpeg'],'-v','error','-y','-ss',str(offset),'-i',video,'-t',str(length),'-vn','-ac','1','-ar','16000',audio])
        try:
            rows=json.loads(run([cfg['executable'],'--classify-opening',audio]))
            if not isinstance(rows,list):raise ValueError('Invalid audio classification result')
        except (RuntimeError,OSError,ValueError) as error:
            # Optional song analysis must not abort translation and speech.
            # Retain verified chapters; do not invent an unverified song range
            # or cache a failed classifier as a successful negative result.
            failures.append(dict(kind=kind,error=str(error),action='continue-dialogue',confirmedRanges=found.copy()))
            emit('OP／ED 提示',f'{kind} 音樂分類未完成；保留已確認章節，其餘繼續按日文對白處理。',.01,
                 warningCode='opening-classifier-unavailable',classificationError=str(error))
            audio.unlink(missing_ok=True)
            continue
        (folder/(kind+'-scores.json')).write_text(json.dumps(rows))
        detected=candidates(rows,length)
        if normal and not detected:detected=source_song_ranges(rows,length,meta.get('chapters',[]),offset)
        for r in detected:
            r.update(start=round(r['start']+offset,3),end=round(r['end']+offset,3),kind=kind)
            if not any(r['start']<x['end'] and r['end']>x['start'] for x in found):found.append(r)
        audio.unlink(missing_ok=True)
    found.sort(key=lambda r:r['start'])
    if failures:
        (folder/'classification-errors.json').write_text(json.dumps(failures,ensure_ascii=False,indent=2))
        cfg['openingDetectionWarnings']=[dict(kind=f['kind'],code='opening-classifier-unavailable') for f in failures]
        return found
    tmp=result.with_suffix('.tmp');tmp.write_text(json.dumps(found));tmp.replace(result)
    return found


def source_song_ranges(rows,duration,chapters=(),offset=0):
    """Singing and music scores are independent evidence, not both mandatory.

    A sustained singing run may have low instrumental music scores. Short
    chapter boundaries can refine an acoustically confirmed song, but an
    unnamed chapter or music alone never establishes an OP/ED.
    """
    rows=sorted([r for r in rows if all(math.isfinite(float(r.get(k,0))) for k in ('start','duration','singing','music','speech'))],key=lambda r:r['start'])
    groups=[]
    for r in rows:
        singing=max(r.get('singing',0),r.get('choir_singing',0))
        if singing<.18 or max(singing,r.get('music',0))<.4 or r.get('speech',0)>.55:continue
        if groups and r['start']-(groups[-1][-1]['start']+groups[-1][-1]['duration'])<=4.5:groups[-1].append(r)
        else:groups.append([r])
    result=[]
    for group in groups:
        a,b=group[0]['start'],min(duration,group[-1]['start']+group[-1]['duration'])
        if not 30<=b-a<=180:continue
        covered=[r for r in rows if a<=r['start']<b]
        if not covered:continue
        singing=sum(max(r.get('singing',0),r.get('choir_singing',0)) for r in covered)/len(covered)
        speech=sum(r.get('speech',0) for r in covered)/len(covered)
        if singing<.25 or speech>.4 or len(group)/len(covered)<.65:continue
        for chapter in chapters:
            try:ca,cb=float(chapter['start_time'])-offset,float(chapter['end_time'])-offset
            except (KeyError,ValueError,TypeError):continue
            if 30<=cb-ca<=180 and abs(ca-a)<=6 and abs(cb-b)<=6:
                a,b=max(0,ca),min(duration,cb);break
        result.append(dict(start=round(a,3),end=round(b,3),confidence=round(min(.95,.55+singing*.4),3),source='sustained-singing-with-source-boundaries'))
    return sorted(result,key=lambda r:-r['confidence'])[:1]


def detected_local_ranges(cfg):
    # Old saved reviews contain ranges without an autoSkipOP key.
    if cfg.get('autoSkipOP') is False:return []
    start=cfg.get('startOffset',0);end=start+cfg['duration']
    from source_evidence import merge_ranges
    return merge_ranges([dict(start=max(0,r['start']-start),end=min(cfg['duration'],r['end']-start)) for r in cfg.get('opRanges',[]) if r['end']>start and r['start']<end])


def subtract_ranges(rows,removed):
    from source_evidence import merge_ranges
    pieces=merge_ranges(rows)
    for r in removed:
        pieces=[dict(start=a,end=b) for p in pieces for a,b in ((p['start'],min(p['end'],r['start'])),(max(p['start'],r['end']),p['end'])) if b>a]
    return merge_ranges(pieces)


def local_ranges(cfg):
    """Only ranges authorized to restore Japanese or exclude dubbing."""
    from source_evidence import merge_ranges
    detected=detected_local_ranges(cfg)
    captions=cfg.get('_captionPreserveRanges',[])
    if cfg.get('translateOPED'):
        return subtract_ranges(captions,detected)
    return merge_ranges(detected+captions)


def prepare(cfg,meta,run,emit):
    """Detect once; translation never jumps past the opening in a sample."""
    if not cfg.get('autoSkipOP'):
        cfg.pop('opRanges',None)
        return
    cfg['opRanges']=detect(cfg,meta,run,emit)
    translate=bool(cfg.get('translateOPED'))
    for r in cfg['opRanges']:
        emit('OP／ED 翻譯配音' if translate else '保留 OP／ED',
             f"{r.get('kind','OP')}：{r['start']:.1f}–{r['end']:.1f} 秒；"+
             ('按原聲／字幕翻譯配音，範圍內對白照常生成。' if translate else '保留完整日文原聲，唔翻譯或配音。'),.02)
    if not cfg['opRanges']:
        emit('OP／ED 檢查','未確認片頭／片尾歌曲；未確認區域仍會按正文處理。',.02)
    r=next((r for r in cfg['opRanges'] if r.get('kind','OP')=='OP'),{'start':999999})
    if not translate and cfg.get('limit') and not cfg.get('startOffset',0) and r['start']<3:
        cfg['startOffset']=r['end']
        emit('試片範圍','試片由 OP 後開始；完整影片輸出會保留 OP。',.02)


def excludes(cue,ranges):
    midpoint=(cue['start']+cue['end'])/2
    return any(r['start']<=midpoint<r['end'] for r in ranges)


def preserve_filter(ranges, dubbed='mixed',original='0:a:0'):
    # Replace (do not add to) the dub mix during the OP. Original audio only
    # reaches the output inside these explicitly selected local time ranges.
    condition='+'.join(f'between(t,{r["start"]:.6f},{r["end"]:.6f})' for r in ranges)
    return f"[{dubbed}]aformat=channel_layouts=stereo,aeval=exprs='val(0)*if({condition},0,1)|val(1)*if({condition},0,1)'[body];[{original}]asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo,aeval=exprs='val(0)*if({condition},1,0)|val(1)*if({condition},1,0)'[op];[body][op]amix=inputs=2:duration=first:normalize=0[dub]"
