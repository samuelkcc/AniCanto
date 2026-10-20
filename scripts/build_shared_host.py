"""Build release hosts with pinned dependencies and anonymised compiler paths."""
import argparse,os,subprocess
from pathlib import Path
from build_environment import rust_environment
ROOT=Path(__file__).resolve().parents[1]

def build(target=None):
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
