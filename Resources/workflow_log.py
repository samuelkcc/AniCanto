"""Human-readable persistent event journal alongside the untouched raw process log."""
import json,time
from pathlib import Path


def folder(root,row):
    root=Path(root).resolve();value=row.get('attempt',{}).get('path')
    if not value:return None
    path=Path(value).resolve()
    return path if path.is_relative_to(root/'attempts') and path!=root/'attempts' else None


def record(root,row,event,language=None):
    stage=str(event.get('stage') or '').strip();message=str(event.get('message') or event.get('error') or '').strip()
    if not stage and not message:return
    path=folder(root,row)
    if path is None:return
    now=time.time();row['lastEventAt']=now
    progress=[stage,event.get('workID'),event.get('workCompleted'),event.get('workTotal'),event.get('progress')]
    if progress!=row.get('activitySignature'):
        row.update(activitySignature=progress,lastProgressAt=now)
    signature=[stage,message,language]
    if row.get('workflowSignature')==signature:return
    sequence=int(row.get('workflowSequence',0))+1
    entry=dict(sequence=sequence,at=time.time(),stage=stage,message=message,error=bool(event.get('error') or stage.lower() in ('error','failed','錯誤','失敗')))
    if language in ('en','zh-HK'):
        from workflow_localization import present
        entry.update(present(stage,message,language),language=language,originalStage=stage,originalMessage=message)
    path.mkdir(parents=True,exist_ok=True)
    with (path/'workflow.jsonl').open('a',encoding='utf-8') as out:out.write(json.dumps(entry,ensure_ascii=False)+'\n')
    row.update(workflowSignature=signature,workflowSequence=sequence)


def summary(root,row,language='en',limit=262144):
    path=folder(root,row);entries=[]
    if path:
        journal=path/'workflow.jsonl'
        source=journal if journal.is_file() else path/'process.log'
        if source.is_file():
            with source.open('rb') as stream:
                size=source.stat().st_size;stream.seek(max(0,size-limit));raw=stream.read(limit).decode('utf-8','replace')
            for line in raw.splitlines():
                try:event=json.loads(line)
                except ValueError:continue
                if isinstance(event,dict) and (event.get('stage') or event.get('message')):entries.append(event)
    if not entries and row:entries=[dict(stage=row.get('stage',''),message=row.get('message') or row.get('status',''))]
    result=[];last=None
    for index,event in enumerate(entries,1):
        stage=str(event.get('stage') or '');message=str(event.get('message') or event.get('error') or '')
        if [stage,message]==last:continue
        last=[stage,message]
        at=event.get('at');stamp=time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime(at)) if isinstance(at,(int,float)) else ('時間未記錄' if language=='zh-HK' else 'time not recorded')
        number=event.get('sequence',index)
        result.append(f'{number:03d} | {stamp} | {stage} | '+message.replace('\n',' · '))
    return '\n'.join(result)[-limit:]
