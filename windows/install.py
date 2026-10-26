"""Explicit Windows setup. Separate environments keep voice engines independent."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.request

from gpu import adapters, amd_supported, data_root, recommended, vendor

HERE = Path(__file__).resolve().parent
SHARED = HERE / 'shared' if (HERE / 'shared').is_dir() else HERE.parent / 'Resources'
sys.path.insert(0, str(SHARED))
from runtime_installer import ensure_env,pip_command


def emit(message):
    print(json.dumps(dict(stage='Setup', message=message), ensure_ascii=False), flush=True)


def call(args):
    subprocess.run([str(arg) for arg in args], check=True)


def env_python(name):
    folder = data_root() / 'runtimes' / name
    return folder / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')



def install_torch(python, backend, repair=False, packages=None, cuda_index=None):
    root=data_root()
    extra=['--force-reinstall','--no-deps'] if repair else []
    selected=set(packages or ('torch','torchaudio'))
    if backend == 'amd':
        base = 'https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1/'
        if not repair:call(pip_command(python,root,'install',*extra) + [base + name for name in
              ['rocm_sdk_core-7.2.1-py3-none-win_amd64.whl',
               'rocm_sdk_devel-7.2.1-py3-none-win_amd64.whl',
               'rocm_sdk_libraries_custom-7.2.1-py3-none-win_amd64.whl', 'rocm-7.2.1.tar.gz']])
        call(pip_command(python,root,'install',*extra) + [base + name for name in
              ['torch-2.9.1%2Brocm7.2.1-cp312-cp312-win_amd64.whl',
               'torchaudio-2.9.1%2Brocm7.2.1-cp312-cp312-win_amd64.whl',
               'torchvision-0.24.1%2Brocm7.2.1-cp312-cp312-win_amd64.whl'] if not repair or name.split('-',1)[0] in selected])
    else:
        if backend=='nvidia' and cuda_index is None:
            from gpu import planning_hardware
            from hardware_runtimes import nvidia
            h=planning_hardware();cuda_index=nvidia(h.get('acceleratorName',''),h.get('cudaComputeCapability'),h.get('cudaDriverVersion'),h.get('selectedTorchIndex'))['torchIndex']
        if backend=='nvidia' and cuda_index not in ('cu126','cu128','cu130'):raise ValueError('Detect a supported GPU runtime before installing CUDA.')
        index = {'nvidia': cuda_index, 'intel': 'xpu', 'cpu': 'cpu'}[backend]
        call(pip_command(python,root,'install',*extra,'--index-url',
              'https://download.pytorch.org/whl/' + index,
              *[name+'==2.9.1' for name in ('torch','torchaudio') if not repair or name in selected]))


def extract_source(row, target):
    from downloads import download
    archive = data_root() / 'downloads' / (row['revision'] + '.tar.gz')
    download(row['url'], archive, row['sha256'])
    if (target / '.source-complete').is_file():
        return
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            parts = Path(member.name).parts[1:]
            if not parts:
                continue
            if member.issym() or member.islnk() or '..' in parts or Path(*parts).is_absolute():
                raise ValueError('Invalid source archive entry.')
            member.name = str(Path(*parts))
            source.extract(member, target, filter='data')
    (target / '.source-complete').write_text(row['revision'], encoding='utf-8')


def download_manifest(row, target):
    from downloads import download
    for i, file in enumerate(row['files']):
        emit(f"{row['repo']}: {i+1}/{len(row['files'])} · {file['path']}")
        download(f"https://huggingface.co/{row['repo']}/resolve/{row['revision']}/{file['path']}",
                 target / file['path'], file['sha256'], file['size'])


def setup(engine, backend, qwen_model='qwen-large'):
    if sys.platform != 'win32':
        raise RuntimeError('Run setup on your Windows 11 x64 desktop.')
    if sys.maxsize <= 2**32:
        raise RuntimeError('A 64-bit Python runtime is required.')
    if sys.getwindowsversion().build < 22000:
        raise RuntimeError('This test package targets Windows 11.')
    root = data_root()
    root.mkdir(parents=True, exist_ok=True)
    rows = adapters()
    backend = recommended(rows) if backend == 'auto' else backend
    if backend == 'amd' and not any(vendor(row) == 'amd' and amd_supported(row.get('Name', '')) for row in rows):
        raise RuntimeError('This Radeon is outside the pinned ROCm Windows support list. Use CPU setup; AMD hardware video export remains available.')
    if engine in ('gpt', 'cosy') and backend == 'intel':
        emit('This voice engine uses CPU on Intel. Qwen can use the Intel XPU runtime.')
        backend = 'cpu'
    python = env_python(engine)
    marker = root / f'{engine}-windows-ready.json'
    previous = json.loads(marker.read_text()) if marker.is_file() else {}
    if previous and previous.get('backend') != backend:
        raise RuntimeError('An environment already exists for another GPU backend. Use a separate CANTOSYNC_WINDOWS_DATA folder for a hardware change.')
    marker.unlink(missing_ok=True)
    emit(f'Installing {engine} / {backend}; models and tools stay in {root}.')
    if not python.is_file():
        ensure_env(root,python.parent.parent)
    install_torch(python, backend)
    # Protect the vendor torch wheel during voice dependency resolution.
    versions = json.loads(subprocess.check_output([python, '-c',
        'import torch, torchaudio, json; print(json.dumps([torch.__version__, torchaudio.__version__]))'], text=True))
    constraints = root / f'{engine}-torch-constraints.txt'
    constraints.write_text(f'torch=={versions[0]}\ntorchaudio=={versions[1]}\n', encoding='utf-8')
    command = pip_command(python,root,'install','-c',constraints)
    call(command + ['-r', HERE / f'requirements-{engine}.lock'])
    manifests = json.loads((HERE / 'models.json').read_text())
    if engine == 'cosy':
        extract_source(manifests['cosy-source'], root / 'sources/cosy')
        extract_source(manifests['matcha-source'], root / 'sources/cosy/third_party/Matcha-TTS')
        download_manifest(manifests['cosy'], root / 'models/cosy')
    elif engine == 'qwen':
        download_manifest(manifests[qwen_model], root / 'models' / qwen_model)
    elif engine == 'gpt':
        from dubbing_setup import REV, SOURCE_SHA
        source = root / 'gpt-sovits' / REV
        extract_source(dict(revision=REV, sha256=SOURCE_SHA,
                            url=f'https://codeload.github.com/RVC-Boss/GPT-SoVITS/tar.gz/{REV}'), source)
        download_manifest(manifests['gpt'], source / 'GPT_SoVITS/pretrained_models')
        call([python, HERE / 'native_tts.py', '--prepare-gpt', str(root)])
    probe_device = {'nvidia':'cuda','amd':'cuda','intel':'xpu','cpu':'cpu'}[backend]
    call([python, HERE / 'gpu.py', '--probe', engine, '--device', probe_device])
    call([python, HERE / 'native_tts.py', '--load-check', engine, '--root', root, '--qwen-model', qwen_model])
    packages = subprocess.check_output(pip_command(python,root,'freeze'), text=True)
    (root / f'{engine}-installed-packages.txt').write_text(packages, encoding='utf-8')
    marker.write_text(json.dumps(dict(engine=engine, backend=backend, python=str(python),
                                    qwenModel=qwen_model if engine=='qwen' else None,
                                    modelVersion='v4' if engine=='gpt' else None, modelLoadPassed=True, speechInferencePassed=False), indent=2), encoding='utf-8')
    emit('Setup and model loading passed. Generate a short sample to test voice quality and speed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('engine', choices=['qwen', 'cosy', 'gpt'])
    parser.add_argument('--backend', choices=['auto', 'nvidia', 'amd', 'intel', 'cpu'], default='auto')
    parser.add_argument('--qwen-model', choices=['qwen-small', 'qwen-large'], default='qwen-large')
    args = parser.parse_args()
    try:
        setup(args.engine, args.backend, args.qwen_model)
    except Exception as error:
        emit('Setup failed: ' + str(error))
        sys.exit(1)
