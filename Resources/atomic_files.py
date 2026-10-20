"""Atomic UTF-8 JSON replacement, including short-lived Windows file locks.

Each writer owns a unique same-directory temporary file. Never truncate or
remove the last committed file as a workaround for a denied replacement.
Critical callers retain errors; optional telemetry decides its own failure policy.
"""
import json
import os
from pathlib import Path
import tempfile
import time


def write_json(path, value, *, indent=None):
    path=Path(path)
    payload=json.dumps(value,ensure_ascii=False,indent=indent)
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                prefix='.'+path.name+'-',suffix='.tmp',delete=False) as handle:
            temp=Path(handle.name)
            handle.write(payload)
        # Close our handle before replacing: Windows does not permit renaming
        # an open NamedTemporaryFile. Readers/scanners may also briefly own it.
        delays=(.01,.025,.05,.1,.2)
        for attempt in range(len(delays)+1):
            try:
                os.replace(temp,path)
                return
            except OSError as error:
                transient=isinstance(error,PermissionError) or getattr(error,'winerror',None) in (5,32,33)
                if not transient or attempt==len(delays):raise
                time.sleep(delays[attempt])
    finally:
        if temp is not None:
            try:temp.unlink(missing_ok=True)
            except OSError:pass
