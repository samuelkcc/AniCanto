"""Install/probe only missing isolated Mac dependencies in Application Support.

Runs after Swift bootstraps app-owned CPython from a pinned verified archive. No system Python,
Homebrew or compiler is required on the user's Mac. Receipts follow successful
package and import checks; interrupted installs retain the private pip cache.
"""
import argparse,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
from runtime_installer import clean_environment,ensure_env,pip_command,repair_command
HERE=Path(__file__).resolve().parent

def emit(message,**extra):print(json.dumps(dict(stage='執行環境',message=message,**extra),ensure_ascii=False),flush=True)
def text(zh,en):return en if os.environ.get('CANTOSYNC_UI_LANGUAGE','').startswith('en') else zh
def catalog():return json.loads((HERE/'mac-runtime-catalog.json').read_text())
def requirements(path):
    rows={}
    for line in Path(path).read_text().splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        if not re.fullmatch(r'[A-Za-z0-9_.-]+==[^\s;]+',line):raise ValueError('Runtime lock must contain exact package versions: '+line)
        name,version=line.split('==',1);rows[re.sub(r'[-_.]+','-',name.lower())]=version
    return rows
def spec(name):
    data=catalog()
    if name not in data['runtimes']:raise ValueError('Unknown Mac runtime')
    row=data['runtimes'][name];lock=HERE/row['requirements']
    identity=hashlib.sha256(lock.read_bytes()+row['probe'].encode()+b'mac-runtime-1-py311').hexdigest()
    return dict(row,identity=identity,packages=requirements(lock))
def environment(root):
    root=Path(root)
    env=dict(clean_environment(root),
             PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',
             NUMBA_CACHE_DIR=str(root/'cache/numba'))
    env.pop('PYTHONHOME',None);env.pop('PYTHONPATH',None);return env
def package_state(python,env):
    code="import importlib.metadata as m,json,platform,sys,re; print(json.dumps(dict(python=list(sys.version_info[:2]),machine=platform.machine(),packages={re.sub(r'[-_.]+','-',d.metadata['Name'].lower()):d.version for d in m.distributions() if d.metadata['Name']})))"
    return json.loads(subprocess.check_output([str(python),'-c',code],env=env,text=True,timeout=60))
def damaged_packages(python,env,expected):
    # Inspect wheel RECORD hashes only after a failed import. Do not download or
    # reinstall healthy libraries just because a different package cannot load.
    code='''import base64,hashlib,importlib.metadata as m,json,sys
expected=json.loads(sys.argv[1]);broken=[]
for name in expected:
    try:d=m.distribution(name)
    except m.PackageNotFoundError:broken.append(name);continue
    for f in d.files or []:
        if not f.hash:continue
        p=d.locate_file(f)
        if not p.is_file():broken.append(name);break
        h=hashlib.new(f.hash.mode)
        with p.open('rb') as stream:
            for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
        if base64.urlsafe_b64encode(h.digest()).rstrip(b'=').decode()!=f.hash.value:
            broken.append(name);break
print(json.dumps(broken))'''
    return json.loads(subprocess.check_output([str(python),'-c',code,json.dumps(list(expected))],env=env,text=True,timeout=300))
def check(root,name):
    root=Path(root);python=root/name/'bin/python3';env=environment(root);row=spec(name)
    current=package_state(python,env)
    if current.get('python')!=[3,11] or current.get('machine') not in ('arm64','aarch64'):return False
    if any(current['packages'].get(key)!=version for key,version in row['packages'].items()):return False
    subprocess.run([str(python),'-c',row['probe']],env=env,check=True,timeout=180)
    return True
def ensure(root,name,run=subprocess.run,state=package_state,damage=damaged_packages):
    root=Path(root).resolve();python=root/name/'bin/python3';env=environment(root);row=spec(name)
    folder=root/'runtime-receipts';target=folder/(name+'.json')
    bundled=HERE/'runtimes'/name/'bin/python3'
    if bundled.is_file():raise ValueError('This installer only manages external runtimes; rebuild the app as a lightweight package.')
    # A previous successful receipt must not survive a subsequent failed check.
    target.unlink(missing_ok=True)
    if not python.is_file():
        emit(text('下載／準備 Python 3.11 · ','Preparing private Python 3.11 · ')+name)
        ensure_env(root,root/name,run=run)
    try:current=state(python,env)
    except (OSError,subprocess.CalledProcessError,ValueError):
        ensure_env(root,root/name,run=run,recreate=True)
        current=state(python,env)
    if current.get('python')!=[3,11] or current.get('machine') not in ('arm64','aarch64'):
        raise ValueError('This Mac package requires an app-owned Apple Silicon Python 3.11 runtime.')
    missing=[key for key,version in row['packages'].items() if current['packages'].get(key)!=version]
    command=pip_command(python,root,'install','--only-binary',':all:','--no-deps','--find-links',HERE/'wheels','-r',HERE/row['requirements'])
    if missing:
        emit(name+text(' · 補齊 '+str(len(missing))+' 個缺少／版本不符套件；已符合版本會沿用。',' · Installing '+str(len(missing))+' missing / mismatched packages; compatible packages are reused.'),missingPackages=missing)
        run(command,env=env,check=True)
    probe=[str(python),'-c',row['probe']]
    repaired=[]
    try:run(probe,env=env,check=True,timeout=180)
    except subprocess.CalledProcessError:
        repaired=damage(python,env,row['packages'])
        if not repaired:raise RuntimeError(name+' import check failed; installed files are intact. See the preceding import error. No healthy packages were redownloaded.')
        emit(name+text(' · 只修復 '+str(len(repaired))+' 個損壞套件。',' · Repairing only '+str(len(repaired))+' damaged packages.'),damagedPackages=repaired)
        repair=repair_command(python,root,repaired,row['packages'],links=[HERE/'wheels'])
        run(repair,env=env,check=True);run(probe,env=env,check=True,timeout=180)
    fresh=state(python,env)
    remaining=[key for key,version in row['packages'].items() if fresh['packages'].get(key)!=version]
    if remaining:raise ValueError('Runtime packages remain incomplete: '+', '.join(remaining))
    from runtime_exclusions import cleanup_command
    cleanup=cleanup_command(root,python,name,fresh['packages'])
    if cleanup:run(cleanup,env=env,check=True)
    receipt=dict(schemaVersion=1,name=name,identity=row['identity'],python=str(python),verifiedAt=time.time(),
                 importsPassed=True,packageCount=len(row['packages']),installedOrRepaired=sorted(set(missing+repaired)))
    folder.mkdir(parents=True,exist_ok=True);temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps(receipt,indent=2));temp.replace(target)
    try:
        from runtime_licenses import update
        update(root)
    except OSError as error:emit('執行環境可用；授權清單稍後可重新整理：'+str(error))
    emit(name+text(' · 已檢查，可以使用。',' · Verified and ready.'),runtime=receipt);return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('root');p.add_argument('name');args=p.parse_args()
    try:
        if args.check:sys.exit(0 if check(args.root,args.name) else 1)
        ensure(args.root,args.name)
    except Exception as error:emit(str(error),error=True);sys.exit(1)
