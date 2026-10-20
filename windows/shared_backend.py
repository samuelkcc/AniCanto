"""Native child-process boundary for the shared production worker.

Only inference/process launch is platform-specific. Call bind() around the shared
worker entry point to retain its existing recovery budgets and recording history.
This module does not declare Windows setup or desktop feature parity complete.
"""
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
SHARED = HERE/'shared' if (HERE/'shared').is_dir() else HERE.parent/'Resources'
ACTIONS = {'tts':'gpt', 'separate':'separator', 'speakers':'separator', 'independent-voices':'separator', 'cosy':'cosy', 'asr':'asr', 'normal-listen':'asr', 'voxcpm2':'local', 'wsyue':'local', 'drama3':'drama3'}


def launch_spec(cfg, action, request):
    """A verified native marker is required; an MLX marker is never sufficient."""
    if action not in ACTIONS:
        raise ValueError(f'Windows native adapter is not integrated for {action}; no incompatible Mac runtime was launched.')
    root=Path(cfg['storage']);kind=ACTIONS[action]
    runtime='analysis' if kind=='separator' else 'worker' if kind=='drama3' else kind
    marker=root/f'{kind}-windows-ready.json'
    try:ready=json.loads(marker.read_text(encoding='utf-8'))
    except (OSError,ValueError) as error:
        raise ValueError(f'Native Windows {kind} setup is incomplete.') from error
    if not isinstance(ready,dict) or ready.get('modelLoadPassed') is not True:
        raise ValueError(f'Native Windows {kind} has not passed its model-load probe.')
    if kind=='local':
        if ready.get('speechInferencePassed') is not True or action not in ready.get('verifiedEngines',[]):
            raise ValueError('The selected native voice engine has not passed its own speech probe.')
        key='voxcpmModel' if action=='voxcpm2' else 'wsyueModel'
        expected=ready.get('variants',{}).get(action)
        if not expected or request.get(key,cfg.get(key,expected))!=expected:
            raise ValueError('The selected voice variant is not the one verified by Windows setup.')
    if action=='tts' and request.get('gsvVersion','v4') not in ready.get('modelVersions',[ready.get('modelVersion')]):
        raise ValueError('The selected GPT version is not the version verified by Windows setup.')
    python=root/'runtimes'/runtime/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
    if not python.is_file():raise ValueError(f'Native Windows {kind} runtime is missing.')
    backend=ready.get('backend')
    if backend not in ('nvidia','amd','cpu','cuda') or (backend=='cuda' and action!='drama3'):raise ValueError('Unsupported native voice runtime backend.')
    wanted=request.get('device', 'auto')
    if wanted=='mps':wanted='auto' # Only the hardware choice migrates, never MLX weights.
    if wanted not in ('auto','cpu','cuda') and not str(wanted).startswith('cuda:'):
        raise ValueError('Unsupported native voice inference device.')
    if backend=='cpu' and str(wanted).startswith('cuda'):raise ValueError('CUDA was requested from a CPU-only runtime.')
    device='cpu' if wanted=='cpu' or backend=='cpu' else 'cuda'
    if action=='wsyue':device='cpu'
    index=int(str(wanted).split(':',1)[1]) if str(wanted).startswith('cuda:') else int(request.get('gpuIndex',0))
    if index<0:raise ValueError('Invalid native GPU index.')
    native=dict(request,device=device,gpuIndex=index,nativeBackend=backend,nativeFormat=ready.get('nativeFormat','pytorch'),nativeAdapter='shared-worker-1')
    if kind=='local':native[key]=expected
    if action=='drama3' and ready.get('variant')=='drama3-small-iq3' and request.get('drama3Model',cfg.get('drama3Model'))!='drama3-small-iq3':raise ValueError('Drama3-small is retired and cannot replace the selected model. Deploy a supported quality preset.')
    if action=='drama3':native.update(drama3Backend=device,drama3Model=ready.get('variant',request.get('drama3Model','drama3-native-q2')))
    return python,native


def run_model_job(cfg, action, request, emit):
    from track_control import check
    from dubbing import model_error_detail
    request=dict(request,asrModel=cfg.get('asrModel'))
    if cfg.get('_trackControl'):request['_trackControl']=cfg['_trackControl']
    check(request)
    if action in ('tts','cosy','voxcpm2','wsyue','drama3'):
        from native_service import unload
        unload(cfg)
    python,request=launch_spec(cfg,action,request)
    folder=Path(request['out'] if action=='separate' else request['job']);folder.mkdir(parents=True,exist_ok=True)
    req=folder/f'{action}-request.json';req.write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8')
    env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',ORT_DISABLE_TELEMETRY='1')
    env['PATH']=str(Path(cfg['ffmpeg']).parent)+os.pathsep+env.get('PATH','')
    log=req.with_suffix('.log');error=None
    kwargs=dict(stdout=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',env=env)
    if sys.platform=='win32':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
    with log.open('w',encoding='utf-8') as errors:
        process=subprocess.Popen([str(python),str(HERE/'shared_inference.py'),action,str(req)],stderr=errors,**kwargs)
        last=[time.monotonic()];stalled=[False];done=threading.Event()
        def watchdog():
            while not done.wait(1):
                if time.monotonic()-last[0]>float(cfg.get('modelStallSeconds',600)):
                    stalled[0]=True;process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill()
                    return
        threading.Thread(target=watchdog,daemon=True).start()
        try:
            for line in process.stdout:
                last[0]=time.monotonic()
                try:event=json.loads(line)
                except ValueError:continue
                if not isinstance(event,dict) or not event.get('stage'):continue
                if event['stage']=='錯誤':error=event.get('message')
                fields={k:event[k] for k in ('cueIndex','workID','workCompleted','workTotal','componentProgress') if event.get(k) is not None}
                if fields.get('workID')=='tts' and 'primaryGeneration' in request:fields['primaryGeneration']=bool(request['primaryGeneration'])
                emit(event['stage'],event.get('message',''),event.get('progress'),**fields)
            code=process.wait()
        finally:
            done.set()
            process.stdout.close()
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
        if stalled[0]:raise RuntimeError(f'Windows native model stalled; completed recordings retained. See {log}')
    if code:
        check(request)
        raise RuntimeError(f'Native model exited {code}: {error or model_error_detail(log.read_text(errors="replace"))} (see {log})')


@contextlib.contextmanager
def bind():
    """Replace the inference boundary, not model_job's recovery/history policy."""
    import dubbing
    previous=dubbing._run_model_job
    dubbing._run_model_job=run_model_job
    try:yield
    finally:dubbing._run_model_job=previous
