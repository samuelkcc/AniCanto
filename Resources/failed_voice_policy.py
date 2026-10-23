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
    job = Path(job)
    checks = read(job / 'normal-checks.json', {})
    unresolved = set(checks.get('unresolved', []))
    repairs = {r.get('index'): r for r in checks.get('repairs', [])}
    generic = read(job / 'target-reference-recovery.json', {})
    generic_available = {r.get('index') for r in generic.values()
                         if r.get('status') in ('adopted', 'selected-unverified')
                         and audible(r.get('selectedAudio') or r.get('audio'))}
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
            if candidate:
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
