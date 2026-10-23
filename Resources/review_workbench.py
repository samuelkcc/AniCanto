"""AniCanto editorial triage. Original implementation; no external app code.

Human review is distinct from model verification and from an export choice.
Decisions bind to the line, track, edited words and diagnostic evidence.
"""
import hashlib,json,time
from pathlib import Path

CATEGORIES=('missing','content','timing','reference','fallback','other')

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
    return digest(dict(references=references,issue={k:issue.get(k) for k in ('id','index','engine','language','kind','text','evidence','diagnostic','attempts')},cue=cue,segments=[{k:s.get(k) for k in ('id','sources','start','end','text','english','speakerId','take','rate','trimStart','trimEnd')} for s in segments]))

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
        text=segment.get('english' if language=='en' else 'text','');reasons=[]
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

def project(root,snapshot):
    data=read(Path(root)/'review-triage.json');saved=data.get('decisions',{});counts={k:0 for k in CATEGORIES};states=dict(pending=0,checked=0,deferred=0)
    for issue in snapshot.get('issues',[]):
        fp=fingerprint(issue,snapshot);entry=saved.get(issue.get('id'),{})
        state=entry.get('state','pending') if entry.get('fingerprint')==fp else 'pending'
        if state not in states:state='pending'
        issue.update(category=category(issue),triage=state,triageFingerprint=fp)
        counts[issue['category']]+=1;states[state]+=1
    snapshot['workbench']=dict(categories=counts,**states,canUndo=bool(data.get('history')),qualityCertified=False)
    snapshot['staleRecordings']=stale_recordings(snapshot)
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
        if issue is None or fingerprint(issue,snapshot)!=expected:raise ValueError('Review evidence changed. Refresh and listen again before confirming.')
        history.append(dict(id=ident,previous=decisions.get(ident)));data['history']=history[-50:]
        decisions[ident]=dict(state=state,fingerprint=expected,at=time.time(),qualityCertified=False)
    data.update(schemaVersion=1,updatedAt=time.time())
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temporary.replace(path)
    return project(root,snapshot)
