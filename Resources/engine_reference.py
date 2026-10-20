"""Engine-owned conditioning from original recordings, never another TTS output."""
import hashlib,json,wave
from pathlib import Path

def prepare(cfg,job,profile,run):
    engine=cfg.get('ttsBackend','cosyvoice3')
    if profile.get('mixedReference'):raise ValueError('角色參考只有多人重疊聲音；請重新取樣單人原聲，已保留其他配音進度。')
    from reference_quality import measure,read,clean,conditioned_quality
    # Consider only same-character originals with their own matching transcript.
    # Explicit per-engine references clear automatic candidates in profile_for.
    original=profile
    primary=Path(profile['reference'])
    try:source_quality=conditioned_quality(measure(*read(primary)),profile.get('referenceQuality'))
    except (ValueError,wave.Error):
        # Imported float WAVs still pass through the existing FFmpeg PCM16
        # conversion before conditioning, even when wave cannot inspect them.
        source_quality=dict(score=0,warnings=['source-measurement-unavailable'])
    choices=[]
    for candidate in profile.get('referenceCandidates',[])[:2]:
        if not candidate.get('promptText') or candidate.get('language','ja')!=profile.get('language','ja'):continue
        try:
            samples,rate=read(candidate['reference']);quality=conditioned_quality(measure(samples,rate),candidate.get('quality'))
            if 3<=len(samples)/rate<=10.1 and quality['score']>source_quality['score']+8:
                choices.append((quality['score'],candidate,quality))
        except (ValueError,OSError,wave.Error):continue
    if choices:
        _,candidate,source_quality=max(choices,key=lambda row:row[0])
        profile=dict(profile,reference=candidate['reference'],promptText=candidate['promptText'],shortReference=False,
                     referenceRanges=candidate.get('ranges') or [candidate.get('range',[])],referenceQuality=source_quality)
    source=Path(profile['reference']);digest=hashlib.sha256(source.read_bytes()).hexdigest()
    from speech_level import REVISION as level_revision
    reference_rate=32000 if engine.startswith('gpt-sovits') else 44100 if engine=='drama3' else 24000
    identity=dict(engine=engine,sourceSHA=digest,prompt=profile['promptText'],language=profile.get('language','ja'),revision=6 if engine.startswith('gpt-sovits') else 5,levelRevision=level_revision)
    if engine.startswith('gpt-sovits') or engine=='drama3':identity['referenceSampleRate']=reference_rate
    key=hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
    folder=Path(cfg['storage'])/'engine-references'/engine/key;folder.mkdir(parents=True,exist_ok=True)
    target=folder/'reference.wav';manifest=folder/'reference.json'
    if not target.exists():
        temporary=folder/'reference.partial.wav'
        run([cfg['ffmpeg'],'-v','error','-y','-i',source,'-ar',str(reference_rate),'-ac','1','-c:a','pcm_s16le',temporary])
        with wave.open(str(temporary)) as f:
            duration=f.getnframes()/f.getframerate()
            if not 3<=duration<=10.1:raise ValueError('原聲參考需要 3–10 秒。')
        from speech_level import prepare_file
        cleaned,cleanup=clean(temporary,folder,cfg['ffmpeg'],run)
        conditioned,quality=prepare_file(cleaned,folder/'levels',reference=True)
        if 'insufficient-signal' in quality['warnings']:raise ValueError('參考錄音有效聲音太少，請重新取樣或匯入乾淨原聲。')
        target.write_bytes(conditioned.read_bytes());temporary.unlink(missing_ok=True)
        manifest.write_text(json.dumps(dict(identity,source=str(source),requestedSource=original['reference'],selectedAlternate=str(source)!=original['reference'],reference=str(target),quality=quality,sourceQuality=source_quality,cleanup=cleanup,shortReference=bool(profile.get('shortReference')),referenceRanges=profile.get('referenceRanges',[]),purityVerified=False,method='Independent engine conditioning from original recording; no generated bridge'),ensure_ascii=False,indent=2))
    result=dict(profile,reference=str(target),referenceProvenance=str(manifest))
    alternates=[]
    candidates=list(original.get('referenceCandidates',[])[:2])
    if str(source)!=original['reference']:candidates.insert(0,dict(reference=original['reference'],promptText=original['promptText'],language=original.get('language','ja'),quality=original.get('referenceQuality',{}),ranges=original.get('referenceRanges',[])))
    for candidate in candidates[:3]:
        if not candidate.get('promptText') or candidate.get('reference')==str(source):continue
        try:
            alternate=prepare(cfg,job,dict(profile,reference=candidate['reference'],promptText=candidate['promptText'],referenceCandidates=[],mixedReference=False,referenceQuality=candidate.get('quality',{}),referenceRanges=candidate.get('ranges') or [candidate.get('range',[])]),run)
            alternates.append(dict(reference=alternate['reference'],promptText=alternate['promptText'],language=alternate.get('language','ja')))
        except (ValueError,OSError):continue
        if len(alternates)>=2:break
    result['referenceCandidates']=alternates
    return result
