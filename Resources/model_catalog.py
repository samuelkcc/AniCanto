"""Pinned local model variants and independently persisted deployment selections."""
import json,sys
from pathlib import Path
DEFAULTS={'text':'mlx:qwen3.5-35b-a3b:4bit','asr':'asr-1.7b-bf16','speech':'whisper-large-v3','referenceSpeech':'whisper-small'}
def catalog():
    rows=json.loads(Path(__file__).with_name('model-options.json').read_text())
    if sys.platform=='win32':
        native=Path(__file__).resolve().parent.parent/'native-models.json'
        if not native.is_file():native=Path(__file__).resolve().parent.parent/'windows/native-models.json'
        rows+=json.loads(native.read_text(encoding='utf-8'))
    return rows
def choice(ident):
    row=next((r for r in catalog() if r['id']==ident),None)
    if row is None:raise ValueError('未知模型版本：'+str(ident))
    return row

def selected(root,role):
    p=Path(root)/'model-selections.json'
    return (json.loads(p.read_text()).get(role) if p.exists() else None) or ('asr-native-1.7b' if sys.platform=='win32' and role=='asr' else DEFAULTS[role])
def folder(root,row):return Path(root)/(row.get('legacy') or (('models/voice-variants/' if row['category']=='voice' else 'models/variants/')+row['id'].replace(':','-')))
def resolve(root,ident):
    row=choice(ident);path=folder(root,row)
    if not row['files'] or not row['bytes']:raise ValueError('此模型版本未有已驗證下載檔案：'+row['title'])
    if not all((path/f['path']).is_file() and (not f.get('size') or (path/f['path']).stat().st_size==f['size']) for f in row['files']):raise ValueError('所選模型未下載完整：'+row['title'])
    return path

def install(root,ident):
    from dubbing_setup import download,emit
    import shutil
    root=Path(root);row=choice(ident)
    from engine_availability import require
    require(row.get('engine'),root)
    if row.get('retired'):raise ValueError('This model is retired and cannot be downloaded.')
    if not row['files'] or not row['bytes']:raise ValueError('此模型版本未有已驗證下載檔案：'+row['title'])
    if row.get('licenseReviewRequired'):raise ValueError('This model conversion has no confirmed license. Choose a reviewed variant, such as Qwen 9B or 35B.')
    from model_licenses import install_notices
    install_notices(row,folder(root,row))
    root.mkdir(parents=True,exist_ok=True);path=folder(root,row)
    required=sum(max(0,f['size']-((path/(f['path']+'.partial')).stat().st_size if (path/(f['path']+'.partial')).exists() else 0)) for f in row['files'] if not (path/f['path']).exists())
    if shutil.disk_usage(root).free<required+2_000_000_000:raise ValueError('可用儲存空間不足，模型以外需預留 2 GB。')
    for i,f in enumerate(row['files']):
        emit(f'{row["title"]} · {i+1}/{len(row["files"])} · {f["path"]}')
        download(f'https://huggingface.co/{row["repo"]}/resolve/{row["revision"]}/{f["path"]}',path/f['path'],f['sha'],expected_size=f['size'])
    resolve(root,ident)
    from model_ownership import mark_available
    mark_available(root,row)
    markers=root/'model-ready';markers.mkdir(exist_ok=True)
    (markers/(ident.replace(':','-')+'.json')).write_text(json.dumps(dict(id=ident,revision=row['revision'])))
    return path
