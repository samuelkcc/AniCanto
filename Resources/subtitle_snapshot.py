"""Freeze actual external caption bytes per submission, not a mutable path."""
import hashlib
from pathlib import Path
from atomic_files import write_json
MAX_BYTES=16*1024*1024

def freeze(cfg,root,identity):
 source=Path(cfg['subtitle']);raw=source.read_bytes()
 if not raw or len(raw)>MAX_BYTES:raise ValueError('Subtitle file must contain 1 byte to 16 MB.')
 sha=hashlib.sha256(raw).hexdigest();folder=Path(root)/'requests/assets'/identity;folder.mkdir(parents=True,exist_ok=False)
 target=folder/('subtitles'+source.suffix.lower());target.write_bytes(raw)
 cfg.update(subtitle=str(target),subtitleSnapshot=dict(revision=1,originalName=source.name,sha256=sha,bytes=len(raw),path=str(target)))
 write_json(folder/'caption-evidence.json',cfg['subtitleSnapshot'])
 return cfg

def verify(cfg):
 snapshot=cfg.get('subtitleSnapshot')
 if not snapshot:return
 path=Path(snapshot['path'])
 if str(path)!=cfg.get('subtitle') or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=snapshot['sha256']:
  raise ValueError('The frozen subtitle evidence changed or is missing. Start a new conversion with the intended subtitles.')


def record_extracted(cfg,job,path,stream=None):
 """Preserve the actual normalised subtitle evidence, retaining its source clocks."""
 source=Path(path)
 if not source.is_file():return
 raw=source.read_bytes()
 receipt=dict(revision=1,source=cfg.get('subtitleSnapshot') or dict(type='embedded',stream=stream),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),path=str(source),timing='original-source-clock')
 target=Path(job)/'subtitle-extracted-evidence.json'
 if target.is_file():
  import json
  old=json.loads(target.read_text())
  if old['sha256']!=receipt['sha256']:raise ValueError('Extracted subtitle evidence changed; start a new analysis.')
 else:write_json(target,receipt)


def verify_extracted(job):
 import json
 receipt=Path(job)/'subtitle-extracted-evidence.json'
 if not receipt.is_file():return  # Legacy jobs have no snapshot receipt.
 saved=json.loads(receipt.read_text());path=Path(saved['path'])
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=saved['sha256']:
  raise ValueError('Saved subtitle evidence changed. Existing recordings were kept; start a new analysis.')
