"""Scan app-owned storage, including unregistered crash residue, before explicit cleanup.

Rebuildable caches and abandoned working recordings are separate opt-ins. No
model/runtime, current project, source media or final movie is a cleanup target.
"""
import hashlib,json,os,re,sqlite3,time
from contextlib import contextmanager,ExitStack
from pathlib import Path

VIDEO={'.mp4','.mkv','.mov','.m4v','.avi','.webm'}


def safe(root,path):
    return path.resolve().is_relative_to(root) and not any(p.is_symlink() for p in (path,*path.parents) if p.resolve().is_relative_to(root))


def walk(root,folder):
    if not folder.is_dir() or not safe(root,folder):return
    for base,dirs,names in os.walk(folder,followlinks=False):
        dirs[:]=[n for n in dirs if safe(root,Path(base)/n)]
        for name in names:
            path=Path(base)/name
            if path.is_file() and safe(root,path):yield path


@contextmanager
def preview_lock(directory):
    """Nonblocking OS lock: a stale status file is not proof a worker is alive."""
    path=directory/'prepare.lock';stream=None;locked=False
    try:
        if path.is_symlink():yield False;return
        stream=path.open('a+b')
        if os.name=='nt':
            import msvcrt
            stream.seek(0);stream.write(b'0');stream.flush();stream.seek(0)
            try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1);locked=True
            except OSError:pass
        else:
            import fcntl
            try:fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);locked=True
            except OSError:pass
        yield locked
    finally:
        if stream:
            if locked:
                if os.name=='nt':stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
            stream.close()


def read(path,default):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return default


def footprint(files):
    """Only count space whose last hardlink would disappear with this selection."""
    inodes={}
    for f in files:
        key=(f['device'],f['inode']);item=inodes.setdefault(key,[f['bytes'],f['links'],0]);item[2]+=1
    return sum(size for size,links,count in inodes.values() if count>=links)


def plan(root,rows,settings=None):
    root=Path(root).resolve();jobs=root/'jobs';files={};groups={};protected=set();job_refs=set();busy=set();warnings=[]
    def references(value):
        if isinstance(value,str):
            p=Path(value)
            if p.is_absolute():
                p=p.resolve();protected.add(p)
                if p.is_relative_to(jobs) and p!=jobs:job_refs.add(jobs/p.relative_to(jobs).parts[0])
        elif isinstance(value,dict):
            for v in value.values():references(v)
        elif isinstance(value,list):
            for v in value:references(v)
    references(settings or {})
    for row in rows:
        references(row)
        for value in (row.get('job'),row.get('review')):
            if value and row.get('status')!='complete':
                p=Path(value).resolve()
                if p.is_relative_to(jobs) and p!=jobs:busy.add(jobs/p.relative_to(jobs).parts[0])
        if row.get('request'):
            p=Path(row['request'])
            if safe(root,p):references(read(p,{}))
    # Saved projects need protection even if their videos are no longer queued.
    db=root/'projects.sqlite3';database_ok=True
    if db.is_file():
        try:
            if not safe(root,db):raise sqlite3.DatabaseError('Linked project index')
            con=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True,timeout=.5)
            try:
                for (review,) in con.execute('SELECT review FROM projects'):references(review)
            finally:con.close()
        except sqlite3.Error:
            database_ok=False;warnings.append('saved-project-index-unavailable')
    # Interrupted batch submissions can outlive the window or queue entry.
    for name in ('batch-inflight.json','batch-submissions.json'):
        data=read(root/name,{})
        entries=data if isinstance(data,list) else data.get('queue',[data]) if isinstance(data,dict) else []
        for entry in entries:
            if isinstance(entry,dict) and entry.get('status') not in ('complete','finished','failed','cancelled'):references(entry)
    def entry(path,label):
        st=path.stat();return dict(path=str(path.resolve().relative_to(root)),bytes=st.st_size,mtime=st.st_mtime_ns,device=st.st_dev,inode=st.st_ino,links=st.st_nlink,group=label)
    def add(path,label):
        if path.is_file() and safe(root,path) and path.resolve() not in protected:files[str(path.resolve().relative_to(root))]=entry(path,label)
    for name,label in [('cache/uv','package-cache'),('cache/pip','package-cache'),('cache/numba','compiler-cache')]:
        for path in walk(root,root/name) or ():add(path,label)
    previews=root/'cache/studio-preview'
    if previews.is_dir() and safe(root,previews):
        for directory in previews.iterdir():
            if directory.is_file():
                if re.fullmatch(r'[a-f0-9]{24}\.mp4',directory.name):add(directory,'video-preview')
                continue
            if not directory.is_dir() or not safe(root,directory):continue
            if not (re.fullmatch(r'[a-f0-9]{24}',directory.name) or (directory/'status.json').is_file()):continue
            with preview_lock(directory) as available:
                if not available:continue
                for path in walk(root,directory) or ():
                    if path.name!='prepare.lock' and (path.suffix in {'.mp4','.json','.txt'}):add(path,'video-preview')
    orphans=[];job_count=0
    if jobs.is_dir() and safe(root,jobs):
        for job in jobs.iterdir():
            if not job.is_dir() or not safe(root,job):continue
            job_count+=1
            content=list(walk(root,job) or ())
            known=bool(re.fullmatch(r'[a-f0-9]{16,64}',job.name)) or any((job/n).is_file() for n in ('review.json','production-progress.json','processing-preview.json'))
            referenced=job.resolve() in job_refs
            if known and job.resolve() not in busy:
                for path in content:
                    if any(x.name in ('frames-pts','ocr-discovery') for x in path.parents) and path.suffix.lower() in {'.jpg','.jpeg','.png'}:add(path,'ocr-frames')
            if not known or referenced:continue
            # Preserve source/input files recorded in the job's own manifests.
            source_paths=set();title=job.name
            for name in ('processing-preview.json','review.json','config.json'):
                info=read(job/name,{})
                if isinstance(info,dict):
                    cfg=info.get('config',info)
                    if isinstance(cfg,dict):
                        for key in ('video','source','input'):
                            if isinstance(cfg.get(key),str):
                                source_paths.add(Path(cfg[key]).resolve())
                                if key=='video':title=Path(cfg[key]).name
            candidates=[];kept=0
            for path in content:
                # Videos and subtitle deliverables survive even an abandoned-job cleanup.
                if path.resolve() in protected|source_paths or path.suffix.lower() in VIDEO|{'.srt','.ass','.vtt'}:kept+=path.stat().st_size;continue
                key=str(path.resolve().relative_to(root))
                if key not in files:candidates.append(entry(path,'orphan-work'))
            if candidates:orphans.append(dict(id=job.name,title=title,bytes=footprint(candidates),logicalBytes=sum(f['bytes'] for f in candidates),files=candidates,canRemove=database_ok,keptMediaBytes=kept))
    ordered=sorted(files.values(),key=lambda x:x['path'])
    for label in {f['group'] for f in ordered}:groups[label]=footprint([f for f in ordered if f['group']==label])
    orphans.sort(key=lambda x:x['id'])
    identity=[str(root),ordered,orphans,sorted(str(p) for p in job_refs),warnings]
    return dict(token=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest(),bytes=footprint(ordered),logicalBytes=sum(f['bytes'] for f in ordered),count=len(ordered),groups=groups,files=ordered,orphanWork=orphans,warnings=warnings,scannedJobFolders=job_count,scope='application-storage')


def execute(root,rows,token,orphan_ids=(),settings=None,progress=None):
    report=progress or (lambda **_:None)
    report(phase='checking',processed=0,total=0,removed=0,failed=0,freedBytes=0)
    root=Path(root).resolve();preview=plan(root,rows,settings)
    if preview['token']!=token:raise ValueError('Cache changed. Review cleanup again.')
    if not isinstance(orphan_ids,(list,tuple)) or any(not isinstance(x,str) for x in orphan_ids):raise ValueError('Invalid work-data selection.')
    chosen={x['id']:x for x in preview['orphanWork'] if x['canRemove']}
    if set(orphan_ids)-set(chosen):raise ValueError('Work data is still in use or cannot be checked.')
    with ExitStack() as locks:
        for directory in sorted({(root/f['path']).parent for f in preview['files'] if f['group']=='video-preview' and (root/f['path']).parent!=root/'cache/studio-preview'}):
            if not locks.enter_context(preview_lock(directory)):raise ValueError('Preview is in use. Try again after closing preview.')
        current=plan(root,rows,settings)
        # Scanning our own preview locks skips them; validate the exact selected
        # paths directly under the held locks instead of treating that as a stale scan.
        current_orphans={x['id']:x for x in current['orphanWork'] if x['canRemove']}
        if any(x not in current_orphans or current_orphans[x]!=chosen[x] for x in orphan_ids):raise ValueError('Work data changed. Review cleanup again.')
        selected=preview['files']+[f for ident in set(orphan_ids) for f in chosen[ident]['files']]
        report(phase='checking',processed=0,total=len(selected),removed=0,failed=0,freedBytes=0)
        for f in selected:
            path=root/f['path']
            if not safe(root,path) or not path.is_file():raise ValueError('Cache changed. Review cleanup again.')
            st=path.stat()
            if (st.st_size,st.st_mtime_ns,st.st_ino,st.st_dev)!=(f['bytes'],f['mtime'],f['inode'],f['device']):raise ValueError('Cache changed. Review cleanup again.')
        # Every path verified before the first deletion; no recursive tree removal.
        failures=[];removed=[];last_update=0
        report(phase='deleting',processed=0,total=len(selected),removed=0,failed=0,freedBytes=0)
        for index,f in enumerate(selected,1):
            try:(root/f['path']).unlink();removed.append(f)
            except OSError:failures.append(f['path'])
            now=time.monotonic()
            if now-last_update>=.15 or index==len(selected):
                report(phase='deleting',processed=index,total=len(selected),removed=len(removed),failed=len(failures),freedBytes=footprint(removed))
                last_update=now
        report(phase='tidying',processed=len(selected),total=len(selected),removed=len(removed),failed=len(failures),freedBytes=footprint(removed))
        # Empty app-owned working/cache folders can be removed; original containers stay.
        parents={p for f in removed for p in (root/f['path']).parents if p!=root and p.is_relative_to(root) and p not in (root/'cache',root/'jobs')}
        for directory in sorted(parents,key=lambda p:-len(p.parts)):
            try:directory.rmdir()
            except OSError:pass
    result=dict(freedBytes=footprint(removed),complete=not failures,removedCount=len(removed),failedCount=len(failures),processedCount=len(selected),failedFiles=failures,orphanWorkRemoved=list(set(orphan_ids)))
    from atomic_files import write_json
    write_json(root/'last-project-cache-cleanup.json',result)
    return result


def cleanup_status(root,operation_id):
    """A small receipt, readable while the mutation RPC owns the state lock."""
    if not isinstance(operation_id,str) or not re.fullmatch(r'[A-Za-z0-9-]{1,80}',operation_id):
        raise ValueError('Invalid cleanup operation.')
    path=Path(root)/'project-cache-progress.json'
    if path.is_symlink():return None
    value=read(path,{})
    return value if isinstance(value,dict) and value.get('operationID')==operation_id else None


def tracked_execute(root,rows,token,orphan_ids=(),settings=None,operation_id=None):
    # Validate the operation identifier before touching the last receipt.
    cleanup_status(root,operation_id)
    from atomic_files import write_json
    path=Path(root)/'project-cache-progress.json'
    if path.is_symlink():raise ValueError('Cleanup status path is linked.')
    state=dict(operationID=operation_id)
    def report(**values):
        state.update(values,updatedAt=time.time())
        # Status is best-effort telemetry; a locked receipt must not make an
        # otherwise successful cleanup fail halfway through deleting files.
        try:write_json(path,state)
        except OSError:pass
    try:
        result=execute(root,rows,token,orphan_ids,settings,report)
    except Exception:
        report(phase='failed')
        raise
    report(phase='complete' if result['complete'] else 'partial',**{k:result[k] for k in ('freedBytes','removedCount','failedCount','processedCount')})
    return result
