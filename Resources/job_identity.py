"""Resume source work independently of presentation and final mix choices.

Old folders are adopted only when their original content-addressed name can be
reconstructed using the current source stat, subtitles and processing inputs.
This locates intermediate work; it never certifies or adopts an old final movie.
"""
import copy
import hashlib
import json
from pathlib import Path
import re

PRESENTATION_FIELDS = frozenset(('animeTheme', 'themeSession', 'randomAnimeTheme',
    'appearance', 'controlDensity', 'interfaceMode', 'language', 'interfaceLanguage',
    '_standardProductionSettings'))
# These alter final delivery, not recognition, translation or voice references.
# Downstream track/mix identities continue to include the relevant actual values.
DELIVERY_FIELDS = frozenset(('exportFolder', 'backgroundGain', 'backgroundDucking', 'mixOriginal'))
REUSABLE_FIELDS = PRESENTATION_FIELDS | DELIVERY_FIELDS
SCHEMA = 1


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def canonical(identity):
    return {k: copy.deepcopy(v) for k, v in identity.items() if k not in REUSABLE_FIELDS}


def read(path):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def compatible(folder, identity, body, fingerprint):
    saved = read(folder/'resume-identity.json')
    if saved:
        return (saved.get('schemaVersion') == SCHEMA
                and saved.get('fingerprint') == fingerprint
                and saved.get('identity') == body)
    # A review alone is insufficient: it may describe media changed in place.
    # Reconstruct the old key with today's source stat and caption checksum.
    previous = read(folder/'review.json').get('config')
    if not isinstance(previous, dict):
        return False
    legacy = copy.deepcopy(identity)
    for key in REUSABLE_FIELDS:
        if key in previous:
            legacy[key] = copy.deepcopy(previous[key])
        else:
            legacy.pop(key, None)
    return digest(legacy)[:16] == folder.name


def resolve(storage, identity, emit=None, *, persist=True):
    jobs = Path(storage)/'jobs'
    body = canonical(identity)
    fingerprint = digest(body)
    target = jobs/fingerprint[:16]
    matches = []
    if jobs.is_dir():
        for folder in jobs.iterdir():
            if folder.is_symlink() or not folder.is_dir() or not re.fullmatch('[0-9a-f]{16}', folder.name):
                continue
            if compatible(folder, identity, body, fingerprint):
                review = folder/'review.json'
                cues = folder/'cues.json'
                matches.append((2 if review.is_file() and cues.is_file() else 1 if cues.is_file() else 0,
                                review.stat().st_mtime_ns if review.is_file() else 0,
                                folder == target, folder))
    if matches:
        target = max(matches, key=lambda item: item[:3])[3]
    elif target.exists():
        # A corrupt receipt or an unexpected collision cannot overwrite work.
        raise ValueError('Saved work identity could not be verified; existing files were kept.')
    if persist:
        from atomic_files import write_json
        target.mkdir(parents=True, exist_ok=True)
        write_json(target/'resume-identity.json', dict(schemaVersion=SCHEMA,
            fingerprint=fingerprint, identity=body, qualityCertified=False))
    if matches and emit:
        emit('續做', '已找到相同影片及處理設定嘅保存進度；沿用辨識、配音稿同可用錄音，只補未完成部分。',
             workCached=True, resumeMatched=True, job=str(target))
    return target
