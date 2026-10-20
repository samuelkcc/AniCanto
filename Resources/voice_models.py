"""Pinned, explicit voice-model selection. Missing selection never falls back."""
import json,sys
from pathlib import Path
DEFAULTS={'qwen-tts':'qwen-0.6b-4bit','cosyvoice3':'cosy-native-0.5b','voxcpm2':'voxcpm2-2b-bf16','wsyue':'wsyue-cosy2-zjg','drama3':'drama3-35b-4bit'}
def catalog():
    rows=json.loads(Path(__file__).with_name('voice-models.json').read_text())
    if sys.platform=='win32':
        rows=[r for r in rows if r.get('platform')!='darwin']
        from model_catalog import catalog as models
        rows += [r for r in models() if r.get('nativeFormat') and r.get('category')=='voice']
    return rows
def choice(engine,variant=None):
    variant=variant or DEFAULTS[engine]
    for row in catalog():
        if row['id']==variant and row['engine']==engine:return row
    raise ValueError('配音模型版本無效：'+str(variant))
def folder(root,row):
    return Path(root)/(row.get('legacy') or ('models/voice-variants/'+row['id']))
def resolve(root,engine,variant=None):
    row=choice(engine,variant);path=folder(root,row)
    if not all((path/f['path']).is_file() and (not f.get('size') or (path/f['path']).stat().st_size==f['size']) for f in row['files']):raise ValueError(f'未下載所選模型 {row["title"]}；請到模型中心下載，或由處理流程尋找已安裝嘅相容版本。')
    return path

def install_files(root,engine,variant,download,emit):
    row=choice(engine,variant);path=folder(root,row)
    from engine_availability import require
    require(row.get('engine'),root)
    if row.get('retired'):raise ValueError('This model is retired and cannot be downloaded.')
    from model_licenses import install_notices
    install_notices(row,path)
    for i,file in enumerate(row['files']):
        emit(f'下載／校驗 {row["title"]} · {i+1}/{len(row["files"])}：{file["path"]}')
        download(f'https://huggingface.co/{row["repo"]}/resolve/{row["revision"]}/{file["path"]}',path/file['path'],file['sha'],expected_size=file.get('size'))
    return row,path

def mark_ready(root,row):
    from model_ownership import mark_available
    mark_available(root,row)
    path=Path(root)/'voice-model-ready';path.mkdir(exist_ok=True)
    (path/(row['id']+'.json')).write_text(json.dumps(dict(id=row['id'],revision=row['revision'])))
