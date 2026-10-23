"""Read-only review projection across parent and current child tracks.

An empty issue file is not a completed quality check. No inference is launched
and historical failures are not silently certified repaired by this projection.
"""
import hashlib,json
from pathlib import Path


def read(path,default):
    try:
        value=json.loads(Path(path).read_text());return value if isinstance(value,type(default)) else default
    except (OSError,ValueError):return default


def archived_recordings(folder):
    """Expose immutable rejected WAVs from this track and its retry jobs."""
    rows=[]
    for manifest in folder.rglob('recording-history/*/take.json'):
        relative=manifest.relative_to(folder)
        if relative.parts[0]=='tracks' or manifest.parent.parent.name!='recording-history':continue
        record=read(manifest,{})
        if type(record.get('index')) is not int or record.get('status')!='rejected':continue
        audio=manifest.parent/'audio.wav'
        if not audio.is_file():continue
        rows.append(dict(index=record['index'],language=record.get('language'),action='retained-rejected-recording',status='not-verified',engine=record.get('engine'),candidateAudio=str(audio),check=record.get('generation',{}).get('speechCheck',{}),reason=record.get('reason',''),recordedAt=record.get('created',0)))
    return rows


def project(root,review,row):
    root=Path(root).resolve();cfg=review.get('config',{});cues=review.get('cues',[])
    active=row.get('status')=='running';items={};resolved={};contexts={}
    milestones=read(root/'production-progress.json',{}).get('milestones',[])
    phase=next((x.get('id') for x in milestones if x.get('state')=='running'),None)
    def insert(value,engine=None,language=None,status='unresolved',origin=''):
        index=value.get('index')
        if type(index) is not int or index<1:return
        e=value.get('engine') or engine or cfg.get('ttsBackend','');lang=value.get('language') or language or cfg.get('targetLanguage','yue')
        key=f'{lang}:{e}:{index}';cue=cues[index-1] if index<=len(cues) else {}
        target=resolved if status=='repaired' else items
        item=target.setdefault(key,dict(id=hashlib.sha256(key.encode()).hexdigest()[:20],index=index,engine=e,language=lang,start=value.get('start',cue.get('start')),end=value.get('end',cue.get('end')),kind=value.get('kind') or value.get('reason') or 'verification-unresolved',status=status,evidence=[],attempts=[]))
        item['evidence'].append(dict(file=origin,**value));item['text']=cue.get('english' if lang=='en' else 'cantonese','')
        if value.get('kind') in ('timing-overrun','targeted-language-or-integrity','reference-blocked','missing-script'):item['kind']=value['kind']
        if status=='repairing':item['status']='repairing'
    # Explicit current-track records avoid merging every obsolete render hash.
    folders={root};progress=read(root/'track-progress.json',{}).get('tracks',[])
    for t in progress:
        p=Path(t.get('folder','')).resolve()
        if p.is_dir() and p.is_relative_to(root):folders.add(p)
    report=read(root/'report.json',{})
    if len(folders)==1:
        for t in report.get('tracks',[]):
            p=Path(t.get('report','')).resolve().parent
            if p.is_dir() and p.is_relative_to(root):folders.add(p)
    coverage=read(root/'dialogue-delivery-audit.json',{})
    for track in coverage.get('tracks',[]):
        for v in track.get('rows',[]):
            if not v.get('available'):insert(v,track.get('engine'),track.get('language'),'awaiting-recheck' if active else 'unresolved','dialogue-delivery-audit.json')
    for folder in sorted(folders):
        local_review=read(folder/'review.json',{});local=local_review.get('config',{});engine=local.get('ttsBackend',cfg.get('ttsBackend'));language=local.get('targetLanguage','yue')
        contexts[(language,engine)]=(folder,local_review)
        origin=str(folder.relative_to(root))
        for v in read(folder/'segment-issues.json',[]):insert(v,engine,language,origin=origin+'/segment-issues.json')
        for v in read(folder/'resolved-segment-issues.json',[]):insert(v,engine,language,'repaired',origin+'/resolved-segment-issues.json')
        for v in read(folder/'timing.json',[]):
            if v.get('originalFallback'):insert(dict(v,kind='preview-original-fallback'),engine,language,origin=origin+'/timing.json')
        checks=read(folder/'normal-checks.json',{})
        for v in read(folder/'failed-voice-choices.json',{}).get('decisions',[]):
            insert(dict(v,kind='failed-voice-choice'),engine,language,origin=origin+'/failed-voice-choices.json')
        for v in checks.get('repairs',[]):
            insert(dict(v,kind='targeted-language-or-integrity'),engine,language,'repaired' if v.get('repaired') else 'repairing' if active else 'unresolved',origin+'/normal-checks.json')
        for v in checks.get('advisories',[]):
            insert(dict(v,kind='first-audible-take-retained'),engine,language,'language-unconfirmed',origin+'/normal-checks.json')
        for index in checks.get('nameLanguageUnconfirmed',[]):insert(dict(index=index,kind='name-language-unconfirmed'),engine,language,'language-unconfirmed',origin+'/normal-checks.json')
        for index in checks.get('unresolved',[]):insert(dict(index=index,kind='targeted-language-or-integrity'),engine,language,origin=origin+'/normal-checks.json')
        placement=read(folder/'natural-placement.json',{})
        for v in placement.get('rows',[]):
            if v.get('seconds') is not None and not v.get('fit'):insert(dict(v,kind='timing-overrun'),engine,language,'repairing' if active else 'unresolved',origin+'/natural-placement.json')
        for v in read(folder/'target-reference-recovery.json',{}).values():
            fit=next((p.get('fit') for p in placement.get('rows',[]) if p.get('index')==v.get('index')),False)
            status='repaired' if v.get('status')=='adopted' and fit else 'repairing' if active and v.get('status') in ('reserved','generating','generated') else 'unresolved'
            insert(dict(v,kind='target-reference-recovery',voiceSimilarityMayDiffer=True),engine,language,status,origin+'/target-reference-recovery.json')
        director=read(folder/'automatic-recovery.json',{})
        for v in director.get('rows',{}).values():
            if not v.get('attempts'):continue
            fit=next((p.get('fit') for p in placement.get('rows',[]) if p.get('index')==v.get('index')),False)
            status='repaired' if v.get('selectedVerified') and fit and v.get('index') not in checks.get('unresolved',[]) else 'repairing' if active and v['attempts'][-1].get('status') in ('reserved','generating','generated') else 'unresolved'
            insert(dict(index=v.get('index'),kind='automatic-recovery',attempts=v['attempts']),engine,language,status,origin+'/automatic-recovery.json')
            target=resolved if status=='repaired' else items;key=f"{language}:{engine}:{v.get('index')}"
            if key in target:target[key]['attempts']=v['attempts']
    from review_diagnostics import enrich
    facts={}
    for item in list(items.values())+list(resolved.values()):
        folder,local_review=contexts.get((item['language'],item['engine']),(root,review))
        local_cfg=local_review.get('config') or cfg
        local_cues=local_review.get('cues') or cues
        cue=next((c for n,c in enumerate(local_cues) if c.get('reviewIndex',n)+1==item['index']),{})
        if folder not in facts:
            facts[folder]=dict(placement=read(folder/'natural-placement.json',{}).get('rows',[]),checks=read(folder/'normal-checks.json',{}),director=list(read(folder/'automatic-recovery.json',{}).get('rows',{}).values()),target=list(read(folder/'target-reference-recovery.json',{}).values()),natural=read(folder/'natural-repair.json',{}).get('candidates',[]),finishing=read(folder/'natural-finishing.json',{}).get('operations',[]),alternate=list(read(folder/'alternate-engine-recovery.json',{}).values()),archived=archived_recordings(folder))
        evidence=facts[folder]
        placement=next((p for p in evidence['placement'] if p.get('index')==item['index']),{})
        checks=evidence['checks']
        director=next((v for v in evidence['director'] if v.get('index')==item['index']),{})
        target=next((v for v in evidence['target'] if v.get('index')==item['index']),None)
        if target:director=dict(director,selectedAudio=target.get('selectedAudio') or target.get('audio') if target.get('status') in ('adopted','selected-unverified') else director.get('selectedAudio'),attempts=(director.get('attempts') or [])+[dict(target,candidateAudio=target.get('selectedAudio') or target.get('audio'))])
        earlier=[]
        for record in checks.get('repairs',[])+checks.get('advisories',[]):
            if record.get('index')==item['index']:
                if record.get('originalAudio'):
                    earlier.append(dict(action='initial-voice-attempt',status='retained' if record.get('retainedFirstTake') else 'not-verified',candidateAudio=record['originalAudio'],check=record.get('originalCheck') or record.get('check',{})))
                earlier.extend(dict(a,action='retry-clauses',status='adopted' if a.get('repaired') else 'not-verified',check=a.get('candidateCheck',{})) for a in record.get('attempts',[]) if isinstance(a,dict))
        earlier.extend(dict(a,action='adapt-source',status='adopted' if a.get('adopted') else 'not-verified',candidateSeconds=a.get('seconds'),check=a.get('languageCheck',{})) for a in evidence['natural'] if a.get('index')==item['index'])
        earlier.extend(a for a in evidence['finishing'] if a.get('index')==item['index'])
        earlier.extend(dict(a,candidateAudio=a.get('selectedAudio') or a.get('audio')) for a in evidence['alternate'] if a.get('index')==item['index'])
        earlier.extend(a for a in evidence['archived'] if a['index']==item['index'] and a.get('language')==item['language'])
        if earlier:director=dict(director,attempts=earlier+(director.get('attempts') or []))
        enrich(item,cue,local_cfg,folder,placement,checks,director,active,phase)
    # A verified, delivered target-language fallback resolves missing language,
    # while preserving the explicit loss-of-character-voice notice. Old failed
    # actor attempts must not override this final outcome in the pending count.
    for key,item in list(items.items()):
        folder,local_review=contexts.get((item['language'],item['engine']),(root,review))
        evidence=facts.get(folder,{})
        target=next((v for v in evidence.get('target',[]) if v.get('index')==item['index'] and v.get('status')=='adopted'),None)
        timing=next((v for v in read(folder/'timing.json',[]) if v.get('index')==item['index']),{})
        final_check_pending=item['index'] in evidence.get('checks',{}).get('unresolved',[])
        if target and not final_check_pending and timing.get('renderedAudio') and not timing.get('skipped') and not timing.get('originalFallback') and not timing.get('needsReview') and not timing.get('requiresTimingReview'):
            item.update(status='voice-fallback',kind='target-reference-recovery')
    # An explicit choice changes the plan, never turns an AI defect into a pass.
    draft=read(root/'editor-draft-studio.json',{})
    for segment in draft.get('segments',[]):
        for key,decision in segment.get('reviewDecisions',{}).items():
            lang,engine=key.split(':',1) if ':' in key else ('','')
            for n in segment.get('sources',[]):
                item=items.get(f'{lang}:{engine}:{n+1}')
                if item:item.update(status='user-choice-saved',userDecision=decision)
    for key in items:resolved.pop(key,None)
    summary=dict(processing=active,pending=sum(x['status']!='voice-fallback' for x in items.values()),voiceFallbacks=sum(x['status']=='voice-fallback' for x in items.values()),repairing=sum(x['status']=='repairing' for x in items.values()),repaired=len(resolved),userChoices=sum(x['status']=='user-choice-saved' for x in items.values()),qualityChecked=not active and report.get('qualityStatus')=='automatic-checks-passed',hasReport=bool(report or coverage or items or resolved))
    if not items and row.get('status')=='attention':summary['projectProblem']=(row.get('lastError') or {}).get('message') or row.get('message') or 'The last attempt needs attention; no line-level verdict is available yet.'
    return dict(issues=sorted(items.values(),key=lambda x:(x['index'],x['language'],x['engine'])),resolvedIssues=sorted(resolved.values(),key=lambda x:(x['index'],x['language'])),reviewState=summary)
