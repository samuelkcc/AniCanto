"""Metadata-only queue removal; work/media files never enter a deletion path."""
import time,uuid
from desktop_state import read,write


def detach(store,ids,archive):
    if not isinstance(ids,list) or not ids or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):
        raise ValueError('Select one or more videos from the list.')
    wanted=set(ids);rows=[r for r in store.queue if r['id'] in wanted]
    if len(rows)!=len(wanted):raise ValueError('The video list changed. Review your selection again.')
    if any(r.get('status')=='running' for r in rows):raise ValueError('A processing video cannot be removed from the list.')
    batch=uuid.uuid4().hex;history=read(archive,[])
    # Archive first: interruption before state save leaves recoverable duplicates,
    # never an unrecoverable row. Restore below deduplicates by identity.
    history.append(dict(batch=batch,created=time.time(),rows=rows,selected=store.selected))
    write(archive,history)
    store.queue=[r for r in store.queue if r['id'] not in wanted]
    if store.selected in wanted:store.selected=next((r['id'] for r in store.queue),None)
    store.save()
    return dict(batch=batch,removedIDs=ids,retainedWork=True)


def restore(store,batch,archive):
    if not isinstance(batch,str):raise ValueError('Choose a saved removal batch.')
    history=read(archive,[]);entry=next((b for b in history if b.get('batch')==batch),None)
    if not entry:raise ValueError('This removal batch is no longer available.')
    existing={r['id'] for r in store.queue};added=[r for r in entry['rows'] if r['id'] not in existing]
    store.queue.extend(added)
    if store.selected is None:store.selected=entry.get('selected') or next((r['id'] for r in store.queue),None)
    store.save()
    return dict(restoredIDs=[r['id'] for r in added])
