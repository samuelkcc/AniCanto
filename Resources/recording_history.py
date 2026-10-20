"""Immutable diagnostic recordings. Rejection never means delete the evidence.

The archive belongs to the model job, not a global voice library. Each record
keeps cue, engine, language, words and the original failure reason together.
It is never an automatically accepted take.
"""
import hashlib
import json
from pathlib import Path
import shutil
import time
import uuid


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {} if default is None else default


def engine_for(cfg, action):
    return {'tts': cfg.get('ttsBackend', 'gpt-sovits'), 'cosy': 'cosyvoice3',
            'qwen': 'qwen-tts'}.get(action, action)


def preserve(job, engine, language, item, audio, reason, cue=None, generation=None):
    """Copy a rejected recording once, before another attempt can overwrite it."""
    job, audio = Path(job), Path(audio)
    if not audio.is_file() or audio.stat().st_size <= 44:
        return None
    cue = cue or {}
    position = item.get('reviewIndex')
    if type(position) is not int or position < 0:
        return None  # Never associate a recording by words alone.
    text = item.get('approvedText', item.get('text', ''))
    requested = (generation or {}).get('submittedText',item.get('text',text))
    stat = audio.stat()
    digest = hashlib.sha256(audio.read_bytes()).hexdigest()
    identity = [engine, language, position, text, requested, digest, str(reason),
                (generation or {}).get('seed', item.get('seed'))]
    ident = hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    folder = job / 'recording-history'
    destination = folder / ident
    if (destination / 'take.json').is_file():
        return destination
    folder.mkdir(parents=True, exist_ok=True)
    stage = folder / ('.pending-' + uuid.uuid4().hex)
    stage.mkdir()
    try:
        shutil.copy2(audio, stage / 'audio.wav')
        if hashlib.sha256((stage / 'audio.wav').read_bytes()).hexdigest() != digest:
            raise OSError('Diagnostic recording changed while being archived')
        record = dict(schemaVersion=1, id=ident, status='rejected', engine=engine,
                      language=language, index=position + 1, text=text,
                      spokenText=requested, reason=str(reason),
                      created=stat.st_mtime, archivedAt=time.time(),
                      sourceAudio=str(audio), sourceMTime=stat.st_mtime,
                      audio='audio.wav', audioSHA256=digest,
                      editorID=cue.get('editorID'), start=cue.get('start'), end=cue.get('end'),
                      speakerId=item.get('profile', {}).get('id', cue.get('speakerId')),
                      generation=generation or {}, automaticallyAccepted=False)
        (stage / 'take.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        try:
            stage.rename(destination)
        except OSError:
            if not (destination / 'take.json').is_file():
                raise
        return destination
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def preserve_request(cfg, action, request):
    """Called around every isolated model attempt, including runtime retries.

    Readers also expose legacy diagnostic files, so an existing episode does
    not need to be regenerated merely to audition its failures.
    """
    if action not in ('tts', 'cosy', 'qwen', 'voxcpm2', 'wsyue', 'drama3'):
        return
    job = request.get('job')
    if not job:
        return
    job = Path(job)
    review = read(job / 'review.json')
    cues = review.get('cues', []) if isinstance(review, dict) else []
    for item in request.get('items', []):
        try:
            path = Path(item['output'])
            failure = read(path.with_suffix('.failure.json'))
            if not isinstance(failure, dict):
                failure = {}
            health = read(path.with_suffix('.health.json'), [])
            if not isinstance(health, (dict, list)):
                health = {}
            if isinstance(health, list):
                last = health[-1] if health and isinstance(health[-1], dict) else {}
                problem = last.get('problems', last.get('errors', []))
                reason = failure.get('error') or last.get('error') or (', '.join(map(str, problem)) if isinstance(problem,list) else str(problem or ''))
            else:
                reason = failure.get('error') or (str(health.get('attempts', [])[-1]) if health.get('passed') is False and health.get('attempts') else '')
            generation = read(path.with_suffix('.generation.json'))
            if not isinstance(generation, dict):
                generation = {}
            candidates = [path.with_suffix(suffix) for suffix in ('.rejected.raw.wav', '.raw.wav', '.rejected.wav')]
            candidates += [Path(generation['rejectedAudio'])] if generation.get('rejectedAudio') else []
            audio = next((p for p in candidates if p.is_file() and p.stat().st_size > 44), None)
            if audio is None:
                continue
            if not reason and not path.is_file():
                reason='生成未完成；保留原始錄音供比較。'
            if not reason:
                continue
            position = item.get('reviewIndex')
            cue = next((c for n,c in enumerate(cues) if c.get('reviewIndex',n)==position),{}) if type(position) is int and position>=0 else {}
            preserve(job, engine_for(cfg, action), request.get('targetLanguage', cfg.get('targetLanguage', 'yue')),
                     item, audio, reason, cue, generation)
        except (OSError, ValueError, TypeError, KeyError) as error:
            # Failure to save a diagnostic copy must not discard a usable take
            # or terminate the movie conversion. The original remains intact.
            print(json.dumps(dict(stage='錄音歷史', message='未能保存診斷錄音副本：' + str(error)), ensure_ascii=False), flush=True)


def preserve_review(cfg,job,cue,index,audio,reason,check=None):
    """A generated WAV can be rejected later by review, not just the decoder."""
    try:
        item=dict(reviewIndex=cue.get('reviewIndex',index),text=cue.get('cantonese',''),
                  approvedText=cue.get('_approvedText',cue.get('cantonese','')),seed=cue.get('_seed',42))
        return preserve(job,cfg.get('ttsBackend','gpt-sovits'),cfg.get('targetLanguage','yue'),item,
                        audio,reason,cue,dict(speechCheck=check or {},stage='post-generation-review'))
    except (OSError,ValueError,TypeError,KeyError) as error:
        print(json.dumps(dict(stage='錄音歷史',message='未能保存覆核錄音副本：'+str(error)),ensure_ascii=False),flush=True)
