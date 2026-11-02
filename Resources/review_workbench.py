"""AniCanto editorial triage. Original implementation; no external app code.

Human review is distinct from model verification and from an export choice.
Decisions bind to the line, track, edited words and diagnostic evidence.
"""
import hashlib,json,time
import atomic_files
from pathlib import Path

CATEGORIES=('missing','content','timing','reference','fallback','other')
LINE_PREFIX='line-'

def line_id(index,language,engine):
    """Public id for a dialogue line that carries no diagnostic issue."""
    return f'{LINE_PREFIX}{index}-{language}-{engine}'

def row_id(row):
    return line_id(row.get('index'),row.get('language','yue'),row.get('engine',''))

def category(issue):
    kind=issue.get('kind','')
    if kind in ('missing-audio','fast-generation-failed','tts-generation','generation-limit','no-audible-voice','retry-budget-exhausted'):return 'missing'
    if kind in ('timing-overrun',):return 'timing'
    if kind in ('reference','reference-blocked'):return 'reference'
    if kind in ('target-reference-recovery','preview-original-fallback','first-audible-take-retained'):return 'fallback'
    if any(x in kind for x in ('language','integrity','verification','script','normal-unresolved','name-')):return 'content'
    return 'other'

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def read(path):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return {}

def reference_signature(profile):
    return digest({k:profile.get(k) for k in ('id','reference','referenceSHA256','promptText','promptLanguage','language','referenceRanges')})

def fingerprint(issue,snapshot):
    index=issue['index']-1
    cue=(snapshot.get('review',{}).get('cues') or [])[index] if index<len(snapshot.get('review',{}).get('cues',[])) else {}
    segments=[s for s in snapshot.get('draft',{}).get('segments',[]) if index in s.get('sources',[])]
    profiles=snapshot.get('draft',{}).get('settings',{}).get('voiceProfiles',snapshot.get('review',{}).get('config',{}).get('voiceProfiles',[]))
    roles={s.get('speakerId') for s in segments} or {cue.get('speakerId')}
    references=[p for p in profiles if p.get('id') in roles]
    return digest(dict(references=references,issue={k:issue.get(k) for k in ('id','index','engine','language','kind','text','evidence','diagnostic','attempts')},cue=cue,segments=[{k:s.get(k) for k in ('id','sources','start','end','text','mandarin','english','speakerId','take','rate','trimStart','trimEnd')} for s in segments]))

def line_fingerprint(row,snapshot):
    """Bind a human check to the words, the time slot and the recording in use."""
    index=row.get('index')
    cues=(snapshot.get('review') or {}).get('cues') or []
    cue=cues[index-1] if type(index) is int and 0<index<=len(cues) else {}
    segments=[s for s in (snapshot.get('draft') or {}).get('segments',[]) if index-1 in s.get('sources',[])]
    line=dict(index=index,language=row.get('language'),engine=row.get('engine'))
    recording={k:row.get(k) for k in ('selectedAudio','recordingSHA256')}
    words={k:cue.get(k) for k in ('text','cantonese','mandarin','english','japanese','speakerId')}
    span={k:cue.get(k) for k in ('start','end','speechStart','speechEnd')}
    draft=[{k:s.get(k) for k in ('id','sources','start','end','text','mandarin','english','speakerId','take','rate','trimStart','trimEnd','audioTake')} for s in segments]
    return digest(dict(line=line,recording=recording,cue=dict(**words,**span),segments=draft))

def stale_recordings(snapshot):
    draft=snapshot.get('draft') or {};review=snapshot.get('review') or {};cfg=review.get('config',{})
    profiles={p.get('id'):p for p in draft.get('settings',{}).get('voiceProfiles',cfg.get('voiceProfiles',[]))}
    result={};seen=set()
    for take in reversed(snapshot.get('takes',[])):
        index=take.get('index');language=take.get('language','yue');engine=take.get('engine','')
        if type(index) is not int:continue
        identity=(index,language,engine)
        if identity in seen:continue
        seen.add(identity)
        segment=next((s for s in draft.get('segments',[]) if s.get('sources')==[index-1]),None)
        if not segment or segment.get('enabled') is False or segment.get('preserveOriginalSpeech'):continue
        text=segment.get('english' if language=='en' else 'mandarin' if language=='zh' else 'text','');reasons=[]
        provenance=take.get('recordingProvenance') or {}
        spoken=take.get('text',take.get('cantonese',provenance.get('text')))
        if spoken is not None and spoken!=text:reasons.append('script')
        provenance=take.get('recordingProvenance') or {}
        if 'speakerId' in provenance and provenance['speakerId']!=segment.get('speakerId',''):reasons.append('role')
        expected=profiles.get(segment.get('speakerId'))
        if expected and provenance.get('reference') and provenance['reference']!=reference_signature(expected):reasons.append('reference')
        if reasons:
            key=f'{index}:{language}:{engine}'
            result.setdefault(key,dict(index=index,language=language,engine=engine,reasons=[],recordings=[],protected=bool(segment.get('reviewDecisions',{}).get(language+':'+engine))))
            result[key]['reasons']=sorted(set(result[key]['reasons']+reasons));result[key]['recordings'].append(take['audio'])
    return list(result.values())

def voice_references(snapshot):
    """Report the separated voice each saved recording was built from.

    The engine writes the reference file and its digest beside every take. The
    first recorded digest for a line is the baseline. A later take with a
    different digest used a different voice reference. This report never changes
    a recording, a review state, or a regeneration target.
    """
    result={};baseline={}
    for take in sorted(snapshot.get('takes',[]),key=lambda x:((x.get('created') or 0),str(x.get('audio') or ''))):
        audio=take.get('audio')
        if not audio:continue
        provenance=take.get('recordingProvenance') or {}
        line=':'.join(str(x) for x in (take.get('index'),take.get('language','yue'),take.get('engine','')))
        recorded=provenance.get('recordedReferenceSHA256')
        if not recorded:
            result[str(audio)]=dict(state='unknown',reference='',seed=None,line=line)
            continue
        earlier=baseline.get(line)
        if earlier is None:
            baseline[line]=recorded;state='first'
        else:
            state='same' if recorded==earlier else 'different'
        result[str(audio)]=dict(state=state,reference=Path(provenance.get('recordedReference','')).name,
                                seed=provenance.get('recordedSeed'),line=line)
    return result

def project(root,snapshot):
    data=read(Path(root)/'review-triage.json');saved=data.get('decisions',{});counts={k:0 for k in CATEGORIES};states=dict(pending=0,checked=0,deferred=0)
    line_states=dict(pending=0,checked=0,deferred=0)
    def stored(ident,expected):
        entry=saved.get(ident,{})
        state=entry.get('state','pending') if entry.get('fingerprint')==expected else 'pending'
        return state if state in line_states else 'pending'
    for issue in snapshot.get('issues',[]):
        fp=fingerprint(issue,snapshot);entry=saved.get(issue.get('id'),{})
        state=entry.get('state','pending') if entry.get('fingerprint')==fp else 'pending'
        if state not in states:state='pending'
        issue.update(category=category(issue),triage=state,triageFingerprint=fp)
        counts[issue['category']]+=1
        if state!='pending' or issue.get('reportGroup') in (None,'reportMissing'):states[state]+=1
    # Every dialogue line carries a human review state, so the report can filter
    # what the user has already listened to. A line with a diagnostic issue keeps
    # that issue's state; the words, time slot or recording reset an older check.
    by_line={};issue_by_line={}
    for issue in snapshot.get('issues',[]):
        issue_by_line.setdefault(line_id(issue.get('index'),issue.get('language','yue'),issue.get('engine','')),issue)
    for row in snapshot.get('reportRows') or []:
        ident=row_id(row);issue=issue_by_line.get(ident)
        if issue is not None:
            state=issue.get('triage','pending');fp=issue.get('triageFingerprint')
        else:
            fp=line_fingerprint(row,snapshot);state=stored(ident,fp)
        row.update(triage=state,triageFingerprint=fp,triageID=ident);by_line[ident]=state
        line_states[state]+=1
    snapshot['reviewTriage']=dict(line_states,total=len(by_line))
    snapshot['workbench']=dict(categories=counts,**states,canUndo=bool(data.get('history')),qualityCertified=False)
    snapshot['staleRecordings']=stale_recordings(snapshot)
    snapshot['voiceReferences']=voice_references(snapshot)
    return snapshot

def mark(root,snapshot,ident,expected,state):
    if state not in ('pending','checked','deferred','undo'):raise ValueError('Unknown review state.')
    path=Path(root)/'review-triage.json';data=read(path);decisions=data.setdefault('decisions',{});history=data.setdefault('history',[])
    if state=='undo':
        if not history:raise ValueError('There is no review decision to undo.')
        change=history.pop();ident=change['id']
        if change['previous'] is None:decisions.pop(ident,None)
        else:decisions[ident]=change['previous']
    else:
        issue=next((x for x in snapshot.get('issues',[]) if x.get('id')==ident),None)
        row=None
        if issue is None:
            row=next((x for x in snapshot.get('reportRows') or [] if row_id(x)==ident),None)
            if row is not None and line_fingerprint(row,snapshot)!=expected:raise ValueError('Review evidence changed. Refresh and listen again before confirming.')
        elif fingerprint(issue,snapshot)!=expected:raise ValueError('Review evidence changed. Refresh and listen again before confirming.')
        if issue is None and row is None:raise ValueError('Unknown review target. Refresh the report and try again.')
        history.append(dict(id=ident,previous=decisions.get(ident)));data['history']=history[-50:]
        decisions[ident]=dict(state=state,fingerprint=expected,at=time.time(),qualityCertified=False)
    data.update(schemaVersion=1,updatedAt=time.time())
    atomic_files.write_bytes(path, (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    return project(root,snapshot)
