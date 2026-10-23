"""Explicit per-model repair/redownload; never changes selected engines or jobs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

HERE=Path(__file__).resolve().parent
WINDOWS=Path(os.environ.get('CANTOSYNC_WINDOWS_PACKAGE',HERE.parent/'windows'))
if str(WINDOWS) not in sys.path:sys.path.insert(0,str(WINDOWS))


def catalog_paths(platform=None):
    if (platform or sys.platform)=='win32':
        from native_setup import catalog,folder
        return [r for r in catalog() if r.get('nativeFormat')],folder
    from model_catalog import catalog,folder
    return catalog(),folder


def model(root,ident,platform=None):
    rows,folder=catalog_paths(platform)
    row=next((r for r in rows if r['id']==ident),None)
    if row is None or not row.get('files'):raise ValueError('Unknown or unsupported model.')
    root=Path(root).resolve();base=Path(folder(root,row)).resolve()
    if not base.is_relative_to(root) or base==root:raise ValueError('Model folder is outside application data.')
    for f in row['files']:
        path=(base/f['path']).resolve()
        if not path.is_relative_to(base) or path==base:raise ValueError('Invalid model file path.')
        if not f.get('sha'):raise ValueError('Model file has no pinned checksum.')
    return row,base


def emit(message,**extra):
    print(json.dumps(dict(stage='Model maintenance',message=message,**extra),ensure_ascii=False),flush=True)


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def verified(path,file):
    return path.is_file() and path.stat().st_size==file['size'] and digest(path)==file['sha']


def replace(source,target):
    for attempt in range(6):
        try:os.replace(source,target);return
        except PermissionError:
            if attempt==5:raise
            time.sleep(.05*(attempt+1))


def maintain(root,ident,mode='repair',platform=None):
    from atomic_files import write_json
    from model_download import download
    if mode not in ('repair','redownload'):raise ValueError('Unknown model maintenance operation.')
    root=Path(root).resolve();row,base=model(root,ident,platform)
    # A verified download may be prepared on a computer that cannot run it.
    # Setup still enforces hardware and runtime compatibility before use.
    if row.get('retired'):raise ValueError('This model is retired and cannot be downloaded.')
    key=hashlib.sha256(ident.encode()).hexdigest()[:24]
    record=root/'studio/model-maintenance'/(key+'.json')
    state=dict(id=ident,title=row['title'],mode=mode,status='running',startedAt=time.time(),reused=0,downloaded=0)
    write_json(record,state)
    emit('Checking '+row['title'],modelID=ident,maintenance=state)
    try:
        if row.get('engine')=='whisper-mlx':
            from model_licenses import install_notices
            install_notices(row,base)
        work=[]
        for i,f in enumerate(row['files']):
            path=base/f['path']
            emit('Verifying '+f['path'],modelID=ident,fileIndex=i+1,fileCount=len(row['files']))
            if mode=='repair' and verified(path,f):state['reused']+=1
            else:work.append(f)
        if work and row.get('licenseReviewRequired'):
            raise ValueError('This model download is paused for licence review. Existing files were kept. Choose a reviewed model variant.')
        needed=sum(f['size'] for f in work)
        if work and shutil.disk_usage(root).free<needed+2_000_000_000:raise ValueError('Insufficient free storage; reserve model download size plus 2 GB.')
        stage=root/'downloads/model-maintenance'/key
        for i,f in enumerate(work):
            target=(stage if mode=='redownload' else base)/f['path']
            if not target.resolve().is_relative_to(root):raise ValueError('Model download path is outside application data.')
            emit('Downloading '+row['title']+' · '+f['path'],modelID=ident,fileIndex=i+1,fileCount=len(work))
            if 'content' in f:
                raw=f['content'].encode()
                if len(raw)!=f['size'] or hashlib.sha256(raw).hexdigest()!=f['sha']:raise ValueError('Pinned model metadata is invalid.')
                target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_name(target.name+'.partial');temp.write_bytes(raw);replace(temp,target)
            else:
                url=f.get('url') or f"https://huggingface.co/{row['repo']}/resolve/{row['revision']}/{f['path']}"
                download(url,target,f['sha'],f['size'])
            if not verified(target,f):raise ValueError('Downloaded model checksum verification failed: '+f['path'])
            state['downloaded']+=1
        if mode=='redownload':
            # No current weights are removed before every replacement verifies.
            for f in work:
                target=base/f['path'];target.parent.mkdir(parents=True,exist_ok=True);replace(stage/f['path'],target)
            shutil.rmtree(stage,ignore_errors=True)
        if not all(verified(base/f['path'],f) for f in row['files']):raise ValueError('Model files remain incomplete.')
        marker=root/'model-ready'/(ident.replace(':','-')+'.json')
        write_json(marker,dict(id=ident,revision=row.get('revision'),sha256Verified=True,verifiedAt=time.time()))
        from model_ownership import mark_available
        mark_available(root,row)
        state.update(status='complete',finishedAt=time.time());write_json(record,state)
        emit('Model verified: '+row['title'],modelID=ident,maintenance=state,progress=1)
        return state
    except Exception as error:
        state.update(status='failed',message=str(error),finishedAt=time.time());write_json(record,state)
        emit(str(error),modelID=ident,maintenance=state,error=str(error))
        raise


def maintain_many(root,idents,platform=None):
    if not isinstance(idents,list) or not idents or len(idents)>32 or any(not isinstance(ident,str) for ident in idents) or len(set(idents))!=len(idents):
        raise ValueError('Select between 1 and 32 different voice models.')
    # Validate the full batch before writing any files. A later failed download
    # does not undo earlier verified models; retry only fetches missing files.
    for ident in idents:
        row,_=model(root,ident,platform)
        if row.get('category')!='voice' or row.get('retired') or row.get('licenseReviewRequired'):
            raise ValueError('This voice model is unavailable for download: '+ident)
    failures=[]
    for index,ident in enumerate(idents,1):
        emit(f'Downloading voice model {index}/{len(idents)}',modelID=ident,modelIndex=index,modelCount=len(idents))
        try:maintain(root,ident,'repair',platform)
        except Exception as error:failures.append(dict(id=ident,error=str(error)))
    emit('Voice model downloads finished' if not failures else f'{len(failures)} voice model download(s) failed',modelCount=len(idents),failedModels=failures,progress=1,**({'error':'; '.join(f['id']+': '+f['error'] for f in failures)} if failures else {}))
    return failures


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);choice=p.add_mutually_exclusive_group(required=True);choice.add_argument('--id');choice.add_argument('--ids-json');p.add_argument('--mode',choices=['repair','redownload'],default='repair');p.add_argument('--platform',default=sys.platform)
    args=p.parse_args()
    try:
        if args.ids_json:
            if args.mode!='repair':raise ValueError('Batch downloads only support repair mode.')
            return 1 if maintain_many(args.root,json.loads(args.ids_json),args.platform) else 0
        maintain(args.root,args.id,args.mode,args.platform)
    except Exception:return 1
    return 0

if __name__=='__main__':sys.exit(main())


def remove_retired(root,ident,platform=None):
    """Remove only a retired, catalog-owned download; frozen jobs protect it."""
    from model_switch import pending_models,read,write
    root=Path(root).resolve();row,base=model(root,ident,platform)
    if not row.get('retired'):raise ValueError('Only retired models can be removed here.')
    if ident in pending_models(root):raise ValueError('A waiting or paused job still uses this model. Remove that job before removing its model.')
    for file in row['files']:
        for path in (base/file['path'],base/(file['path']+'.partial')):
            if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('Model path is outside application data.')
            if path.is_file():path.unlink()
    selections=read(root/'model-selections.json',{})
    write(root/'model-selections.json',{k:v for k,v in selections.items() if v!=ident})
    for name in ('native-ready.json','drama3-windows-ready.json'):
        receipt=read(root/name,{})
        if receipt.get('variant')==ident or receipt.get('roles',{}).get('voice')==ident:(root/name).unlink(missing_ok=True)
    for relative in ('model-ready/'+ident.replace(':','-')+'.json','voice-model-ready/'+ident+'.json'):(root/relative).unlink(missing_ok=True)
    from model_ownership import mark_removed
    mark_removed(root,row)
    return dict(removed=True,id=ident)


def removal_plan(root,ident,platform=None,selected_ids=()):
    """Read-only preview; explicit removal never follows symlinks or erases shared files."""
    from model_switch import pending_models
    from model_ownership import removed_ids
    root=Path(root).resolve();row,base=model(root,ident,platform)
    rows,folder=catalog_paths(platform)
    pending=pending_models(root)
    if ident in pending:reason='pending-job'
    elif ident in set(selected_ids):reason='selected-model'
    else:reason=None
    removed=removed_ids(root,rows);protected=pending|set(selected_ids)
    shared=set();owners={}
    for other in rows:
        if other['id']==ident or other['id'] in removed and other['id'] not in protected:continue
        parent=Path(folder(root,other))
        for f in other.get('files',[]):
            for path in (parent/f['path'],parent/(f['path']+'.partial')):
                if path.is_file():
                    key=path.resolve();shared.add(key);owners.setdefault(key,set()).add(other['id'])
    files=[];retained=0;retained_by=set()
    for f in row['files']:
        for path in (base/f['path'],base/(f['path']+'.partial')):
            if path.is_symlink() or any(x.is_symlink() for x in [base,*path.parents] if x!=root and x.is_relative_to(root)):
                raise ValueError('Model path is a symlink; no files were removed.')
            if not path.resolve().is_relative_to(root):raise ValueError('Model path is outside application data.')
            if path.is_file():
                if path.resolve() in shared:
                    retained+=path.stat().st_size;retained_by.update(owners[path.resolve()])
                else:files.append(dict(path=str(path.relative_to(root)),bytes=path.stat().st_size))
    return dict(id=ident,title=row['title'],canRemove=reason is None,reason=reason,bytes=sum(f['bytes'] for f in files),sharedBytesRetained=retained,sharedModels=[dict(id=r['id'],title=r['title']) for r in rows if r['id'] in retained_by],files=files)


def remove_model(root,ident,platform=None,selected_ids=()):
    from model_switch import read,write
    root=Path(root).resolve();plan=removal_plan(root,ident,platform,selected_ids)
    if not plan['canRemove']:raise ValueError('Switch model first.' if plan['reason']=='selected-model' else 'A pending job still uses this model.')
    # Recheck protections and all paths before the first deletion.
    for f in plan['files']:
        path=root/f['path']
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('Unsafe model path.')
    for f in plan['files']:(root/f['path']).unlink(missing_ok=True)
    for relative in ('model-ready/'+ident.replace(':','-')+'.json','voice-model-ready/'+ident+'.json'):(root/relative).unlink(missing_ok=True)
    selections=read(root/'model-selections.json',{})
    write(root/'model-selections.json',{k:v for k,v in selections.items() if v!=ident})
    pins=read(root/'studio/model-pins.json',[])
    if ident in pins:write(root/'studio/model-pins.json',[x for x in pins if x!=ident])
    from model_ownership import mark_removed
    row,_=model(root,ident,platform);mark_removed(root,row)
    return dict(removed=True,id=ident,freedBytes=plan['bytes'],sharedBytesRetained=plan['sharedBytesRetained'],sharedModels=plan['sharedModels'])
