"""Remove app-owned project data; keep source media and finished movie exports."""
import hashlib,json,os,re,shutil,tempfile
from contextlib import closing
from pathlib import Path


def read(path,fallback):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return fallback


def separation_folders(root, original):
    """Use the separation producer's identity record, including older revisions."""
    base=root/'separations'
    if base.is_symlink() or not base.is_dir():return []
    folders=[]
    for folder in base.iterdir():
        if folder.is_symlink() or not folder.is_dir() or not re.fullmatch(r'[0-9a-f]{20}',folder.name):
            continue
        marker=folder/'complete.json'
        if marker.is_symlink():continue
        identity=read(marker,[])
        if not isinstance(identity,list) or not identity or identity[0]!=str(original):continue
        if hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:20]==folder.name:
            folders.append(folder)
    return folders


def save_output(path, root):
    """Keep an internal finished movie before removing its working directory."""
    export=root/'exports'
    if export.is_symlink():raise ValueError('The export folder is linked. Check it before removing the video.')
    export.mkdir(exist_ok=True)
    def digest(file):
        with file.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    for count in range(10000):
        dest=export/(path.name if not count else f'{path.stem} ({count}){path.suffix}')
        if dest.is_symlink():continue
        if dest.is_file() and dest.stat().st_size==path.stat().st_size and (dest.samefile(path) or digest(dest)==digest(path)):
            return dest
        if dest.exists():continue
        try:
            os.link(path,dest)
        except FileExistsError:
            continue
        except OSError:
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(dir=export,prefix='.ani-export-',delete=False) as target:
                    temporary=Path(target.name)
                    with path.open('rb') as source:shutil.copyfileobj(source,target)
                    target.flush()
                    os.fsync(target.fileno())
                if digest(temporary)!=digest(path):raise OSError('The export copy could not be verified.')
                # Reserve the name without replacing a user file which appeared during the copy.
                try:
                    with dest.open('xb'):pass
                except FileExistsError:
                    continue
                try:
                    temporary.replace(dest)
                except OSError:
                    dest.unlink(missing_ok=True)
                    raise
            finally:
                if temporary is not None:temporary.unlink(missing_ok=True)
        return dest
    raise OSError('Cannot choose an unused export filename.')


def remove(root,row,others=(),*,completed_list_removal=False):
    root=Path(root).resolve();original=Path(row['video']).resolve();jobs=root/'jobs';saved=[]
    def owned(path,base):
        raw=Path(path)
        return not base.is_symlink() and base.resolve().is_relative_to(root) and not raw.is_symlink() and raw.resolve().is_relative_to(base.resolve()) and raw.resolve()!=base.resolve()
    def project_folder(key,value):
        path=Path(value)
        if key=='review':
            if path.name!='review.json' or path.is_symlink():raise ValueError('The project review path is invalid; no files were removed.')
            folder=path.parent
        else:
            # A completed version records its own job path, while the review
            # and working files still live in the enclosing app-owned project.
            folder=path.parent.parent if path.parent.name=='versions' else path
            if path!=folder and (path.is_symlink() or path.parent.is_symlink()):
                raise ValueError('The project version path is a symlink; no files were removed.')
        if not owned(folder,jobs) or folder.resolve().parent!=jobs.resolve() or not path.resolve().is_relative_to(folder.resolve()):
            raise ValueError('The project is outside the app-owned jobs folder; no files were removed.')
        return folder.resolve()
    folders=set()
    for key in ('review','job'):
        value=row.get(key)
        if not value:continue
        folders.add(project_folder(key,value))
    if len(folders)>1:raise ValueError('The project paths disagree; no files were removed.')
    for job in folders:
        if original.is_relative_to(job):raise ValueError('The source video is inside this project. Move the original before removing processing data.')
    shared_jobs={project_folder(key,v) for other in others for key in ('review','job') if (v:=other.get(key))}
    folders-=shared_jobs
    registered={};other_sources={Path(r['video']).resolve() for r in others}
    db_path=root/'projects.sqlite3'
    if completed_list_removal and db_path.is_symlink():
        raise ValueError('The project catalogue is linked. Check it before removing the video.')
    if completed_list_removal and db_path.is_file():
        from project_store import connect
        with closing(connect(root)) as db:
            registered={Path(path).resolve():(status,updated) for path,status,updated in db.execute('SELECT path,status,updated FROM outputs')}
            other_sources.update(Path(video).resolve() for review,video in db.execute('SELECT review,video FROM projects')
                                 if not any(Path(review).resolve().is_relative_to(job) for job in folders))
    finished={}
    if completed_list_removal:
        candidates=set(registered)
        if row.get('output'):candidates.add(Path(row['output']))
        for job in folders:
            report=read(job/'report.json',{})
            for key in ('exportedOutput','output'):
                if report.get(key) and (key=='exportedOutput' or not report.get('exportedOutput')):
                    candidates.add(Path(report[key]))
            for version_path in job.glob('versions/*/version.json'):
                version=read(version_path,{})
                if version.get('status')=='complete' and version.get('output'):
                    candidates.add(Path(version['output']))
        if any(source.is_relative_to(job) for source in other_sources for job in folders):
            raise ValueError('Another saved project uses a source inside this project.')
        for path in sorted(candidates):
            if path.is_file() and any(owned(path,job) for job in folders):
                resolved=path.resolve()
                finished[resolved]=save_output(resolved,root)
        saved.extend(str(path) for path in finished.values())
    # Preserve actual final outputs only. Per-engine movies, preview proxies and
    # JSON/SRT diagnostics are working data, not additional user exports.
    for job in (() if completed_list_removal else folders):
        report=read(job/'report.json',{})
        outputs=[row.get('output'),report.get('exportedOutput')]
        if not any(v and Path(v).is_file() and not Path(v).resolve().is_relative_to(job) for v in outputs):
            output=Path(report.get('output') or row.get('output') or '')
            if output.is_file() and owned(output,job):
                export=root/'exports';export.mkdir(exist_ok=True);dest=export/output.name;count=1
                while dest.exists():dest=export/f'{output.stem} ({count}){output.suffix}';count+=1
                shutil.copy2(output,dest)
                if dest.stat().st_size!=output.stat().st_size:raise OSError('Export preservation did not complete; project retained.')
                saved.append(str(dest))
    # Remove only timing sidecars positively identified as app-generated.
    for value in (() if completed_list_removal else (row.get('output'),row.get('outputThisAttempt'))):
        if not value:continue
        output=Path(value);sidecar=output.with_suffix('.processing-time.json')
        record=read(sidecar,{})
        if not sidecar.is_symlink() and record.get('excludesPausedTime') is True and record.get('output')==str(output):sidecar.unlink(missing_ok=True)
    if db_path.is_file() or finished:
        from project_store import connect
        with closing(connect(root)) as db, db:
            for path,dest in finished.items():
                status,updated=registered.get(path,('complete',path.stat().st_mtime))
                db.execute('INSERT OR IGNORE INTO outputs VALUES(?,?,?,?)',(str(dest),'',status,updated))
                db.execute('DELETE FROM outputs WHERE path=?',(str(path),))
            projects=[r[0] for r in db.execute('SELECT review FROM projects') if any(Path(r[0]).resolve().is_relative_to(j) for j in folders)]
            for project in projects:
                db.execute('DELETE FROM documents WHERE project=?',(project,));db.execute('DELETE FROM issues WHERE project=?',(project,))
                db.execute('DELETE FROM projects WHERE review=?',(project,));db.execute("UPDATE outputs SET project='' WHERE project=?",(project,))
    requests={row.get('request')}
    attempt=root/'attempts'/str(row.get('id',''))
    if row.get('id') and owned(attempt,root/'attempts'):
        for p in attempt.glob('*/attempt.json'):requests.add(read(p,{}).get('request'))
    other_requests={r.get('request') for r in others}
    for value in requests-other_requests:
        if value and owned(value,root/'requests'):Path(value).unlink(missing_ok=True)
    for job in folders:
        if job.exists():shutil.rmtree(job)
    if row.get('id') and owned(attempt,root/'attempts') and attempt.exists():shutil.rmtree(attempt)
    if original not in other_sources:
        if completed_list_removal:
            protected_paths={original,*other_sources,*registered,*finished.values()}
            for folder in separation_folders(root,original):
                if not any(path.is_relative_to(folder) for path in protected_paths):
                    shutil.rmtree(folder)
        key=(row.get('sourcePreflight') or {}).get('cacheKey','')
        if len(key)==64 and all(c in '0123456789abcdef' for c in key):
            probe=root/'source-language'/key
            if owned(probe,root/'source-language') and probe.is_dir():shutil.rmtree(probe)
        cache=root/'cache/studio-preview'
        for folder in cache.iterdir() if cache.is_dir() and cache.resolve().is_relative_to(root) else []:
            if not folder.is_dir() or folder.is_symlink():continue
            status=read(folder/'status.json',{})
            same=status.get('source') and Path(status['source']).resolve()==original
            # Pre-v0.24.11 cache had no manifest; identify only the exact owned
            # source fingerprint. Never sweep other movies' preview cache.
            legacy=original.is_file() and folder.name==hashlib.sha256((str(original)+str(original.stat().st_mtime_ns)).encode()).hexdigest()[:24]
            if same or legacy:shutil.rmtree(folder)
    return saved
