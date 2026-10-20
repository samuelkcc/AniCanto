"""Reuse completed full utterances across orchestration/policy upgrades.

Matching generation inputs is separate from the version of downstream fitting or
review code. A failed/fragmentary recording is never promoted by this migration.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import time

CONFIG_FIELDS=('targetLanguage','gsvVersion','sampleSteps','qwenModel','cosyModel',
               'voxcpmModel','wsyueModel','drama3Model','device','voxcpmDevice',
               'nativeComputeBackend','nativeDramaFormat','audioRerunToken','productionMode')
ITEM_FIELDS=('text','approvedText','seed','targetSeconds','deliveryStyle','expressionSettings',
             'cantoneseReadings','experimentalProsody','prosodyStrength')

def read(path):
    try:return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}

def project_root(job):
    job=Path(job).resolve()
    for parent in [job,*job.parents]:
        if parent.parent.name=='jobs':return parent
    return job

def identity(request,item,engine,hashes):
    # A phrase request cannot establish that the approved complete line exists.
    if item.get('approvedText',item.get('text'))!=item.get('text'):return None
    profile=item.get('profile') or {}
    reference=Path(profile.get('reference',''))
    try:
        stat=reference.stat();key=(str(reference.resolve()),stat.st_size,stat.st_mtime_ns)
        if key not in hashes:hashes[key]=hashlib.sha256(reference.read_bytes()).hexdigest()
    except OSError:return None
    config={k:request.get(k) for k in CONFIG_FIELDS}
    config['targetLanguage']=request.get('targetLanguage','yue')
    config['productionMode']=request.get('productionMode','standard')
    values={k:item.get(k) for k in ITEM_FIELDS}
    values.update(seed=int(item.get('seed',42)),approvedText=item.get('approvedText',item.get('text')),
                  deliveryStyle=item.get('deliveryStyle','normal'))
    voice={k:profile.get(k) for k in ('id','promptText','language','naturalReferenceId')}
    body=[engine,config,values,voice,item.get('_referenceSHA256AtSubmission') or hashes[key]]
    return hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def candidates(job,engine):
    root=project_root(job)
    # Only this episode, not another project or a global user's voice library.
    paths=list(root.glob('**/'+engine+'-request.json'))+list(root.glob('**/generation-requests/'+engine+'-*.json'))
    return sorted(paths,key=lambda p:p.stat().st_mtime,reverse=True)

def archive(job,request,engine):
    """Later repair batches must not overwrite the full original input record."""
    snapshot=copy.deepcopy(request);snapshot.pop('_trackControl',None)
    for item in snapshot.get('items',[]):
        try:item['_referenceSHA256AtSubmission']=hashlib.sha256(Path(item['profile']['reference']).read_bytes()).hexdigest()
        except (OSError,KeyError):pass
    raw=json.dumps(snapshot,sort_keys=True,ensure_ascii=False).encode()
    folder=Path(job)/'generation-requests';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(engine+'-'+hashlib.sha256(raw).hexdigest()+'.json')
    if not path.exists():
        temp=path.with_suffix('.tmp');temp.write_bytes(raw);temp.replace(path)
    return path

def plan(job,request,engine):
    from audio_fallback import healthy
    hashes={};wanted={};existing=0
    for item in request.get('items',[]):
        path=Path(item['output'])
        if path.is_file() and healthy(path):existing+=1;continue
        key=identity(request,item,engine,hashes)
        if key:wanted.setdefault(key,[]).append(item)
    found={};root=project_root(job)
    if not wanted:return [],existing
    for manifest in candidates(job,engine):
        prior=read(manifest)
        flagged=set();provenance=Path(prior.get('job',str(manifest.parent)))
        for name in ('speech-check.json','final-speech-check.json'):
            for check in read(provenance/name).get('rows',[]):
                if check.get('confirmedContentFailure'):flagged.add(check.get('index'))
        for item in prior.get('items',[]):
            key=identity(prior,item,engine,hashes)
            if key not in wanted or key in found:continue
            path=Path(item.get('output','')).resolve()
            if not path.is_relative_to(root) or not path.is_file():continue
            if any(token in path.name for token in ('.partial.','.raw.','.rejected.','skipped-')):continue
            if path.with_suffix('.failure.json').exists():continue
            if type(item.get('reviewIndex')) is int and item['reviewIndex']+1 in flagged:continue
            generation=read(path.with_suffix('.generation.json'))
            if generation and generation.get('status')!='completed':continue
            if not healthy(path):continue
            found[key]=(path,manifest,generation)
        if len(found)==len(wanted):break
    rows=[]
    for key,(path,manifest,generation) in found.items():
        for item in wanted[key]:
            if path!=Path(item['output']).resolve():rows.append(dict(identity=key,source=str(path),output=item['output'],request=str(manifest),index=item.get('reviewIndex'),generation=generation))
    return rows,existing

def recover(job,request,engine,emit):
    if engine not in ('drama3','tts','cosy','voxcpm2','wsyue','qwen'):return
    rows,existing=plan(job,request,engine)
    receipt=[]
    for row in rows:
        source=Path(row['source']);target=Path(row['output']);target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_suffix('.reuse.partial.wav')
        try:
            shutil.copy2(source,temp)
            digest=hashlib.sha256(temp.read_bytes()).hexdigest()
            if digest!=hashlib.sha256(source.read_bytes()).hexdigest():continue
            temp.replace(target);target.with_suffix('.failure.json').unlink(missing_ok=True)
            for suffix in ('.level.json','.generation.json'):
                old=source.with_suffix(suffix)
                if old.is_file():shutil.copy2(old,target.with_suffix(suffix))
            record={k:v for k,v in row.items() if k!='generation'}
            record.update(audioSHA256=digest,reusedAt=time.time(),matching='same-full-text-model-reference-and-generation-inputs',qualityCertified=False)
            target.with_suffix('.reuse.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            receipt.append(record)
        finally:temp.unlink(missing_ok=True)
    if receipt:
        from worker import atomic_json
        file=Path(job)/'take-reuse.json';old=read(file)
        atomic_json(file,dict(schemaVersion=1,rows=old.get('rows',[])+receipt))
    if existing or receipt:
        emit('錄音沿用',f'沿用 {existing+len(receipt)}/{len(request.get("items",[]))} 段完成錄音；只生成缺少或輸入已更改嘅片段。',reusedTakes=existing+len(receipt),totalTakes=len(request.get('items',[])))
