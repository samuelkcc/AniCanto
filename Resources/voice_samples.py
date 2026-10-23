"""Small, versioned Cantonese audition set from approved lines and role cards."""
import copy
import hashlib
import json
from pathlib import Path


def select(cues, limit=20):
    groups = {}
    for cue in cues:
        if not cue.get('enabled', True) or not cue.get('cantonese', '').strip() or not cue.get('speakerId') or cue.get('preserveOriginalSpeech') or cue.get('nonlexicalTail'):
            continue
        groups.setdefault(cue['speakerId'], []).append(cue)
    for group in groups.values():
        group.sort(key=lambda c: (not 2 <= c['end']-c['start'] <= 10, not 8 <= len(c['cantonese']) <= 40, c['start']))
    result = []
    while len(result) < limit and any(groups.values()):
        for group in groups.values():
            if group and len(result) < limit:
                result.append(copy.deepcopy(group.pop(0)))
    return result


def generate(w, cfg, folder, cues):
    import dubbing, delivery, speechcheck
    from natural_voices import prepare_cast
    prepare_cast(cfg,folder,cues,w.run)
    from multitrack import selected, ENGINES
    chosen = select(cues)
    if not chosen:
        raise ValueError('未有已配對角色嘅廣東話台詞可作試音。')
    profiles = {p['id']: p for p in cfg.get('voiceProfiles', [])}
    result = dict(scope='Cantonese audition only; no movie render or automatic take adoption',pronunciationStatus='audition-required',rows=[],errors={})
    record = Path(folder)/'voice-samples.json'
    for engine in selected(cfg):
        work = Path(folder)/('samples-'+engine)
        work.mkdir(exist_ok=True)
        own = dict(cfg,ttsBackend=engine,targetLanguage='yue',autoFit=False,autoValidate=True,boundedRepairs=True,previewLooseTiming=True)
        manifest={}
        for cue in chosen:
            try:
                profile=dubbing.profile_for(cue,own)
                manifest[profile['id']]=hashlib.sha256(Path(profile['reference']).read_bytes()).hexdigest()
            except (ValueError,OSError):continue
        own['_voiceManifest']=manifest
        own_cues = copy.deepcopy(chosen)
        for i,cue in enumerate(own_cues):
            cue.setdefault('reviewIndex',i)
            for key in ('editorAudio','editorAudioBackend','editorAudioLanguage'):
                cue.pop(key,None)
        try:
            w.atomic_json(work/'review.json',dict(config=own,cues=own_cues,status='approved'))
            paths = delivery.synthesize(own,work,own_cues,dubbing.gsv_audio,w.run,w.emit)
            good = [(c,p) for c,p in zip(own_cues,paths) if p.exists() and not p.name.startswith(('skipped-','failed-'))]
            checks = speechcheck.inspect(own,work,[c for c,p in good],[p for c,p in good],w.emit) if good and (Path(cfg['storage'])/'asr-ready.json').exists() else [{} for c,p in good]
            evidence = {c['editorID']:check for (c,p),check in zip(good,checks)}
            for cue,path in zip(own_cues,paths):
                result['rows'].append(dict(editorID=cue['editorID'],engine=engine,engineTitle=ENGINES[engine],role=profiles.get(cue['speakerId'],{}).get('name',cue['speakerId']),text=cue['cantonese'],start=cue['start'],audio=str(path) if path.exists() and not path.name.startswith(('skipped-','failed-')) else None,speechCheck=evidence.get(cue['editorID'],{})))
        except (ValueError,RuntimeError) as error:
            result['errors'][engine]=str(error)
            w.atomic_json(record,result)
            if not cfg.get('continueOnError',True):raise
        w.atomic_json(record,result)
    if not any(r.get('audio') for r in result['rows']):
        raise ValueError('試音未完成；詳見保存嘅試音紀錄。')
    return result


def compare(w,cfg,folder,cues,segment):
    """Two explicitly selected candidates, sequential generation and independent failures."""
    from audio_audition import generate as audition
    from multitrack import ENGINES
    from engine_policy import ACTIVE
    from voice_expression import settings as expression_settings
    from gsv_versions import VERSIONS
    selected=copy.deepcopy([c for c in cues if c.get('editorID')==segment and c.get('enabled',True)])
    if len(selected)!=1:raise ValueError('請選擇一段啟用嘅對白。')
    candidates=cfg.get('comparisonCandidates')
    if not isinstance(candidates,list) or len(candidates)!=2:raise ValueError('請設定 A、B 兩個試音版本。')
    language=cfg.get('targetLanguage','yue')
    if language not in ('yue','zh','en'):raise ValueError('試音支援廣東話、普通話或英文。')
    cfg=copy.deepcopy(cfg);cfg['voiceStyleMode']='clone'
    if language=='en':
        from dub_languages import english_script
        english_script(w,cfg,Path(folder),selected)
    result=dict(scope='Two user-selected sequential A/B auditions; no movie render or automatic adoption',language=language,rows=[],errors={})
    for label,candidate in zip(('A','B'),candidates):
        engine=candidate.get('engine')
        if engine not in ACTIVE:raise ValueError('A／B 模型設定無效。')
        parameters=expression_settings(candidate.get('parameters') or cfg)
        work=Path(folder)/('candidate-'+label);work.mkdir(exist_ok=True)
        own=copy.deepcopy(cfg);own.update(parameters)
        own.update(ttsBackend=engine,targetLanguage=language,voiceStyleMode='clone',continueOnError=False,editorCache=str(work),audioRerunToken=str(cfg.get('audioRerunToken',''))+'-'+label)
        if engine in VERSIONS:own['gsvVersion']=VERSIONS[engine]
        cue=copy.deepcopy(selected[0]);cue['preserveOriginalSpeech']=False
        if language=='en':cue['cantonese']=cue['english']
        row=dict(candidate=label,editorID=segment,engine=engine,voiceStyleMode='clone',language=language,parameters=parameters,engineTitle=ENGINES[engine],role=cue.get('speakerId',''),text=cue['cantonese'],start=cue['start'],audio=None)
        w.atomic_json(work/'review.json',dict(config=own,cues=[cue]))
        try:
            path,seconds=audition(w,own,work,cue)
            row.update(audio=str(path),seconds=seconds,speechCheck=json.loads((work/'report.json').read_text())['speechCheck'])
        except (ValueError,RuntimeError,OSError) as error:
            result['errors'][label]=str(error);row['error']=str(error)
            # Retain an explicit diagnostic audition, never a usable/adopted take.
            try:
                timing=json.loads((work/'timing.json').read_text())
                diagnostic=Path(timing[0].get('audio','')) if timing else None
            except (OSError,ValueError,TypeError,IndexError):diagnostic=None
            if not diagnostic or not diagnostic.is_file():
                rejected=sorted(work.rglob('*.rejected.wav'),key=lambda p:p.stat().st_mtime,reverse=True)
                diagnostic=rejected[0] if rejected else None
            if diagnostic and diagnostic.is_file():row['diagnosticAudio']=str(diagnostic)
        result['rows'].append(row);w.atomic_json(Path(folder)/'voice-samples.json',result)
    return result
