"""Private CPython + standard venv/pip; no system Python, uv or shell activation.

pip is executed from a checksum-verified wheel, so legacy uv-created venvs can
be repaired without installing pip into, or rebuilding, a healthy environment.
"""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def catalog():return json.loads((HERE/'python-installer.json').read_text())
def clean_environment(root):
    env=dict(os.environ)
    for key in list(env):
        if key.startswith(('PIP_','UV_')) or key in ('PYTHONHOME','PYTHONPATH','VIRTUAL_ENV','CONDA_PREFIX','__PYVENV_LAUNCHER__'):env.pop(key,None)
    env.update(PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',PYTHONUTF8='1')
    return env

def owned(root,path):
    root=Path(root).resolve();path=Path(path).absolute()
    # The executable of a venv may be an intentional symlink to its private base.
    if not path.resolve().is_relative_to(root):raise ValueError('Installer target must be inside application data.')
    return path

def platform_key():
    if sys.platform=='darwin':return 'macos-arm64'
    if sys.platform=='win32':return 'windows-x64'
    raise ValueError('Only Apple Silicon macOS and Windows x64 runtimes are supported.')

def python_path(folder):return Path(folder)/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python3')
def base_python(root,run=subprocess.run):
    key=platform_key();row=catalog()['platforms'][key];root=Path(root).resolve()
    base=owned(root,root/'python'/row['directory']/row['executable'])
    # Native scripts perform download verification, staging and import probing.
    if sys.platform=='win32':
        command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(HERE/'python-bootstrap.ps1'),'-DataRoot',str(root),'-Resources',str(HERE)]
    else:command=['/bin/sh',str(HERE/'python-bootstrap.sh'),str(root),str(HERE)]
    run(command,env=clean_environment(root),check=True)
    return base

def ensure_env(root,folder,run=subprocess.run,recreate=False):
    root=Path(root).resolve();folder=owned(root,folder);python=python_path(folder)
    if recreate or not python.is_file():
        base=base_python(root,run)
        # Cleanup deliberately preserves symlinks. venv does not replace an
        # existing dangling python link, so reconnect only app-owned aliases
        # before recreating the interpreter. Packages and other files survive.
        if sys.platform!='win32':
            for name in ('python','python3','python3.11'):
                alias=folder/'bin'/name
                if alias.is_symlink():
                    owned(root,alias)  # Reject a link outside this app's data.
                    alias.unlink()
        # Do not use --clear or upgrade dependencies; resumed packages survive.
        run([str(base),'-I','-m','venv','--without-pip',str(folder)],env=clean_environment(root),check=True)
    return python

def pip_command(python,root,*args):
    root=Path(root).resolve();python=owned(root,python)
    row=catalog()['pip'];wheel=HERE/row['file']
    if not wheel.is_file() or hashlib.sha256(wheel.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Bundled pip wheel is missing or fails SHA-256 verification.')
    # -I and --isolated exclude user site, PYTHONPATH and user pip configuration.
    # Explicit cache path also works when --isolated ignores PIP_CACHE_DIR.
    code="import runpy,sys,pathlib;root=pathlib.Path(sys.argv.pop(1)).resolve();assert sys.prefix!=sys.base_prefix and pathlib.Path(sys.prefix).resolve().is_relative_to(root),'pip requires an isolated app environment';sys.path.insert(0,sys.argv.pop(1));runpy.run_module('pip',run_name='__main__')"
    return [str(python),'-I','-c',code,str(root),str(wheel),'--isolated','--disable-pip-version-check','--no-input','--cache-dir',str(root/'cache/pip'),*map(str,args)]

def repair_command(python,root,packages,expected,**options):
    if not packages or any(p not in expected for p in packages):raise ValueError('Repair must name damaged packages from the pinned lock.')
    args=['install','--only-binary',':all:','--force-reinstall','--no-deps']
    for link in options.get('links',[]):args+=['--find-links',str(link)]
    if options.get('constraints'):args+=['-c',str(options['constraints'])]
    args += [p+'=='+expected[p] for p in packages]
    return pip_command(python,root,*args)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root');parser.add_argument('action',choices=['env','pip']);parser.add_argument('target');parser.add_argument('args',nargs=argparse.REMAINDER);a=parser.parse_args()
    if a.action=='env':ensure_env(a.root,Path(a.root)/a.target)
    else:subprocess.run(pip_command(a.target,a.root,*a.args),check=True,env=clean_environment(a.root))
