"""Persistent per-attempt evidence; terminal summaries never erase a failure."""
import copy,json,time,uuid
from pathlib import Path
ERROR_STAGES={'錯誤','批量錯誤','Error','error','Failed','失敗'}
STATUS_CODES={0xC0000135:('missing-dll','A required Windows runtime DLL could not be loaded. Repair the runtime in Welcome.'),0xC000001D:('unsupported-instruction','The process used a CPU instruction unavailable on this PC.'),0xC0000005:('native-crash','A native component crashed. The full process log is retained.'),0xC0000409:('native-crash','Windows stopped a native component after a runtime error.')}
def failure(event):
    stage=str(event.get('stage',''))
    if stage in ERROR_STAGES or stage.endswith('錯誤') or event.get('error'):
        return dict(code=event.get('errorCode','worker-error'),message=str(event.get('error') or event.get('message') or stage),stage=stage,at=time.time())
    return None

def exit_failure(code,log='',error_string=''):
    unsigned=code & 0xffffffff
    key,message=STATUS_CODES.get(unsigned,('process-exit',f'Conversion process exited with code {code}.'))
    detail=(log.strip()[-6000:] or error_string.strip())
    return dict(code=key,message=message+('\n'+detail if detail else ''),exitCode=code,at=time.time())

def start(root,row,action,request):
    folder=Path(root)/'attempts'/row['id']/uuid.uuid4().hex;folder.mkdir(parents=True,exist_ok=True)
    record=dict(id=folder.name,action=action,request=str(request),video=row['video'],startedAt=time.time(),status='running',path=str(folder))
    (folder/'attempt.json').write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8')
    try:
        from conversion_details import start as conversion_start
        conversion_start(root,row,request,record)
    except (OSError,ValueError,TypeError,KeyError) as error:record['conversionDetailsWarning']=str(error)[:500]
    row.update(attempt=record,lastError=None,outputThisAttempt=None,resultSummary='',partial=False,workflowSequence=0,workflowSignature=None)
    return record

def finish(root,row,code,paused=False,stderr='',error_string='',success_without_movie=False):
    attempt=row.get('attempt',{});diagnostic=copy.deepcopy(row.get('lastError'))
    if not paused and not diagnostic and (code or (not success_without_movie and not row.get('outputThisAttempt'))):
        diagnostic=exit_failure(code,stderr,error_string) if code else dict(code='no-output',message='The worker ended without publishing a movie. Check the retained result summary and process log.',at=time.time())
        row['lastError']=diagnostic
    if attempt:
        path=Path(attempt['path']);attempt.update(endedAt=time.time(),exitCode=code,status='paused' if paused else 'failed' if diagnostic else 'exported' if row.get('outputThisAttempt') else 'finished' if success_without_movie else 'review',error=diagnostic)
        (path/'attempt.json').write_text(json.dumps(attempt,ensure_ascii=False,indent=2),encoding='utf-8')
    return diagnostic
