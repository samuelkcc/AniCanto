"""Assemble and verify source delivery for the reviewed native/desktop components.

Run after public_source.py. Source URLs alone do not satisfy a source-delivery
obligation. Missing archives fail assembly rather than silently disappearing.
The scope is engineering source-input coverage, never legal or publication approval.
"""
import argparse,gzip,hashlib,json,tarfile
from pathlib import Path
from public_source import findings

ROOT=Path(__file__).resolve().parents[1]

def checked_file(root,relative,digest):
    root=Path(root).resolve();path=root/relative
    if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('Unsafe source material path')
    if not path.is_file():raise ValueError('Missing source material: '+str(relative))
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if actual!=digest:raise ValueError('Source checksum mismatch: '+str(relative))
    return path

def assemble(source,output):
    source=Path(source).resolve();output=Path(output).resolve();base=ROOT/'.build/compliance/native-source'
    if not source.is_relative_to(ROOT/'.build/public-review') or not (source/'SOURCE-MANIFEST.json').is_file():raise ValueError('Reviewed source export required')
    if not output.is_relative_to(ROOT/'.build/public-review') or output.exists():raise ValueError('Use a fresh local review archive')
    files={};records=[]
    def include(path,name,digest=None):
        path=Path(path)
        if path.is_symlink():raise ValueError('Source symlink forbidden')
        raw=path.read_bytes();actual=hashlib.sha256(raw).hexdigest()
        if digest and actual!=digest:raise ValueError('Source checksum mismatch: '+str(path.name))
        files[name]=path;records.append(dict(path=name,bytes=len(raw),sha256=actual))
    manifest=json.loads((source/'SOURCE-MANIFEST.json').read_text())
    for row in manifest['files']:include(checked_file(source,row['path'],row['sha256']),'AniCanto/'+row['path'],row['sha256'])
    include(source/'SOURCE-MANIFEST.json','AniCanto/SOURCE-MANIFEST.json')
    native=json.loads((ROOT/'licenses/native-source-manifest.json').read_text())
    for component in native['components']:
        folder=base/(component['name']+'-'+component['version'])
        for row in component['archives']:
            delivery=row.get('deliverySubset',row)
            include(checked_file(folder,delivery['file'],delivery['sha256']),'native/'+folder.name+'/'+delivery['file'],delivery['sha256'])
        for name in [component['recipe'],'build-receipt.json']:
            path=folder/name
            if findings(path.read_bytes(),name):raise ValueError('Private build metadata must not enter public sources')
            include(path,'native/'+folder.name+'/'+name)
    include(base/'ffmpeg-build.txt','native/ffmpeg-build.txt')
    tools=json.loads((ROOT/'licenses/tool-source-manifest.json').read_text())
    for tool in tools['tools']:
        if tool.get('bundled') is False:continue
        include(base/tool['name']/'upstream-source.tar.gz','tools/'+tool['name']+'/upstream-source.tar.gz',tool['sha256'])
    for row in tools['uvDependencySources'] if tools.get('uvDependencySourcesBundled',True) else []:
        if 'sha256' not in row:raise ValueError('Missing uv source checksum')
        name=row['name']+'-'+row['version']+'.crate';include(base/'uv-crates'/name,'tools/uv-crates/'+name,row['sha256'])
    wheels=json.loads((ROOT/'licenses/python-wheels.json').read_text())
    for row in wheels:
        if row.get('bundled') is False:continue
        name=row['sourceArchive'];include(base/'python-wheels'/name,'python/'+name,row['sourceSHA256'])
    small=base/'audio.cpp-small';row=json.loads((small/'SOURCE.json').read_text())
    for name,key in [('runtime-source.tar.gz','runtimeSourceArchiveSHA256'),('drama3-small-audiocpp.patch','patchSHA256'),('cantosync-loader.patch','loaderPatchSHA256')]:include(small/name,'tools/audio.cpp-small/'+name,row[key])
    include(small/'SOURCE.json','tools/audio.cpp-small/SOURCE.json')
    # Include desktop/launcher/policy crates from their exact locked versions.
    import tomllib
    registry={}
    for lock in ['core/Cargo.lock','studio/src-tauri/Cargo.lock','windows/launcher/Cargo.lock']:
        for row in tomllib.loads((ROOT/lock).read_text())['package']:
            if row.get('source','').startswith('registry+'):
                name=row['name']+'-'+row['version']+'.crate';registry[name]=row['checksum']
    for name,digest in registry.items():
        candidates=list((Path.home()/'.cargo/registry/cache').glob('*/'+name))
        if not candidates:
            extra=base/'desktop-crates'/name
            if extra.is_file():candidates=[extra]
        if not candidates:raise ValueError('Missing locked desktop source: '+name)
        include(candidates[0],'desktop-crates/'+name,digest)
    # Exact Windows FFmpeg sources are separate from the bootstrap executable.
    # Preserve checked archives, recursive source dependencies and build recipes.
    windows_manifest=ROOT/'licenses/ffmpeg/windows-source.json'
    if windows_manifest.is_file():
        from ffmpeg_source_audit import verify_windows
        windows_base=ROOT/'.build/compliance/remaining-licenses'
        windows_verification=verify_windows(windows_base)
        for row in json.loads(windows_manifest.read_text())['materials']:
            include(checked_file(windows_base,row['path'],row['sha256']),'windows-ffmpeg/'+row['path'],row['sha256'])
    from ffmpeg_source_audit import verify_mac
    version=json.loads((ROOT/'VERSION.json').read_text())['version']
    mac_verification=verify_mac(ROOT/'.build/shared-release'/version/'AniCanto.app')
    # pip is a source-form wheel: preserve its Python sources, vendored certifi
    # MPL sources/certificate data and all original notices, not just an URL.
    installer=json.loads((ROOT/'Resources/python-installer.json').read_text())['pip']
    include(ROOT/'Resources'/installer['file'],'installer/'+Path(installer['file']).name,installer['sha256'])
    coverage=dict(schemaVersion=1,version=version,
        completeCorrespondingSource=True,published=False,legalApproval=False,
        scope='Engineering coverage of the selected Mac/Windows native tools, locked desktop dependencies and bundled source-form installer; not a legal opinion or future-use guarantee.',
        verification=[mac_verification,windows_verification],
        limitations=['Publication is a separate step; provide this exact source attachment with the matching binary pair.',
          'Windows first-launch/GPU inference acceptance is separate and has not been executed on a Windows device.',
          'Compiler/SDK and general-purpose build tool variation is not a claim of bit-identical reproduction.',
          'Optional model weights retain their own terms; unreviewed conversions remain disabled.'],files=records)
    output.parent.mkdir(parents=True,exist_ok=True)
    # Reopen verification below makes a truncated/corrupt archive detectable.
    with output.open('wb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0,compresslevel=1) as zipped,tarfile.open(fileobj=zipped,mode='w|') as archive:
        for name,path in sorted(files.items()):
            info=archive.gettarinfo(str(path),arcname=name);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0;info.mode=0o644
            with path.open('rb') as f:archive.addfile(info,f)
        import io
        data=(json.dumps(coverage,indent=2)+'\n').encode();info=tarfile.TarInfo('SOURCE-MATERIALS.json');info.size=len(data);info.mode=0o644;archive.addfile(info,io.BytesIO(data))
    with tarfile.open(output) as archive:
        for record in records:
            stream=archive.extractfile(record['path'])
            if hashlib.file_digest(stream,'sha256').hexdigest()!=record['sha256']:raise ValueError('Source archive readback mismatch')
    return dict(file=output.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),verifiedFiles=len(records),completeCorrespondingSource=True,legalApproval=False,published=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True,type=Path);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();print(json.dumps(assemble(args.source,args.output),indent=2))
