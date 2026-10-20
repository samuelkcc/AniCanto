"""One shared automatic repair per source turn; persists across resume."""
import hashlib,json
from pathlib import Path


def claim(cfg,job,cue,reason):
    if not cfg.get('boundedRepairs'):return True
    # Source identity deliberately excludes translated text and subphrase boundaries.
    identity=[cue.get('reviewIndex', [cue.get('start'),cue.get('end')]),cue.get('speakerId','')]
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    path=Path(job)/'repair-budget.json'
    ledger=json.loads(path.read_text()) if path.exists() else {}
    row=ledger.get(key,{})
    reasons=row.get('reasons',[row['reason']] if row.get('reason') else [])
    kind='timing' if reason in ('duration','brisk','timed','short-delivery') else reason
    if kind in reasons or len(reasons)>=3:return False
    ledger[key]=dict(index=cue.get('reviewIndex'),reason=reason,reasons=reasons+[kind],limit=3)
    from worker import atomic_json
    atomic_json(path,ledger)
    return True


def clear_content_problem(cue,check):
    if check.get('cantoneseReviewPolicy'):
        return bool(check.get('confirmedContentFailure'))
    # Keep ambiguous Cantonese ASR disagreements as flags, not automatic retakes.
    # Negation disagreements still remain visible in the final report.
    import re
    count=len(re.sub(r'\W','',cue['cantonese']))
    # Written Chinese can match Cantonese exactly; an auto language label alone
    # cannot establish Mandarin speech, especially on short names/reactions.
    wrong_language=check.get('languageMismatch') and check.get('similarity',1)<.72 and count>=6
    lost_negation=bool(check.get('criticalDifferences'))
    # Short lexical lines can also collapse to an almost silent 0.44-second
    # take. A failed transcript is different from a Mandarin language label or
    # a homophone disagreement: give it the same single bounded content retry.
    # Nonverbal/source-preserved clips are excluded by check_content's caller.
    no_words=(count>=3 and check.get('languageUnverified') is True and
              not str(check.get('heard') or '').strip() and check.get('similarity')==0)
    return no_words or (count>=8 and check.get('similarity',1)<.45) or (count>=3 and (wrong_language or lost_negation))


def take_key(cue,path):
    return hashlib.sha256(Path(path).read_bytes()+cue['cantonese'].encode()).hexdigest()


def retained_takes(job,cues,originals):
    path=Path(job)/'selected-takes.json'
    saved=json.loads(path.read_text()) if path.exists() else {}
    if not saved:return list(originals)
    result=[]
    for cue,original in zip(cues,originals):
        if not Path(original).is_file():result.append(original);continue
        entry=saved.get(take_key(cue,original),{})
        target=Path(entry.get('path',''))
        valid=target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==entry.get('sha')
        result.append(target if valid else original)
    return result


def remember_takes(job,cues,originals,selected):
    path=Path(job)/'selected-takes.json'
    saved=json.loads(path.read_text()) if path.exists() else {}
    for cue,original,chosen in zip(cues,originals,selected):
        if original==chosen or not Path(original).is_file() or not Path(chosen).is_file():continue
        saved[take_key(cue,original)]=dict(path=str(chosen),sha=hashlib.sha256(Path(chosen).read_bytes()).hexdigest())
    if saved:
        from worker import atomic_json
        atomic_json(path,saved)
