"""Keep private builder paths out of release panic locations and metadata."""
import os,shlex
from pathlib import Path

def rust_environment(target=None,base=None,home=None,**overrides):
 env=dict(os.environ if base is None else base);env.update(overrides)
 encoded=env.pop('CARGO_ENCODED_RUSTFLAGS',None)
 flags=encoded.split('\x1f') if encoded else shlex.split(env.pop('RUSTFLAGS',''))
 env.pop('RUSTFLAGS',None)
 if target and 'windows' in target:
  flags+=['-C','target-feature=+crt-static']
 prefix=str(Path.home() if home is None else Path(home))
 flags.append('--remap-path-prefix='+prefix+'=/build-home')
 env['CARGO_ENCODED_RUSTFLAGS']='\x1f'.join(flags)
 env.setdefault('CARGO_BUILD_JOBS','4')
 return env
