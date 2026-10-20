"""Check actual release containers for local account/build identifiers."""
import argparse,hashlib,json,re
from pathlib import Path
import zipfile

def markers(home=None,account=None):
 root=Path.home() if home is None else Path(home);name=account or root.name
 values=[str(root)+'/',str(root)+'\\',str(root).replace('/','\\')+'\\',name+'@','Google'+'Drive-'+name+'@']
 return list(dict.fromkeys(v.encode(encoding) for v in values for encoding in ['utf8','utf-16-le']))

def findings(raw,tokens):
 return sum(raw.count(token) for token in tokens)

def verify(app,exe,payload):
 app,exe,payload=map(Path,(app,exe,payload));tokens=markers();errors=[];files=0
 for path in app.rglob('*'):
  if not path.is_file():continue
  files+=1
  if findings(path.read_bytes(),tokens):errors.append('Mac:'+path.relative_to(app).as_posix())
 if findings(exe.read_bytes(),tokens):errors.append('Windows executable')
 with zipfile.ZipFile(payload) as archive:
  for name in archive.namelist():
   files+=1
   if findings(archive.read(name),tokens):errors.append('Windows:'+name)
 if errors:raise ValueError('Private build/account identifiers remain in '+', '.join(errors))
 return dict(scannedFiles=files,privateBuildOrAccountIdentifierHits=0,scope='Actual Mac files, Windows executable and every embedded payload entry; required third-party author attributions remain.',published=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--app',type=Path,required=True);p.add_argument('--exe',type=Path,required=True);p.add_argument('--payload',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();result=verify(a.app,a.exe,a.payload);a.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
