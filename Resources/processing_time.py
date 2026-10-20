"""Persist active processing time; a heartbeat survives abrupt pause/termination."""
import functools,json,threading,time,uuid
from pathlib import Path
from atomic_files import write_json
_lock=threading.RLock()
_active=None

def persist(path,value):
    """Timing is optional telemetry, never a reason to stop a media task."""
    try:
        write_json(path,value)
        return True
    except OSError as error:
        warnings=_active.setdefault('writeWarnings',set()) if _active is not None else set()
        if str(path) not in warnings:
            warnings.add(str(path))
            print(json.dumps(dict(stage='時間紀錄',message='轉換繼續；未能儲存時間紀錄：'+str(error)),ensure_ascii=False),flush=True)
        return False

def category(stage):
    if stage.startswith('AI '):return 'verification'
    if any(x in stage for x in ('場景理解','場景改編','字幕對齊','場景補稿','翻譯','改稿','英文配音稿','口語')):return 'script'
    if any(x in stage for x in ('日語','日文辨識','語音辨識')):return 'recognition'
    if any(x in stage for x in ('角色','聲線','畫面分析','逐句聲音配對','逐句參考')):return 'roles'
    if any(x in stage for x in ('覆聽','配音核對','驗證','配音覆核')):return 'verification'
    if any(x in stage for x in ('配音','音軌','生成聲音','試聽','語速')):return 'voice'
    if any(x in stage for x in ('分離','原聲表演','原聲音效')):return 'separation'
    if any(x in stage for x in ('合成','輸出','影片加速','封裝')):return 'export'
    return 'preparation'

def checkpoint(job=None,stage=None):
    global _active
    with _lock:
        if _active is None:return
        if job and _active['folder'] is None:
            _active['folder']=Path(job)
            try:prior=json.loads((_active['folder']/'processing-time.json').read_text())
            except (OSError,ValueError):prior={}
            _active['base']=float(prior.get('seconds',0));_active['runs']=prior.get('runs',[])
            _active['categories']=dict(prior.get('categorySeconds',{}))
            _active['legacyTimingUnverified']=bool(prior.get('legacyTimingUnverified') or (prior.get('seconds',0)>0 and prior.get('accountingVersion',0)<2))
        if _active['folder'] is None:return
        now=time.monotonic()
        elapsed_category=max(0,now-_active['categoryStart'])
        previous=_active['category']
        _active['categories'][previous]=_active['categories'].get(previous,0)+elapsed_category
        _active['categoryStart']=now
        if stage:_active['category']=category(stage)
        elapsed=max(0,time.monotonic()-_active['start'])
        from production_progress import snapshot
        journey=snapshot()
        path=_active['folder']/'processing-time.json'
        row=dict(id=_active['id'],seconds=elapsed,status=_active['status'],startedAt=_active['wallStart'],updatedAt=time.time())
        obj=dict(accountingVersion=2,excludesPausedTime=True,includesLoadingWaitingAndRetries=True,currentRunSeconds=elapsed,seconds=_active['base']+elapsed,runs=_active['runs']+[row],categorySeconds=_active['categories'],updated=time.time(),precisionSeconds=2)
        obj['legacyTimingUnverified']=_active.get('legacyTimingUnverified',False)
        if journey:obj['milestones']=journey['milestones']
        persist(path,obj)

def measured(fn):
    @functools.wraps(fn)
    def wrapped(request,*args,**kwargs):
        global _active
        with _lock:
            nested=_active is not None
        if nested:return fn(request,*args,**kwargs)
        from production_progress import reset
        reset()
        with _lock:
            folder=Path(request['review']).parent if request.get('review') else None
            now=time.monotonic()
            _active=dict(folder=None,wallStart=time.time(),start=now,base=0,runs=[],id=uuid.uuid4().hex,status='running',category='preparation',categoryStart=now,categories={})
        stopped=threading.Event()
        def beat():
            while not stopped.wait(2):
                try:checkpoint()
                except OSError:pass
        thread=threading.Thread(target=beat,daemon=True);thread.start()
        try:
            if folder:checkpoint(folder)
            result=fn(request,*args,**kwargs)
            with _lock:_active['status']='finished'
            return result
        except BaseException:
            with _lock:_active['status']='interrupted'
            raise
        finally:
            stopped.set();thread.join(timeout=3)
            try:
                checkpoint()
                if _active['folder'] is not None:
                    report=_active['folder']/'report.json'
                    if report.is_file():
                        fresh=report.stat().st_mtime>=_active['wallStart']
                        data=json.loads(report.read_text());data['processingSeconds']=_active['base']+max(0,time.monotonic()-_active['start']);data['categorySeconds']=_active['categories']
                        from production_progress import snapshot
                        journey=snapshot()
                        if journey:data['milestones']=journey['milestones']
                        persist(report,data)
                        # Keep per-export timing inside the app-managed project.
                        # Do not relabel an older export after an interrupted rerun.
                        if fresh and _active['status']=='finished':
                            try:record=json.loads((_active['folder']/'processing-time.json').read_text())
                            except (OSError,ValueError):record=dict(seconds=data['processingSeconds'],categorySeconds=_active['categories'],runs=[])
                            record.update(output=data.get('exportedOutput') or data.get('output'),completedAt=time.time(),excludesPausedTime=True)
                            # Timing belongs to this removable project, not
                            # beside the user's exported movie.
                            persist(_active['folder']/'export-timing.json',record)
                    labels={'script':'LLM 改稿','recognition':'日語辨識','roles':'角色分析','verification':'聲音覆核','voice':'配音生成','separation':'音訊分離','export':'影片輸出','preparation':'準備／其他'}
                    summary='；'.join(labels[k]+f' {v:.1f} 秒' for k,v in _active['categories'].items() if v>=1)
                    print(json.dumps(dict(stage='耗時摘要',message=summary or '處理時間少於 1 秒。'),ensure_ascii=False),flush=True)
            except OSError as error:
                print(json.dumps(dict(stage='時間紀錄',message='轉換結果保留；未能更新時間摘要：'+str(error)),ensure_ascii=False),flush=True)
            finally:
                from production_progress import reset
                reset()
                with _lock:_active=None
    return wrapped
