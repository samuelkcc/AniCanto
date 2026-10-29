from repair_limits import bounded as bounded_repair
"""Try installed, compatible voice engines for failed Normal-mode dialogue.

This is a bounded last actor-clone attempt.  It never downloads a model, changes
healthy lines, or accepts an unverified language/content result.  Failed takes
and the evidence ledger remain under the job for later audition.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REVISION = 'alternate-voice-engine-1'
ORDER = ('drama3', 'gpt-sovits-v2', 'gpt-sovits', 'cosyvoice3', 'voxcpm2', 'wsyue')


def read(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def installed(cfg):
    """Return at most two complete, locally available alternate engines."""
    if cfg.get('automaticAlternateVoice', True) is False or not cfg.get('storage'):
        return []
    from engine_policy import ACTIVE, languages
    from model_catalog import catalog, resolve
    root = Path(cfg['storage'])
    current = cfg.get('ttsBackend')
    language = cfg.get('targetLanguage', 'yue')
    preferred = tuple(dict.fromkeys((cfg.get('selectedEngines') or []) + list(ORDER)))
    choices = []
    for engine in preferred:
        if engine == current or engine not in ACTIVE or language not in languages(engine):
            continue
        variants = [r for r in catalog() if r.get('category') == 'voice' and r.get('engine') == engine and not r.get('retired') and not r.get('licenseReviewRequired')]
        variant = next((r for r in variants if r['id'] == cfg.get('deploymentModels', {}).get('voice')), None)
        ordered = ([variant] if variant else []) + [r for r in variants if r is not variant]
        for row in ordered:
            try:
                resolve(root, row['id'])
                if sys.platform == 'win32':
                    from native_models import missing_setup
                    if missing_setup(root, [engine]):
                        continue
                else:
                    if engine.startswith('gpt-sovits'):
                        from gsv_versions import version
                        runtime = 'gsv-' + version({'ttsBackend': engine})
                    else:
                        runtime = 'cosy' if engine == 'cosyvoice3' else engine
                    if not (root / (runtime + '-ready.json')).is_file():
                        continue
                budget = float(cfg.get('modelMemoryBudgetGB') or 0)
                if budget and float(row.get('estimatedMemoryGB') or 0) > budget:
                    continue
                choices.append((engine, row['id']))
                break
            except (OSError, ValueError, TypeError):
                continue
        if len(choices) == 2:
            break
    return choices


@bounded_repair('normal_engine_fallback.repair')
def repair(cfg, job, cues, paths, placement, run, emit):
    permissions=__import__('repair_permissions')
    if permissions.enabled(cfg) and (not permissions.alternate(cfg) or cfg.get('_genericTargetVoice') and not permissions.generic(cfg)):return paths
    if cfg.get('editorRender') or cfg.get('productionMode') != 'normal' or not placement or cfg.get('automaticAlternateVoice', True) is False:
        return paths
    from dubbing import gsv_audio, is_vocalization, profile_for
    from normal_mode import inspect, audio_present
    from normal_recovery import verified_check, clear_confirmed
    from natural_delivery import seconds
    from natural_schedule import plan
    from speech_timing import natural_window
    from track_control import check, UserSkipped
    from worker import atomic_json

    job = Path(job)
    pending = set(read(job / 'normal-checks.json', {}).get('unresolved', []))
    if __import__('delivery_policy').bounded_delivery(cfg):pending=__import__('delivery_policy').confirmed_indices(cfg,job)
    selected = list(paths)
    root = job.parent.parent if job.parent.name == 'tracks' else job
    cuts = read(root / 'natural-scene-boundaries.json', {}).get('cuts', [])
    planning = read(job / 'natural-placement.json', {})
    lengths = [p.get('seconds') for p in placement]
    confirmed = set()
    ledger_path = job / 'alternate-engine-recovery.json'
    ledger = read(ledger_path, {})
    language = cfg.get('targetLanguage', 'yue')

    def simulate(trial):
        if cfg.get('naturalTimingPolicy', 'micro-shift') == 'micro-shift':
            return plan(cfg, cues, trial, cuts)
        rows = []
        for cue, length in zip(cues, trial):
            start, deadline = natural_window(cue, cues, cfg['duration'], cfg)
            rows.append(dict(fit=length is not None and length <= deadline-start, start=start, deadline=deadline))
        return rows

    choices=installed(cfg)
    for engine, variant in choices[:cfg.get('_maximumAlternateEngines',len(choices))]:
        generic_profiles={}
        alternate = dict(cfg, ttsBackend=engine, selectedEngines=[engine], voiceStyleMode='clone')
        if engine in ('drama3', 'voxcpm2', 'wsyue'):
            from local_tts import ENGINES
            alternate[ENGINES[engine]['key']] = variant
        if engine.startswith('gpt-sovits'):
            from gsv_versions import version
            alternate['gsvVersion'] = version(alternate)
        if engine == 'cosyvoice3':
            alternate['cosyModel'] = variant
        records = []
        for i, cue in enumerate(cues):
            index = cue.get('reviewIndex', i) + 1
            if cfg.get('preferFirstAudibleTake',True) and audio_present(selected[i]) and index not in pending and placement[i].get('fit'):
                continue
            if index not in pending and audio_present(selected[i]) and placement[i].get('fit'):
                continue
            if cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not cue.get('enabled', True) or is_vocalization(cue) or not cue.get('cantonese', '').strip():
                continue
            try:
                if cfg.get('_genericTargetVoice'):
                    try:original=profile_for(cue,alternate)
                    except (OSError,ValueError):original=dict(id=cue.get('speakerId') or f'generic-{index}',language='',reference='',promptText='')
                    from natural_voices import resolve
                    reference=resolve(dict(original,engineReferences={},promptText=''),dict(alternate,voiceStyleMode='natural'))
                    generic_profiles[reference['id']]=reference
                else:reference = profile_for(cue, alternate)
                reference_hash = hashlib.sha256(Path(reference['reference']).read_bytes()).hexdigest()
            except (OSError, ValueError, KeyError):
                continue
            identity = [REVISION, bool(cfg.get('_genericTargetVoice')), engine, variant, language, index, cue.get('start'), cue.get('end'), cue['cantonese'], cue.get('speakerId'), reference_hash, reference.get('promptText')]
            key = hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
            old = ledger.get(key, {})
            if old and any(__import__('delivery_policy').rejected_audio(cfg,job,index,old.get(k)) for k in ('audio','selectedAudio')):
                old.update(status='not-verified',reason='confirmed-on-selected-audio')
                atomic_json(ledger_path,ledger)
                continue
            if __import__('delivery_policy').bounded_delivery(cfg) and old.get('generationAttempts',0)>=1 and not audio_present(old.get('audio','')):continue
            if old.get('status') in ('not-verified', 'timing-not-fit', 'generation-failed') or cfg.get('_genericTargetVoice') and old.get('generationAttempts',0)>=2 and not audio_present(old.get('audio')):
                continue
            if old.get('status') == 'adopted' and audio_present(old.get('selectedAudio')):
                selected[i] = Path(old['selectedAudio'])
                confirmed.add(index)
                continue
            draft = dict(cue, speakerId=reference['id'], reviewIndex=index-1, _seed=781433, _targetSeconds=placement[i]['deadline']-placement[i]['start'], _deliveryStyle='cantonese-strict-clauses' if language == 'yue' else 'complete-clauses')
            records.append((i, index, key, draft))
            ledger.setdefault(key, dict(index=index, engine=engine, variant=variant, action='alternate-engine', status='reserved', text=cue['cantonese'], voiceSimilarityCertified=False,genericTargetReference=bool(cfg.get('_genericTargetVoice'))))
        if not records:
            continue
        if generic_profiles:
            alternate['voiceProfiles']=list(generic_profiles.values())
            alternate['_voiceManifest']={p['id']:hashlib.sha256(Path(p['reference']).read_bytes()).hexdigest() for p in generic_profiles.values()}
        atomic_json(ledger_path, ledger)
        folder = job / 'alternate-engine-recovery' / engine
        folder.mkdir(parents=True, exist_ok=True)
        alternate.update(editorCache=str(folder), audioRerunToken=REVISION + '-' + engine)
        fresh = [r for r in records if not ledger[r[2]].get('audio') or not audio_present(ledger[r[2]]['audio'])]
        if fresh and __import__('delivery_policy').repair_first(cfg):
            from recovery_attempts import reserve
            fresh=[r for r in fresh if reserve(job,'alternate-generation',r[1],1)]
        if fresh:
            emit('其他模型補聲', f'{engine}：試用已下載配音模型補救 {len(fresh)} 句，原本錄音會保留。', .90)
            for _, _, key, _ in fresh:
                ledger[key]['status'] = 'generating'
                ledger[key]['generationAttempts']=ledger[key].get('generationAttempts',0)+1
            atomic_json(ledger_path, ledger)
            try:
                check(cfg)
                generated = gsv_audio(alternate, folder, [r[3] for r in fresh], run, emit)
                if len(generated) != len(fresh):
                    raise ValueError('Alternate engine returned an incomplete batch')
                for (_, _, key, _), path in zip(fresh, generated):
                    ledger[key].update(audio=str(path), status='generated' if audio_present(path) else 'generation-failed')
            except UserSkipped:
                raise
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
                for _, _, key, _ in fresh:
                    ledger[key].update(status='generation-failed', error=str(error)[:300])
            atomic_json(ledger_path, ledger)
        candidates = [r for r in records if ledger[r[2]].get('audio') and audio_present(ledger[r[2]]['audio'])]
        if not candidates:
            continue
        try:
            proof = {} if cfg.get('workMode')=='performance' and __import__('delivery_policy').bounded_delivery(cfg) else inspect(alternate, folder, [r[3] for r in candidates], [Path(ledger[r[2]]['audio']) for r in candidates], emit)
        except UserSkipped:
            raise
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
            for _, _, key, _ in candidates:
                ledger[key].update(status='verification-failed', error=str(error)[:300])
            atomic_json(ledger_path, ledger)
            continue
        for i, index, key, _ in candidates:
            record = ledger[key]
            evidence = proof.get(index, {})
            if (bool(evidence.get('languageFailure') or evidence.get('contentFailure')) if __import__('delivery_policy').bounded_delivery(cfg) else not verified_check(evidence, cues[i]['cantonese'], language)):
                record.update(status='not-verified', check=evidence)
                continue
            candidate = Path(record['audio'])
            if __import__('delivery_policy').rejected_audio(cfg,job,index,candidate):
                record.update(status='not-verified',reason='confirmed-audio-fingerprint');continue
            try:
                trial = list(lengths)
                trial[i] = seconds(candidate, alternate, run)
                scheduled = simulate(trial)
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
                record.update(status='timing-check-failed', error=str(error)[:300], check=evidence)
                continue
            if not scheduled[i]['fit'] or any(p['fit'] and not scheduled[j]['fit'] for j, p in enumerate(placement)):
                record.update(status='timing-not-fit', candidateSeconds=trial[i], check=evidence)
                continue
            selected[i] = candidate
            lengths, placement = trial, scheduled
            confirmed.add(index)
            record.update(status='adopted', qualityCertified=False, contentVerified=verified_check(evidence,cues[i]['cantonese'],language), selectedAudio=str(candidate), candidateSeconds=trial[i], check=evidence)
        atomic_json(ledger_path, ledger)
    clear_confirmed(cfg, job, confirmed, atomic_json)
    return selected
