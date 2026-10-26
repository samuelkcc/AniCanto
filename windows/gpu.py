"""Windows device policy. Advertising an adapter never proves inference support."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

_shared=Path(__file__).resolve().parent/'shared'
if not _shared.is_dir():_shared=Path(__file__).resolve().parent.parent/'Resources'
sys.path.insert(0,str(_shared))
from hardware_runtimes import POLICY,amd_supported,nvidia as nvidia_runtime
AMD_ROCM_NAMES=tuple(POLICY['amd']['models'])


def adapters():
    if sys.platform != 'win32':
        return []
    command = ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
               'Get-CimInstance Win32_VideoController | Select-Object Name,PNPDeviceID,DriverVersion | ConvertTo-Json -Compress']
    try:
        result = subprocess.run(command, capture_output=True, timeout=20, check=True)
        rows = json.loads(result.stdout.decode('utf-8-sig'))
        return rows if isinstance(rows, list) else [rows]
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def vendor(row):
    name = (row.get('Name', '') + ' ' + row.get('PNPDeviceID', '')).upper()
    if 'NVIDIA' in name or 'VEN_10DE' in name:
        return 'nvidia'
    if 'AMD' in name or 'RADEON' in name or 'VEN_1002' in name:
        return 'amd'
    if 'INTEL' in name or 'VEN_8086' in name:
        return 'intel'
    return 'unknown'


def recommended(rows):
    # A discrete NVIDIA adapter takes priority over an integrated display GPU.
    if any(vendor(row) == 'nvidia' for row in rows):
        return 'nvidia'
    if any(vendor(row) == 'amd' and amd_supported(row.get('Name', '')) for row in rows):
        return 'amd'
    if any(vendor(row) == 'intel' and 'ARC' in row.get('Name', '').upper() for row in rows):
        return 'intel'
    return 'cpu'




def torch_probe(engine='qwen', requested='auto', index=0):
    import torch
    device, backend, name, memory = 'cpu', 'cpu', 'CPU', 0
    if requested in ('auto', 'cuda') and torch.cuda.is_available():
        if not 0 <= index < torch.cuda.device_count():
            raise ValueError('Selected GPU index is unavailable.')
        device = f'cuda:{index}'
        backend = 'rocm' if torch.version.hip else 'cuda'
        name = torch.cuda.get_device_name(index)
        memory = torch.cuda.get_device_properties(index).total_memory / 2**30
        torch.cuda.set_device(index)
    elif requested in ('auto', 'xpu') and engine == 'qwen' and hasattr(torch, 'xpu') and torch.xpu.is_available():
        device, backend = f'xpu:{index}', 'xpu'
        name = torch.xpu.get_device_name(index)
        memory = getattr(torch.xpu.get_device_properties(index), 'total_memory', 0) / 2**30
    elif requested != 'auto' and requested != 'cpu':
        raise RuntimeError(f'{requested} is unavailable for {engine}; select CPU explicitly or fix the GPU runtime.')
    dtype = torch.float32 if device == 'cpu' else torch.float16
    if backend == 'cuda':
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        # Leave space for display/other applications; stages run serially.
        torch.cuda.set_per_process_memory_fraction(.80, index)
    started = time.monotonic()
    with torch.inference_mode():
        a = torch.ones((256, 256), device=device, dtype=dtype)
        result = a @ a
        if backend in ('cuda','rocm'):
            signal=torch.ones((1,1,64),device=device,dtype=dtype);kernel=torch.ones((1,1,3),device=device,dtype=dtype)
            conv=torch.nn.functional.conv1d(signal,kernel)
            if not torch.isfinite(conv).all().item():raise RuntimeError('GPU convolution check failed.')
        if not torch.isfinite(result).all().item() or abs(result[0, 0].item() - 256) > .5:
            raise RuntimeError('GPU calculation check failed.')
        if backend in ('cuda', 'rocm'):
            torch.cuda.synchronize(index)
        elif backend == 'xpu':
            torch.xpu.synchronize(index)
    free_memory=None
    if backend in ('cuda','rocm'):
        try:free_memory=round(torch.cuda.mem_get_info(index)[0]/2**30,2)
        except (RuntimeError,AttributeError):pass
    return dict(torchIndex=('cu'+str(torch.version.cuda).replace('.','')) if backend=='cuda' else None,computeCapability=list(torch.cuda.get_device_capability(index)) if backend=='cuda' else None,compiledArchitectures=torch.cuda.get_arch_list() if backend=='cuda' else None,device=device, backend=backend, name=name, memoryGB=round(memory, 2),freeMemoryGB=free_memory,
                dtype=str(dtype).split('.')[-1], torch=torch.__version__,
                kernelSeconds=round(time.monotonic()-started, 4), kernelPassed=True,
                note='Kernel check only; voice quality and model speed require a real inference test.')


def encoder_options(name):
    return {'h264_nvenc': ['-preset', 'p5', '-rc', 'vbr', '-cq', '20', '-b:v', '0'],
            'h264_amf': ['-quality', 'quality', '-rc', 'cqp', '-qp_i', '20', '-qp_p', '20'],
            'h264_qsv': ['-preset', 'medium', '-global_quality', '20'],
            'libx264': ['-preset', 'veryfast', '-crf', '20']}[name]


def encoder_candidates(rows, preference='auto'):
    if preference == 'software':
        return ['libx264']
    choices = {'nvidia': 'h264_nvenc', 'amd': 'h264_amf', 'intel': 'h264_qsv'}
    if preference in choices:
        return [choices[preference], 'libx264']
    result = []
    for key in ('nvidia', 'amd', 'intel'):
        if any(vendor(row) == key for row in rows):
            result.append(choices[key])
    return result + ['libx264']


def data_root():
    return Path(os.environ.get('CANTOSYNC_WINDOWS_DATA', str(Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'CantoSync-Windows')))


def hardware_snapshot():
    """Physical RAM from the shared native core; adapter discovery remains platform-specific.

    WMI AdapterRAM is deliberately not used as VRAM (it can overflow at 4 GB).
    Only a successful runtime probe supplies usable accelerator memory/backend.
    """
    from studio_core import call
    info=call('hardware')
    info['adapters']=adapters()
    if not info['adapters']:
        info['adapters']=[{'Name':row.get('name',''), 'PNPDeviceID':f"VEN_{int(row.get('vendorId',0)):04X}"}
                          for row in info.get('displayAdapters',[])]
    info['suggestedSetupBackend']=recommended(info['adapters'])
    if sys.platform=='win32' and info['suggestedSetupBackend']=='nvidia':
        try:
            p=subprocess.run(['nvidia-smi','--query-gpu=name,compute_cap,driver_version','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=8,check=True)
            info['cudaCapabilities']=[dict(name=name.strip(),computeCapability=float(cc.strip()),driverVersion=driver.strip()) for line in p.stdout.splitlines() if line.count(',')>=2 for name,cc,driver in [line.rsplit(',',2)]]
        except (OSError,ValueError,subprocess.SubprocessError):info['cudaCapabilities']=[]
    return info


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', choices=['qwen', 'cosy', 'gpt'])
    parser.add_argument('--device', default='auto')
    parser.add_argument('--index', type=int, default=0)
    args = parser.parse_args()
    try:
        print(json.dumps(torch_probe(args.probe, args.device, args.index) if args.probe else
                         dict(adapters=adapters(), recommendation=recommended(adapters())), ensure_ascii=False))
    except Exception as error:
        print(json.dumps(dict(error=str(error)), ensure_ascii=False))
        sys.exit(1)


def planning_hardware():
    """Driver VRAM is only a planning hint; setup still requires a Torch kernel probe."""
    h=hardware_snapshot()
    wanted=h.get('suggestedSetupBackend')
    vendor_id={'nvidia':0x10DE,'amd':0x1002}.get(wanted)
    if vendor_id:
        candidates=[row for row in h.get('displayAdapters',[])
                    if row.get('vendorId')==vendor_id and
                    (wanted!='amd' or amd_supported(row.get('name',''))) and
                    float(row.get('dedicatedMemoryGB') or 0)>0]
        if candidates:
            chosen=max(candidates,key=lambda row:float(row['dedicatedMemoryGB']))
            h.update(backend='cuda' if wanted=='nvidia' else 'rocm',
                     acceleratorMemoryGB=float(chosen['dedicatedMemoryGB']),acceleratorName=chosen.get('name',''),
                     inferenceVerified=False,memorySource='DXGI dedicated video memory; kernel not yet tested')
            return apply_runtime_selection(h)
    if sys.platform=='win32' and h['suggestedSetupBackend']=='nvidia':
        try:
            result=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10,check=True)
            name,amount=next(x.rsplit(',',1) for x in result.stdout.splitlines() if x.strip())
            gib=float(amount.strip())/1024
            h.update(backend='cuda',acceleratorName=name.strip(),acceleratorMemoryGB=gib,inferenceVerified=False,memorySource='nvidia-smi; kernel not yet tested')
        except (OSError,ValueError,subprocess.SubprocessError):pass
    return apply_runtime_selection(h)


def apply_runtime_selection(h):
    if h.get('backend')!='cuda':return h
    cap=next((x for x in h.get('cudaCapabilities',[]) if x['name'].upper()==h.get('acceleratorName','').upper()),{})
    if cap.get('computeCapability') is not None:h['cudaComputeCapability']=cap['computeCapability']
    if cap.get('driverVersion'):h['cudaDriverVersion']=cap['driverVersion']
    try:
        saved=json.loads((data_root()/'gpu-runtime-selection.json').read_text())
        if saved.get('name')==h.get('acceleratorName') and saved.get('driver')==h.get('cudaDriverVersion'):
            if saved.get('kernelPassed') is True:h['selectedTorchIndex']=saved['torchIndex']
            elif saved.get('torchIndex')=='cpu':
                h.update(backend='cpu',detectedBackend='cuda',suggestedSetupBackend='cpu',gpuCompatibilityReason='The GPU runtime check failed on this card and driver. The verified CPU fallback remains selected.')
    except (OSError,ValueError,KeyError):pass
    return h
