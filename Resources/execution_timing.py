"""Per-process operation receipts for explaining model loading/repeated work.

These are observations, not elapsed estimates or quality certification. Recording
telemetry must never prevent delivery of successfully generated audio/video.
"""
import contextlib,json,time,uuid
from pathlib import Path

@contextlib.contextmanager
def measure(folder,operation,**details):
    began=time.monotonic();row=dict(schemaVersion=1,operation=operation,startedAt=time.time(),status='running',**details)
    path=Path(folder)/'execution-timing'/(uuid.uuid4().hex+'.json')
    def save():
        try:
            path.parent.mkdir(parents=True,exist_ok=True)
            temp=path.with_suffix('.tmp');temp.write_text(json.dumps(row,ensure_ascii=False,indent=2));temp.replace(path)
        except OSError:pass
    save()
    try:
        yield row
    except BaseException as error:
        row.update(status='failed',errorType=type(error).__name__);raise
    else:row['status']='completed'
    finally:
        row.update(seconds=max(0,time.monotonic()-began),finishedAt=time.time());save()
