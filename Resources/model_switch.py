"""Transactional model replacement. Downloads commit before old weights retire.

Only the previous choices are candidates, never arbitrary extra expert models.
Shared blobs, pinned models and immutable pending jobs protect their files.
"""
import hashlib
import json
from pathlib import Path
import uuid

ROLES={'text','voice','speech','asr','referenceSpeech'}


def read(path,default):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return default


def write(path,data):
    from worker import atomic_json
    Path(path).parent.mkdir(parents=True,exist_ok=True);atomic_json(path,data)


def begin(root,plan,requested,remove_old,expert=False):
    if set(requested)-ROLES or any(not isinstance(v,str) for v in requested.values()):raise ValueError('Unknown model choice.')
    if plan.get('canDeployModels') is not True:raise ValueError('Resolve model compatibility before downloading.')
    root=Path(root);token=uuid.uuid4().hex
    prior=read(root/'model-selections.json',{})
    previous=set(prior.values())
    record=dict(token=token,status='downloading',plan=plan,requested=requested,
        previous=prior,oldIDs=sorted(previous),removeOld=bool(remove_old and not expert),
        expert=bool(expert),previousReady=read(root/'native-ready.json',None))
    write(root/'studio/model-switches'/(token+'.json'),record);return token


def pending_models(root):
    root=Path(root).resolve();values=set()
    def visit(value):
        if isinstance(value,str):values.add(value)
        elif isinstance(value,dict):
            # Frozen production settings also remember preferences for engines
            # that this job does not use. Do not lock those unrelated weights.
            engines=set(value.get('selectedEngines') or [])|({value['ttsBackend']} if value.get('ttsBackend') else set())
            voice_keys={'cosyModel':{'cosyvoice3'},'drama3Model':{'drama3'},'qwenModel':{'qwen3'},'voxcpmModel':{'voxcpm2'},'wsyueModel':{'wsyue'},'gsvVersion':{'gpt-sovits','gpt-sovits-v2'}}
            for key,x in value.items():
                if engines and (key=='deploymentModels' or key in voice_keys and not engines.intersection(voice_keys[key])):continue
                visit(x)
        elif isinstance(value,list):
            for x in value:visit(x)
    for file in [root/'desktop-state.json',root/'studio/desktop-state.json',root/'batch-inflight.json',root/'batch-submissions.json']:
        data=read(file,{})
        rows=data.get('queue',[]) if isinstance(data,dict) and 'queue' in data else data if isinstance(data,list) else [data]
        for row in rows:
            if not isinstance(row,dict) or row.get('status') in ('complete','完成'):continue
            if 'queue' in data or file.name.endswith('state.json'):
                if row.get('status') not in ('waiting','running','paused'):continue
            visit(row)
            if row.get('request'):
                path=Path(row['request']).resolve()
                if path.is_relative_to(root):visit(read(path,{}))
    return values


def finish(root,token,models,folder_for,success=True):
    root=Path(root).resolve()
    if not isinstance(token,str) or len(token)!=32 or any(c not in '0123456789abcdef' for c in token):raise ValueError('Invalid model switch.')
    journal=root/'studio/model-switches'/(token+'.json');record=read(journal,{})
    if record.get('token')!=token:raise ValueError('Unknown model switch.')
    if record.get('status')=='complete':return record
    if not success:
        if record.get('previousReady'):
            write(root/'native-ready.json',record['previousReady']);write(root/'model-selections.json',record['previous'])
            (root/'setup-invalidated.json').unlink(missing_ok=True)
        record['status']='incomplete';write(journal,record);return record
    roles={k:v for k,v in record['plan']['roles'].items() if isinstance(v,str)}
    current=read(root/'model-selections.json',{})
    engine=record['plan']['engine']
    selected=lambda role:current.get(engine) if role=='voice' and engine in current else current.get(role)
    if any(selected(role)!=ident for role,ident in roles.items()):raise ValueError('New model selections have not been committed.')
    by_id={row['id']:row for row in models}
    def files(ident):
        if ident not in by_id:return []
        row=by_id[ident];base=Path(folder_for(root,row))
        result=[]
        for f in row.get('files',[]):
            path=base/f['path'];resolved=path.resolve()
            if path.is_symlink() or not resolved.is_relative_to(root) or resolved==root:raise ValueError('Model path is outside application data.')
            result.append((path,f.get('size',0)))
        return result
    for ident in set(roles.values()):
        paths=files(ident)
        if not paths or any(not p.is_file() or (size and p.stat().st_size!=size) for p,size in paths):raise ValueError('New model verification is incomplete: '+ident)
    # The installers commit these receipts only after successful loading/tests.
    mac=read(root/'first-run-deployment.json',{})
    windows=read(root/'native-ready.json',{})
    mac_ok=mac.get('status')=='complete' and mac.get('plan',{}).get('roles')==record['plan']['roles']
    windows_ok=windows.get('modelLoadPassed') is True and windows.get('speechInferencePassed') is True and all(windows.get('roles',{}).get(k)==v for k,v in roles.items())
    if not (mac_ok or windows_ok):raise ValueError('New model loading has not passed; old models are retained.')
    from model_ownership import mark_available,mark_removed,removed_ids
    for ident in set(roles.values()):mark_available(root,by_id[ident])
    pins=set(read(root/'studio/model-pins.json',[]))
    if record['expert']:
        pins.update(roles.values());write(root/'studio/model-pins.json',sorted(pins))
    new=set(roles.values());protected=new|pins|pending_models(root)
    # Extra expert models not part of this replacement also retain shared blobs.
    candidates=(set(record['oldIDs'])-new) if record['removeOld'] else set()
    retained=(set(by_id)-candidates-removed_ids(root,models))|protected
    shared={p.resolve() for ident in retained for p,_ in files(ident) if p.is_file()}
    removed=[];kept=[]
    for ident in sorted(candidates):
        if ident in protected:kept.append(dict(id=ident,reason='in-use-or-pinned'));continue
        deleted=[]
        for path,_ in files(ident):
            if path.resolve() in shared:continue
            if path.is_file():path.unlink();deleted.append(str(path.relative_to(root)))
            partial=path.with_name(path.name+'.partial')
            if partial.is_file() and not partial.is_symlink():partial.unlink()
        mark_removed(root,by_id[ident])
        removed.append(dict(id=ident,files=deleted))
        marker=root/'model-ready'/(ident.replace(':','-')+'.json');marker.unlink(missing_ok=True)
        for key in list(current):
            if current[key]==ident:current.pop(key)
    write(root/'model-selections.json',current)
    record.update(status='complete',removed=removed,kept=kept);write(journal,record)
    return record
