"""Fill missing speech only. Keep native takes immutable and record every donor."""
import array,hashlib,json,math,wave
from pathlib import Path

def read_json(path,default):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return default

def healthy(path):
    try:
        with wave.open(str(path)) as f:
            if f.getsampwidth()!=2 or not f.getnframes():return False
            data=array.array('h',f.readframes(f.getnframes()))
            return bool(data) and max(abs(x) for x in data)>32
    except (OSError,wave.Error,EOFError):return False

def background_gain(cfg,pcm,sr,overlays,start,end):
    """A replacement overlay must retain the native mix's audibility repair."""
    from mix_balance import levels,automatic_enabled
    requested=float(cfg.get('backgroundGain',.8));gain=requested*(.5 if cfg.get('backgroundDucking') else 1.)
    result=dict(start=start,end=end,requestedGain=requested,gain=gain,automatic=False)
    if not automatic_enabled(cfg) or gain<=0:return gain,result
    bed=levels(pcm.tobytes(),sr=sr)
    voices=[]
    for anchor,audio,voice_gain,row in overlays:
        if row is None or voice_gain<=0:continue
        lo=max(0,round((start-anchor)*sr));hi=min(len(audio),round((end-anchor)*sr))
        if hi<=lo:continue
        measured=levels(audio[lo:hi].tobytes(),sr=sr)
        if measured:voices.append(measured['activeRMSDB']+20*math.log10(voice_gain))
    if bed and voices:
        voice=min(voices);needed=10**((voice-6-bed['activeRMSDB'])/20)
        gain=min(gain,max(requested*.2,needed))
        result.update(gain=gain,automatic=gain<result['gain'],voiceDB=voice,backgroundDB=bed['activeRMSDB'],
                      marginDB=voice-bed['activeRMSDB']-20*math.log10(max(1e-12,gain)))
    # Whole-turn RMS cannot detect a quiet initial syllable masked by a short
    # sound effect. A cap requires a verified isolated take plus a successful
    # encoded trial, and expires as soon as that actual foreground changes.
    for anchor,audio,voice_gain,row in overlays:
        if not row or anchor>=end or anchor+len(audio)/sr<=start:continue
        for cap in cfg.get('_fallbackBackgroundCaps',[]):
            if any(cap.get(k)!=row.get(k) for k in ('index','text','speakerId','renderedStart','renderedEnd')):continue
            background=Path(cfg.get('backgroundPath',''))
            if not background.is_file():continue
            source=background.stat()
            if cap.get('background')!=dict(path=str(background.resolve()),bytes=source.st_size,modified=source.st_mtime_ns):continue
            path=Path(row.get('audio',''))
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=cap.get('audioSHA'):continue
            limited=min(gain,float(cap['maximumGain']))
            if limited<gain:result.update(gain=limited,automatic=True,evidence='verified-foreground-and-encoded-background-trial',index=row['index'])
            gain=limited
    return gain,result

def choose(cue,target,tracks,require_verified=False):
    for donor in tracks:
        if donor is target or donor['language']!=target['language']:continue
        quality=read_json(donor['folder']/'validation.json',{})
        bad=set(quality.get('contentReviewIndices',[])+quality.get('languageReviewIndices',[]))
        for row in read_json(donor['folder']/'timing.json',[]):
            checks=read_json(donor['folder']/'final-speech-check.json',{}).get('rows',[])
            check=next((r for r in checks if r.get('index')==row.get('index')),None)
            from cantonese_review import verified,retain_original
            variant=bool(check and verified(check))
            original_retained=bool(check and row.get('originalVoiceRetained') and donor['engine']==target['engine'] and retain_original(check))
            if row.get('skipped') or (row.get('index') in bad and not (variant or original_retained)):continue
            if require_verified:
                if not check or not (variant or original_retained):continue
            # Ending early can be a pacing flag, not missing words. Preserve a
            # verified same-language take if it stays inside the source slot.
            if row.get('requiresTimingReview') and (row.get('needsReview') or float(row.get('overrun',0))>.12 or abs(float(row.get('startDrift',0)))>.15):continue
            if row.get('speakerId') != cue.get('speakerId'):continue
            if row.get('text') and cue.get('text') and row['text']!=cue['text']:continue
            if abs(row.get('start',-1)-cue['start'])>.001 or abs(row.get('end',-1)-cue['end'])>.001:continue
            path=row.get('renderedAudio')
            if path and healthy(path):return donor,row,Path(path)
    return None

def track_language_failure(evidence):
    lexical=[r for r in evidence if len(''.join(c for c in r.get('expected','') if c.isalnum()))>=6 and r.get('detectedLanguage') not in ('','none','unknown')]
    return len(lexical)>=5 and sum(bool(r.get('languageMismatch')) for r in lexical)/len(lexical)>=.8

def merged_intervals(intervals):
    result=[]
    for a,b in sorted((max(0,float(a)),float(b)) for a,b in intervals if b>a):
        if result and a<=result[-1][1]:result[-1]=(result[-1][0],max(b,result[-1][1]))
        else:result.append((a,b))
    return result

def muted_base(cfg,output,folder,intervals,run):
    from audio_format import delivery_rate
    sr=delivery_rate(cfg)
    """Bounded stereo PCM blocks avoid FFmpeg's expression depth limit."""
    decoded=folder/'fallback-base-decoded.wav';muted=folder/'fallback-base-muted.wav'
    run([cfg['ffmpeg'],'-v','error','-y','-i',output,'-map','0:a:0','-ar',str(sr),'-ac','2','-c:a','pcm_s16le',decoded])
    spans=[(round(a*sr),round(b*sr)) for a,b in merged_intervals(intervals)]
    try:
        with wave.open(str(decoded),'rb') as src,wave.open(str(muted),'wb') as dest:
            dest.setparams(src.getparams());offset=0;cursor=0
            while True:
                chunk=bytearray(src.readframes(sr))
                if not chunk:break
                end=offset+len(chunk)//4
                while cursor<len(spans) and spans[cursor][1]<=offset:cursor+=1
                for a,b in spans[cursor:]:
                    if a>=end:break
                    lo=max(a,offset)-offset;hi=min(b,end)-offset
                    chunk[lo*4:hi*4]=bytes((hi-lo)*4)
                dest.writeframes(chunk);offset=end
        return muted
    finally:decoded.unlink(missing_ok=True)

def repair(cfg,job,tracks,run,emit,target_keys=None,donor_tracks=None):
    duration=max(float(x['report']['duration']) for x in tracks)
    # The original separated dialogue uses local job time, while source video uses sourceStart.
    stem=Path(cfg.get('dialoguePath',''))
    all_fallbacks=[]
    for target in tracks:
        if target_keys is not None and target['engine']+':'+target['language'] not in target_keys:continue
        try:
            from audio_format import delivery_rate
            target_cfg=dict(cfg,ttsBackend=target['engine'])
            sr=delivery_rate(target_cfg)
            # Always rebuild overlays from the immutable native mix. Resuming
            # from with-fallback.mp4 and adding the same formerly missing cue
            # again doubles previously repaired voices on every repair pass.
            native=Path(target['report'].get('output',''))
            base_output=native if native.is_file() else target['output']
            from source_evidence import recover_caption_base
            corrected=recover_caption_base(target_cfg,target['folder'],base_output,run,emit)
            if corrected!=base_output:
                target['report'].setdefault('originalNativeOutput',str(base_output))
                target['report']['output']=str(corrected)
                target['output']=corrected
                base_output=native=corrected
            prior_fallbacks=target['report'].get('audioFallbacks',[])
            if prior_fallbacks and not native.is_file():raise ValueError('原始混音缺失，未將已補聲錄音重複疊加。')
            target['report'].setdefault('output',str(base_output))
            timing=read_json(target['folder']/'timing.json',[])
            # A cancelled/broken generator may omit its timing row entirely.
            # A verified retake still needs a destination slot in the mix.
            saved=read_json(target['folder']/'review.json',{})
            approved_cues={c.get('reviewIndex',n)+1:c for n,c in enumerate(saved.get('cues',[]))}
            stale_indices=set()
            for row in timing:
                current=approved_cues.get(row['index'],{})
                if 'text' in row and current and row['text']!=current.get('cantonese',''):
                    row.update(text=current.get('cantonese',''),unsafeContent=True)
                    stale_indices.add(row['index'])
            known={r['index'] for r in timing}
            for n,cue in enumerate(saved.get('cues',[])):
                index=cue.get('reviewIndex',n)+1
                if index in target.get('aiRepairIndices',[]) and index not in known:
                    timing.append(dict(index=index,start=cue['start'],end=cue['end'],speakerId=cue.get('speakerId'),text=cue.get('cantonese',''),skipped=True,renderedSeconds=0))
            missing=[r for r in timing if r.get('skipped') or r.get('renderedSeconds')==0 or r['index'] in stale_indices]
            for row in timing:
                if row.get('index') in target.get('aiRepairIndices', []) and row not in missing:
                    missing.append(dict(row,unsafeContent=True))
            for row in timing:
                if any(p.get('index')==row.get('index') for p in prior_fallbacks) and not any(r.get('index')==row.get('index') for r in missing):
                    missing.append(dict(row,unsafeContent=True))
            from cantonese_review import needs_repair
            evidence=read_json(target['folder']/'final-speech-check.json',{}).get('rows',[])
            # Repeated explicit wrong-language evidence across a track is stronger
            # than a short isolated ASR disagreement. Do not pass Mandarin as Yue
            # merely because its written characters resemble the approved script.
            wrong_language_track=track_language_failure(evidence)
            if wrong_language_track:target['report']['trackLanguageFailure']=True
            for cue in timing:
                check=next((r for r in evidence if r.get('index')==cue.get('index')),None)
                strong=check and needs_repair({'cantonese':check.get('expected','')},check,target['language'])
                if not strong or any(r.get('index')==cue.get('index') for r in missing):continue
                a,b=cue.get('renderedStart',cue['start']),cue.get('renderedEnd',cue['end'])
                missing.append(dict(cue,unsafeContent=True))
            if not missing:
                target['report']['channelSummary']=dict(generated=len(timing),unresolved=[],repaired=0,japaneseFallback=0)
                from worker import atomic_json
                atomic_json(target['folder']/'report.json',target['report'])
                continue
            # Replace the connected overlap component and restore good roles too.
            # Muting one rendered take alone would erase simultaneous native voices.
            selected_indices={r['index'] for r in missing}
            expanded=True
            while expanded:
                expanded=False
                ranges=[(r.get('renderedStart',r['start']),r.get('renderedEnd',r['end'])) for r in missing if r.get('unsafeContent')]
                for r in timing:
                    if r['index'] in selected_indices or r.get('skipped'):continue
                    if any(r.get('renderedStart',r['start'])<b and r.get('renderedEnd',r['end'])>a for a,b in ranges):
                        missing.append(dict(r,unsafeContent=True,restoreNative=not any(e.get('index')==r['index'] and needs_repair({'cantonese':e.get('expected','')},e,target['language']) for e in evidence)));selected_indices.add(r['index']);expanded=True
            overlays=[];mute=[];original_ranges=[];full_source_ranges=[];unresolved=[]
            for cue in missing:
                uses_full_source=False
                decision=target.get('aiRepairActions', {}).get(cue['index'])
                available=[r for r in (donor_tracks or [])+tracks if r['engine'] in cfg.get('selectedEngines',[cfg.get('ttsBackend','')])]
                permitted=decision not in ('keep','needs-reference')
                selected=(target,cue,Path(cue['renderedAudio'])) if cue.get('restoreNative') and cue.get('renderedAudio') and healthy(cue['renderedAudio']) else (choose(cue,target,available,require_verified=bool(cfg.get('aiAutoFix'))) if permitted and (cfg.get('allowCrossEngineRepair',False) or cue['index'] in target.get('aiRepairIndices', [])) else None)
                if selected is None:
                    previous=next((p for p in prior_fallbacks if p.get('index')==cue.get('index') and p.get('sourceLanguage')==target['language'] and
                        p.get('speakerId')==cue.get('speakerId') and p.get('text')==cue.get('text') and
                        abs(p.get('start',-1)-cue['start'])<.001 and abs(p.get('end',-1)-cue['end'])<.001 and healthy(p.get('audio',''))),None)
                    if previous:
                        selected=(dict(target,engine=previous.get('sourceEngine',target['engine'])),dict(previous,renderedAudio=previous['audio']),Path(previous['audio']))
                if selected:
                    donor,row,path=selected;start=float(row.get('renderedStart',cue['start']))
                    raw=run([cfg['ffmpeg'],'-v','error','-i',path,'-ar',str(sr),'-ac','1','-f','s16le','pipe:1'])
                    gain=float(row.get('mixGain',1));source=donor['engine'];language=donor['language']
                else:
                    unresolved.append(cue['index'])
                    emit('補聲需覆核',f"{target['id']} 第 {cue['index']} 段未有已授權、同角色同語言替代；保留成功錄音，不使用日文補聲。")
                    continue
                pcm=array.array('h',raw)
                if source=='original' and stem.is_file() and (not pcm or max(abs(v) for v in pcm)<=32) and cfg.get('video'):
                    raw=run([cfg['ffmpeg'],'-v','error','-ss',f'{start+float(cfg.get("startOffset",0)):.6f}','-i',cfg['video'],'-t',f'{float(cue["end"])-start:.6f}','-ar',str(sr),'-ac','1','-f','s16le','pipe:1'])
                    uses_full_source=True
                    pcm=array.array('h',raw);mute.append((start,float(cue['end'])))
                if not pcm or max(abs(v) for v in pcm)<=32:
                    if cue.get('unsafeContent'):
                        mute.append((cue.get('renderedStart',cue['start']),cue.get('renderedEnd',cue['end'])))
                        unresolved.append(cue['index'])
                    emit('補聲需覆核',f'{target["id"]} 第 {cue.get("index")} 段未找到可聽同語言替代錄音。');continue
                approved=next((c for c in read_json(target['folder']/'review.json',{}).get('cues',[]) if abs(c.get('start',-1)-cue['start'])<.001 and abs(c.get('end',-1)-cue['end'])<.001),{})
                compression=1.
                if cfg.get('strictSpeechTiming') and source!='original':
                    from speech_timing import fit_pcm,window
                    start,deadline=window(approved or cue,[],duration)
                    fitted,compression=fit_pcm(target_cfg,pcm.tobytes(),(math.floor(deadline*sr)-round(start*sr))/sr,run)
                    pcm=array.array('h',fitted)
                if cue.get('unsafeContent'):
                    a,b=cue.get('renderedStart',cue['start']),cue.get('renderedEnd',cue['end']);mute.append((a,b))
                row=dict(text=approved.get('cantonese'),speakerId=approved.get('speakerId'),seed=approved.get('_seed',42),index=cue.get('index'),start=cue['start'],end=cue['end'],renderedStart=start,renderedEnd=start+len(pcm)/sr,engine=target['engine'],language=target['language'],sourceEngine=source,sourceLanguage=language,donorTimingReview=bool(selected and selected[1].get('requiresTimingReview')),slotCompression=compression,reason='unresolved-content-or-language' if cue.get('unsafeContent') else 'user-skipped-or-missing-voice')
                if selected and selected[1].get('asrVariation'):row['asrVariation']=True
                preview=target['folder']/f'fallback-{cue.get("index")}.wav'
                with wave.open(str(preview),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(pcm.tobytes())
                row['audio']=str(preview)
                if source=='original':
                    # Original source spans can overlap; never double the same speech.
                    for a,b in original_ranges:
                        lo=max(0,round((a-start)*sr));hi=min(len(pcm),round((b-start)*sr))
                        if hi>lo:pcm[lo:hi]=array.array('h',[0])*(hi-lo)
                    original_ranges=merged_intervals(original_ranges+[(start,row['renderedEnd'])])
                    if uses_full_source:full_source_ranges.append((start,row['renderedEnd']))
                overlays.append((start,pcm,gain,row))
            target['report']['unresolvedFallbackIndices']=unresolved
            target['report']['channelSummary']=dict(generated=sum(not r.get('skipped') for r in timing),unresolved=unresolved,repaired=len(overlays),japaneseFallback=0)
            if unresolved:target['report']['qualityStatus']='needs-review'
            from worker import atomic_json
            atomic_json(target['folder']/'report.json',target['report'])
            if not overlays and not mute:continue

            background=Path(cfg.get('backgroundPath',''))
            bed_levels=[]
            if background.is_file():
                for a,b in merged_intervals(mute):
                    remaining=[(a,b)]
                    for lo,hi in merged_intervals(full_source_ranges):
                        remaining=[piece for x,y in remaining for piece in ((x,min(y,lo)),(max(x,hi),y)) if piece[1]>piece[0]]
                    for x,y in remaining:
                        bg=array.array('h',run([cfg['ffmpeg'],'-v','error','-ss',f'{x:.6f}','-i',background,'-t',f'{y-x:.6f}','-ar',str(sr),'-ac','1','-f','s16le','pipe:1']))
                        gain,measured=background_gain(dict(target_cfg,_fallbackBackgroundCaps=target['report'].get('fallbackBackgroundCaps',[])),bg,sr,overlays,x,y)
                        bed_levels.append(measured)
                        overlays.append((x,bg,gain,None))
            atomic_json(target['folder']/'fallback-mix-audibility.json',dict(rows=bed_levels,method='Measured foreground/background active PCM power; limited background attenuation; not perceptual certification'))
            mix=array.array('i',[0])*math.ceil(duration*sr)
            from pcm_mix import add,finish
            for start,pcm,gain,row in overlays:
                offset=max(0,round(start*sr))
                add(mix,pcm,offset,gain)
            pcm,scale=finish(mix)
            voice=target['folder']/'fallback-overlay.wav'
            with wave.open(str(voice),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(pcm.tobytes())
            output=target['folder']/'with-fallback.mp4'
            temporary=target['folder']/'with-fallback.partial.mp4'
            inputs=['-i',base_output,'-i',voice]
            base='0:a:0'
            if mute:
                muted=muted_base(target_cfg,base_output,target['folder'],mute,run)
                inputs+=['-i',muted];base='2:a:0'
            filt=f'[{base}][1:a:0]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0:latency=1[a]'
            run([cfg['ffmpeg'],'-v','error','-y',*inputs,'-filter_complex',filt,'-map','0:v:0','-map','[a]','-map','0:a:1?','-map','0:s?','-c:v','copy','-c:a','aac','-ac','2','-c:s','copy','-t',f'{duration:.6f}',temporary])
            temporary.replace(output)
            if mute:muted.unlink(missing_ok=True)
            (target['folder']/'fallback-error.json').unlink(missing_ok=True)
            all_fallbacks.extend(r for _,_,_,r in overlays if r is not None)
            target['output']=output
            rows=[r for _,_,_,r in overlays if r is not None];target['report']['audioFallbacks']=rows;target['report']['deliveredOutput']=str(output)
            target['report']['qualityStatus']='needs-review';target['report']['unresolvedFallbackIndices']=unresolved
            from worker import atomic_json
            atomic_json(target['folder']/'fallbacks.json',rows)
            report=read_json(target['folder']/'report.json',{});report.setdefault('output',str(base_output));report['audioFallbacks']=rows;report['deliveredOutput']=str(output);report['qualityStatus']='needs-review';report['trackLanguageFailure']=wrong_language_track;report['unresolvedFallbackIndices']=unresolved;atomic_json(target['folder']/'report.json',report)
            emit('補聲摘要',f'{target["id"]}：{len(rows)} 段用已授權同語言引擎補聲；原引擎缺聲紀錄保留，請試聽。')
        except (RuntimeError,ValueError,OSError) as error:
            target['report']['fallbackError']=str(error)
            target['report']['qualityStatus']='needs-review'
            from worker import atomic_json
            atomic_json(target['folder']/'fallback-error.json',dict(error=str(error),status='not-repaired'))
            emit('補聲失敗',target['id']+'：'+str(error)+'；已保留原音軌，其他音軌繼續。')
    return all_fallbacks


def original_placeholder(cfg,folder,engine,language,cues,run):
    from audio_format import delivery_rate
    sr=delivery_rate(dict(cfg,ttsBackend=engine))
    """Recover a partial track without overwriting successful native timing/takes.

    Original Japanese may be present ONLY as the separate second stream.
    """
    folder.mkdir(parents=True,exist_ok=True)
    duration=float(cfg['duration']);output=folder/'partial-track.mp4'
    timing=read_json(folder/'timing.json',[])
    voice=folder/'cantonese.wav'
    if not healthy(voice):
        samples=array.array('i',[0])*round(duration*sr)
        for row in timing:
            take=row.get('renderedAudio')
            if row.get('skipped') or not take or not healthy(take):continue
            pcm=array.array('h',run([cfg['ffmpeg'],'-v','error','-i',take,'-ar',str(sr),'-ac','1','-f','s16le','pipe:1']))
            start=round(row.get('renderedStart',row['start'])*sr)
            for i,value in enumerate(pcm):
                if 0<=start+i<len(samples):samples[start+i]+=value
        peak=max((abs(x) for x in samples),default=0);gain=min(1,32000/max(1,peak))
        with wave.open(str(voice),'wb') as f:
            f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(array.array('h',(round(x*gain) for x in samples)).tobytes())
    if not timing:
        timing=[dict(index=c.get('reviewIndex',i)+1,start=c['start'],end=c['end'],speakerId=c.get('speakerId'),text=c.get(__import__('output_language').field(language)),skipped=True,renderedSeconds=0) for i,c in enumerate(cues) if c.get('enabled',True)]
    cmd=[cfg['ffmpeg'],'-v','error','-y','-ss',str(cfg.get('startOffset',0)),'-i',cfg['video'],'-i',voice]
    background=Path(cfg.get('backgroundPath',''))
    if background.is_file():
        cmd+=['-i',background,'-filter_complex',f"[2:a]volume={float(cfg.get('backgroundGain',.8))}[bg];[1:a][bg]amix=inputs=2:normalize=0,alimiter=limit=0.95:level=0:latency=1[dub]",'-map','0:v:0','-map','[dub]']
    else:cmd+=['-map','0:v:0','-map','1:a:0']
    cmd+=['-map',__import__('source_language').audio_label(cfg)+'?','-t',str(duration),'-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-ac','2',output]
    run(cmd)
    from worker import atomic_json
    atomic_json(folder/'timing.json',timing)
    report=dict(duration=duration,qualityStatus='needs-review',generationFailed=True,output=str(output),nativePreserved=sum(not r.get('skipped') for r in timing),japaneseFallback=0)
    atomic_json(folder/'report.json',report)
    return dict(engine=engine,language=language,id=engine if language=='yue' else language+'-'+engine,folder=folder,output=output,report=report)
