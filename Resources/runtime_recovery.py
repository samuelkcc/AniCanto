"""Bounded subprocess recovery. Completed outputs and selected model IDs stay intact."""
import copy,json,re
from pathlib import Path

def recoverable(error):
    return bool(re.search(r'out.of.memory|bad_alloc|insufficient.memory|memory.pressure|mps.*(?:alloc|memory)|metal.*(?:memory|resource)|訊號 (?:9|11|6)|killed|allocation.*failed',str(error),re.I))

def smaller(cfg,action):
    if action not in ('cosy','qwen'):return None
    import model_catalog
    role,key=('cosyvoice3','cosyModel') if action=='cosy' else ('qwen-tts','qwenModel')
    try:current=model_catalog.choice(cfg[key])
    except (KeyError,ValueError):return None
    rows=sorted((r for r in model_catalog.catalog() if r['category']=='voice' and r['engine']==role and r['estimatedMemoryGB']<current['estimatedMemoryGB']),key=lambda r:r['estimatedMemoryGB'],reverse=True)
    for row in rows:
        try:model_catalog.resolve(cfg['storage'],row['id']);return key,row['id']
        except (OSError,ValueError):pass

def run(cfg,action,request,emit,execute):
    from track_control import UserSkipped,check
    try:return execute(cfg,action,request,emit)
    except (RuntimeError,ValueError) as error:
        if isinstance(error,UserSkipped) or not recoverable(error):raise
        if action not in ('tts','cosy','qwen','voxcpm2','wsyue','drama3') or not request.get('items'):raise
        original=error
    check(request)
    # The failed subprocess has exited and released its model before this call.
    alternate=smaller(cfg,action)
    changes={alternate[0]:alternate[1]} if alternate else ({'device':'cpu','gsvDevice':'cpu'} if action=='tts' else {'voxcpmDevice':'cpu'} if action=='voxcpm2' else {})
    from audio_fallback import healthy
    pending=[i for i in request['items'] if not healthy(i['output'])]
    if not pending:raise original
    audit=dict(action=action,reason=str(original),strategy='smaller-local-model' if alternate else 'cpu-single-item' if action in ('tts','voxcpm2') else 'restart-single-item',changes=changes,items=[],status='running')
    folder=Path(request['job']);ledger=folder/'runtime-recovery.json'
    from worker import atomic_json
    history=json.loads(ledger.read_text()) if ledger.exists() else []
    history.append(audit);atomic_json(ledger,history)
    emit('資源自動恢復',f'{len(pending)} 段未完成；模型程序已釋放，改用 '+str(changes or '逐句重新載入')+'。完成錄音保留，最多再試一次。')
    failures=[]
    for item in pending:
        check(request)
        if len(failures)>=2:
            audit['items'].append(dict(original=item['output'],output=item['output'],status='deferred-to-fallback'));continue
        fresh=copy.deepcopy(item)
        if alternate:
            output=Path(item['output']);fresh['output']=str(output.with_name(output.stem+'-recovery-'+alternate[1]+output.suffix))
        elif Path(fresh['output']).exists() and not healthy(fresh['output']):
            output=Path(fresh['output']);fresh['output']=str(output.with_name(output.stem+'-recovery-single'+output.suffix))
        row=dict(original=item['output'],output=fresh['output'],status='running');audit['items'].append(row)
        try:
            retry=dict(request,**changes,items=[fresh])
            execute(dict(cfg,**changes),action,retry,emit)
            if not healthy(fresh['output']):raise RuntimeError('Recovery did not produce usable audio')
            cfg.setdefault('_runtimeReplacements',{})[item['output']]=fresh['output'];row['status']='generated-needs-check'
        except (RuntimeError,ValueError) as error:
            if isinstance(error,UserSkipped):raise
            row.update(status='failed',error=str(error));failures.append(str(error))
        finally:atomic_json(ledger,history)
    audit['status']='partial' if failures else 'generated-needs-check';atomic_json(ledger,history)
    if failures:raise RuntimeError('資源恢復後仍有片段失敗，已保留其餘錄音：'+'；'.join(failures))
