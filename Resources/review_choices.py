"""Explicit, track-scoped editorial choices; never automatic quality approval."""
import copy,hashlib,json,time,uuid,wave,shutil
from pathlib import Path


def select(root,review,draft,snapshot,index,engine,language,action,audio=None,confirm_defect=False):
    root=Path(root).resolve()
    if type(index) is not int or index<0 or index>=len(review.get('cues',[])):raise ValueError('Unknown dialogue.')
    cfg=review['config'];engines=cfg.get('selectedEngines') or [cfg.get('ttsBackend')]
    if engine not in engines or language not in cfg.get('dubLanguages',['yue']):raise ValueError('This audio track does not belong to the project.')
    if action not in ('automatic','original','recording'):raise ValueError('Unknown review action.')
    segment=next((s for s in draft['segments'] if s.get('sources')==[index]),None)
    if segment is None:raise ValueError('This line was split or merged. Open the editor to choose its audio.')
    key=language+':'+engine;choices=segment.setdefault('reviewDecisions',{})
    if action=='automatic':choices.pop(key,None);return draft
    text=segment.get('english' if language=='en' else 'text','')
    decision=dict(action=action,engine=engine,language=language,text=text,acceptedByUser=True,acceptedAt=time.time(),qualityCertified=False)
    if action=='original':
        if not Path(cfg['video']).is_file():raise ValueError('Original video is unavailable.')
        streams=review.get('meta',{}).get('streams')
        if streams is not None and not any(s.get('codec_type')=='audio' for s in streams):raise ValueError('The source video has no original audio track.')
    else:
        if confirm_defect is not True:raise ValueError('Confirm that you accept this recording with its reported defects.')
        known=[p for p in snapshot.get('takes',[]) if p.get('index')==index+1 and p.get('engine')==engine and p.get('language')==language]
        known += [p for p in snapshot.get('history',[]) if p.get('index')==index+1 and p.get('engine')==engine and p.get('language')==language]
        for issue in snapshot.get('issues',[])+snapshot.get('resolvedIssues',[]):
            if issue.get('index')!=index+1 or issue.get('engine')!=engine or issue.get('language')!=language:continue
            known += [dict(path=a['audition']['path']) for a in issue.get('attempts',[]) if isinstance(a.get('audition'),dict) and a['audition'].get('path')]
        match=next((p for p in known if (p.get('audio') or p.get('path'))==audio),None)
        if match is None:raise ValueError('Choose a retained recording from this line and audio track.')
        source=Path(audio).resolve()
        if not source.is_relative_to(root) or not source.is_file() or source.suffix.lower()!='.wav':raise ValueError('The recording does not belong to this project.')
        expected=match.get('text',match.get('cantonese'))
        if expected is not None and expected!=text:raise ValueError('The script changed. Generate a recording for the current words.')
        try:
            with wave.open(str(source)) as f:seconds=f.getnframes()/f.getframerate()
        except (OSError,wave.Error,EOFError):raise ValueError('This recording is unreadable. Choose another take or keep original audio.')
        from speech_timing import natural_window
        cue=dict(review['cues'][index],start=segment['start'],end=segment['end'])
        a,b=natural_window(cue,review['cues'],cfg['duration'],cfg)
        if seconds<=0 or seconds>b-a+2.0 or a+seconds>cfg['duration']+.015:raise ValueError('The full recording is more than two seconds over its slot or exceeds the video. Adjust timing in the editor.')
        ident=uuid.uuid4().hex;folder=root/'accepted-recordings'/ident;folder.mkdir(parents=True)
        target=folder/'audio.wav';shutil.copy2(source,target);digest=hashlib.sha256(target.read_bytes()).hexdigest()
        decision.update(audio=str(target),audioSHA256=digest,seconds=seconds,defectsAccepted=True,timingOverlapSeconds=round(max(0,seconds-(b-a)),3))
        (folder/'acceptance.json').write_text(json.dumps(decision,indent=2)+'\n')
    choices[key]=decision
    return draft


def apply(cues,cfg,engine,language):
    if not (cfg.get('editorRender') or cfg.get('_reviewRetry')):return cues
    root=Path(cfg.get('_editorSourceRoot','/nonexistent')).resolve();result=copy.deepcopy(cues)
    for cue in result:
        decision=cue.get('editorDecisions',{}).get(language+':'+engine)
        if not decision:continue
        if not decision.get('acceptedByUser') or decision.get('text')!=cue.get('cantonese',''):raise ValueError('The explicit audio choice no longer matches this script.')
        if decision['action']=='original':
            cue.update(preserveOriginalSpeech=True,originalSpeechReason='user-choice',manualReviewChoice='original')
            cue.pop('missingScript',None);cue.pop('editorAudio',None)
        elif decision['action']=='recording':
            path=Path(decision['audio']).resolve()
            if not path.is_relative_to(root/'accepted-recordings') or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=decision['audioSHA256']:raise ValueError('The accepted recording changed or is unavailable.')
            cue.update(editorAudio=str(path),editorAudioBackend=engine,editorAudioLanguage=language,preserveOriginalSpeech=False,manualReviewChoice='accepted-defect-recording')
            cue.pop('missingScript',None)
        else:raise ValueError('Unknown saved audio choice.')
    return result
