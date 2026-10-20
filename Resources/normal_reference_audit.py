"""Bounded source-reference transcript audit before a same-actor repair.

Uses the already installed local witness in one batch. No new downloads,
concatenated neighbours, translated reference words or source audio mutations.
"""
import hashlib,json,re
from pathlib import Path
from difflib import SequenceMatcher
from types import SimpleNamespace

REVISION='own-source-reference-audit-1'

def prepare(cfg,job,cues,run,emit):
    profiles={p.get('id'):p for p in cfg.get('voiceProfiles',[])};pending=[];seen=set();job=Path(job)
    for cue in cues:
        profile=profiles.get(cue.get('speakerId'),{});ident=profile.get('id');source=Path(profile.get('reference',''))
        if not ident or ident in seen or profile.get('language')!='ja' or profile.get('mixedReference') or profile.get('transcriptSource')!='original-japanese-words' or not source.is_file():continue
        seen.add(ident);key=hashlib.sha256(source.read_bytes()+profile.get('promptText','').encode()+REVISION.encode()).hexdigest()[:24]
        folder=job/'own-reference-audit'/key;folder.mkdir(parents=True,exist_ok=True);pending.append((profile,folder,source))
    if not pending:return cfg
    from secondary_speech import transcribe_batch
    from worker import atomic_json
    emit('原聲參考覆核',f'只覆聽 {len(pending)} 段未能生成目標語言嘅原角色參考；保留同一錄音，核對日文稿有冇對準。')
    records=[];replacements={}
    try:
        results=transcribe_batch(SimpleNamespace(run=run,atomic_json=atomic_json),cfg,[(folder,source) for _,folder,source in pending],auto_language=True)
        if len(results)!=len(pending):raise ValueError('Source witness count mismatch')
        clean=lambda s:re.sub(r'[^\wぁ-んァ-ヶ一-龥]','',s)
        for (profile,folder,source),result in zip(pending,results):
            result=result or {};heard=result.get('heard','').strip();before=profile.get('promptText','');a,b=clean(before),clean(heard)
            accepted=result.get('language','').lower() in ('ja','jpn','japanese') and len(b)>=3 and bool(a) and SequenceMatcher(None,a,b).ratio()>=.75 and .65<=len(b)/len(a)<=1.45
            record=dict(roleID=profile['id'],source=str(source),sourceSHA256=hashlib.sha256(source.read_bytes()).hexdigest(),before=before,heard=heard,language=result.get('language'),adoptedTranscript=accepted,actorChanged=False,audioChanged=False)
            records.append(record)
            if accepted:replacements[profile['id']]=dict(profile,promptText=heard,transcriptSource='independent-own-source-listen',originalPromptText=before,referenceTranscriptAudit=str(folder/'audit.json'))
            atomic_json(folder/'audit.json',record)
    except (OSError,RuntimeError,ValueError,KeyError,TypeError) as error:
        records.append(dict(error=str(error)[:300],adoptedTranscript=False,actorChanged=False));emit('原聲參考覆核','獨立覆聽未完成，保留原角色錄音同原稿：'+str(error)[:160])
    atomic_json(job/'own-reference-audit.json',dict(revision=REVISION,records=records,qualityCertified=False))
    return dict(cfg,voiceProfiles=[replacements.get(p.get('id'),p) for p in cfg.get('voiceProfiles',[])])
