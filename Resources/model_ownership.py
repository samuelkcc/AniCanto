"""Remember explicit removals when variants share files on disk.

A retained common file is not evidence that every catalogue variant is still
installed. Successful explicit installation/verification restores ownership.
"""
from pathlib import Path
import time
from atomic_files import write_json

def records(root):
    from model_switch import read
    data=read(Path(root)/'studio/model-removals.json',{})
    return data if isinstance(data,dict) else {}

def removed_ids(root,models):
    data=records(root)
    return {r['id'] for r in models if isinstance(data.get(r['id']),dict) and data[r['id']].get('revision')==r.get('revision')}

def mark_removed(root,row):
    data=records(root);data[row['id']]=dict(revision=row.get('revision'),removedAt=time.time())
    write_json(Path(root)/'studio/model-removals.json',data)

def mark_available(root,row):
    data=records(root)
    if row['id'] in data:
        data.pop(row['id']);write_json(Path(root)/'studio/model-removals.json',data)
