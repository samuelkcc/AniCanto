"""Pinned GGML CUDA plug-in for the patched small-model host, never the stock server.

CUDA is only selected for production after the exact host has generated audio.
No CUDA toolkit or system Python is required on the user's PC.
"""
import json,os,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent

def capable():
    return (HERE/'tools/drama-small-cuda/audiocpp_server.exe').is_file()

def ready(root):
    path=Path(root)/'tools/drama-small-cuda'
    try:receipt=json.loads((path/'verified.json').read_text())
    except (OSError,ValueError):return False
    return bool(receipt.get('files')) and all((path/name).is_file() and (path/name).stat().st_size==row['bytes'] for name,row in receipt['files'].items())

def prepare(root,emit):
    from native_setup import tool
    from downloads import sha256
    if not capable():raise ValueError('This package has no compatible Drama3-small CUDA host.')
    target=Path(root)/'tools/drama-small-cuda';target.mkdir(parents=True,exist_ok=True)
    (target/'verified.json').unlink(missing_ok=True)
    for name in ('drama-cuda','drama-cudart'):
        source=tool(name)
        for path in source.glob('*.dll'):
            # Use our matching GGML host libraries, including the small-model patch.
            if path.name.startswith('ggml') and path.name!='ggml-cuda.dll':continue
            destination=target/path.name
            if not destination.exists() or destination.stat().st_size!=path.stat().st_size:shutil.copy2(path,destination)
    for path in (HERE/'tools/drama-small-cuda').iterdir():
        if path.is_file():shutil.copy2(path,target/path.name)
    binary=target/'audiocpp_server.exe'
    emit('Checking NVIDIA CUDA devices for Drama3-small',setupStep='verify')
    result=subprocess.run([str(binary),'--list-devices'],capture_output=True,text=True,timeout=90,env=dict(os.environ,PATH=str(target)+os.pathsep+os.environ.get('PATH','')))
    output=result.stdout+'\n'+result.stderr
    (target/'device-probe.log').write_text(output,encoding='utf-8')
    if result.returncode or not any(line.startswith('CUDA:') for line in result.stdout.splitlines()):
        raise RuntimeError('Drama3-small CUDA device check failed. See '+str(target/'device-probe.log'))
    files={p.name:dict(bytes=p.stat().st_size,sha256=sha256(p)) for p in target.iterdir() if p.suffix in ('.dll','.exe')}
    (target/'verified.json').write_text(json.dumps(dict(files=files,deviceProbePassed=True,speechInferencePassed=False)))
    return target

def plan_components(root):
    rows=json.loads((HERE/'native-tools.json').read_text());root=Path(root);result=[]
    for name in ('drama-cuda','drama-cudart'):
        row=rows[name];path=root/'tools'/name;installed=False
        try:
            receipt=json.loads((path/'verified.json').read_text())
            installed=receipt.get('sha256')==row['sha256'] and all((path/n).is_file() and (path/n).stat().st_size==v['bytes'] for n,v in receipt.get('files',{}).items()) and bool(receipt.get('files'))
        except (OSError,ValueError):pass
        result.append(dict(id=name,title='NVIDIA CUDA plug-in' if name=='drama-cuda' else 'NVIDIA CUDA runtime',bytes=row['size'],installed=installed,purpose='Drama3-small GPU',kind='tool'))
    return result
