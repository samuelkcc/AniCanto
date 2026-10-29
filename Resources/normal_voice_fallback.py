from repair_limits import bounded as bounded_repair
"""One final target-language reference trial; keep original actor attempts intact.

Only automatic Normal production, after same-actor repairs. Uses the bundled,
licensed reference bank with the selected engine. Voice similarity may differ;
language/content and timing still need evidence. No new model download.
"""
import hashlib,json,re
from pathlib import Path

REVISION='normal-target-reference-fallback-1'
TIMING_REVISION='measured-before-rejection-3-source-locked'


def read(path,default):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return default


@bounded_repair('normal_voice_fallback.repair')
def repair(cfg,job,cues,paths,placement,run,emit):
    if __import__('repair_permissions').enabled(cfg) and not __import__('repair_permissions').generic(cfg) and not cfg.get('_mandatoryPresence'):return paths
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
    objective=bool(cfg.get('_objectiveFallbackOnly'))
    unchecked=__import__('work_modes').enabled(cfg) and __import__('work_modes').mode(cfg)=='performance'
    job=Path(job);marker=job/'target-reference-recovery.json';ledger=read(marker,{})
    selected=list(paths);pending=set(read(job/'normal-checks.json',{}).get('unresolved',[]));language=cfg.get('targetLanguage','yue')
    if __import__('delivery_policy').bounded_delivery(cfg):pending=__import__('delivery_policy').confirmed_indices(cfg,job)
    records=[];profiles={};drafts=[]
    for i,(cue,path) in enumerate(zip(cues,paths)):
        index=cue.get('reviewIndex',i)+1
        if cfg.get('_mandatoryPresence') and audio_present(path):continue
        if cfg.get('preferFirstAudibleTake',True) and audio_present(path) and index not in pending and placement[i].get('fit'):continue
        if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not cue.get('enabled',True) or is_vocalization(cue) or not cue.get('cantonese','').strip():continue
        # Merely being a little long is not a reason to change the actor. Only
        # the final delivery boundary may authorise a timing fallback, after
        # same-actor repairs and gentle tempo fitting have already failed.
        timing_exhausted=cfg.get('_sourceVoiceRepairsExhausted') is True and not placement[i]['fit']
        if index not in pending and audio_present(path) and not timing_exhausted:continue
        try:
            try:original=profile_for(cue,cfg)
            except (OSError,ValueError):
                # Missing/corrupt actor references must not prevent a translated
                # line from trying the bundled target-language bank voice.
                original=dict(id=cue.get('speakerId') or f'generic-{index}',name='Generic voice',
                              language=cfg.get('sourceLanguage','ja'),reference='',promptText='')
            # The final bank voice must really be a generic target-language
            # reference, even when the actor profile already uses that language.
            reference=resolve(dict(original,engineReferences={},promptText=''),dict(cfg,voiceStyleMode='natural'))
        except (OSError,ValueError) as error:
            ledger['unavailable-'+str(index)]=dict(index=index,status='reference-unavailable',error=str(error)[:300],attempts=0,qualityCertified=False)
            atomic_json(marker,ledger)
            continue
        reference_sha=hashlib.sha256(Path(reference['reference']).read_bytes()).hexdigest()
        identity=[REVISION,cfg.get('ttsBackend'),cfg.get('drama3Model'),cfg.get('gsvVersion'),language,index,cue['start'],cue['end'],cue['cantonese'],reference_sha]
        if __import__('delivery_policy').bounded_delivery(cfg):identity.append(cfg.get('_genericAttempt',0))
        key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24]
        record=ledger.get(key)
        if record is not None and record.get('referenceSHA256')!=reference_sha:
            record['referenceSHA256']=reference_sha
            atomic_json(marker,ledger)
        if record and any(__import__('delivery_policy').rejected_audio(cfg,job,index,record.get(k)) for k in ('audio','selectedAudio')):
            record.update(status='not-verified',reason='confirmed-on-selected-audio')
            atomic_json(marker,ledger)
            continue
        retry_timing=record and record.get('status')=='timing-not-fit' and record.get('timingAdmissionRevision')!=TIMING_REVISION
        if record and record.get('status') not in ('reserved','generating','generated','adopted','selected-unverified') and not retry_timing:continue
        if __import__('delivery_policy').bounded_delivery(cfg) and record and record.get('attempts',0)>=1 and not (record.get('audio') and audio_present(record['audio'])):continue
        if record and record.get('attempts',0)>=(1 if objective else 2) and not (record.get('audio') and audio_present(record['audio'])):
            record.update(status='attempt-exhausted',maximumAttempts=1 if objective or __import__('delivery_policy').bounded_delivery(cfg) else 2)
            atomic_json(marker,ledger)
            continue
        records.append((i,index,key,reference));profiles[reference['id']]=reference
        draft=dict(cue,reviewIndex=index-1,speakerId=reference['id'],_seed=781433,_targetSeconds=placement[i]['deadline']-placement[i]['start'],_deliveryStyle='cantonese-strict-clauses' if language=='yue' else 'complete-clauses');drafts.append(draft)
        if record is None:ledger[key]=dict(index=index,status='reserved',text=cue['cantonese'],action='target-language-reference',maximumAttempts=1 if objective or __import__('delivery_policy').bounded_delivery(cfg) else 2,reason='timing-after-source-voice-repairs' if timing_exhausted and index not in pending else 'language-or-missing-voice',voiceSimilarityCertified=False,referenceID=reference.get('naturalReferenceId'),referenceLanguage=language,referenceSHA256=reference_sha)
    if not records:return selected
    def save():atomic_json(marker,ledger)
    save();folder=job/'target-reference-batch';folder.mkdir(exist_ok=True)
    fresh=[n for n,(_,_,key,_) in enumerate(records) if not ledger[key].get('audio') or not audio_present(ledger[key]['audio'])]
    if fresh and __import__('delivery_policy').repair_first(cfg):
        from recovery_attempts import reserve
        cap=1 if __import__('repair_permissions').enabled(cfg) else 2 if cfg.get('workMode')=='quality' else 1
        fresh=[n for n in fresh if reserve(job,'generic-generation',records[n][1],cap)]
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
    evidence=inspect(dict(cfg,_forceIndependentListening=True) if objective else cfg,job,[drafts[n] for n,_ in candidates],[p for _,p in candidates],emit) if candidates and not unchecked else {}
    planning=read(job/'natural-placement.json',{});base=job.parent.parent if job.parent.name=='tracks' else job
    cuts=read(base/'natural-scene-boundaries.json',{}).get('cuts',[]);lengths=[p.get('seconds') for p in placement];confirmed=set();uncertain=set()
    def simulate(trial):
        if cfg.get('naturalTimingPolicy','source-locked')=='micro-shift':return plan(cfg,cues,trial,cuts)
        rows=[]
        for cue,length in zip(cues,trial):
            a,b=natural_window(cue,cues,cfg['duration'],cfg)
            if __import__('basic_flow').relaxed(cfg) and length is not None:b=max(b,a+length)
            rows.append(dict(fit=length is not None and length<=b-a,start=a,deadline=b))
        return rows
    for n,path in candidates:
        path=__import__('speech_duration').trim(cfg,job,path)
        i,index,key,reference=records[n];record=ledger[key];proof=evidence.get(index,{})
        verified=verified_check(proof,cues[i]['cantonese'],language)
        foreign_script_only=objective and language in ('yue','zh') and not any(re.search(r'[\u3400-\u9fff]',str(text)) for text in (proof.get('heard',''),proof.get('independent',{}).get('heard','')))
        modern=__import__('delivery_policy').bounded_delivery(cfg)
        if foreign_script_only and not unchecked and not modern:
            record.update(status='not-verified',check=proof,reason='no-target-script-evidence');continue
        if modern and (proof.get('languageFailure') or proof.get('contentFailure') or __import__('delivery_policy').rejected_audio(cfg,job,index,path)):
            record.update(status='not-verified',check=proof,reason='confirmed-language-or-content-failure');continue
        if not modern and not unchecked and not verified and (not proof.get('heard') or proof.get('languageFailure') or proof.get('contentFailure') or proof.get('decision') in ('japanese','mandarin')):
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
    clear_confirmed(cfg,job,confirmed | uncertain if __import__('delivery_policy').bounded_delivery(cfg) else confirmed,atomic_json)
    if uncertain and not __import__('delivery_policy').bounded_delivery(cfg):
        checks=read(job/'normal-checks.json',{});checks['unresolved']=sorted(set(checks.get('unresolved',[]))|uncertain)
        atomic_json(job/'normal-checks.json',checks)
    save()
    return selected
