"""Per-line original references without speaker embeddings, clustering or vision.

Each reference is bounded to its own source utterance. Short recordings receive
silence only; neighbouring voices are never borrowed to satisfy TTS duration.
"""
from fast_mode import enabled as one_pass

import hashlib,json,math,time
from pathlib import Path

REVISION='independent-source-lines-native-1'


def prepare(cfg, emit):
    import numpy as np
    import soundfile as sf
    from reference_quality import measure
    source=Path(cfg['audio']);job=Path(cfg['job']);root=Path(cfg['storage'])
    profiles=[];assignments=[]
    with sf.SoundFile(source) as stream:
        sr=stream.samplerate;duration=stream.frames/sr
        for index,cue in enumerate(cfg['cues']):
            if not cue.get('enabled',True):continue
            ident=f'line-{job.name}-{index+1}'
            profile=dict(id=ident,name=f'第 {index+1} 句原聲',reference='',promptText='',language=cfg.get('sourceLanguage','ja'),referenceCandidates=[],referenceRanges=[],identityStatus='independent',sourceIndex=index)
            a=float(cue.get('speechStart',cue['start']));b=min(float(cue.get('speechEnd',cue['end'])),a+8,duration)
            try:
                if not math.isfinite(a+b) or a<0 or b<=a:raise ValueError('本句原聲範圍無效。')
                stream.seek(round(a*sr));clip=stream.read(max(1,round(b*sr)-round(a*sr)),dtype='float32',always_2d=True).mean(axis=1)
                if not len(clip):raise ValueError('本句未有有效原聲。')
                quality=dict(warnings=[],qualityChecked=False) if one_pass(cfg) else measure(clip,sr)
                actual=len(clip)/sr;short=actual<3
                # Keep source-bandwidth PCM and expose actual speech length.
                padded=np.pad(clip,(0,max(0,round(3.1*sr)-len(clip)))) if short else clip
                key=hashlib.sha256(json.dumps([REVISION,str(source),source.stat().st_size,source.stat().st_mtime_ns,index,a,b]).encode()).hexdigest()[:20]
                folder=job/'line-references'/key;folder.mkdir(parents=True,exist_ok=True)
                target=folder/'reference.wav'
                if not target.exists():
                    temporary=target.with_suffix('.partial.wav');sf.write(temporary,padded,sr,subtype='PCM_16');temporary.replace(target)
                warnings=list(quality.get('warnings',[]))
                if short:warnings.append('short-source-reference')
                profile.update(reference=str(target),referenceRanges=[[a,a+actual]],shortReference=short,mixedReference=bool(cue.get('mixedVoices',False)),referenceQuality=dict(quality,warnings=warnings),originalReferenceSeconds=actual,paddedSeconds=len(padded)/sr-actual)
                (folder/'source.json').write_text(json.dumps(dict(source=str(source),sourceIndex=index,range=profile['referenceRanges'][0],sampleRate=sr,originalSeconds=actual,silencePaddingSeconds=profile['paddedSeconds'],speakerGrouped=False,visualAnalysis=False,method=REVISION),ensure_ascii=False,indent=2))
            except (ValueError,OSError,RuntimeError) as error:
                profile['referenceIssue']=str(error)
                if not cfg.get('continueOnError',True):raise
            profiles.append(profile)
            assignments.append(dict(index=index,speakerId=ident,speakerNote='本句獨立原聲參考；未建立角色或共用聲線分組。',mixedVoices=bool(cue.get('mixedVoices',False)),previousSpeakerSimilarity=0,identityEvidence=dict(state='independent',reason='own-source-utterance; identity not compared')))
            emit('逐句聲音配對',f'已準備第 {index+1}/{len(cfg["cues"])} 句獨立原聲參考。',workID='independent-voice-mapping',workCompleted=index+1,workTotal=len(cfg['cues']))
    result=dict(revision=REVISION,profiles=profiles,assignments=assignments,speakerGrouped=False,visualAnalysis=False)
    from worker import atomic_json
    atomic_json(job/'independent-voices.json',result)


def assign(cfg,job,cues,emit):
    started=time.monotonic()
    from dubbing import model_job
    from speakers import transcribe_profiles
    from model_catalog import folder,choice,selected
    root=Path(cfg['storage']);job=Path(job);source=Path(cfg['dialoguePath'])
    analysis=job/'japanese-analysis.json'
    text_hash=hashlib.sha256(analysis.read_bytes()).hexdigest() if analysis.exists() else ''
    identity=[REVISION,cfg.get('productionMode','standard'),str(source),source.stat().st_size,source.stat().st_mtime_ns,cfg.get('referenceSpeechModel'),text_hash,[(c['start'],c['end'],c.get('speechStart'),c.get('speechEnd'),c.get('enabled',True)) for c in cues]]
    key=hashlib.sha256(json.dumps(identity).encode()).hexdigest();cache=job/'independent-voices.json'
    saved=json.loads(cache.read_text()) if cache.exists() else {}
    reused=saved.get('key')==key and all(not p['reference'] or Path(p['reference']).is_file() for p in saved.get('profiles',[]))
    if not reused:
        model_job(cfg,'independent-voices',dict(storage=str(root),job=str(job),audio=str(source),cues=cues,sourceLanguage=cfg.get('sourceLanguage','ja'),productionMode=cfg.get('productionMode','standard'),continueOnError=cfg.get('continueOnError',True)),emit)
        saved=json.loads(cache.read_text())
        speech=folder(root,choice(cfg.get('referenceSpeechModel') or selected(root,'referenceSpeech')))
        ready=[p for p in saved['profiles'] if p.get('reference')]
        transcribe_profiles(dict(cfg,independentVoiceMapping=True),job,ready,speech,emit)
        saved['key']=key
        from worker import atomic_json
        atomic_json(cache,saved)
    for row in saved['assignments']:
        cue=cues[row['index']]
        cue.update({k:v for k,v in row.items() if k!='index'})
    cfg.update(voiceProfiles=saved['profiles'],defaultSpeaker='',independentVoiceMapping=True)
    result=dict(status='complete',requested='independent',actual='independent',analyzed=len(saved['profiles']),total=sum(c.get('enabled',True) for c in cues),shortReferences=sum(bool(p.get('shortReference')) for p in saved['profiles']),missingReferences=sum(not p.get('reference') or not p.get('promptText') for p in saved['profiles']),speakerGrouped=False,visualAnalysis=False,method=REVISION,elapsedSeconds=round(time.monotonic()-started,3),cacheReused=reused)
    cfg['roleAnalysisResult']=result
    from worker import atomic_json
    atomic_json(job/'voice-mapping.json',dict(result,profiles=saved['profiles']))
    # Lightweight compatibility feed for the live preview; these are per-line
    # references, never acoustic or visual character groups.
    atomic_json(job/'turn-voices.json',saved['profiles'])
    emit('逐句聲音配對',f'已準備 {len(saved["profiles"])} 句獨立參考；沒有聲紋分組或角色畫面分析。',.29)
    return cues
