"""Normalise only diagnostic source-file literals in retained native tools.

Rust hosts are recompiled with --remap-path-prefix. For prebuilt C/C++ tools,
this narrowly scoped post-link step is equivalent to remapping __FILE__ text:
only same-length substitutions in non-code string data are permitted. It never
patches machine instructions, models, runtime search paths, notices or symbols.
"""
import hashlib,json,re,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def sections(raw):
 if raw[:2]==b'MZ':
  pe=struct.unpack_from('<I',raw,0x3c)[0]
  if raw[pe:pe+4]!=b'PE\0\0':raise ValueError('Invalid PE')
  count=struct.unpack_from('<H',raw,pe+6)[0];optional=struct.unpack_from('<H',raw,pe+20)[0];start=pe+24+optional;out=[]
  for i in range(count):
   p=start+40*i;name=raw[p:p+8].rstrip(b'\0').decode();size,offset=struct.unpack_from('<II',raw,p+16);flags=struct.unpack_from('<I',raw,p+36)[0]
   out.append(dict(name=name,offset=offset,size=size,code=bool(flags&0x20000000),strings=name=='.rdata' and not flags&0x20000000))
  return 'pe',out
 if raw[:4]==b'\xcf\xfa\xed\xfe':
  count=struct.unpack_from('<I',raw,16)[0];p=32;out=[]
  for _ in range(count):
   cmd,size=struct.unpack_from('<II',raw,p)
   if cmd==0x19:
    n=struct.unpack_from('<I',raw,p+64)[0]
    for i in range(n):
     q=p+72+80*i;name=raw[q:q+16].rstrip(b'\0').decode();length=struct.unpack_from('<Q',raw,q+40)[0];offset=struct.unpack_from('<I',raw,q+48)[0];flags=struct.unpack_from('<I',raw,q+64)[0]
     out.append(dict(name=name,offset=offset,size=length,code=bool(flags&0x80000400),strings=name=='__cstring'))
   p+=size
  return 'macho',out
 raise ValueError('Unsupported native binary')


def code_hashes(raw):
 _,rows=sections(raw)
 return [(s['name'],hashlib.sha256(raw[s['offset']:s['offset']+s['size']]).hexdigest()) for s in rows if s['code']]


def remap(raw,prefix):
 if len(prefix)<4:raise ValueError('Unexpected build prefix')
 kind,rows=sections(raw);result=bytearray(raw);changes=[]
 wide=prefix.decode('utf8').encode('utf-16-le')
 variants=[(prefix,b'/b/'+b'x'*(len(prefix)-4)+b'/','utf8'),(wide,('/b/'+'x'*(len(wide)//2-4)+'/').encode('utf-16-le'),'utf-16-le')]
 for token,alias,encoding in variants:
  if len(alias)!=len(token):raise ValueError('Path alias length mismatch')
  for match in re.finditer(re.escape(token),raw):
   at=match.start();section=next((s for s in rows if s['offset']<=at and at+len(token)<=s['offset']+s['size']),None)
   if not section or section['code'] or not section['strings']:raise ValueError('Build path is outside diagnostic string data')
   limit=section['offset']+section['size']
   if encoding=='utf-16-le':
    if at%2:raise ValueError('Unaligned wide source filename')
    end=at
    while end+1<limit and raw[end:end+2]!=b'\0\0':end+=2
    name=raw[at:end].decode(encoding)
   else:
    begin=raw.rfind(b'\0',section['offset'],at)+1;end=raw.find(b'\0',at,limit)
    if end<0:raise ValueError('Unterminated source filename')
    name=raw[begin:end].decode('utf8')
   if not re.search(r'\.(?:c|cc|cpp|cxx|h|hpp|rs|m|mm)$',name):raise ValueError('Build path is not a diagnostic source filename')
   result[at:at+len(token)]=alias;changes.append(dict(offset=at,section=section['name'],bytes=len(token),encoding=encoding))
 result=bytes(result)
 if len(result)!=len(raw) or code_hashes(raw)!=code_hashes(result):raise ValueError('Native executable code was changed')
 return result,dict(format=kind,replacedSourceLocations=len(changes),codeSectionsUnchanged=True,sameLengthPathSubstitutions=True,changes=changes)


def prepare():
 prefix=(str(Path.home())+'/').encode();backup=ROOT/'.build/compliance/private-build-path-originals';evidence=ROOT/'licenses/build-path-remapping.json'
 previous=json.loads(evidence.read_text()) if evidence.is_file() else dict(schemaVersion=1,scope='Only diagnostic source-location text normalised in C/C++ tool data. Rust binaries use compiler path remapping. No model or machine instruction is changed.',files=[])
 changed=False
 files=([ROOT/'Resources/drama3-small-server'] if (ROOT/'Resources/drama3-small-server').is_file() else [])+[p for p in (ROOT/'windows/tools').rglob('*') if p.is_file() and p.suffix in ('.exe','.dll') and p.name.startswith(('audiocpp','ggml'))]
 for p in files:
  raw=p.read_bytes()
  if prefix not in raw and prefix.decode('utf8').encode('utf-16-le') not in raw:continue
  rel=p.relative_to(ROOT);clean,record=remap(raw,prefix);input_digest=hashlib.sha256(raw).hexdigest();saved=backup/input_digest/rel;saved.parent.mkdir(parents=True,exist_ok=True)
  if saved.exists() and hashlib.sha256(saved.read_bytes()).hexdigest()!=input_digest:raise ValueError('Private original checksum mismatch')
  if not saved.exists():shutil.copy2(p,saved)
  p.write_bytes(clean)
  if record['format']=='macho':
   subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(p)],check=True,capture_output=True)
   if code_hashes(raw)!=code_hashes(p.read_bytes()):raise ValueError('Signing changed native instructions')
  record.update(path=rel.as_posix(),inputSHA256=hashlib.sha256(raw).hexdigest(),outputSHA256=hashlib.sha256(p.read_bytes()).hexdigest(),privateOriginalRetained=True,codeSectionsUnchangedAfterSigning=True)
  if not any(r['path']==record['path'] and r['inputSHA256']==record['inputSHA256'] and r['outputSHA256']==record['outputSHA256'] for r in previous['files']):previous['files'].append(record);changed=True
 if changed or not evidence.is_file():
  temporary=evidence.with_suffix('.partial');temporary.write_text(json.dumps(previous,indent=2)+'\n');temporary.replace(evidence)
 return previous
if __name__=='__main__':
 result=prepare();print(json.dumps(dict(files=len({r['path'] for r in result['files']}),transformationSteps=len(result['files']),diagnosticLocations=sum(row['replacedSourceLocations'] for row in result['files']),instructionsUnchanged=all(row['codeSectionsUnchanged'] for row in result['files']))))
