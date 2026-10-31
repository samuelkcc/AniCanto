"""Explicit removal of one retained review recording. Never automatic.

A removed WAV moves into the job's discarded-recordings folder with a manifest.
The review list hides it through the block file. Audio used by the current
export, a saved choice or a render never moves.

The caller passes the same zero-based dialogue position that the review report
uses for every other per-line action. Snapshot rows number the same line from
one, so this module adds one internally.
"""
import hashlib,json,shutil,time,uuid
from pathlib import Path

BLOCKS='review-take-blocks.json';DISCARDED='discarded-recordings'


def blocks(root):
    """Return the saved removal records for one job folder."""
    try:
        rows=json.loads((Path(root)/BLOCKS).read_text())
    except (OSError,ValueError):
        return []
    return [x for x in rows if isinstance(x,dict) and x.get('path')] if isinstance(rows,list) else []


def hidden(root):
    return {str(Path(row['path']).resolve()) for row in blocks(root)}


def listed(snapshot,line,language):
    """Every recording path the review report can show for one line and track."""
    found={}
    def add(path,engine,kind):
        if isinstance(path,str) and path:found.setdefault(str(Path(path).resolve()),dict(engine=engine or '',kind=kind))
    for row in snapshot.get('takes') or []:
        if row.get('index')==line and (row.get('language') or 'yue')==language:add(row.get('audio'),row.get('engine'),'take')
    for row in snapshot.get('history') or []:
        if row.get('index')==line and (row.get('language') or 'yue')==language:add(row.get('path'),row.get('engine'),'history')
    for row in snapshot.get('recordingCandidates') or []:
        if row.get('index')==line and (row.get('language') or 'yue')==language:add(row.get('path'),row.get('engine'),'candidate')
    for issue in (snapshot.get('issues') or [])+(snapshot.get('resolvedIssues') or []):
        if issue.get('index')!=line or (issue.get('language') or 'yue')!=language:continue
        for attempt in issue.get('attempts') or []:
            audition=attempt.get('audition')
            if isinstance(audition,dict):add(audition.get('path'),attempt.get('engine') or issue.get('engine'),'attempt')
        for kind,audition in (issue.get('auditions') or {}).items():
            if kind in ('generated','lastFailed') and isinstance(audition,dict):add(audition.get('path'),issue.get('engine'),'audition')
    return found


def protected(snapshot,draft,line,language):
    """Recordings on one line that still carry delivered or explicitly chosen audio."""
    return {path for path,record in protection(snapshot,draft).items()
            if record.get('index') in (None,line) and record.get('language') in (None,language)}


def protection(snapshot,draft):
    """The whole protection rule, in one place, for the guard and the report.

    Only these four links protect a recording: the audio in the current export,
    a saved review choice, a take inside a completed version, and the recording
    link on the dialogue segment. A recording with none of them is removable,
    including the first generated take. Paths are resolve-normalised so the
    report and this guard always compare the same spelling.
    """
    kept={}
    def add(path,reason,index=None,language=None):
        if not isinstance(path,str) or not path:return
        kept.setdefault(str(Path(path).resolve()),dict(reason=reason,index=index,language=language))
    for row in snapshot.get('reportRows') or []:
        add(row.get('selectedAudio'),'current export',row.get('index'),row.get('language') or 'yue')
        add(row.get('audio'),'current export',row.get('index'),row.get('language') or 'yue')
    for take in snapshot.get('takes') or []:
        if take.get('versionStatus')=='complete':
            add(take.get('audio'),'completed version take',take.get('index'),take.get('language') or 'yue')
    for segment in (draft or {}).get('segments') or []:
        add(segment.get('audioTake'),'recording saved on this line')
        for decision in (segment.get('reviewDecisions') or {}).values():
            if isinstance(decision,dict):add(decision.get('audio'),'saved review choice')
    return kept


def remove(root,snapshot,draft,index,language,engine,path,confirm=False):
    root=Path(root).resolve()
    if type(index) is not int or index<0:raise ValueError('Unknown dialogue line.')
    line=index+1
    if language not in ((snapshot.get('review',{}).get('config',{}) or {}).get('dubLanguages') or ['yue']):raise ValueError('Unknown dubbing language.')
    if confirm is not True:raise ValueError('Confirm that you want to remove this recording.')
    target=Path(path).resolve() if isinstance(path,str) and path else None
    if target is None:raise ValueError('Choose a recording to remove.')
    if str(target) in hidden(root):raise ValueError('This recording is already removed.')
    if target.is_relative_to(root/DISCARDED):raise ValueError('This recording is already in the discarded-recordings folder.')
    candidates=listed(snapshot,line,language)
    if str(target) not in candidates:raise ValueError('This recording is not listed on this line. Refresh the review report.')
    if str(target) in protected(snapshot,draft,line,language):raise ValueError('This recording is used by the current export or a saved choice.')
    if not target.is_relative_to(root) or target.suffix.lower()!='.wav' or not target.is_file():raise ValueError('The recording does not belong to this project.')
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    ident=uuid.uuid4().hex;folder=root/DISCARDED/ident;folder.mkdir(parents=True)
    record=dict(path=str(target),discarded=str(folder/'audio.wav'),sha256=digest,index=line,language=language,
                engine=engine or candidates.get(str(target),{}).get('engine') or '',removedAt=time.time(),qualityCertified=False)
    shutil.move(str(target),str(folder/'audio.wav'))
    (folder/'removal.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    path_file=root/BLOCKS;rows=blocks(root);rows.append(record)
    temporary=path_file.with_suffix('.tmp');temporary.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');temporary.replace(path_file)
    return record
