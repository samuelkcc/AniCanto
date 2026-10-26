"""Build release hosts with pinned dependencies and anonymised compiler paths."""
import argparse,json,os,re,subprocess
from pathlib import Path
from build_environment import rust_environment
ROOT=Path(__file__).resolve().parents[1]

def sync_version():
 version=json.loads((ROOT/'VERSION.json').read_text())['version']
 for name in ('Cargo.toml','Cargo.lock'):
  path=ROOT/'studio/src-tauri'/name;text=path.read_text()
  pattern=r'(name = "anicanto-studio"\nversion = ")[^"]+("|$)'
  updated,count=re.subn(pattern,lambda m:m.group(1)+version+m.group(2),text,count=1)
  if count!=1:raise RuntimeError('Missing native host package identity: '+name)
  if updated!=text:path.write_text(updated)
 path=ROOT/'studio/src-tauri/tauri.conf.json';config=json.loads(path.read_text())
 if config['version']!=version:config['version']=version;path.write_text(json.dumps(config,indent=2)+'\n')


def build(target=None):
 sync_version()
 # Refresh versioned web resources before embedding them in either native host.
 from prepare_shared_studio import prepare
 prepare()
 command=['cargo']+(['xwin'] if target and 'windows' in target and os.name!='nt' else [])
 command+=['build','--release','--locked','--offline','--manifest-path',str(ROOT/'studio/src-tauri/Cargo.toml')]
 if target:command+=['--target',target]
 env=rust_environment(target,XWIN_CACHE_DIR=str(ROOT/'.build/windows/xwin-cache'))
 subprocess.run(command,env=env,check=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--target',choices=['native','x86_64-pc-windows-msvc'],default='native');args=parser.parse_args();build(None if args.target=='native' else args.target)
