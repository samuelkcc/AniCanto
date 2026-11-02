"""Owned temporary files and bounded replacement retries for Windows file locks.

Never truncate or remove the last committed file after a denied replacement.
Critical callers keep errors. Optional telemetry selects its own failure policy.
"""
import contextlib
import json
import os
from pathlib import Path
import tempfile
import time


@contextlib.contextmanager
def temporary_path(path, *, suffix='.tmp'):
    """Own one closed temporary file beside its destination. Always clean it up."""
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.'+path.name+'-',suffix=suffix,delete=False) as handle:
        temp=Path(handle.name)
    try:
        yield temp
    finally:
        try:temp.unlink(missing_ok=True)
        except OSError:pass


def replace_file(source,path):
    """Commit a closed file. Retry only known temporary Windows access failures."""
    delays=(.01,.025,.05,.1,.2,.4,.8)
    for attempt in range(len(delays)+1):
        try:
            os.replace(source,path)
            return
        except OSError as error:
            transient=isinstance(error,PermissionError) or getattr(error,'winerror',None) in (5,32,33)
            if not transient or attempt==len(delays):raise
            time.sleep(delays[attempt])


@contextlib.contextmanager
def staged_path(path, *, suffix='.tmp'):
    """Commit only after the producer exits successfully."""
    with temporary_path(path,suffix=suffix) as temp:
        yield temp
        replace_file(temp,path)


def write_bytes(path,payload):
    with staged_path(path) as temp:
        temp.write_bytes(payload)


def write_json(path,value,*,indent=None):
    payload=json.dumps(value,ensure_ascii=False,indent=indent).encode('utf-8')
    write_bytes(path,payload)
