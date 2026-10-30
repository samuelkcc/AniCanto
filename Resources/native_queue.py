"""Durable native-host queue intent, separate from browser selection/rendering.

Reservations are persisted before preparing each task. Closing the application
never automatically launches work at next boot: a fresh explicit Start is needed.
"""
import time
from desktop_state import read,write


def dispatch(app,op,p):
    path=app.root/'studio'/'queue-session.json'
    session=read(path,{})
    if op=='queue-arm':
        session=dict(epoch=p['epoch'],enabled=True,includeAttention=bool(p.get('includeAttention')),attempted=[p['id']],errors=[],created=time.time())
        write(path,session);return session
    if op=='queue-stop':
        session['enabled']=False;write(path,session);return session
    if not session.get('enabled') or session.get('epoch')!=p.get('epoch'):return None
    if any(row.get('status')=='running' for row in app.store.queue):return None
    attempted=set(session.get('attempted',[]))
    # Consult current persisted order each time, including newly appended videos.
    for row in app.store.queue:
        if row['id'] in attempted or row.get('status') not in (('waiting','paused','attention') if session.get('includeAttention') else ('waiting','paused')):continue
        session['attempted'].append(row['id']);write(path,session)
        try:
            if row.get('status')!='paused' and not row.get('output'):
                info=app.dispatch('source-language',dict(id=row['id']))
                if info.get('needsConfirmation'):
                    raise ValueError('Confirm this video’s source language before starting it.')
            app.store.selected=row['id'];app.store.save()
            spec=app.dispatch('start',dict(id=row['id']))
            spec['nativeQueue']=p['epoch'];return spec
        except __import__('source_preparation').SourcePreparationCancelled:
            session['enabled']=False;write(path,session);return None
        except Exception as error:
            # Keep saved progress and files. A failed preparation is actionable,
            # never repeatedly retried in the same session.
            session['errors'].append(dict(id=row['id'],message=str(error)))
            row['queueNotice']=str(error);write(path,session);app.store.save()
    session['enabled']=False;write(path,session);return None
