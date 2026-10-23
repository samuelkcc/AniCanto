"""Welcome package controls; only catalog-owned files in the app data root."""
import json,shutil
from pathlib import Path
RUNTIMES=('worker','analysis','asr','gpt','cosy','local')

def safe_path(root,relative):
    root=Path(root).resolve();path=root/relative
    if not path.resolve().is_relative_to(root) or path.resolve()==root:raise ValueError('Invalid package path')
    return path

def inventory(root,catalog,downloads=()):
    from native_setup import complete,folder
    root=Path(root);required={r['id'] for r in downloads};rows=[]
    for row in catalog:
        if not row.get('nativeFormat'):continue
        path=folder(root,row);ready=complete(root,row)
        if row['id'] in required or path.exists():
            saved=sum(min(f['size'],(path/f['path']).stat().st_size) if (path/f['path']).is_file() else min(f['size'],(path/(f['path']+'.partial')).stat().st_size) if (path/(f['path']+'.partial')).is_file() else 0 for f in row['files'])
            rows.append(dict(id=row['id'],title=row['title'],kind='model',bytes=row['bytes'],savedBytes=saved,installed=ready,required=row['id'] in required))
    for name in RUNTIMES:
        exists=(root/'runtimes'/name/'Scripts/python.exe').is_file()
        if exists:rows.append(dict(id=name,title=name+' runtime',kind='runtime',installed=True,bytes=None))
    return rows

def remove(root,kind,ident,catalog):
    root=Path(root)
    def erase(relative):
        path=safe_path(root,relative)
        if path.is_symlink() or path.is_file():path.unlink()
        elif path.is_dir():shutil.rmtree(path)
    if kind=='tool':
        from drama_full_cuda import TOOLS
        if ident not in ('drama-cuda','drama-cudart')+TOOLS:raise ValueError('Unknown managed tool')
        if ident in TOOLS:
            erase('tools/'+ident);erase('drama-full-cuda-ready.json')
            # Removing an unused CUDA download must not invalidate a working CPU installation.
            try:current=json.loads((root/'drama3-windows-ready.json').read_text())
            except (OSError,ValueError):current={}
            if current.get('backend')=='cuda':
                erase('drama3-windows-ready.json');erase('native-ready.json')
                (root/'setup-invalidated.json').write_text(json.dumps(dict(kind=kind,id=ident)))
            return
        erase('tools/'+ident);erase('tools/drama-small-cuda');erase('drama3-windows-ready.json');erase('native-ready.json')
        (root/'setup-invalidated.json').write_text(json.dumps(dict(kind=kind,id=ident)))
        return
    if kind=='runtime':
        if ident not in RUNTIMES:raise ValueError('This runtime cannot be removed while the desktop is open.')
        erase('runtimes/'+ident);erase(ident+'-runtime-ready.json')
        for marker in ['native-ready.json',('separator' if ident=='analysis' else ident)+'-windows-ready.json']:erase(marker)
        (root/'setup-invalidated.json').write_text(json.dumps(dict(kind=kind,id=ident)))
        return
    row=next((r for r in catalog if r['id']==ident and r.get('nativeFormat')),None)
    if kind!='model' or row is None:raise ValueError('Unknown local package')
    from native_setup import folder,complete
    others={str(folder(root,r)/f['path']) for r in catalog if r['id']!=ident and r.get('nativeFormat') and complete(root,r) for f in r['files']}
    for file in row['files']:
        path=folder(root,row)/file['path']
        if str(path) not in others:
            erase(path);erase(str(path)+'.partial')
    erase('model-ready/'+ident.replace(':','-')+'.json');erase('native-ready.json')
    (root/'setup-invalidated.json').write_text(json.dumps(dict(kind=kind,id=ident)))

WARNINGS={
 'native-drama-full-cuda-needs-probe':('Full Drama 3 will use NVIDIA CUDA with CPU/RAM offload. Memory figures are estimates; deployment must pass a real speech test.','完整 Drama 3 會使用 NVIDIA CUDA，部分資料仍放喺 CPU／RAM。記憶體數值屬估算；部署必須通過實際配音測試。'),
 'native-drama-small-cuda-planned':('Drama3-small will try NVIDIA CUDA. Setup must pass a real speech test before GPU use is confirmed. Cantonese quality is experimental.','Drama3-small 會嘗試 NVIDIA CUDA；要實際生成測試通過先會確認 GPU 可用。廣東話效果屬實驗性。'),
 'native-drama-small-cpu-fallback':('Drama3-small is selected to keep Drama as your voice engine. This build uses CPU; Cantonese quality is experimental. Your NVIDIA GPU remains available for the other models.','會用 Drama3-small 保留 Drama 配音引擎。此版本使用 CPU，廣東話效果屬實驗性；其他模型仍可使用 NVIDIA GPU。'),
 'native-drama-cuda-unavailable-fallback-gpt-v2-pro-plus':('This package has no full Drama 3 CUDA adapter. GPT is the available fallback; this does not mean your GPU is too slow.','此版本未提供完整 Drama 3 CUDA 接法，會使用可用嘅 GPT 後備；唔代表顯示卡太慢。'),
 'native-drama-cpu-explicit-slow-path':('Drama 3 will run on the CPU and can be slow.','Drama 3 會用 CPU 執行，速度可能較慢。'),
 'visual-analysis-unavailable-use-audio-roles':('Role analysis will use audio because the visual model exceeds the memory budget.','畫面模型超出記憶體預算，角色分析會使用聲音。'),
}
def warning(code,language='en'):
    return WARNINGS.get(code,(code.replace('-',' '),code.replace('-',' ')))[language=='zh-HK']
