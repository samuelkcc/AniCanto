"""Keep saved job and budget identities stable after an explicit data-root relocation."""
import json
from pathlib import Path


def canonical(root, value):
    root=Path(root).resolve()
    try:record=json.loads((root/'data-root-relocation.json').read_text())
    except (OSError,ValueError):return value
    if record.get('schemaVersion')!=1 or record.get('complete') is not True or record.get('newRoot')!=str(root):return value
    old=record.get('oldRoot','')
    if not old or Path(old).parent!=root.parent or Path(old).name not in ('SamCantoSync','CantoSync-Windows'):return value
    def visit(item):
        if isinstance(item,str):return item.replace(str(root),old)
        if isinstance(item,list):return [visit(x) for x in item]
        if isinstance(item,tuple):return tuple(visit(x) for x in item)
        if isinstance(item,dict):return {visit(k):visit(v) for k,v in item.items()}
        return item
    return visit(value)


def for_folder(folder, value):
    folder=Path(folder).resolve()
    for parent in [folder,*folder.parents]:
        if (parent/'data-root-relocation.json').is_file():return canonical(parent,value)
    return value
