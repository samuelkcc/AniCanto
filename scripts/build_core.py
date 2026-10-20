"""Reproducible Rust policy helper for macOS ARM/Intel and Windows x64.

The universal helper is not a claim that bundled ML runtimes are universal.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'.build/core'

def build(target=None):
    command=['cargo']
    if target=='x86_64-pc-windows-msvc' and os.name!='nt':command+=['xwin']
    command+=['build','--release','--locked','--offline','--manifest-path',str(ROOT/'core/Cargo.toml')]
    if target:command+=['--target',target]
    from build_environment import rust_environment
    env=rust_environment(target,CARGO_TARGET_DIR=str(TARGET),XWIN_CACHE_DIR=str(ROOT/'.build/windows/xwin-cache'))
    subprocess.run(command,env=env,check=True)
    return TARGET/(target or '')/'release'/('anicanto-core.exe' if target and 'windows' in target else 'anicanto-core')

def install(destination, target=None):
    binary=build(target)
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(binary,destination);destination.chmod(0o755)
    notices(destination.parent.parent)
    return destination

def notices(resources):
    """Inventory pinned crates, including build dependencies; retain their actual notices."""
    metadata=json.loads(subprocess.check_output(['cargo','metadata','--locked','--offline','--format-version','1','--manifest-path',str(ROOT/'core/Cargo.toml')]))
    resources=Path(resources);records=[]
    for package in metadata['packages']:
        if package['name']=='anicanto-core':continue
        source=Path(package['manifest_path']).parent
        dest=resources/'Licenses/anicanto-core'/(package['name']+'-'+package['version'])
        paths=[]
        for file in source.iterdir():
            if file.is_file() and file.name.upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE')):
                dest.mkdir(parents=True,exist_ok=True);shutil.copy2(file,dest/file.name)
                paths.append(str((dest/file.name).relative_to(resources)))
        if not paths:raise RuntimeError('Missing Rust license notice: '+package['name'])
        records.append(dict(name=package['name'],version=package['version'],license=package['license'],origin=package.get('repository') or 'Rust dependency',files=paths))
    resources.mkdir(parents=True,exist_ok=True)
    (resources/'core-dependencies.json').write_text(json.dumps(records,indent=2)+'\n')
    return records

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--target',choices=['native','macos-universal','x86_64-pc-windows-msvc'],default='native')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.target=='macos-universal':
        files=[build(t) for t in ['aarch64-apple-darwin','x86_64-apple-darwin']]
        output=args.output or TARGET/'universal/anicanto-core';output.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['lipo','-create',*[str(p) for p in files],'-output',str(output)],check=True)
    else:
        target=None if args.target=='native' else args.target
        output=install(args.output,target) if args.output else build(target)
    print(json.dumps({'binary':str(output),'target':args.target}))
