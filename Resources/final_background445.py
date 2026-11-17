"""Final optional background reuse cannot start separation or block saved dubbing."""
import errno,hashlib,json,subprocess
from pathlib import Path

REVISION='optional-source-cache-final-background-445'

def enabled(cfg):return cfg.get('optionalSourceCacheRevision')==REVISION

def identity(cfg):
    from dubbing import REVISION as separation_revision
    video=Path(cfg['video']);stat=video.stat()
    return [str(video.resolve()),stat.st_size,stat.st_mtime_ns,cfg.get('startOffset',0),cfg['duration'],separation_revision,cfg.get('sourceAudioStream')]

def folder(cfg):
    key=hashlib.sha256(json.dumps(identity(cfg)).encode()).hexdigest()[:20]
    return Path(cfg['storage'])/'separations'/key

def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def remember(cfg, path):
    if not enabled(cfg):return
    from atomic_files import write_json
    path=Path(path)
    write_json(path/'source-binding445.json',dict(revision=REVISION,identity=identity(cfg),folder=str(path.resolve()),
        files={name:digest(path/name) for name in ('background.wav','dialogue.wav')}))

def mandatory(error,cfg):
    from track_control import UserSkipped,check
    if isinstance(error,UserSkipped):raise error
    if any(text in str(error).lower() for text in ('no space left on device','disk quota exceeded','permission denied')):raise error
    check(cfg)
    if isinstance(error,OSError) and error.errno in (errno.ENOSPC,errno.EDQUOT,errno.EACCES,errno.EPERM):raise error

def warning(cfg,job,error,emit):
    mandatory(error,cfg)
    from atomic_files import write_json
    write_json(Path(job)/'optional-background445.json',dict(revision=REVISION,status='source-mix-fallback',error=str(error)[:500],
        separationRepeated=False,sourceVerificationBypassed=False,selectedRecordingsChanged=False))
    emit('Background warning','Optional background preparation failed. Saved dubbing will still be exported with the verified source mix.',.93)

def prepare(cfg,job,run,emit):
    """Use only the current source/range/track folder and its verified stem hashes."""
    from track_control import check
    from dubbing import validate_stems
    check(cfg)
    try:
        path=folder(cfg);saved=json.loads((path/'source-binding445.json').read_text())
        if saved.get('revision')!=REVISION or saved.get('identity')!=identity(cfg) or saved.get('folder')!=str(path.resolve()):raise ValueError('Optional background cache belongs to another source or range')
        for name in ('background.wav','dialogue.wav'):
            if saved.get('files',{}).get(name)!=digest(path/name):raise ValueError('Optional background cache hash changed')
        validate_stems(cfg,path,run)
        check(cfg)
        return path/'background.wav'
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as error:
        warning(cfg,job,error,emit);return None

def preserve(cfg,job,background,run,emit):
    import nonverbal
    try:return nonverbal.preserve_background(cfg,job,background,run,emit)
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as error:
        warning(cfg,job,error,emit);return background
