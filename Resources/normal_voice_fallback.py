"""One final target-language reference trial; keep original actor attempts intact.

Only automatic Normal production, after same-actor repairs. Uses the bundled,
licensed reference bank with the selected engine. Voice similarity may differ;
language/content and timing still need evidence. No new model download.
"""
import hashlib,json
from pathlib import Path

REVISION='normal-target-reference-fallback-1'
TIMING_REVISION='measured-before-rejection-2'


def read(path,default):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return default


def repair(cfg,job,cues,paths,placement,run,emit):
    if cfg.get('editorRender') or cfg.get('productionMode')!='normal' or not placement or not cfg.get('automaticVoiceFallback',True):return paths
    from dubbing import gsv_audio,profile_for,is_vocalization
    from normal_mode import inspect,audio_present
    from normal_recovery import verified_check,clear_confirmed
    from natural_voices import resolve
    from natural_schedule import plan
    from natural_delivery import seconds
    from speech_timing import natural_window
    from worker import atomic_json
    from track_control import check,UserSkipped
    job=Path(job);marker=job/'target-reference-recovery.json';ledger=read(marker,{})
    selected=list(paths);pending=set(read(job/'normal-checks.json',{}).get('unresolved',[]));language=cfg.get('targetLanguage','yue')
    records=[];profiles={};drafts=[]
    for i,(cue,path) in enumerate(zip(cues,paths)):
        index=cue.get('reviewIndex',i)+1
        if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not cue.get('enabled',True) or is_vocalization(cue) or not cue.get('cantonese','').strip():continue
        # Merely being a little long is not a reason to change the actor. Only
        # the final delivery boundary may authorise a timing fallback, after
        # same-actor repairs and gentle tempo fitting have already failed.
        timing_exhausted=cfg.get('_sourceVoiceRepairsExhausted') is True and not placement[i]['fit']
        if index not in pending and audio_present(path) and not timing_exhausted:continue
        try:
            original=profile_for(cue,cfg)
            if original.get('language')==language:continue
            reference=resolve(dict(original,engineReferences={}),dict(cfg,voiceStyleMode='natural'))
        except (OSError,ValueError):continue
        identity=[REVISION,cfg.get('ttsBackend'),cfg.get('drama3Model'),cfg.get('gsvVersion'),language,index,cue['start'],cue['end'],cue['cantonese'],hashlib.sha256(Path(reference['reference']).read_bytes()).hexdigest()]
        key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24]
        record=ledger.get(key)
        retry_timing=record and record.get('status')=='timing-not-fit' and record.get('timingAdmissionRevision')!=TIMING_REVISION
        if record and record.get('status') not in ('reserved','generating','generated','adopted','selected-unverified') and not retry_timing:continue
        if record and record.get('attempts',0)>=2 and not (record.get('audio') and audio_present(record['audio'])):continue
        records.append((i,index,key,reference));profiles[reference['id']]=reference
        draft=dict(cue,reviewIndex=index-1,_seed=781433,_targetSeconds=placement[i]['deadline']-placement[i]['start'],_deliveryStyle='cantonese-strict-clauses' if language=='yue' else 'complete-clauses');drafts.append(draft)
        if record is None:ledger[key]=dict(index=index,status='reserved',text=cue['cantonese'],action='target-language-reference',reason='timing-after-source-voice-repairs' if timing_exhausted and index not in pending else 'language-or-missing-voice',voiceSimilarityCertified=False,referenceID=reference.get('naturalReferenceId'),referenceLanguage=language,referenceSHA256=identity[-1])
    if not records:return selected
    def save():atomic_json(marker,ledger)
    save();folder=job/'target-reference-batch';folder.mkdir(exist_ok=True)
    fresh=[n for n,(_,_,key,_) in enumerate(records) if not ledger[key].get('audio') or not audio_present(ledger[key]['audio'])]
    if fresh:
        batch=[drafts[n] for n in fresh];fallback=dict(cfg,voiceProfiles=list(profiles.values()),voiceStyleMode='clone',editorCache=str(folder),audioRerunToken=REVISION,_voiceManifest={p['id']:hashlib.sha256(Path(p['reference']).read_bytes()).hexdigest() for p in profiles.values()})
        emit('後備聲線修復',f'原裝聲線修復後仍有 {len(fresh)} 句未能交付；使用同一配音引擎同內置目標語言參考試讀，聲線可能有差異，仍須核對完整性同時長。',.90)
        for n in fresh:
            record=ledger[records[n][2]];record.update(status='generating',attempts=record.get('attempts',0)+1)
        save()
        try:
            check(cfg);generated=gsv_audio(fallback,folder,batch,run,emit)
            if len(generated)!=len(fresh):raise ValueError('Fallback line count mismatch')
            for n,path in zip(fresh,generated):ledger[records[n][2]].update(audio=str(path),status='generated' if audio_present(path) else 'generation-failed')
        except UserSkipped:raise
        except (OSError,RuntimeError,ValueError) as error:
            for n in fresh:ledger[records[n][2]].update(status='generation-failed',error=str(error)[:300])
        save()
    candidates=[(n,Path(ledger[key]['audio'])) for n,(_,_,key,_) in enumerate(records) if ledger[key].get('audio') and audio_present(ledger[key]['audio'])]
    evidence=inspect(cfg,job,[drafts[n] for n,_ in candidates],[p for _,p in candidates],emit) if candidates else {}
    planning=read(job/'natural-placement.json',{});base=job.parent.parent if job.parent.name=='tracks' else job
    cuts=read(base/'natural-scene-boundaries.json',{}).get('cuts',[]);lengths=[p.get('seconds') for p in placement];confirmed=set();uncertain=set()
    def simulate(trial):
        if planning.get('sceneBoundaryStatus')=='detected':return plan(cfg,cues,trial,cuts)
        rows=[]
        for cue,length in zip(cues,trial):
            a,b=natural_window(cue,cues,cfg['duration'],cfg);rows.append(dict(fit=length is not None and length<=b-a,start=a,deadline=b))
        return rows
    for n,path in candidates:
        i,index,key,reference=records[n];record=ledger[key];proof=evidence.get(index,{})
        verified=verified_check(proof,cues[i]['cantonese'],language)
        if not verified and (not proof.get('heard') or proof.get('languageFailure') or proof.get('contentFailure') or proof.get('decision') in ('japanese','mandarin')):
            record.update(status='not-verified',check=proof);continue
        trial=list(lengths);trial[i]=seconds(path,cfg,run);new=simulate(trial);raw_seconds=trial[i];tempo_record=None
        if not new[i]['fit'] or any(p['fit'] and not new[j]['fit'] for j,p in enumerate(placement)):
            # Final target-language audio receives the same bounded finishing
            # trial as an actor take BEFORE it can be rejected for its duration.
            from natural_finish import bounded_tempo
            trial_errors=[]
            fitted=bounded_tempo(cfg,job,cues[i],path,trial,placement,i,simulate,run,failures=trial_errors)
            if trial_errors:record['timingTrialErrors']=trial_errors
            if fitted:path,trial,new,tempo_record=fitted
        record['timingAdmissionRevision']=TIMING_REVISION
        if not new[i]['fit'] or any(p['fit'] and not new[j]['fit'] for j,p in enumerate(placement)):
            record.update(status='timing-not-fit',candidateSeconds=raw_seconds,check=proof);continue
        selected[i]=path;lengths=trial;placement=new
        if tempo_record:
            finishing=read(job/'natural-finishing.json',{});operations=finishing.setdefault('operations',[])
            if not any(x.get('output')==tempo_record['output'] for x in operations):operations.append(tempo_record)
            atomic_json(job/'natural-finishing.json',finishing)
        (confirmed if verified else uncertain).add(index)
        record.update(status='adopted' if verified else 'selected-unverified',candidateSeconds=raw_seconds,selectedSeconds=trial[i],selectedAudio=str(path),tempoRate=tempo_record['totalRate'] if tempo_record else 1.,check=proof,audioSHA256=hashlib.sha256(Path(record['audio']).read_bytes()).hexdigest(),selectedAudioSHA256=hashlib.sha256(path.read_bytes()).hexdigest(),voiceSimilarityCertified=False)
    clear_confirmed(cfg,job,confirmed,atomic_json)
    if uncertain:
        checks=read(job/'normal-checks.json',{});checks['unresolved']=sorted(set(checks.get('unresolved',[]))|uncertain)
        atomic_json(job/'normal-checks.json',checks)
    save()
    return selected
