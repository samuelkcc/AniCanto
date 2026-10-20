"""Verify actual encoded track audio; a healthy isolated WAV is insufficient."""
import hashlib,json
from pathlib import Path
from audio_fallback import read_json

REVISION='encoded-track-speech-2-yue-advisory'

def identity(path):
    path=Path(path);s=path.stat()
    return dict(path=str(path.resolve()),bytes=s.st_size,modified=s.st_mtime_ns)

def script_identity(cues):
    return hashlib.sha256(json.dumps([[c.get('reviewIndex',i)+1,c.get('cantonese',''),c.get('speakerId'),c['start'],c['end'],c.get('enabled',True)] for i,c in enumerate(cues)],ensure_ascii=False).encode()).hexdigest()

def fresh(track):
    folder=Path(track['folder']);data=read_json(folder/'post-mix-speech-check.json',{})
    review=read_json(folder/'review.json',{})
    try:
        if data.get('revision')==REVISION and data.get('movie')==identity(track['output']) and data.get('scripts')==script_identity(review.get('cues',[])):return data
    except OSError:pass
    return {}

def inspect(w,cfg,track):
    folder=Path(track['folder']);review=read_json(folder/'review.json',{});cues=review.get('cues',[])
    if not cues:return {}
    cached=fresh(track)
    if cached:return cached
    movie=identity(track['output']);script=script_identity(cues)
    key=hashlib.sha256(json.dumps([REVISION,movie,script],sort_keys=True).encode()).hexdigest()[:20]
    directory=folder/'mixed-speech'/key;directory.mkdir(parents=True,exist_ok=True)
    timing={r['index']:r for r in read_json(folder/'timing.json',[])}
    repaired={r['index']:r for r in track.get('report',{}).get('audioFallbacks',[]) if r.get('sourceLanguage')==track['language']}
    from dubbing import is_vocalization
    from workflow_policy import original_allowed
    from speechcheck import inspect as listen
    from repair_budget import clear_content_problem
    rows=[];selected=[];paths=[];indices=[]
    for n,cue in enumerate(cues):
        if not cue.get('enabled',True) or original_allowed(review.get('config',{}),cue) or is_vocalization(cue):continue
        index=cue.get('reviewIndex',n)+1;donor=repaired.get(index,{})
        row=donor if donor.get('text')==cue.get('cantonese') and donor.get('speakerId')==cue.get('speakerId') else timing.get(index,{})
        a=row.get('renderedStart',cue.get('speechStart',cue['start']));b=row.get('renderedEnd',cue.get('speechEnd',cue['end']))
        if row.get('skipped') or b<=a or not cue.get('cantonese','').strip():
            rows.append(dict(index=index,expected=cue.get('cantonese',''),heard='',strongContentFailure=True,missing=True));continue
        path=directory/f'{index}.wav'
        if not path.is_file():
            w.run([cfg['ffmpeg'],'-v','error','-y','-ss',str(a),'-i',track['output'],'-t',str(b-a),'-map','0:a:0','-ar','44100','-ac','1','-c:a','pcm_s16le',path])
        selected.append(cue);paths.append(path);indices.append(index)
    def progress(stage,message,fraction=None):w.emit('混音成品覆聽',message,.95)
    if selected:
        # Audio+script hashes remain the evidence identity. Share only this
        # content-addressed ASR cache across mux versions, so changing one
        # overlay does not send every unchanged line back through the model.
        cache_folder=folder/'mixed-speech';cache_path=cache_folder/'speech-check-cache.json'
        cache=read_json(cache_path,{})
        for previous in cache_folder.glob('*/speech-check-cache.json'):
            cache.update(read_json(previous,{}))
        if cache:w.atomic_json(cache_path,cache)
        checks=listen(dict(cfg,targetLanguage=track['language']),cache_folder,selected,paths,progress)
        if len(checks)!=len(selected):raise ValueError('編碼後覆聽回傳數量不完整；不能當作全部通過。')
        for index,cue,check in zip(indices,selected,checks):
            rows.append(dict(check,index=index,strongContentFailure=bool(clear_content_problem(cue,check))))
    result=dict(revision=REVISION,movie=movie,scripts=script,rows=sorted(rows,key=lambda r:r['index']),
                strongFailures=sorted(r['index'] for r in rows if r['strongContentFailure']),
                method='Independent ASR of actual encoded primary audio, after timing, background mixing and repairs; ASR disagreements are evidence, not certified meaning.')
    w.atomic_json(folder/'post-mix-speech-check.json',result)
    return result

def inspect_tracks(w,cfg,tracks,target_keys=None):
    if not cfg.get('autoValidate',True) or not (Path(cfg.get('storage',''))/'asr-ready.json').is_file():return []
    results=[]
    for track in tracks:
        if target_keys is not None and track['engine']+':'+track['language'] not in target_keys:continue
        try:
            result=inspect(w,cfg,track)
            if result:
                results.append(dict(engine=track['engine'],language=track['language'],strongFailures=result['strongFailures']))
                track['report']['encodedSpeechCheck']=dict(path=str(Path(track['folder'])/'post-mix-speech-check.json'),strongFailures=result['strongFailures'])
        except (OSError,RuntimeError,ValueError) as error:
            track['report']['encodedSpeechCheck']=dict(error=str(error),status='unavailable')
            w.emit('混音成品覆聽','覆聽未完成，錯誤已保存：'+str(error),.95)
        w.atomic_json(Path(track['folder'])/'report.json',track['report'])
    return results

def recover_background(w,cfg,job,tracks,target_keys=None):
    """Repair proven mix masking before repeating a correctly spoken take.

    Never infer a missing word from RMS alone. Require independent verification
    of this exact isolated foreground, then a successful AAC background trial.
    Only the selected track's background changes; words, voice and clocks stay.
    """
    if not cfg.get('aiAutoFix'):return False
    background=Path(cfg.get('backgroundPath',''))
    if not background.is_file():return False
    from speechcheck import inspect as listen
    from cantonese_alignment import verify as phonetic
    from cantonese_review import verified
    changed=False
    def accepted(settings,directory,cue,path,check):
        if verified(check):return True
        return bool(phonetic(w,settings,directory,cue,check,audio=path).get('accepted')) if settings['targetLanguage']=='yue' else False
    for track in tracks:
        if target_keys is not None and track['engine']+':'+track['language'] not in target_keys:continue
        fresh_check=fresh(track)
        if not fresh_check.get('strongFailures'):continue
        folder=Path(track['folder']);review=read_json(folder/'review.json',{})
        cues={c.get('reviewIndex',i)+1:c for i,c in enumerate(review.get('cues',[]))}
        settings=dict(cfg,targetLanguage=track['language']);records=[]
        for row in track['report'].get('audioFallbacks',[]):
            index=row['index'];cue=cues.get(index)
            if index not in fresh_check['strongFailures'] or not cue or row.get('sourceLanguage')!=track['language']:continue
            if row.get('text')!=cue.get('cantonese') or row.get('speakerId')!=cue.get('speakerId'):continue
            path=Path(row.get('audio',''))
            if not path.is_file():continue
            sha=hashlib.sha256(path.read_bytes()).hexdigest();bg=identity(background)
            key=hashlib.sha256(json.dumps([REVISION,'background-trials-1',sha,cue['cantonese'],bg,cfg.get('backgroundGain',.8)],sort_keys=True).encode()).hexdigest()[:20]
            directory=folder/'mix-recovery'/key;directory.mkdir(parents=True,exist_ok=True)
            def progress(stage,message,fraction=None):w.emit('混音自動修復',message,.96)
            isolated=listen(settings,directory,[cue],[path],progress)
            if len(isolated)!=1 or not accepted(settings,directory,cue,path,isolated[0]):
                records.append(dict(index=index,status='foreground-not-verified',audioSHA=sha));continue
            w.emit('混音自動修復',f"{track['id']} 第 {index} 段錄音本身完整；自動測試降低背景，保留原有聲線、台詞及時段。",.96)
            requested=max(0,float(cfg.get('backgroundGain',.8)));a=float(row['renderedStart'])
            for factor in (.4,.2,0.):
                gain=requested*factor;trial=directory/f'background-{factor}.m4a'
                if not trial.is_file():
                    w.run([cfg['ffmpeg'],'-v','error','-y','-i',path,'-ss',str(a),'-i',background,
                           '-filter_complex',f'[1:a:0]volume={gain}[bg];[0:a:0][bg]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0:latency=1[a]',
                           '-map','[a]','-ar','44100','-ac','2','-c:a','aac','-b:a','192k',trial])
                checks=listen(settings,directory,[cue],[trial],progress)
                passed=len(checks)==1 and accepted(settings,directory,cue,trial,checks[0])
                records.append(dict(index=index,status='verified-background' if passed else 'rejected-trial',gain=gain,audioSHA=sha,trial=str(trial),check=checks[0] if checks else {}))
                if not passed:continue
                cap=dict(index=index,text=cue['cantonese'],speakerId=cue.get('speakerId'),audioSHA=sha,renderedStart=row.get('renderedStart'),renderedEnd=row.get('renderedEnd'),background=bg,maximumGain=gain,reason='isolated-take-verified-but-encoded-mix-lost-words',proof=str(directory/'speech-check-cache.json'))
                caps=track['report'].setdefault('fallbackBackgroundCaps',[])
                old=next((c for c in caps if all(c.get(k)==cap.get(k) for k in ('index','text','speakerId','audioSHA','renderedStart','renderedEnd','background'))),None)
                if old is None:caps.append(cap);changed=True
                elif gain<float(old['maximumGain']):old.update(cap);changed=True
                break
        w.atomic_json(folder/'mix-recovery.json',dict(rows=records,method='Verify exact isolated foreground; independently verify AAC trials; change only background gain.'))
        w.atomic_json(folder/'report.json',track['report'])
    return changed
