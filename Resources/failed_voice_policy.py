"""Choose an audible disposition for lines still unresolved after automatic repair.

This is an editorial fallback, never a quality pass. The rejected take and all
replacement attempts remain on disk for the review report.
"""
import json
from pathlib import Path


def read(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def audible(path):
    from normal_mode import audio_present
    return bool(path) and audio_present(path)


def choose(cfg, job, cues, paths):
    """Return selected TTS paths and indices whose source speech is preferred."""
    if __import__('repair_permissions').enabled(cfg):
        return __import__('repair_permissions').choose(cfg,job,cues,paths)
    job = Path(job)
    checks = read(job / 'normal-checks.json', {})
    unresolved = set(checks.get('unresolved', []))
    placement=read(job/'natural-placement.json',{})
    unresolved.update(r['index'] for r in placement.get('rows',[]) if not r.get('fit') and r.get('seconds') is not None)
    repairs = {r.get('index'): r for r in checks.get('repairs', [])}
    generic = read(job / 'target-reference-recovery.json', {})
    generic_available = {r.get('index') for r in generic.values()
                         if r.get('status') in ('adopted', 'selected-unverified')
                         and audible(r.get('selectedAudio') or r.get('audio'))}
    if __import__('delivery_policy').enabled(cfg):
        alternate=read(job/'alternate-engine-recovery.json',{})
        generic_available.update(r.get('index') for r in alternate.values() if r.get('genericTargetReference') and r.get('status')=='adopted' and audible(r.get('selectedAudio')))
    from delivery_policy import bounded_delivery,confirmed_indices
    confirmed=confirmed_indices(cfg,job)
    if bounded_delivery(cfg):
        unresolved=confirmed | {r['index'] for r in placement.get('rows',[]) if not r.get('fit')} | {c.get('reviewIndex',i)+1 for i,c in enumerate(cues) if not audible(paths[i]) and c.get('cantonese','').strip()}
        native=read(job/'system-voice-fallback.json',{}).get('records',{})
        generic_available.update(r.get('index') for r in native.values() if r.get('status')=='adopted' and audible(r.get('selectedAudio')))
    policy = cfg.get('failedVoicePolicy', 'generic')
    if policy not in ('generic', 'first-take', 'source'):
        policy = 'generic'
    selected = list(paths)
    source = set()
    decisions = []
    for i, cue in enumerate(cues):
        index = cue.get('reviewIndex', i) + 1
        if index not in unresolved or cue.get('editorAudio') or cue.get('preserveOriginalSpeech') or not cue.get('enabled', True):
            continue
        if policy == 'source':
            source.add(i)
            action = 'source-speech'
        elif policy == 'first-take':
            record = repairs.get(index, {})
            first = record.get('originalAudio')
            alternatives = [a.get('candidateAudio') for a in record.get('attempts', [])]
            candidate = next((p for p in [first, *alternatives] if audible(p)), None)
            if bounded_delivery(cfg) and index in confirmed:
                if index in generic_available and audible(selected[i]):
                    action='confirmed-error-replaced-with-target-fallback'
                else:
                    source.add(i);action='source-after-confirmed-error-and-fallback-failure'
            elif bounded_delivery(cfg) and any(r.get('index')==index and not r.get('fit') for r in placement.get('rows',[])):
                source.add(i);action='source-after-measured-overrun-and-fallback-failure'
            elif candidate:
                selected[i] = Path(candidate)
                action = 'first-audible-take'
            elif audible(selected[i]):
                action = 'retained-audible-take'
            else:
                source.add(i)
                action = 'source-after-no-audible-take'
        elif index in generic_available and audible(selected[i]):
            action = 'generic-target-language-take'
        else:
            source.add(i)
            action = 'source-after-generic-failed'
        decisions.append(dict(index=index, policy=policy, action=action, qualityCertified=False))
    if decisions:
        from worker import atomic_json
        atomic_json(job / 'failed-voice-choices.json', dict(policy=policy, decisions=decisions))
    return selected, source
