"""Explicit, archived queue-state reset. Never delete user media or old jobs."""
import copy,hashlib,json,time,uuid
from pathlib import Path

def token(row):return hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def preview(row):
 return dict(id=row['id'],video=row['video'],token=token(row),defaults='current-production-defaults',preserved=[row[k] for k in ('output','review','job') if row.get(k)])
def reset(studio,row,confirmation):
 if any(r.get('status')=='running' for r in studio.store.queue):raise ValueError('Pause processing before resetting a video.')
 if not isinstance(confirmation,str) or confirmation!=token(row):raise ValueError('The video state changed. Review the reset again.')
 from atomic_files import write_json
 from native_queue import dispatch as queue_dispatch
 from desktop_state import read
 nonce=uuid.uuid4().hex;archive=studio.root/'studio/reset-history'/nonce/'state.json'
 write_json(archive,dict(schemaVersion=1,createdAt=time.time(),row=copy.deepcopy(row),selected=studio.store.selected,defaultsScope='current-production-defaults',queueSession=read(studio.root/'studio/queue-session.json',{})))
 fresh=dict(id=row['id'],video=row['video'],status='waiting',progress=0,resetToken=nonce,resetArchive=str(archive))
 index=next(i for i,r in enumerate(studio.store.queue) if r['id']==row['id']);studio.store.queue[index]=fresh;studio.store.selected=row['id']
 studio.store.ui.update(autoQueue=False,autoQueueAttention=False);queue_dispatch(studio,'queue-stop',{});studio.store.save()
 return dict(state=studio.state(),archive=str(archive),reset=True)
