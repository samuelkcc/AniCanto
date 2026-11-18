"""Remove finished work and retain undo for unfinished queue entries."""
import sqlite3,time,uuid
from desktop_state import read,write


def detach(store,ids,archive,clean_completed):
    if not isinstance(ids,list) or not ids or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):
        raise ValueError('Select one or more videos from the list.')
    wanted=set(ids);rows=[r for r in store.queue if r['id'] in wanted]
    if len(rows)!=len(wanted):raise ValueError('The video list changed. Review your selection again.')
    if any(r.get('status')=='running' for r in rows):raise ValueError('A processing video cannot be removed from the list.')
    unfinished=[r for r in rows if r.get('status')!='complete']
    completed=[];failed=[]
    for row in rows:
        if row.get('status')!='complete':continue
        # Keep other live references until their own cleanup has succeeded.
        others=[r for r in store.queue if r is not row and r['id'] not in completed]
        try:
            clean_completed(row,others)
        except (OSError,ValueError,RuntimeError,sqlite3.Error) as error:
            failed.append(dict(id=row['id'],reason=str(error)))
        else:
            completed.append(row['id'])
    history=read(archive,[]);batch=None
    if completed:
        for entry in history:
            entry['rows']=[r for r in entry['rows'] if r['id'] not in completed]
        history=[entry for entry in history if entry['rows']]
    if unfinished:
        batch=uuid.uuid4().hex
        history.append(dict(batch=batch,created=time.time(),rows=unfinished,selected=store.selected))
    if completed or batch:write(archive,history)
    removed=set(completed)|{r['id'] for r in unfinished}
    store.queue=[r for r in store.queue if r['id'] not in removed]
    if store.selected in removed:store.selected=next((r['id'] for r in store.queue),None)
    store.save()
    return dict(batch=batch,removedIDs=[i for i in ids if i in removed],completedIDs=completed,failed=failed,
                retainedWork=bool(unfinished))


def restore(store,batch,archive):
    if not isinstance(batch,str):raise ValueError('Choose a saved removal batch.')
    history=read(archive,[]);entry=next((b for b in history if b.get('batch')==batch),None)
    if not entry:raise ValueError('This removal batch is no longer available.')
    existing={r['id'] for r in store.queue};added=[r for r in entry['rows'] if r['id'] not in existing]
    store.queue.extend(added)
    if store.selected is None:
        selected=entry.get('selected')
        store.selected=selected if any(r['id']==selected for r in store.queue) else next((r['id'] for r in added),None)
    store.save()
    return dict(restoredIDs=[r['id'] for r in added])
