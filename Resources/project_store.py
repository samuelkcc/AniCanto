"""Shared SQLite project catalogue. JSON files are internal worker checkpoints only."""
import json
import sqlite3
import time
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS projects(review TEXT PRIMARY KEY, video TEXT NOT NULL, status TEXT NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS documents(path TEXT PRIMARY KEY, project TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS outputs(path TEXT PRIMARY KEY, project TEXT NOT NULL, status TEXT NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS removed_outputs(path TEXT PRIMARY KEY, removed REAL NOT NULL);
CREATE TABLE IF NOT EXISTS issues(project TEXT NOT NULL, engine TEXT NOT NULL, language TEXT NOT NULL, cue INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(project,engine,language,cue,kind));
CREATE TABLE IF NOT EXISTS migrations(name TEXT PRIMARY KEY, completed REAL NOT NULL);
'''

def connect(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(root/'projects.sqlite3',timeout=15)
    db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA foreign_keys=ON')
    db.executescript(SCHEMA)
    return db

def sync(root, review, output=None, status=None):
    review=Path(review).resolve()
    obj=json.loads(review.read_text())
    with connect(root) as db:
        db.execute('INSERT OR REPLACE INTO projects VALUES(?,?,?,?)',(str(review),obj['config']['video'],status or obj.get('status','review'),time.time()))
        for name in ('review.json','editor-draft.json','editor-voices.json','report.json','validation.json','segment-issues.json'):
            path=review.parent/name
            if path.is_file():
                payload=json.loads(path.read_text())
                db.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?)',(str(path),str(review),name,json.dumps(payload,ensure_ascii=False),time.time()))
        if output:
            path=str(Path(output).resolve())
            if not db.execute('SELECT 1 FROM removed_outputs WHERE path=?',(path,)).fetchone():
                db.execute('INSERT OR REPLACE INTO outputs VALUES(?,?,?,?)',(path,str(review),status or obj.get('status','complete'),time.time()))

def record_issue(cfg, job, cue, kind, message):
    """Idempotent per-engine gaps; never turn a skipped cue into a healthy take."""
    job=Path(job);path=job/'segment-issues.json'
    rows=json.loads(path.read_text()) if path.exists() else []
    index=int(cue.get('reviewIndex',0))+1
    row=dict(index=index,start=cue['start'],end=cue['end'],engine=cfg.get('ttsBackend',''),language=cfg.get('targetLanguage','yue'),kind=kind,message=str(message),status='skipped')
    if cue.get('editorID'):row['editorID']=cue['editorID']
    rows=[r for r in rows if (r['index'],r['kind'])!=(index,kind)]+[row]
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(rows,ensure_ascii=False,indent=2));temporary.replace(path)
    if cfg.get('storage'):
        with connect(cfg['storage']) as db:
            db.execute('INSERT OR REPLACE INTO issues VALUES(?,?,?,?,?,?)',(str(job/'review.json'),row['engine'],row['language'],index,kind,json.dumps(row,ensure_ascii=False)))
    return row

def migrate(root):
    """One transaction, preserving all legacy checkpoint files for recovery."""
    root=Path(root)
    with connect(root) as db:
        if db.execute("SELECT 1 FROM migrations WHERE name='legacy-v1'").fetchone():return
    for review in (root/'jobs').glob('*/review.json'):
        try:
            report=json.loads((review.parent/'report.json').read_text()) if (review.parent/'report.json').exists() else {}
            output=report.get('exportedOutput',report.get('output'))
            sync(root,review,output if output and Path(output).is_file() else None)
        except (OSError,ValueError,KeyError):continue
    with connect(root) as db:db.execute('INSERT OR REPLACE INTO migrations VALUES(?,?)',('legacy-v1',time.time()))


def clear_issues(cfg,job):
    job=Path(job)
    (job/'segment-issues.json').unlink(missing_ok=True)
    if cfg.get('storage'):
        with connect(cfg['storage']) as db:db.execute('DELETE FROM issues WHERE project=?',(str(job/'review.json'),))


def resolve_issues(cfg,job,indices,kinds=None):
    """Remove repaired gaps from the active list, preserving their evidence."""
    job=Path(job);path=job/'segment-issues.json';indices=set(indices)
    rows=json.loads(path.read_text()) if path.exists() else []
    matches=lambda r:r.get('index') in indices and (kinds is None or r.get('kind') in kinds)
    solved=[dict(r,status='repaired') for r in rows if matches(r)]
    if not solved:return
    archive=job/'resolved-segment-issues.json'
    previous=json.loads(archive.read_text()) if archive.exists() else []
    from worker import atomic_json
    atomic_json(archive,previous+solved)
    atomic_json(path,[r for r in rows if not matches(r)])
    if cfg.get('storage') and kinds is None:
        with connect(cfg['storage']) as db:
            db.executemany('DELETE FROM issues WHERE project=? AND cue=?',[(str(job/'review.json'),i) for i in indices])
