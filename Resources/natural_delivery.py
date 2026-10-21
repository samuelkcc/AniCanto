"""Rewrite measured overlong automatic dialogue, never speed it up or crop it."""
import hashlib
import json
from pathlib import Path
import wave


def seconds(path,cfg,run):
    try:
        with wave.open(str(path)) as audio:return audio.getnframes()/audio.getframerate()
    except (wave.Error,EOFError):
        return float(json.loads(run([cfg['ffprobe'],'-v','error','-show_format','-of','json',path]))['format']['duration'])


def recover_batch(saved,cue,cfg,job):
    """Recover completed line files after interruption, without another inference."""
    if not saved or saved.get('paths') or not saved.get('batch'):return saved
    folder=Path(saved['batch']).resolve()
    if not folder.is_relative_to((Path(job)/'concise-batches').resolve()):return saved
    try:manifest=json.loads((folder/'audio-preview.json').read_text())
    except (OSError,ValueError):return saved
    if manifest.get('engine')!=cfg.get('ttsBackend') or manifest.get('language')!=cfg.get('targetLanguage','yue'):return saved
    from audio_fallback import healthy
    for row in manifest.get('rows',[]):
        if any(row.get(k)!=cue.get(k) for k in ('start','end','speakerId','cantonese')):continue
        path=Path(row.get('audio','')).resolve()
        if path.is_relative_to(folder) and not path.name.startswith('skipped-') and path.is_file() and healthy(path):
            return dict(saved,status='generated',paths=[str(path)],recoveredAfterInterruption=True)
    return saved


def repair(cfg,job,cues,paths,run,emit,placement=None):
    # Child tracks are frozen for reproducibility; only an automatically
    # generated job authorises a wording edit. Human editor scripts stay locked.
    if cfg.get('editorRender') or not cfg.get('automaticDurationRewrite') or cfg.get('preferFirstAudibleTake',True):return paths
    from types import SimpleNamespace
    from worker import atomic_json,ollama_chat
    from concise_dialogue import compact,units
    from speech_timing import natural_window
    from dubbing import gsv_audio,is_vocalization
    selected=list(paths);job=Path(job);language=cfg.get('targetLanguage','yue')
    w=SimpleNamespace(atomic_json=atomic_json,ollama_chat=ollama_chat)
    audit=[]
    for attempt in range(2):
        if placement is not None:
            from natural_schedule import prepare
            placement=prepare(cfg,job,cues,selected,run,emit)
        targets={};pending=[]
        for i,(cue,path) in enumerate(zip(cues,selected)):
            if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or is_vocalization(cue) or Path(path).name.startswith('skipped-') or not Path(path).is_file():continue
            if placement is not None and placement[i]['fit']:continue
            a,b=(placement[i]['start'],placement[i]['deadline']) if placement is not None else natural_window(cue,cues,cfg['duration'],cfg);length=seconds(path,cfg,run)
            if length<=b-a+.005:continue
            targets[i]=max(1,int(units(cue.get('cantonese',''),language)*(b-a)/length*.92))
            pending.append(i)
        if not pending:break
        drafts=[dict(c) for c in cues]
        changed=compact(w,cfg,job,drafts,pending,targets,field='cantonese',alternative_index=attempt)
        if not changed:break
        emit('精簡重配',f'只重配 {len(changed)} 句偏長台詞（{attempt+1}/2），保持自然語速同本句原聲參考。',.85)
        records=[];fresh=[]
        for i in changed:
            cue=drafts[i]
            identity=hashlib.sha256(json.dumps(['measured-natural-retake-2',cue,cfg.get('ttsBackend'),language,attempt],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
            folder=job/'concise-takes'/identity;folder.mkdir(parents=True,exist_ok=True)
            marker=folder/'attempt.json'
            try:saved=json.loads(marker.read_text())
            except (OSError,ValueError):saved=None
            recovered=recover_batch(saved,cue,cfg,job)
            if recovered!=saved:atomic_json(marker,recovered)
            saved=recovered
            record=dict(position=i,identity=identity,marker=marker,saved=saved)
            records.append(record)
            if saved is None:
                # Reserve per line before the single batched model load. Old
                # single-line markers remain readable, including failed takes.
                atomic_json(marker,dict(status='attempted',paths=[]));fresh.append(record)
        if fresh:
            from track_control import check,UserSkipped
            batch_key=hashlib.sha256(json.dumps([r['identity'] for r in fresh]).encode()).hexdigest()[:24]
            folder=job/'concise-batches'/batch_key;folder.mkdir(parents=True,exist_ok=True)
            pending=[dict(drafts[r['position']],reviewIndex=cues[r['position']].get('reviewIndex',r['position']),_seed=93017+attempt*104729,_deliveryStyle='cantonese-strict-clauses' if language=='yue' else 'complete-clauses',_targetSeconds=(placement[r['position']]['deadline']-placement[r['position']]['start']) if placement is not None else natural_window(cues[r['position']],cues,cfg['duration'],cfg)[1]-natural_window(cues[r['position']],cues,cfg['duration'],cfg)[0]) for r in fresh]
            for record in fresh:
                record['saved']=dict(status='attempted',paths=[],batch=str(folder))
                atomic_json(record['marker'],record['saved'])
            try:
                check(cfg)
                generated=gsv_audio(dict(cfg,editorCache=str(folder),audioRerunToken=batch_key),folder,pending,run,emit)
                if len(generated)!=len(pending):raise ValueError('精簡重配結果數量不符，未錯配其他句錄音。')
                for record,path in zip(fresh,generated):
                    record['saved']=dict(status='generated',paths=[str(path)])
                    atomic_json(record['marker'],record['saved'])
            except UserSkipped:raise
            except (OSError,RuntimeError,ValueError) as error:
                for record in fresh:
                    record['saved']=recover_batch(dict(status='failed',paths=[],batch=str(folder),error=str(error)[:300]),drafts[record['position']],cfg,job)
                    atomic_json(record['marker'],record['saved'])
        candidates=[]
        for record in records:
            saved=record['saved'] or {};i=record['position']
            candidate=Path(saved['paths'][0]) if saved.get('paths') else None
            if candidate and candidate.is_file() and not candidate.name.startswith('skipped-'):
                if 0<seconds(candidate,cfg,run)<seconds(selected[i],cfg,run):candidates.append((i,candidate))
        # A rewritten take is new speech too. Listen to the changed subset once
        # per bounded pass; never restart the full language-repair loop here.
        checks={}
        if candidates and cfg.get('productionMode')=='normal':
            from normal_mode import inspect
            checks=inspect(cfg,job,[dict(drafts[i],reviewIndex=cues[i].get('reviewIndex',i)) for i,_ in candidates],[p for _,p in candidates],emit)
        for i,candidate in candidates:
            evidence=checks.get(cues[i].get('reviewIndex',i)+1,{})
            rejected=bool(evidence.get('languageFailure') or evidence.get('decision') in ('mandarin','japanese') or evidence.get('contentFailure'))
            audit.append(dict(index=cues[i].get('reviewIndex',i)+1,attempt=attempt+1,candidateAudio=str(candidate),
                seconds=seconds(candidate,cfg,run),adopted=not rejected,languageCheck=evidence,
                reason='language-or-content-failure' if rejected else 'shorter-take-no-confirmed-content-failure'))
            if rejected:continue
            cue=drafts[i]
            selected[i]=candidate;cues[i].update(cantonese=cue['cantonese'],preConciseCantonese=cue.get('preConciseCantonese'))
            if language=='en':cues[i]['english']=cue['cantonese']
            if not cues[i].get('captionOverride'):cues[i]['captionText']=cue['cantonese']
        review=job/'review.json'
        if review.is_file():
            obj=json.loads(review.read_text());by_id={c.get('reviewIndex',i):c for i,c in enumerate(cues)}
            for i,c in enumerate(obj.get('cues',[])):
                revised=by_id.get(c.get('reviewIndex',i))
                if revised:c.update({k:revised[k] for k in ('cantonese','english','captionText','preConciseCantonese') if k in revised})
            atomic_json(review,obj)
    confirmed={r['index']:r for r in audit if r['adopted'] and r['languageCheck'].get('decision')==('english' if language=='en' else 'cantonese')}
    checkfile=job/'normal-checks.json'
    if confirmed and checkfile.is_file():
        normal=json.loads(checkfile.read_text())
        fixed=set(confirmed).intersection(normal.get('unresolved',[]))
        normal['unresolved']=[i for i in normal.get('unresolved',[]) if i not in fixed]
        for row in normal.get('repairs',[]):
            if row.get('index') in fixed:row.update(repaired=True,resolvedBy='concise-natural-retake',candidateAudio=confirmed[row['index']]['candidateAudio'])
        if fixed:
            from project_store import resolve_issues
            resolve_issues(cfg,job,fixed);atomic_json(checkfile,normal)
    atomic_json(job/'natural-repair.json',dict(maximumRewritePasses=2,batchedEngineLoads=True,
        sameSourceReference=True,qualityCertified=False,candidates=audit))
    return selected
