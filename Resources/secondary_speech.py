"""Independent, prompt-free ASR with per-recording checkpoints and bounded resume.

Whisper remains a second recognizer, not a pronunciation certificate. Expected
words never enter the child request. Only this invocation's child is stopped.
"""
from whisper_audio import load as whisper_pcm
import contextlib,hashlib,json,os,platform,queue,subprocess,sys,threading,time
from pathlib import Path

REVISION='whisper-no-prompt-2-checkpointed'
MLX_MODEL='whisper-large-v3-mlx'
ENDPOINT_REVISION='whisper-word-endpoints-1'


def backend(cfg):
    """Auto uses a fully installed MLX model, never an implicit model download."""
    from model_catalog import resolve,choice
    mode=cfg.get('independentAsrBackend','auto')
    if mode not in ('auto','mlx','cpu'):raise ValueError('Unknown independent ASR backend')
    apple=sys.platform=='darwin' and platform.machine() in ('arm64','aarch64')
    if mode=='mlx' and not apple:raise ValueError('Apple MLX independent checking requires Apple Silicon.')
    if apple and mode!='cpu':
        try:
            path=resolve(cfg['storage'],MLX_MODEL)
            return dict(backend='mlx',id=MLX_MODEL,path=str(path),revision=choice(MLX_MODEL)['revision'],runtime='asr-runtime')
        except ValueError:
            if mode=='mlx':raise ValueError('Download Whisper large-v3 · Apple MLX in Preferences before using MLX independent checking.')
    ident=cfg.get('referenceSpeechModel') or 'whisper-large-v3'
    if sys.platform=='win32':
        from whisper_accel import selection
        compute=selection(dict(cfg,speechModel=ident))
        if compute['backend']=='cuda':return dict(backend='cuda',id=ident,path=str(resolve(cfg['storage'],ident)),revision=choice(ident)['revision'],runtime='speech-runtime')
    return dict(backend='cpu',id=ident,path=str(resolve(cfg['storage'],ident)),revision=choice(ident)['revision'],runtime='runtime')


def read_cache(path,key):
    try:row=json.loads(Path(path).read_text())
    except (OSError,ValueError):return None
    if not isinstance(row,dict) or row.get('key')!=key or row.get('status')!='completed':return None
    if not isinstance(row.get('heard'),str) or not isinstance(row.get('language'),str):return None
    return row


def transcribe(w,cfg,folder,audio,auto_language=False):
    return transcribe_batch(w,cfg,[(folder,audio)],auto_language)[0]


def stop_child(p):
    if p.poll() is not None:return
    p.terminate()
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)


def run_batch(cfg,request,python,emit):
    """Stream completion events; heartbeat is not counted as measurable progress."""
    from track_control import check
    q=queue.Queue();last=time.monotonic();started=last;last_heartbeat=last;current=None
    per_item=float(cfg.get('independentAsrItemTimeout',180));total=float(cfg.get('independentAsrBatchTimeout',1200))
    log=Path(request).with_suffix('.log');done=set();failure=None
    with log.open('a') as errors:
        env=os.environ.copy();env.update(PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        p=subprocess.Popen([str(python),'-B',str(Path(__file__).resolve()),str(request)],stdout=subprocess.PIPE,stderr=errors,text=True,env=env)
        def reader():
            try:
                for line in p.stdout:q.put(line)
            finally:q.put(None)
        threading.Thread(target=reader,daemon=True).start()
        try:
            while True:
                check(cfg)
                from normal_policy import finish_requested
                if finish_requested(cfg):
                    failure=dict(reason='finish-requested',key=None);stop_child(p);break
                now=time.monotonic()
                if now-last>per_item or now-started>total:
                    failure=dict(reason='timeout',key=current);stop_child(p);break
                try:line=q.get(timeout=.2)
                except queue.Empty:line=''
                if line is None:break
                if line:
                    try:event=json.loads(line)
                    except ValueError:continue
                    kind=event.get('event')
                    if kind=='started':current=event.get('key');last=now
                    elif kind in ('completed','failed'):
                        done.add(event.get('key'));last=now;current=None
                    elif kind=='loaded':last=now
                    emit(event)
                if now-last_heartbeat>=10:
                    emit(dict(event='heartbeat',seconds=round(now-started),key=current));last_heartbeat=now
            code=p.wait(timeout=5)
            if code and failure is None:failure=dict(reason='process-error',key=current,code=code)
        finally:
            stop_child(p)
            if p.stdout:p.stdout.close()
    return dict(failure=failure,attempted=done,log=str(log))


def transcribe_batch(w,cfg,items,auto_language=False):
    """Reuse identical audio across repair stages; preserve every completed item."""
    if not items:return []
    from runtime_paths import python_for
    from execution_timing import measure
    from track_control import check
    selected=backend(cfg);language=None if auto_language else 'zh';results=[None]*len(items)
    words=bool(cfg.get('_endpointWordTimestamps'));revision=ENDPOINT_REVISION if words else REVISION
    store=Path(cfg['storage'])/'cache/independent-asr';store.mkdir(parents=True,exist_ok=True)
    emit=getattr(w,'emit',None);stage=getattr(w,'secondaryStage','獨立覆聽');rows=[]
    def progress(message,**fields):
        if callable(emit):emit(stage,message,**fields)
    for index,(folder,audio) in enumerate(items):
        identity=[revision,hashlib.sha256(Path(audio).read_bytes()).hexdigest(),selected['id'],selected['revision'],selected['backend'],language]
        key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        row=dict(index=index,key=key,audio=str(audio),cache=str(store/(key+'.json')),localCache=str(folder/'secondary-speech.json'))
        rows.append(row)
    def collect():
        for row in rows:
            if results[row['index']] is not None:continue
            saved=read_cache(row['localCache'],row['key']) or read_cache(row['cache'],row['key'])
            if saved is not None:
                # Cross-stage reuse never supplies the approved words as a prompt.
                if cfg.get('executable') and not saved.get('traditionalConverted'):
                    if words and saved.get('words'):
                        packet='\n'.join([saved['heard'].replace('\n',' ')]+[str(x.get('word','')).replace('\n',' ') for x in saved['words']])
                        converted=subprocess.check_output([cfg['executable'],'--traditional-text'],input=packet.encode(),timeout=30).decode().split('\n')
                        if len(converted)!=len(saved['words'])+1:raise ValueError('Word spelling conversion changed endpoint row count')
                        saved=dict(saved,heard=converted[0],words=[dict(w,word=t) for w,t in zip(saved['words'],converted[1:])],traditionalConverted=True)
                    else:saved=dict(saved,heard=subprocess.check_output([cfg['executable'],'--traditional-text'],input=saved['heard'].encode(),timeout=30).decode(),traditionalConverted=True)
                w.atomic_json(row['localCache'],saved);results[row['index']]=saved
        return sum(r is not None for r in results)
    completed=collect();pending=list({r['key']:r for r in rows if results[r['index']] is None}.values())
    progress(f'獨立覆聽 {completed}/{len(rows)} 句；{selected["backend"].upper()}；已完成結果會逐句保存。',workID='independent-asr',workCompleted=completed,workTotal=len(rows))
    if not pending:return results
    request=Path(items[0][0])/'secondary-speech-request.json';attempted=set();resumes=0
    deadline=time.monotonic()+float(cfg.get('independentAsrBatchTimeout',1200))
    while pending:
        check(cfg)
        remaining=deadline-time.monotonic()
        if remaining<=0:break
        payload=dict(items=pending,model=selected['path'],backend=selected['backend'],modelID=selected['id'],modelRevision=selected['revision'],language=language,storage=cfg['storage'])
        if words:
            payload['wordTimestamps']=True
            # Only endpoint requests add the new deadline/word contract. Old
            # frozen readback requests retain their cache and inference policy.
            deadline_utc=__import__('repair_limits').deadline()
            if deadline_utc is not None:payload['_repairDeadlineUTC']=deadline_utc
        if cfg.get('_trackControl'):payload['_trackControl']=cfg['_trackControl']
        w.atomic_json(request,payload)
        def event(value):
            if value.get('event') in ('completed','failed'):
                n=collect();progress(f'獨立覆聽已保存 {n}/{len(rows)} 句；未確認錄音保留。',workID='independent-asr',workCompleted=n,workTotal=len(rows))
            elif value.get('event')=='heartbeat':
                progress(f'獨立覆聽仍在運作；已保存 {sum(r is not None for r in results)}/{len(rows)} 句；本批已用 {value["seconds"]} 秒。')
        with measure(request.parent,'independent-asr-batch',items=len(pending),model=selected['id'],backend=selected['backend'],modelProcesses=1):
            outcome=run_batch(dict(cfg,independentAsrBatchTimeout=remaining),request,python_for(cfg['storage'],selected['runtime']),event)
        collect();attempted.update(outcome['attempted']);failure=outcome.get('failure')
        if not failure:break
        if failure.get('key'):attempted.add(failure['key'])
        progress('獨立覆聽本批未完成；已保存結果保留，未確認片段唔當作配音失敗。')
        pending=[r for r in rows if results[r['index']] is None and r['key'] not in attempted]
        # A stuck clip must not block later clips. Startup failure is not retried
        # indefinitely; another invocation can resume all still-uncached items.
        if not pending or not failure.get('key') or resumes>=2:break
        resumes+=1;progress(f'接續覆聽剩餘 {len(pending)} 句；跳過本次未完成片段（{resumes}/2）。')
    completed=collect()
    w.atomic_json(request.with_name('secondary-speech-status.json'),dict(revision=REVISION,backend=selected['backend'],actualBackends=sorted({r.get('backend','unknown') for r in results if r is not None}),completed=completed,total=len(rows),remaining=[r['index'] for r in rows if results[r['index']] is None],resumes=resumes,qualityCertified=False))
    return results


def endpoint_words(segments):
    """Normalize native MLX dicts and faster-whisper word objects, without text hints."""
    import math
    result=[]
    def get(obj,key,default=None):return obj.get(key,default) if isinstance(obj,dict) else getattr(obj,key,default)
    for segment in segments or []:
        for row in get(segment,'words',[]) or []:
            try:
                a,b=float(get(row,'start')),float(get(row,'end'));prob=float(get(row,'probability',0))
                text=str(get(row,'word',''))
                if math.isfinite(a+b+prob) and 0<=a<b and text:result.append(dict(word=text,start=a,end=b,probability=prob))
            except (ValueError,TypeError):continue
    return result


def load_transcriber(request):
    if request['backend']=='mlx':
        import mlx.core as mx
        from mlx_audio.stt import load
        from compute_policy import mlx_device
        mlx_device(request.get('storage'),'independent-whisper')
        model=load(request['model'])
        def infer(audio):
            options=dict(word_timestamps=True,return_timestamps=True) if request.get('wordTimestamps') else {}
            result=model.generate(whisper_pcm(audio),language=request.get('language'),condition_on_previous_text=False,initial_prompt=None,temperature=0.,verbose=None,**options)
            answer=dict(heard=result.text.strip(),language=getattr(result,'language','') or '')
            if request.get('wordTimestamps'):answer['words']=endpoint_words(getattr(result,'segments',[]))
            return answer
        return infer
    from faster_whisper import WhisperModel
    def cpu():return WhisperModel(request['model'],device='cpu',compute_type='int8',local_files_only=True,cpu_threads=8)
    if request['backend']=='cuda':
        try:
            import torch,os
            from compute_policy import torch_device
            dll=Path(torch.__file__).parent/'lib'
            if hasattr(os,'add_dll_directory'):dll_handle=os.add_dll_directory(str(dll))
            device=torch_device(torch,request.get('storage'),'independent-whisper',minimum_gb=3.5)
            if not device.startswith('cuda'):raise ValueError('Insufficient supported CUDA memory')
            model=WhisperModel(request['model'],device='cuda',compute_type='int8_float16',local_files_only=True)
        except Exception:
            request['backend']='cpu';model=cpu()
    else:model=cpu()
    def infer(audio):
        nonlocal model
        pcm=whisper_pcm(audio)
        def decode():
            options=dict(word_timestamps=True) if request.get('wordTimestamps') else {}
            segments,info=model.transcribe(pcm,language=request.get('language'),beam_size=5,vad_filter=False,condition_on_previous_text=False,**options)
            segments=list(segments);answer=dict(heard=''.join(s.text for s in segments),language=info.language)
            if request.get('wordTimestamps'):answer['words']=endpoint_words(segments)
            return answer
        try:return decode()
        except Exception:
            # Lazy CUDA execution can fail while consuming segments. Release
            # its model before one CPU retry, including for subsequent items.
            if request['backend']!='cuda':raise
            model=None;request['backend']='cpu';model=cpu();return decode()
    return infer


def process_request(request,infer,send):
    from atomic_files import write_json
    from track_control import check,UserSkipped
    send(dict(event='loaded'))
    for item in request['items']:
        check(request);send(dict(event='started',key=item['key']))
        try:
            with contextlib.redirect_stdout(sys.stderr):result=infer(item['audio'])
            if not isinstance(result.get('heard'),str) or not isinstance(result.get('language'),str):raise ValueError('Incomplete independent speech evidence')
            result.update(key=item['key'],status='completed',method=ENDPOINT_REVISION if request.get('wordTimestamps') else REVISION,backend=request['backend'],model=request['modelID'],modelRevision=request['modelRevision'],languageMode='automatic' if request.get('language') is None else 'zh',conditioning='No expected text, prompt or vocabulary supplied')
            write_json(item['cache'],result);send(dict(event='completed',key=item['key']))
        except UserSkipped:raise
        except Exception as error:
            # An ASR failure is not evidence of a missing voice or wrong words.
            send(dict(event='failed',key=item['key'],error=type(error).__name__))


if __name__=='__main__':
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
    request=json.loads(Path(sys.argv[1]).read_text())
    with contextlib.redirect_stdout(sys.stderr):infer=load_transcriber(request)
    process_request(request,infer,lambda row:print(json.dumps(row,ensure_ascii=False),flush=True))
