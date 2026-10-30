"""Bounded, parseable support export; never runs models or scans arbitrary files."""
import copy,json,platform,re,time,os,sys,subprocess
from pathlib import Path

MAX_JSON=2*1024*1024
RUNTIME_KEYS=('engine','requestedEngine','backend','voiceBackend','device','gpu','textModel','voiceModel','variant','dramaBackend','cudaFailure','hardware','roles','drama3Memory','modelLoadPassed','speechInferencePassed','warnings','analysisFallbackReason')
RECEIPTS=('native-ready.json','gpu-runtime-selection.json','drama-full-cuda-ready.json','drama3-windows-ready.json','gpt-windows-ready.json','cosy-windows-ready.json')
JOB_FILES=('processing-time.json','production-progress.json','report.json','segment-issues.json','normal-script-rescue.json','source-timing-review.json','normal-checks.json','english-overlap.json','concise-dialogue.json','dialogue-delivery-audit.json','translation-brevity.json','natural-repair.json','natural-placement.json','automatic-recovery.json','input-source.json','ocr-status.json','ocr-region.json','ocr-metrics.json','ocr-discovery/ocr-progress.json','frames-pts/ocr-progress.json','source-performance-policy.json','whisper-compute.json','reference-whisper/whisper-compute.json')
SECRET=re.compile(r'(?i)("?(?:api[_-]?key|access[_-]?token|authorization|password|secret)"?\s*[:=]\s*)("[^"\n]*"|[^\s,}\n]+)')

def redact(text):return SECRET.sub(lambda m:m[1]+'"[redacted]"',text)

def bounded_json(data,maximum=MAX_JSON):
    """Keep valid JSON, explicit omission counts, and all scalar error evidence."""
    value=copy.deepcopy(data);omitted=[]
    def encode(v):return json.dumps(v,ensure_ascii=False,indent=2)
    if len(encode(value).encode())<=maximum:return encode(value),omitted
    for _ in range(100):
        candidates=[]
        def visit(v,path):
            if isinstance(v,list):
                if len(v)>2:candidates.append((len(encode(v)),v,path))
                for i,x in enumerate(v):visit(x,path+[str(i)])
            elif isinstance(v,dict):
                for k,x in v.items():visit(x,path+[str(k)])
        visit(value,[])
        if not candidates:break
        _,items,path=max(candidates,key=lambda x:x[0]);before=len(items);keep=max(1,before//4)
        items[:]=items[:keep]+items[-keep:]
        omitted.append(dict(path='/'.join(path),removed=before-len(items),kept='first and last complete entries'))
        result=dict(data=value,exportOmissions=omitted)
        if len(encode(result).encode())<=maximum:return encode(result),omitted
    # One giant scalar/unknown structure is never returned as broken JSON.
    return encode(dict(exportStatus='omitted-too-large',reason='Cannot fit complete structured evidence',originalBytes=len(encode(data).encode()),exportOmissions=omitted)),omitted+[dict(path='',reason='oversize scalar or structure')]

def read(path):
    try:
        if path.stat().st_size>16*1024*1024:return dict(exportStatus='omitted-too-large',bytes=path.stat().st_size)
        return json.loads(path.read_text())
    except (OSError,ValueError,UnicodeError) as e:return dict(exportStatus='unavailable',error=str(e)[:500])

def report(app):
    from conversion_details import build
    root=app.root.resolve();row=app.store.row() or {};manifest=[];parts=[];seen=set()
    def owned(path):
        p=Path(path).resolve();return p if p.is_relative_to(root) else None
    def add(name,text,**meta):
        if name in seen:return
        seen.add(name);parts.extend(['\n===== '+name+' =====',redact(text)])
        manifest.append(dict(section=name,exportedBytes=len(text.encode()),**meta))
    def structured(path,fields=None):
        p=owned(path)
        if not p or not p.is_file():return
        data=read(p)
        if fields and isinstance(data,dict):data={k:data[k] for k in fields if k in data}
        text,omitted=bounded_json(data);add(p.relative_to(root).as_posix(),text,sourceBytes=p.stat().st_size,omissions=omitted)
    structured(root/'source-preparation/current.json')
    current=read(root/'source-preparation/current.json') if (root/'source-preparation/current.json').is_file() else {}
    operation=current.get('operationID','') if isinstance(current,dict) else ''
    if re.fullmatch(r'[A-Za-z0-9-]{1,64}',operation):structured(root/'source-preparation'/operation/'diagnostic.json')
    ready=read(root/'native-ready.json') if (root/'native-ready.json').is_file() else {}
    header=dict(format='AniCanto debug report v2',created=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),platform=app.platform,
                computer=dict(system=platform.system(),release=platform.release(),machine=platform.machine(),python=platform.python_version()),
                project={k:row.get(k) for k in ('id','video','status','stage','message','lastError','resultSummary','processingSeconds','progress','lastEventAt','lastProgressAt','sourceLanguage')},
                runtime={k:ready[k] for k in RUNTIME_KEYS if k in ready})
    try:
        import psutil
        vm=psutil.virtual_memory();proc=psutil.Process()
        header['resourceObservation']=dict(at=time.time(),cpuLogical=psutil.cpu_count(),systemMemoryBytes=vm.total,availableMemoryBytes=vm.available,exportProcessRSSBytes=proc.memory_info().rss,note='Export-process memory is not worker memory; no GPU utilisation measurement inferred.')
        host_id=int(os.environ.get('CANTOSYNC_HOST_PID','0') or 0)
        # The native host passes its PID. Only its directly-owned RPC process
        # may inspect descendants; never enumerate arbitrary user processes.
        if host_id and proc.ppid()==host_id:
            children=[]
            for child in psutil.Process(host_id).children(recursive=True)[:32]:
                if child.pid==proc.pid:continue
                try:
                    cpu=child.cpu_times()
                    children.append(dict(pid=child.pid,parentPID=child.ppid(),name=child.name(),status=child.status(),rssBytes=child.memory_info().rss,cpuUserSeconds=cpu.user,cpuSystemSeconds=cpu.system,createdAt=child.create_time()))
                except (psutil.NoSuchProcess,psutil.AccessDenied):continue
            header['resourceObservation']['ownedProcesses']=children
            header['resourceObservation']['processMeaning']='Snapshot of this native host descendants only; cumulative CPU seconds are not instantaneous CPU percent.'

    except (ImportError,OSError,RuntimeError,ValueError):
        try:
            from studio_core import call
            header['resourceObservation']=dict(at=time.time(),nativeHardware=call('hardware'),processObservation='Process RSS unavailable: optional psutil is not installed; no worker usage inferred.')
        except (OSError,ValueError,RuntimeError):header['resourceObservation']=dict(at=time.time(),status='unavailable')
    if sys.platform=='win32':
        try:
            gpu=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=3)
            header['gpuObservation']=dict(at=time.time(),status='available' if gpu.returncode==0 else 'unavailable',units='memory MiB, utilisation percent',fields=['name','driver','total','used','free','utilisation'],rows=gpu.stdout.strip().splitlines()[:8] if gpu.returncode==0 else [],meaning='Whole GPU snapshot, not attribution to a model or process.')
        except (OSError,subprocess.TimeoutExpired):header['gpuObservation']=dict(at=time.time(),status='unavailable')
    try:
        from storage_capacity import capacity
        header['storageObservation']=dict(at=time.time(),**capacity(root))
    except (OSError,ValueError):header['storageObservation']=dict(status='unavailable')
    add('@header',json.dumps(header,ensure_ascii=False,indent=2))
    for source in app.log_sources():
        ident=source['id']
        if ident=='@conversion':
            text,omitted=bounded_json(build(root,row));add(ident,text,omissions=omitted)
        elif ident.startswith('@'):add(ident,app.log_text(source,512*1024))
        else:
            p=owned(root/ident)
            if not p or not p.is_file():continue
            add(ident,app.log_text(source,512*1024),sourceBytes=p.stat().st_size,truncated=p.stat().st_size>512*1024)
    for name in RECEIPTS:structured(root/name,RUNTIME_KEYS+('name','driver','torchIndex','kernelPassed','cudaVersion','runtimeTool','cudartTool','deviceProbePassed','memory','threads','model','modelVariant','speechVersions','verifiedEngines','fallbackReason'))
    structured(root/'model-selections.json',('text','voice','drama3','speech','referenceSpeech','asr','visual'))
    structured(root/'setup-invalidated.json',('reason','at','id','kind','operation'))
    job=owned(row.get('job') or root/'jobs/nonexistent')
    if job and job.is_relative_to(root/'jobs') and job.is_dir():
        for name in JOB_FILES:structured(job/name)
        # Retain relevant errors from previous attempts, including an OCR failure
        # before Pause/Resume. Read only this selected row's app-owned directory.
        attempts=root/'attempts'/str(row.get('id','nonexistent'))
        if attempts.resolve().is_relative_to(root/'attempts'):
            entries=[]
            for folder in sorted(attempts.iterdir(),key=lambda p:p.stat().st_mtime,reverse=True)[:8] if attempts.is_dir() else []:
                if not owned(folder):continue
                attempt=read(folder/'attempt.json');errors=[]
                log=folder/'process.log'
                if owned(log) and log.is_file():
                    with log.open(errors='replace') as stream:
                        for line in stream:
                            if re.search(r'ocrError|OCR 提示|Traceback|CUDA.*(?:fail|error)|errorCode|"stage"\s*:\s*"(?:錯誤|Error|Failed)',line,re.I):errors.append(line[:6000].rstrip())
                    errors=errors[-24:]
                entries.append(dict(attempt=attempt,relevantErrors=errors))
            text,omitted=bounded_json(entries);add('@attempt-history',text,omissions=omitted)
        files=[]
        for pattern in ('native-drama-request.json','native-drama-server.json','*.generation.json','*.failure.json'):
            files.extend(p for p in job.rglob(pattern) if p.is_file() and p.resolve().is_relative_to(job))
        for p in sorted(set(files),key=lambda p:p.stat().st_mtime,reverse=True)[:24]:structured(p)
    attempt=owned(row.get('attempt',{}).get('path') or root/'attempts/nonexistent')
    if attempt:
        for name in ('attempt.json','conversion-details.json'):structured(attempt/name)
        p=attempt/'workflow.jsonl'
        if owned(p) and p.is_file():add(p.relative_to(root).as_posix(),app.log_text(dict(id=p.relative_to(root).as_posix()),512*1024),sourceBytes=p.stat().st_size,truncated=p.stat().st_size>512*1024)
    add('@export-manifest',json.dumps(dict(sections=manifest,scope='Selected project only. No media/model weights. Dialogue and local paths may be included. Known credential fields are redacted; review before public sharing.',liveMemory='System memory snapshot only; actual worker/GPU utilisation requires separate evidence.'),ensure_ascii=False,indent=2))
    return 'AniCanto — Debug report v2\n'+'\n'.join(parts)+'\n'
