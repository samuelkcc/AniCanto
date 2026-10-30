"""Cancellable cloud hydration before short media probes. No source copy or TTS."""
import hashlib,json,os,re,subprocess,sys,time,uuid
from contextlib import contextmanager
from pathlib import Path,PureWindowsPath
from atomic_files import write_json

CLOUD_ERROR='The cloud video is not ready. Make it available offline in Finder or Explorer, then retry. Your queue and saved work are kept.'
READ_ERROR='The source video could not be read completely. Check the cloud connection or local file, then retry. Your queue and saved work are kept.'
CANCELLED='Source preparation cancelled.'
class SourcePreparationCancelled(RuntimeError):pass

def identity(path):
 s=Path(path).stat();return dict(path=str(Path(path).resolve()),bytes=s.st_size,mtimeNS=s.st_mtime_ns,device=s.st_dev,inode=s.st_ino)
def placeholder(path):return bool(getattr(Path(path).stat(),'st_flags',0)&0x40000000)
def cloud(path):
 parts=[x.casefold() for x in (*Path(path).parts,*PureWindowsPath(str(path)).parts)]
 return any(x in ('cloudstorage','mobile documents','my drive','google drive') or x.startswith(('onedrive','googledrive')) for x in parts) or str(path).startswith('\\\\')
def owner_alive(pid):
 if not pid:return True
 if os.name=='nt':
  import ctypes
  api=ctypes.windll.kernel32;api.OpenProcess.restype=ctypes.c_void_p;handle=api.OpenProcess(0x1000,False,pid)
  if not handle:return False
  code=ctypes.c_ulong();ok=api.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code));api.CloseHandle(ctypes.c_void_p(handle));return bool(ok and code.value==259)
 try:os.kill(pid,0);return True
 except ProcessLookupError:return False
 except PermissionError:return True

class Preparation:
 def __init__(self,root,source,operation_id=None,row_id=None):
  self.root=Path(root);self.source=Path(source);self.id=operation_id or uuid.uuid4().hex
  if not re.fullmatch(r'[A-Za-z0-9-]{1,64}',self.id):raise ValueError('Invalid source preparation operation.')
  self.folder=self.root/'source-preparation'/self.id
  # An operation ID is single-use. A stale cancel must never affect a new run.
  self.folder.mkdir(parents=True,exist_ok=True)
  if (self.folder/'status.json').exists():raise ValueError('Source preparation operation was already used.')
  self.owner=int(os.environ.get('CANTOSYNC_HOST_PID','0') or 0)
  self.state=dict(operationID=self.id,hostPID=self.owner,rowID=row_id,sourceName=self.source.name,phase='reading',state='preparing',bytesRead=0,totalBytes=0,started=time.time())
  self.update()
 def update(self,**kw):
  self.state.update(kw,updated=time.time());write_json(self.folder/'status.json',self.state);write_json(self.root/'source-preparation/current.json',self.state)
 def check(self):
  if (self.folder/'cancel').exists() or not owner_alive(self.owner):raise SourcePreparationCancelled(CANCELLED)
 def capture(self,args,timeout=None,reading=False):
  self.check();token=uuid.uuid4().hex;stdout=self.folder/(token+'.stdout');stderr=self.folder/(token+'.stderr')
  with stdout.open('wb') as out,stderr.open('wb') as err:
   child=subprocess.Popen([str(x) for x in args],stdout=out,stderr=err,stdin=subprocess.DEVNULL)
   start=time.monotonic();last=None;power=None;windows_power=False
   if reading:
    try:
     if sys.platform=='darwin':power=subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(os.getpid())],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
     elif os.name=='nt':
      import ctypes
      windows_power=bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
    except OSError:pass
   try:
    while child.poll() is None:
     self.check()
     if timeout is not None and time.monotonic()-start>timeout:raise subprocess.TimeoutExpired(args,timeout)
     if reading:
      try:progress=json.loads((self.folder/'read-progress.json').read_text())
      except (OSError,ValueError):progress={}
      count=progress.get('bytesRead',0)
      if count!=last or time.time()-self.state['updated']>1:
       self.update(bytesRead=count,waitingSeconds=round(time.monotonic()-start));last=count
     time.sleep(.2)
    data=stdout.read_bytes()
    if child.returncode:raise subprocess.CalledProcessError(child.returncode,args,output=data,stderr=stderr.read_bytes())
    return data
   finally:
    if child.poll() is None:
     child.terminate()
     try:child.wait(timeout=2)
     except subprocess.TimeoutExpired:child.kill();child.wait()
    if power is not None:
     power.terminate();power.wait()
    if windows_power:
     import ctypes
     ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    stdout.unlink(missing_ok=True);stderr.unlink(missing_ok=True)
 @contextmanager
 def exclusive_read(self,path):
  path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('a+b') as lock:
   if os.name=='nt':
    import msvcrt
    lock.seek(0);lock.write(b'0');lock.flush()
   else:import fcntl
   while True:
    self.check()
    try:
     if os.name=='nt':lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
     else:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
     break
    except (BlockingIOError,PermissionError):time.sleep(.2)
   try:yield
   finally:
    if os.name=='nt':lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
    else:fcntl.flock(lock,fcntl.LOCK_UN)
 def ensure_local(self):
  self.check();before=identity(self.source);self.update(totalBytes=before['bytes'])
  if not cloud(self.source) and not placeholder(self.source):return
  key=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest();receipt=self.root/'cache/source-readiness'/(key+'.json')
  with self.exclusive_read(receipt.with_suffix('.lock')):
   try:ready=json.loads(receipt.read_text())
   except (OSError,ValueError):ready={}
   if ready.get('identity')==before and ready.get('bytesRead')==before['bytes'] and ready.get('sha256') and not placeholder(self.source):
    self.update(bytesRead=before['bytes'],reusedReadiness=True);return
   request=dict(source=str(self.source),identity=before,progress=str(self.folder/'read-progress.json'),result=str(self.folder/'read-result.json'))
   req=self.folder/'read-request.json';write_json(req,request)
   # The File Provider can block a read while downloading a large file. Keep the
   # parent responsive and cancellable; there is no total hydration deadline.
   self.capture([sys.executable,str(Path(__file__).resolve()),str(req)],reading=True)
   result=json.loads((self.folder/'read-result.json').read_text())
   if result.get('identity')!=before or result.get('bytesRead')!=before['bytes'] or identity(self.source)!=before:raise RuntimeError(READ_ERROR)
   write_json(receipt,result);self.update(bytesRead=before['bytes'])
 def finish(self):self.update(state='ready',phase='ready')
 def fail(self,error):self.update(state='cancelled' if isinstance(error,SourcePreparationCancelled) else 'waiting',message=str(error)[:500])


def status(root,operation_id=None):
 base=Path(root)/'source-preparation'
 if operation_id is not None and not re.fullmatch(r'[A-Za-z0-9-]{1,64}',operation_id):raise ValueError('Invalid source preparation operation.')
 path=base/operation_id/'status.json' if operation_id else base/'current.json'
 try:return json.loads(path.read_text())
 except (OSError,ValueError):return None

def cancel(root,operation_id):
 if not isinstance(operation_id,str) or not re.fullmatch(r'[A-Za-z0-9-]{1,64}',operation_id):raise ValueError('Invalid source preparation operation.')
 folder=Path(root)/'source-preparation'/operation_id;folder.mkdir(parents=True,exist_ok=True)
 value=status(root,operation_id)
 if value is None or value.get('state')=='preparing':(folder/'cancel').touch()
 return dict(cancelRequested=True)

def read_source(request):
 source=Path(request['source']);expected=request['identity'];count=0;sha=hashlib.sha256();last=0
 if identity(source)!=expected:raise RuntimeError('Source identity changed before reading.')
 with source.open('rb') as f:
  while True:
   block=f.read(1024*1024)
   if not block:break
   count+=len(block);sha.update(block)
   if time.monotonic()-last>.25 or count>=expected['bytes']:
    write_json(request['progress'],dict(bytesRead=count,totalBytes=expected['bytes']));last=time.monotonic()
 if count!=expected['bytes'] or identity(source)!=expected:raise RuntimeError('The provider supplied an incomplete or changed source.')
 write_json(request['result'],dict(identity=expected,bytesRead=count,sha256=sha.hexdigest(),completed=time.time()))
if __name__=='__main__':read_source(json.loads(Path(sys.argv[1]).read_text()))
