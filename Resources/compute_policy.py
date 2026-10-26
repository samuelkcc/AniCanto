"""Stage-local hardware decisions; integrated/shared memory is not dedicated VRAM."""
import json,os,sys
from pathlib import Path
GIB=1024**3

def system_memory_gb():
 try:
  if sys.platform=='win32':
   import ctypes
   class Memory(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in ('total','available','pageTotal','pageAvailable','virtualTotal','virtualAvailable','extended')]
   state=Memory();state.length=ctypes.sizeof(state)
   if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):return 0.
   return state.total/GIB
  return os.sysconf('SC_PHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')/GIB
 except (ValueError,OSError,AttributeError):return 0.


def budgets(ram_gb,vram_gb=0,free_vram_gb=None,dedicated=False):
 ram=max(0,float(ram_gb));vram=max(0,float(vram_gb));reserve=max(8.,ram*.15)
 free=vram if free_vram_gb is None else max(0,float(free_vram_gb))
 gpu=min(vram*.80,max(0,free-max(.5,vram*.1))) if dedicated else 0.
 return dict(systemCapacityGB=ram,systemReserveGB=reserve,systemBudgetGB=max(0,ram-reserve),dedicatedVRAMGB=vram if dedicated else 0.,freeVRAMGB=free if dedicated else None,acceleratorBudgetGB=round(gpu,3),sharedMemoryIsAdditionalVRAM=False)


def record(root,stage,value):
 if not root:return
 from atomic_files import write_json
 folder=Path(root)/'compute-status';folder.mkdir(parents=True,exist_ok=True)
 safe=''.join(c for c in stage if c.isalnum() or c in '-_')
 write_json(folder/(safe+'.json'),dict(stage=stage,**value))


def mlx_device(root=None,stage='mlx'):
 import mlx.core as mx
 available=bool(mx.metal.is_available());mx.set_default_device(mx.gpu if available else mx.cpu)
 info=mx.metal.device_info() if available else {}
 recommended=int(info.get('max_recommended_working_set_size') or info.get('recommendedMaxWorkingSetSize') or 0)
 # Cap cache, not model weights. The allocator remains below Apple's advised
 # working set; unified memory is shared with macOS, never counted twice.
 if recommended:
  mx.set_memory_limit(int(recommended*.9));mx.set_cache_limit(min(GIB,int(recommended*.1)))
 result=dict(backend='metal' if available else 'cpu',configured=True,recommendedWorkingSetGB=round(recommended/GIB,3) if recommended else None,modelInferencePassed=False)
 record(root,stage,result);return result


def torch_device(torch,root=None,stage='torch',requested='auto',minimum_gb=0):
 requested=str(requested);device='cpu';reason='No supported accelerator in this runtime';pool=None
 if requested=='cpu':reason='CPU explicitly selected'
 elif torch.cuda.is_available():
  index=int(requested.split(':')[1]) if ':' in requested else 0
  free,total=torch.cuda.mem_get_info(index);pool=budgets(system_memory_gb(),total/GIB,free/GIB,True)
  compatible=True
  if not getattr(torch.version,'hip',None):
   try:
    major,minor=torch.cuda.get_device_capability(index);arches=torch.cuda.get_arch_list()
    # CUDA cubin forward compatibility applies within one major architecture;
    # PTX availability is not assumed from a driver reporting CUDA support.
    compatible=any(a.startswith('sm_') and a[3:].isdigit() and int(a[3:])//10==major and int(a[3:])<=major*10+minor for a in arches)
   except (AttributeError,RuntimeError,ValueError):compatible=False
  if not compatible:reason='GPU architecture is absent from this pinned runtime; CPU fallback'
  if compatible and pool['acceleratorBudgetGB']>=minimum_gb:
   device=f'cuda:{index}';reason='ROCm runtime' if getattr(torch.version,'hip',None) else 'NVIDIA CUDA runtime'
   if not getattr(torch.version,'hip',None):torch.cuda.set_per_process_memory_fraction(max(.05,min(.8,pool['acceleratorBudgetGB']*GIB/total)),index)
  elif compatible:reason='Available VRAM is below this stage estimate; CPU fallback'
 elif sys.platform=='darwin' and hasattr(torch.backends,'mps') and torch.backends.mps.is_available():device='mps';reason='Apple Metal MPS'
 value=dict(backend='metal-mps' if device=='mps' else 'rocm' if device.startswith('cuda') and getattr(torch.version,'hip',None) else 'cuda' if device.startswith('cuda') else 'cpu',device=device,reason=reason,memoryEstimateGB=minimum_gb,memory=pool,configured=True,modelInferencePassed=False)
 record(root,stage,value);return device


def summary(root):
 root=Path(root);rows=[]
 for path in sorted((root/'compute-status').glob('*.json')):
  try:data=json.loads(path.read_text())
  except (OSError,ValueError):continue
  if isinstance(data,dict):rows.append(data)
 return dict(rows=rows,scope='Latest saved stage decisions; not a live utilisation meter',policy='Use verified available acceleration; keep system/display headroom; integrated memory is not additional dedicated VRAM')
