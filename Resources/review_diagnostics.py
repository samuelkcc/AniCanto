"""Read-only, line-specific repair evidence; never infers success from a caption."""
import json,math,struct,wave
from pathlib import Path


def duration(path):
    # RIFF PCM, IEEE-float and extensible stems all share byte-rate timing.
    # Read chunk headers only: a full episode can be several gigabytes.
    try:
        with open(path,'rb') as f:
            header=f.read(12)
            if header[:4]!=b'RIFF' or header[8:]!=b'WAVE':return None
            rate=size=None
            while True:
                chunk=f.read(8)
                if len(chunk)!=8:break
                kind,length=struct.unpack('<4sI',chunk)
                if kind==b'fmt ':
                    fmt=f.read(min(length,16))
                    if len(fmt)<16:return None
                    rate=struct.unpack('<I',fmt[8:12])[0]
                    f.seek(length-len(fmt)+(length&1),1)
                elif kind==b'data':
                    size=min(length,max(0,Path(path).stat().st_size-f.tell()));break
                else:f.seek(length+(length&1),1)
            return round(size/rate,4) if size is not None and rate else None
    except (OSError,ValueError,struct.error):return None


def managed_separated(cfg,base):
    """Allow this video's completed shared stem, never an arbitrary external path."""
    try:
        storage=Path(cfg['storage']).resolve();p=Path(cfg['dialoguePath']).resolve()
        if not base.is_relative_to(storage/'jobs') or p.name!='dialogue.wav' or p.parent.parent!=storage/'separations':return None
        saved=json.loads((p.parent/'complete.json').read_text())
        video=Path(cfg['video']).resolve();stat=video.stat()
        if not isinstance(saved,list) or len(saved)<5 or saved[:3]!=[str(video),stat.st_size,stat.st_mtime_ns]:return None
        if abs(float(saved[3])-float(cfg.get('startOffset',0)))>.001 or abs(float(saved[4])-float(cfg['duration']))>.001:return None
        seconds=duration(p)
        return str(p) if seconds is not None and abs(seconds-float(cfg['duration']))<=.01 else None
    except (OSError,ValueError,KeyError,TypeError):return None


def enrich(item,cue,cfg,folder,placement=None,checks=None,director=None,processing=False,phase=None):
    placement=placement or {};checks=checks or {};director=director or {}
    base=folder.parent.parent if folder.parent.name=='tracks' else folder
    base=base.resolve();attempts=director.get('attempts') or item.get('attempts',[])
    def safe(path):
        if not path:return None
        p=Path(path).resolve()
        return str(p) if p.is_relative_to(base) and p.is_file() else None
    attempts=[dict(a) for a in attempts if isinstance(a,dict)]
    for attempt in attempts:
        candidate=safe(attempt.get('candidateAudio') or attempt.get('audio') or attempt.get('originalAudio') or attempt.get('output'))
        if candidate:attempt['audition']=dict(path=candidate,start=0,end=duration(candidate))
    index=item['index'];start=float(cue.get('speechStart',cue.get('start',0)));end=float(cue.get('speechEnd',cue.get('end',start)))
    reference=next((p for p in cfg.get('voiceProfiles',[]) if p.get('id')==cue.get('speakerId')), {})
    language=item.get('language','yue');target=cue.get('english' if language=='en' else 'cantonese','')
    if not target:target=item.get('text','')
    repairs=[x for x in checks.get('repairs',[]) if x.get('index')==index]
    selected_audio=safe(director.get('selectedAudio'))
    generated=selected_audio or next((p for a in reversed(attempts) if (p:=safe(a.get('candidateAudio')))),None)
    if not generated:
        generated=next((p for x in reversed(item.get('evidence',[])) if (p:=safe(x.get('renderedAudio') or x.get('audio') or x.get('candidateAudio') or x.get('originalAudio') or x.get('retainedAudio')))),None)
    proof=None
    if generated:
        # The latest failed attempt may differ from the selected recording.
        # Never display one recording's transcript beside another recording.
        matching=[a for a in attempts+repairs if safe(a.get('candidateAudio'))==generated]
        proof=next((a.get('check') or a.get('candidateCheck') for a in reversed(matching) if a.get('check') or a.get('candidateCheck')),None)
        if not proof and not selected_audio:proof=checks.get('checks',{}).get(str(index),{})
        for operation in attempts:
            if operation.get('action') in ('trim-padding','micro-tempo') and operation.get('status')=='adopted' and safe(operation.get('input'))==generated and (p:=safe(operation.get('output'))):generated=p
    proof=proof or {}
    fallback=next((a for a in reversed(attempts) if a.get('action')=='target-language-reference' and a.get('status') in ('adopted','selected-unverified') and safe(a.get('candidateAudio') or a.get('audio'))==generated),None)
    measured=duration(generated) if generated else None
    if measured is None:measured=placement.get('seconds')
    available=None
    if isinstance(placement.get('deadline'),(int,float)) and isinstance(placement.get('start'),(int,float)):available=placement['deadline']-placement['start']
    if available is None:
        for e in item.get('evidence',[]):
            if isinstance(e.get('slot'),(int,float)):available=e['slot'];break
    if measured is None:
        measured=next((x.get('measuredSeconds') for x in item.get('evidence',[]) if isinstance(x.get('measuredSeconds'),(int,float))),None)
    if available is None:
        available=next((x.get('availableSeconds') for x in item.get('evidence',[]) if isinstance(x.get('availableSeconds'),(int,float))),None)
    original=next((p for name in ('japanese-original.wav','source.wav') if (p:=safe(base/name))),None)
    separated=safe(cfg.get('dialoguePath')) or managed_separated(cfg,base)
    auditions={}
    if original:auditions['original']=dict(path=original,start=start,end=end)
    if separated:auditions['separated']=dict(path=separated,start=start,end=end)
    if generated:auditions['generated']=dict(path=generated,start=0,end=duration(generated))
    # Keep the rejected character-voice take distinct from the selected fallback.
    # A language detector can mistake accented Cantonese for Japanese, so the
    # listener must be able to hear the actual rejected candidate.
    failed_candidates=[(n,a) for n,a in enumerate(attempts) if a.get('audition') and
                       a.get('status') in ('not-verified','timing-not-fit','generation-failed','verification-failed','timing-check-failed','meaning-not-verified') and
                       a.get('action')!='target-language-reference']
    failed=max(failed_candidates,key=lambda pair:(pair[1].get('recordedAt') or Path(pair[1]['audition']['path']).stat().st_mtime,pair[0]))[1] if failed_candidates else None
    if failed:auditions['lastFailed']=failed['audition']
    failed_check=(failed.get('check') or failed.get('candidateCheck') or {}) if failed else {}
    if processing and phase in ('prepare','recognition','translation'):next_action='Finish translation, then generate and check affected lines.'
    elif processing:next_action='Automatic repair and rechecking are still running.'
    else:next_action='Automatic attempts finished. Compare the retained recordings and saved output.'
    cause='language-drift' if proof.get('languageFailure') or proof.get('decision') in ('japanese','mandarin') else 'content-incomplete' if proof.get('contentFailure') else 'timing-overrun' if available is not None and measured is not None and measured>available+.005 else item.get('kind')
    item.update(text=target,auditions=auditions,attempts=attempts,diagnostic=dict(cause=cause,voiceSource='target-language-fallback' if fallback else 'source-reference',voiceSimilarityCertified=False,referenceTitle=fallback.get('referenceID') if fallback else reference.get('name'),sourceText=cue.get('japanese') or cue.get('original') or cue.get('text',''),translatedText=target,heard=proof.get('heard',''),detectedLanguage=proof.get('decision') or proof.get('language',''),lastFailedHeard=failed_check.get('heard',''),lastFailedDetectedLanguage=failed_check.get('decision') or failed_check.get('language',''),sourceSeconds=round(max(0,end-start),4),referenceSeconds=duration(reference.get('reference','')),recordingSeconds=measured,availableSeconds=round(available,4) if available is not None else None,overrunSeconds=round(max(0,measured-available),4) if measured is not None and available is not None else None,referenceLanguage=reference.get('language'),nextAction=next_action,phase=phase,qualityCertified=False))
    return item
