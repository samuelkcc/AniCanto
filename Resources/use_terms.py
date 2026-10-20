"""Versioned, explicit acknowledgement of third-party model use conditions.

This is separate from the MIT code license and grants no media/performer rights.
No name, account, device identity or source-media information is collected.
"""
import hashlib,json,time
from pathlib import Path

def document():
    raw=Path(__file__).with_name('USE-TERMS.json').read_bytes()
    return dict(json.loads(raw),sha256=hashlib.sha256(raw).hexdigest())

def accepted(root):
    try:receipt=json.loads((Path(root)/'use-terms-acceptance.json').read_text())
    except (OSError,ValueError):return False
    doc=document()
    return receipt.get('accepted') is True and receipt.get('sha256')==doc['sha256'] and receipt.get('revision')==doc['revision']

def accept(root,params):
    doc=document()
    if params.get('accepted') is not True or params.get('sha256')!=doc['sha256']:
        raise ValueError('Read and explicitly accept the current media, voice and model terms.')
    from worker import atomic_json
    receipt=dict(accepted=True,revision=doc['revision'],sha256=doc['sha256'],acceptedAt=time.time(),language=params.get('language','en'))
    atomic_json(Path(root)/'use-terms-acceptance.json',receipt)
    return receipt

def require(root):
    if not accepted(root):raise ValueError('Please read and accept the media, voice and model terms in Welcome before downloading models or generating speech.')

def revoke(root):
    (Path(root)/'use-terms-acceptance.json').unlink(missing_ok=True)
    return dict(accepted=False)
