"""Verify the exact bundled OCR weights and preserve their distinct terms."""
import hashlib,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent

def evidence():
 base=HERE if (HERE/'licenses/ocr-models.json').is_file() else HERE.parent
 return base,json.loads((base/'licenses/ocr-models.json').read_text())

def install(root,package):
 root=Path(root).resolve();package=Path(package).resolve();base,row=evidence();verified=[]
 for doc in row['documents']:
  p=base/doc['path']
  if not p.resolve().is_relative_to((base/'licenses').resolve()):raise ValueError('Invalid OCR evidence path')
  raw=p.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=doc['sha256']:raise ValueError('OCR licence evidence fails verification')
  verified.append((p.name,raw))
 for model in row['models']:
  p=package/model['path']
  if not p.resolve().is_relative_to(package) or not p.is_file() or p.stat().st_size!=model['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=model['sha256']:
   raise ValueError('OCR model files differ from the verified release. Repair the worker runtime in Model centre.')
 dest=root/'model-notices/rapidocr-1.4.4';dest.mkdir(parents=True,exist_ok=True)
 for name,raw in verified:
  p=dest/name
  if p.is_file() and p.read_bytes()==raw:continue
  temp=p.with_name(p.name+'.partial');temp.write_bytes(raw);temp.replace(p)
 raw=(json.dumps(row,indent=2)+'\n').encode();p=dest/'provenance.json'
 if not p.is_file() or p.read_bytes()!=raw:
  temp=p.with_suffix('.partial');temp.write_bytes(raw);temp.replace(p)
 return dest
