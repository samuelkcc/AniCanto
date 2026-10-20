"""Embed relocatable CPython prefixes and isolated, already validated dependencies."""
from pathlib import Path
import json
import shutil
import subprocess
import os


def bundle(resources, root, build):
    data=Path(os.environ.get('CANTO_BUILD_DATA',str(Path.home()/'Library/Application Support/SamCantoSync')))
    base=(data/'runtime/bin/python3').resolve().parent.parent
    manifest={}
    local_tts=Path(os.environ.get('CANTO_LOCAL_TTS_RUNTIME',str(data/'local-tts-runtime')))
    names=('runtime','separator-runtime','cosy-runtime','gsv-runtime','asr-runtime','qwen-runtime','text-runtime')
    if local_tts.is_dir():names+=('local-tts-runtime',)
    for name in names:
        source=data/name
        if name=='local-tts-runtime':source=local_tts
        if name=='asr-runtime' and not source.exists():source=build/'qa093/asr-runtime'
        if name=='qwen-runtime' and not source.exists():source=build/'qa120/qwen-runtime'
        if name=='text-runtime' and not source.exists():source=build/'qa124/text-runtime'
        visual_source=Path(os.environ.get('CANTO_VISUAL_RUNTIME',str(build/'qa211/visual-runtime')))
        if name=='text-runtime' and (visual_source/'lib/python3.11/site-packages/mlx_vlm').is_dir():source=visual_source
        packages=source/'lib/python3.11/site-packages'
        if not packages.is_dir():raise RuntimeError(f'Missing validated build environment: {source}')
        target=resources/'runtimes'/name
        if target.exists():shutil.rmtree(target)
        # Standalone uv CPython locates its prefix relative to the real executable.
        # Never embed a venv pointing to the build machine's absolute interpreter.
        shutil.copytree(base,target,symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        dest=target/'lib/python3.11/site-packages'
        shutil.rmtree(dest)
        shutil.copytree(packages,dest,symlinks=False,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        # Console entry points in copied venvs have absolute shebangs. Only the
        # standalone interpreter entry points are shipped and used by workers.
        manifest[name]={'python':'3.11','packages':sorted(p.name for p in dest.glob('*.dist-info'))}
    for name in ('ollama','gpt-sovits'):
        target=resources/name
        if target.exists():shutil.rmtree(target)
        selected=Path(os.environ.get('CANTO_GSV_SOURCE',str(data/name))) if name=='gpt-sovits' else data/name
        shutil.copytree(selected,target,symlinks=False,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git'))
    entry=resources/'ollama/bin/ollama'
    entry.unlink(missing_ok=True);entry.symlink_to('../ollama')
    (resources/'BUNDLED-RUNTIMES.json').write_text(json.dumps(manifest,indent=2))
    # Validate relocation in a new process without the developer's Python paths.
    modules={'runtime':'faster_whisper','separator-runtime':'torch, audio_separator, sklearn','cosy-runtime':'mlx.core, mlx_audio, soundfile','gsv-runtime':'torch, transformers, pyopenjtalk','asr-runtime':'mlx_audio.stt','qwen-runtime':'mlx_audio.tts.models.qwen3_tts','text-runtime':'mlx_lm.models.qwen3_5_moe'}
    if 'local-tts-runtime' in names:modules['local-tts-runtime']='torch, torchaudio, transformers, hyperpyyaml, diffusers, whisper, conformer'
    env=dict(os.environ,PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
    for name, imports in modules.items():
        subprocess.run([str(resources/'runtimes'/name/'bin/python3'),'-c',f'import {imports}; import sys; assert sys.prefix.startswith({str(resources)!r}), sys.prefix'],env=env,check=True)
