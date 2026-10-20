"""Remove app-owned project data; keep source media and finished movie exports."""
import hashlib,json,shutil
from pathlib import Path


def read(path,fallback):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return fallback


def remove(root,row,others=()):
    root=Path(root).resolve();original=Path(row['video']).resolve();jobs=root/'jobs';saved=[]
    def owned(path,base):
        raw=Path(path)
        return not base.is_symlink() and base.resolve().is_relative_to(root) and not raw.is_symlink() and raw.resolve().is_relative_to(base.resolve()) and raw.resolve()!=base.resolve()
    folders=set()
    for value in (row.get('review'),row.get('job')):
        if not value:continue
        path=Path(value);folder=path.parent if path.name=='review.json' else path
        if not owned(folder,jobs) or folder.resolve().parent!=jobs.resolve():
            raise ValueError('The project is outside the app-owned jobs folder; no files were removed.')
        folders.add(folder.resolve())
    for job in folders:
        if original.is_relative_to(job):raise ValueError('The source video is inside this project. Move the original before removing processing data.')
    shared_jobs={Path(v).resolve().parent if key=='review' else Path(v).resolve() for other in others for key in ('review','job') if (v:=other.get(key))}
    folders-=shared_jobs
    # Preserve actual final outputs only. Per-engine movies, preview proxies and
    # JSON/SRT diagnostics are working data, not additional user exports.
    for job in folders:
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
    for value in (row.get('output'),row.get('outputThisAttempt')):
        if not value:continue
        output=Path(value);sidecar=output.with_suffix('.processing-time.json')
        record=read(sidecar,{})
        if not sidecar.is_symlink() and record.get('excludesPausedTime') is True and record.get('output')==str(output):sidecar.unlink(missing_ok=True)
    if (root/'projects.sqlite3').is_file():
        from project_store import connect
        with connect(root) as db:
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
    if not any(Path(r['video']).resolve()==original for r in others):
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
