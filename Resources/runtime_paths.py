"""Prefer self-contained app runtimes; model/data storage stays writable."""
from pathlib import Path
import sys

def python_for(root, name='runtime'):
    if not name or '/' in name or '\\' in name or name in ('.','..'):
        raise ValueError('Invalid runtime name')
    if sys.platform=='win32':
        # Shared workers can resolve native Windows environments. This never
        # maps an MLX runtime to a PyTorch runtime: adapters must be explicit.
        native={'runtime':'worker','gsv-runtime':'gpt','separator-runtime':'analysis','asr-runtime':'asr','speech-runtime':'analysis','cosy-runtime':'cosy','local-tts-runtime':'local','visual-runtime':'worker','text-runtime':'worker'}.get(name,name)
        return Path(root)/'runtimes'/native/'Scripts/python.exe'
    if name=='visual-runtime':
        for base in (Path(__file__).resolve().parent/'runtimes/text-runtime',Path(root)/'text-runtime'):
            if (base/'lib/python3.11/site-packages/mlx_vlm').is_dir():return base/'bin/python3'
    bundled=Path(__file__).resolve().parent/'runtimes'/name/'bin/python3'
    return bundled if bundled.is_file() else Path(root)/name/'bin/python3'

def is_bundled(path):
    return (Path(__file__).resolve().parent/'runtimes') in Path(path).parents

def packages_ready(root,name):
    """Avoid a second dependency resolver after the lightweight installer checked it."""
    python=python_for(root,name)
    if is_bundled(python):return True
    if sys.platform=='win32':return False
    import json
    try:
        from mac_runtime import spec
        receipt=json.loads((Path(root)/'runtime-receipts'/(name+'.json')).read_text())
        return python.is_file() and receipt.get('importsPassed') is True and receipt.get('identity')==spec(name)['identity']
    except (OSError,ValueError,KeyError):return False
