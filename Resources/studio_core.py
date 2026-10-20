"""Single policy authority shared by Swift, Windows Qt and background workers.

The Rust helper is a small bundled executable, independent of Python/model runtimes.
Never substitute a different policy when it is missing or stale: fail at submission,
before hours of generation. Existing saved recordings are never modified here.
"""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent

@lru_cache(maxsize=1)
def catalog():
    return json.loads((HERE/'production-contract.json').read_text(encoding='utf-8'))

def executable():
    name = 'anicanto-core.exe' if sys.platform == 'win32' else 'anicanto-core'
    if os.environ.get('CANTOSYNC_CORE'):
        candidate = Path(os.environ['CANTOSYNC_CORE'])
    else:
        candidate = HERE/'bin'/name
        # Source checkout only. A packaged app never searches arbitrary PATH entries.
        if not candidate.is_file() and (HERE.parent/'core/Cargo.toml').is_file():
            candidate = HERE.parent/'.build/core/release'/name
    if not candidate.is_file():
        raise RuntimeError('AniCanto shared core is missing. Rebuild or repair the app package.')
    return candidate

def _invoke(request):
    result = subprocess.run([str(executable())], input=json.dumps(request,ensure_ascii=False),
                            text=True,encoding='utf-8',capture_output=True,timeout=30)
    try:
        response=json.loads(result.stdout)
    except ValueError as error:
        raise RuntimeError('AniCanto shared core returned an invalid response.') from error
    if result.returncode or not response.get('ok'):
        raise ValueError(response.get('error','shared-core-failed'))
    return response['result']

@lru_cache(maxsize=1)
def verify():
    expected=hashlib.sha256((HERE/'production-contract.json').read_bytes()).hexdigest()
    if _invoke({'operation':'catalog'})['sha256'] != expected:
        raise RuntimeError('AniCanto core/catalog version mismatch. Rebuild or repair the app package.')
    return expected

def call(operation, **fields):
    verify()
    return _invoke(dict(operation=operation,**fields))

def production_plan(settings):
    return call('plan',settings=settings)

def freeze(settings):
    """Attach a fresh audit projection after merging saved settings, before per-track work."""
    settings['productionPlan']=production_plan(settings)
    return settings['productionPlan']

def deployment_plan(hardware,engine='drama3',installed=None,selected=None):
    models=json.loads((HERE/'model-options.json').read_text(encoding='utf-8'))
    return call('deployment',hardware=hardware,engine=engine,models=models,installedModels=installed or [],selectedModels=selected or {})

if __name__=='__main__':
    print(json.dumps(call('hardware'),ensure_ascii=False))
