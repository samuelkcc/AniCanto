"""Create a local, allowlisted source candidate. Never publishes or runs Git.

The development checkout and binary releases require separate reviews. Unknown
file types, binaries, private paths and secrets cannot enter this export.
"""
import argparse,hashlib,json,os,re,shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TOP={'LICENSE','NOTICE.txt','README.md','VERSION.json','.gitignore'}
TREES={'Sources','Resources','core','scripts','studio','windows','tests','licenses','docs'}
SUFFIXES={'.py','.rs','.toml','.lock','.json','.yaml','.yml','.swift','.js','.mjs','.cjs',
          '.html','.css','.md','.txt','.srt','.strings','.ps1','.cmd','.sh','.svg','.png','.otf','.icns','.ico','.patch','.h','.c','.cpp','.hpp','.cmake','.in','.cfg','.rst','.pyx','.pxd','.tiktoken','.plist','.entitlements'}
SKIP_PARTS={'__pycache__','target','node_modules','.git','.cargo','gen','wheels','archive'}
DOCS={'README.md','SHARED-ARCHITECTURE.md','SHARED-STUDIO.md','WINDOWS-PORT-2026-10-17.md',
      'WINDOWS-STUDIO-ALIGNMENT.md','MAC-LIGHTWEIGHT-DEPLOYMENT.md',
      'WELCOME-DOWNLOAD-MANAGEMENT.md','PUBLIC-DISTRIBUTION-REVIEW.md','ANICANTO-REBRAND.md','OCR-SAMPLING.md'}
PRIVATE=re.compile(rb'(?:/'+rb'Users/[^/\s"\x27]+/|[A-Z]:\\Users\\[^\\\s"\x27]+\\|Google'+rb'Drive-[^/\s]+)',re.I)
SECRET=re.compile(rb'(?:-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{35,}|AKIA[0-9A-Z]{16})')
IMAGE_SUFFIXES={'.png','.otf','.icns','.ico'}
THEMES={'studio','energy','ocean','ninja','retro','forest','future','mint','moonflower'}
REVIEWED_ASSETS={'Resources/AniCanto.icns','Resources/app-icon-art.png','Resources/AniCanto-icon.png',
                 'Resources/fonts/NotoSansCJKtc-Regular.otf','studio/src-tauri/icons/icon.ico','studio/src-tauri/icons/icon.png'}
REVIEWED_ASSETS|={'Resources/pet-'+theme+'.png' for theme in THEMES}
REVIEWED_ASSETS|={'Resources/welcome-art/welcome-'+theme+'-'+str(i)+'.png' for theme in THEMES for i in range(1,5)}

REVIEWED_SYNTHETIC_VOICES={'Resources/natural-voices/yue-low.wav': '31a0e62d885c62d05088bb9a870a979055174f476ea865e14d407c1c4b13cdbb', 'Resources/natural-voices/yue-mid.wav': 'cc1c5706fd49923407f86eedc2234c2bb5a6a06c19d48cf58039717e2fbafbc5', 'Resources/natural-voices/yue-bright.wav': 'a52f80a32e1c24c975972f11eebd0b2dc63010e81e885b1e379db57e67d7b1ff', 'Resources/natural-voices/yue-soft.wav': 'a33e0c21adf2fd00698ce9673f95d54ba20a0012c1f4b28bacaa285a0c48a5b9', 'Resources/natural-voices/en-low.wav': '59a003dc1b8023c3c9beb38c741ee842798d415ef71c605d523f962354ede1c9', 'Resources/natural-voices/en-mid.wav': '9d8bc5e25f7923f7526195dc7c3bdde44e3cc38dc942548ea0f0863845339f8e', 'Resources/natural-voices/en-bright.wav': '331056d0a2d2c95fca1a1ccb2519be655e496af77d609e63cb836510f163798d'}

def selected(relative):
    p=Path(relative)
    if len(p.parts)==1:return p.name in TOP
    if p.parts[0] not in TREES or any(x in SKIP_PARTS for x in p.parts):return False
    if p.name.startswith('.') or p.name in {'VLC-COPYING.txt'}:return False
    if p.parts[:2]==('windows','tools'):return False
    if p.parts[:2]==('licenses','tools') and p.parts[2:3] and p.parts[2].startswith('uv'):return False
    if p.parts[0]=='docs' and (len(p.parts)!=2 or p.name not in DOCS):return False
    # Generated UI assets are rebuilt from the reviewed Resources originals.
    if p.parts[:3]==('studio','web','assets'):return False
    if p.suffix=='.wav':return p.as_posix() in REVIEWED_SYNTHETIC_VOICES
    if p.suffix.lower() in IMAGE_SUFFIXES:return p.as_posix() in REVIEWED_ASSETS
    return p.suffix.lower() in SUFFIXES or any(word in p.name.upper() for word in ('LICENSE','LICENCE','NOTICE','COPYING','COPYRIGHT','AUTHORS')) or p.name in {'CMakeLists.txt','Makefile','PKG-INFO','VERSION'}

def findings(raw,relative):
    errors=[]
    if PRIVATE.search(raw):errors.append('private-user-path')
    if SECRET.search(raw):errors.append('credential-or-private-key')
    if raw[:4] in (b'MZ\x90\0',b'\x7fELF',b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf') or raw[:2]==b'MZ':errors.append('executable-disguised-as-source')
    if Path(relative).suffix.lower() not in IMAGE_SUFFIXES and Path(relative).as_posix() not in REVIEWED_SYNTHETIC_VOICES and b'\0' in raw:errors.append('unexpected-binary')
    if Path(relative).as_posix() in REVIEWED_SYNTHETIC_VOICES:
        if hashlib.sha256(raw).hexdigest()!=REVIEWED_SYNTHETIC_VOICES[Path(relative).as_posix()]:errors.append('synthetic-reference-hash-mismatch')
        if not (raw.startswith(b'RIFF') and raw[8:12]==b'WAVE'):errors.append('invalid-reference-audio')
    # Personal identity is not the same as required upstream author attribution.
    identity=os.environ.get('USER','').encode()
    if len(identity)>4 and identity.lower() in raw.lower():errors.append('local-account-identifier')
    return errors

def export(root,output):
    root=Path(root).resolve();output=Path(output).resolve()
    if output==root or not output.is_relative_to(root/'.build/public-review'):
        raise ValueError('Export must be a dedicated folder under .build/public-review.')
    if output.exists():raise ValueError('Export directory already exists; use a fresh candidate directory.')
    rows=[];errors=[];excluded=0;paths=[]
    for directory,folders,files in os.walk(root,followlinks=False):
        base=Path(directory);relative=base.relative_to(root)
        if base==root:folders[:]=[name for name in folders if name in TREES]
        else:
            folders[:]=[name for name in folders if name not in SKIP_PARTS and not name.startswith('.')]
            if relative.as_posix() in {'windows/tools','studio/web/assets'}:folders[:]=[];continue
        for name in list(folders):
            if (base/name).is_symlink():
                errors.append(dict(path=(base/name).relative_to(root).as_posix(),reasons=['symlink-directory-not-allowed']));folders.remove(name)
        paths.extend(base/name for name in files)
    for path in sorted(paths):
        rel=path.relative_to(root)
        if not rel.parts or rel.parts[0] not in TREES|TOP:continue
        if not selected(rel):
            if path.is_file():excluded+=1
            continue
        if path.is_symlink():errors.append(dict(path=rel.as_posix(),reasons=['symlink-not-allowed']));continue
        if not path.is_file():continue
        raw=path.read_bytes();issues=findings(raw,rel)
        if issues:errors.append(dict(path=rel.as_posix(),reasons=issues));continue
        rows.append((rel,path,hashlib.sha256(raw).hexdigest(),len(raw)))
    if errors:return dict(created=False,errors=errors,filesReviewed=len(rows),excluded=excluded)
    output.mkdir(parents=True)
    for rel,path,_,_ in rows:
        dest=output/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    manifest=dict(schemaVersion=1,scope='Local source candidate with checksum-approved original synthetic references; no executable/model/private recording publication',
        published=False,legalApproval=False,files=[dict(path=r.as_posix(),sha256=h,bytes=n) for r,_,h,n in rows])
    (output/'SOURCE-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return dict(created=True,errors=[],filesReviewed=len(rows),excluded=excluded,bytes=sum(n for _,_,_,n in rows),
        output=str(output.relative_to(root)),published=False,legalApproval=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    report=export(ROOT,args.output);print(json.dumps(report,indent=2));raise SystemExit(0 if report['created'] else 1)
