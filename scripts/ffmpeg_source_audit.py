"""Verify retained FFmpeg build inputs; never uploads or grants legal approval.

The source manifests describe archives shipped alongside releases. Every archive
must exist and match its checksum; source URLs alone are not a delivery result.
"""
import argparse,hashlib,json,re,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def digest(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def checked(root,row):
 root=Path(root).resolve();p=root/row['path']
 if p.is_symlink() or not p.resolve().is_relative_to(root) or not p.is_file():raise ValueError('Missing or unsafe source input: '+row['path'])
 if digest(p)!=row['sha256']:raise ValueError('Source input checksum mismatch: '+row['path'])
 if 'bytes' in row and p.stat().st_size!=row['bytes']:raise ValueError('Source input size mismatch: '+row['path'])
 return p

def verify_windows(materials,manifest=None):
 materials=Path(materials);manifest=manifest or json.loads((ROOT/'licenses/ffmpeg/windows-source.json').read_text());verified=[]
 for row in manifest['materials']:
  p=checked(materials,row)
  if row['path'].endswith(('.tar.gz','.crate')):
   with tarfile.open(p) as archive:
    if not archive.getmembers():raise ValueError('Empty source archive')
    for member in archive.getmembers():
     if member.name.startswith('/') or '..' in Path(member.name).parts:raise ValueError('Unsafe archive member')
  verified.append(row['path'])
 if manifest['unresolved']:raise ValueError('Source input review is incomplete: '+', '.join(manifest['unresolved']))
 binary=checked(materials,manifest['binary'])
 import zipfile
 with zipfile.ZipFile(binary) as z:
  name=next(n for n in z.namelist() if n.endswith('/bin/ffmpeg.exe'));raw=z.read(name)
  if manifest['version'].encode() not in raw:raise ValueError('FFmpeg binary version does not match source review')
  if manifest['configuration'].encode() not in raw:raise ValueError('FFmpeg build configuration does not match source review')
 return dict(platform='windows-x64',verifiedMaterials=len(verified),binaryVersion=manifest['version'],sourceInputsRetained=True,legalApproval=False,published=False)

def verify_mac(app,source_root=None,manifest=None):
 app=Path(app).resolve();base=Path(source_root or ROOT/'.build/compliance/native-source').resolve();manifest=manifest or json.loads((ROOT/'licenses/native-source-manifest.json').read_text());rows=[]
 components={c['name']+'/'+c['version']:c for c in manifest['components']}
 for c in manifest['components']:
  folder=base/(c['name']+'-'+c['version'])
  for a in c['archives']:
   checked(folder,dict(path=a['file'],sha256=a['sha256']))
   if a.get('deliverySubset'):
    d=a['deliverySubset'];checked(folder,dict(path=d['file'],sha256=d['sha256'],bytes=d['bytes']))
  for name in [c['recipe'],'build-receipt.json']:
   if not (folder/name).is_file():raise ValueError('Missing native build recipe/receipt')
 mapping=json.loads((app/'Contents/Resources/BUNDLED-COMPONENTS.json').read_text());native={Path(p).name:p for p in mapping}
 for rel,origin in mapping.items():
  p=app/'Contents'/rel
  if not origin.startswith('homebrew/'):raise ValueError('Unreviewed native origin')
  parts=origin.split('/');key=parts[1]+'/'+parts[2]
  if key not in components:raise ValueError('Unmapped native source component: '+key)
  links=subprocess.check_output(['/usr/bin/otool','-L',str(p)],text=True).splitlines()[1:];deps=[]
  for line in links:
   dep=line.strip().split(' (',1)[0]
   if dep.startswith(('/usr/lib/','/System/Library/')):continue
   if Path(dep).name not in native:raise ValueError('Native dependency lacks a source mapping: '+dep)
   deps.append(Path(dep).name)
  rows.append(dict(path=rel,origin=origin,sha256=digest(p),nonSystemDependencies=deps))
 return dict(platform='macos-arm64',nativeFiles=len(rows),sourceComponents=len(components),allNonSystemDependenciesMapped=True,sourceInputsRetained=True,files=rows,legalApproval=False,published=False)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--windows-materials',type=Path);parser.add_argument('--mac-app',type=Path);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args();reports=[]
 if args.windows_materials:reports.append(verify_windows(args.windows_materials))
 if args.mac_app:reports.append(verify_mac(args.mac_app))
 if not reports:parser.error('Select a platform to verify')
 args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(dict(reports=reports,legalApproval=False,published=False),indent=2)+'\n');print(json.dumps([{k:v for k,v in r.items() if k!='files'} for r in reports],indent=2))
