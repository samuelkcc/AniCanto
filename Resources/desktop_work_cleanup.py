"""Plan explicit removal of saved desktop work; keep original media and exports."""
import hashlib
import json
import os
import re
import sqlite3
import time
from pathlib import Path

VIDEO = {'.mp4', '.mkv', '.mov', '.m4v', '.avi', '.webm', '.ts'}
WEIGHTS = {'.safetensors', '.gguf', '.litertlm', '.onnx', '.pt', '.pth', '.ckpt', '.tflite',
           '.bin', '.mlx', '.mlmodel', '.npz', '.npy', '.h5', '.weights'}


def _read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _database(root):
    path = root / 'projects.sqlite3'
    if not path.exists():
        return [], []
    if path.is_symlink():
        raise ValueError('The saved project index is linked; working data is protected.')
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)
    try:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        projects = db.execute('SELECT review,video,status,updated FROM projects ORDER BY review').fetchall() if 'projects' in tables else []
        outputs = db.execute('SELECT path,project,status,updated FROM outputs ORDER BY path').fetchall() if 'outputs' in tables else []
        return projects, outputs
    finally:
        db.close()


def plan(root, queue=()):
    root = Path(root).resolve()
    projects, outputs = _database(root)
    pending_batch = False
    for name in ('batch-inflight.json', 'batch-submissions.json'):
        data = _read(root / name)
        entries = data if isinstance(data, list) else data.get('queue', [data]) if isinstance(data, dict) else []
        pending_batch |= any(isinstance(row, dict) and (row.get('job') or row.get('review'))
                             and row.get('status') not in ('complete', 'finished', 'failed', 'cancelled') for row in entries)
    result = dict(canRemove=not bool(queue or pending_batch), reason='empty-video-list-required' if queue or pending_batch else None,
                  jobCount=0, separationCount=0, jobFolders=[], files=[], kept=[], projects=projects, outputs=outputs)
    roots = []
    originals = {Path(p[1]).resolve() for p in projects if p[1]}
    final = {Path(p[0]).resolve() for p in outputs if p[0]}
    for name in ('jobs', 'separations'):
        folder = root / name
        if folder.is_symlink():
            raise ValueError('A working-data directory is linked; no cleanup is permitted.')
        if not folder.exists():
            continue
        for child in sorted(folder.iterdir()):
            if child.is_symlink() or not child.is_dir() or not re.fullmatch(r'[a-f0-9]{16,64}', child.name):
                result['kept'].append(str(child.relative_to(root)))
                continue
            result['jobCount' if name == 'jobs' else 'separationCount'] += 1
            roots.append(child)
            if name == 'jobs':
                result['jobFolders'].append(str(child.resolve()))
                for manifest in ('review.json', 'config.json', 'processing-preview.json'):
                    data = _read(child / manifest)
                    if not isinstance(data, dict):
                        continue
                    cfg = data.get('config', data)
                    if isinstance(cfg, dict):
                        for key in ('video', 'source', 'input'):
                            value = cfg.get(key)
                            if isinstance(value, str) and Path(value).suffix.lower() in VIDEO:
                                originals.add(Path(value).resolve())
    for folder in roots:
        for base, dirs, names in os.walk(folder, followlinks=False):
            dirs[:] = [n for n in dirs if not (Path(base) / n).is_symlink()]
            for name in sorted(names):
                path = Path(base) / name
                if path.is_symlink() or not path.is_file():
                    continue
                resolved = path.resolve()
                # Preserve registered exports even if an older producer stored one in a job.
                if resolved in originals or resolved in final or path.suffix.lower() in WEIGHTS:
                    result['kept'].append(str(path.relative_to(root)))
                    continue
                if path.suffix.lower() in VIDEO and not path.name.endswith(('-AniCanto.mp4','-AniCanto-Preview.mp4')) and path.name not in {'preview.mp4', 'processing-preview.mp4'}:
                    result['kept'].append(str(path.relative_to(root)))
                    continue
                st = path.stat()
                result['files'].append(dict(path=str(path.relative_to(root)), bytes=st.st_size,
                                            mtime=st.st_mtime_ns, inode=st.st_ino, device=st.st_dev, links=st.st_nlink))
    result['files'].sort(key=lambda r: r['path'])
    result['kept'].sort()
    result['count'] = len(result['files'])
    result['bytes'] = sum(x['bytes'] for x in result['files'] if x['links'] == 1)
    result['token'] = hashlib.sha256(json.dumps([str(root), result], sort_keys=True).encode()).hexdigest()
    return result


def summary(root, queue=()):
    p = plan(root, queue)
    return {k: p[k] for k in ('token', 'canRemove', 'reason', 'jobCount', 'separationCount', 'bytes', 'count')}


def execute(root, queue, token, progress=None):
    root = Path(root).resolve()
    p = plan(root, queue)
    if not p['canRemove']:
        raise ValueError('Empty the video list before clearing saved desktop work.')
    if p['token'] != token:
        raise ValueError('Saved working data changed. Scan it again before cleanup.')
    report = progress or (lambda **kw: None)
    for row in p['files']:
        path = root / row['path']
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Working data changed. No files were removed.')
        st = path.stat()
        if (st.st_size, st.st_mtime_ns, st.st_ino, st.st_dev) != (row['bytes'], row['mtime'], row['inode'], row['device']):
            raise ValueError('Working data changed. No files were removed.')
    removed, failed, total, last = [], [], len(p['files']), 0
    report(phase='deleting', processed=0, total=total, removed=0, failed=0, freedBytes=0)
    freed = 0
    for i, row in enumerate(p['files'], 1):
        try:
            (root / row['path']).unlink()
            removed.append(row)
            if row['links'] == 1:
                freed += row['bytes']
        except OSError:
            failed.append(row['path'])
        now = time.monotonic()
        if now - last > .2 or i == total:
            report(phase='deleting', processed=i, total=total, removed=len(removed), failed=len(failed), freedBytes=freed)
            last = now
    # A project whose working files failed deletion retains its index for recovery.
    failed_jobs = {Path(x).parts[1] for x in failed if Path(x).parts[0] == 'jobs'}
    dbpath = root / 'projects.sqlite3'
    if dbpath.exists():
        db = sqlite3.connect(dbpath, timeout=10)
        try:
            with db:
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                for review, _, _, _ in p['projects']:
                    path = Path(review).resolve()
                    if str(path.parent) not in p['jobFolders'] or path.parent.name in failed_jobs:
                        continue
                    for table in ('documents', 'issues'):
                        if table in tables:
                            db.execute('DELETE FROM ' + table + ' WHERE project=?', (review,))
                    if 'outputs' in tables:
                        db.execute("UPDATE outputs SET project='' WHERE project=?", (review,))
                    db.execute('DELETE FROM projects WHERE review=?', (review,))
        finally:
            db.close()
    for name in ('jobs', 'separations'):
        for base, dirs, _ in os.walk(root / name, topdown=False, followlinks=False):
            for directory in dirs:
                path = Path(base) / directory
                if not path.is_symlink():
                    try:
                        path.rmdir()
                    except OSError:
                        pass
    result = dict(complete=not failed, freedBytes=freed, removedCount=len(removed), failedCount=len(failed),
                  processedCount=total, failedFiles=failed, kept=p['kept'], savedWorkRemoved=True,
                  sourceMediaPreserved=True, registeredExportsPreserved=True, installedModelsPreserved=True)
    from atomic_files import write_json
    write_json(root / 'last-saved-work-cleanup.json', result)
    return result
