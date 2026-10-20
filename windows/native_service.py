"""Private, worker-owned Ollama; models are released before speech inference."""
import contextlib,json,os,subprocess,time,urllib.request
from pathlib import Path

def request(port,route,body=None,timeout=10):
 req=urllib.request.Request(f'http://127.0.0.1:{port}'+route,None if body is None else json.dumps(body).encode(),{'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)

def unload(cfg):
 for model in set([cfg.get('model'),cfg.get('visualModel')])-{None,''}:
  try:request(int(cfg.get('port',11445)),'/api/generate',dict(model=model,keep_alive=0),30)
  except (OSError,ValueError):pass

@contextlib.contextmanager
def service(root,port=11445):
 root=Path(root);binary=next((root/'tools/ollama').rglob('ollama.exe'),None)
 if binary is None:raise ValueError('Complete native Ollama setup first.')
 # A dedicated loopback port never reconfigures or kills the user's Ollama app.
 try:
  request(port,'/api/version')
 except OSError:pass
 else:raise RuntimeError('AniCanto private model port is already occupied; close the other AniCanto worker before resuming.')
 logs=root/'logs';logs.mkdir(exist_ok=True)
 with (logs/'native-ollama.log').open('a') as log:
  env=dict(os.environ,OLLAMA_HOST=f'127.0.0.1:{port}',OLLAMA_MODELS=str(root/'models/ollama'),OLLAMA_NUM_PARALLEL='1',OLLAMA_MAX_LOADED_MODELS='1',OLLAMA_KEEP_ALIVE='0',OLLAMA_CONTEXT_LENGTH='8192')
  process=subprocess.Popen([str(binary),'serve'],env=env,stdout=log,stderr=log)
  try:
   for _ in range(120):
    if process.poll() is not None:raise RuntimeError('Private model service exited; see native-ollama.log')
    try:request(port,'/api/version');break
    except OSError:time.sleep(.25)
   else:raise RuntimeError('Private model service did not become ready.')
   yield
  finally:
   if process.poll() is None:
    process.terminate()
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:process.kill();process.wait()
