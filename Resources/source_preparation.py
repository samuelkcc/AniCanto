"""Cancellable cloud hydration before short media probes. No source copy or TTS."""
import hashlib,json,os,re,subprocess,sys,time,uuid
from contextlib import contextmanager
from pathlib import Path,PureWindowsPath
from atomic_files import write_json

CLOUD_ERROR='The provider has not finished making this video available. Open the file in the provider and wait until it downloads completely, then retry. Your queue and saved work are kept.'
READ_ERROR='The source video could not be read completely. The file may be incomplete, damaged, or still being written by another program. Your queue and saved work are kept.'
STALLED_ERROR='The provider stopped sending this video part-way through. Your queue and saved work are kept. Retry, or make the video available offline in the provider first.'
CANCELLED='Source preparation cancelled.'
WAIT_AFTER_IDLE=45
WAIT_GRACE=600
WAIT_FILE='wait.json'
class SourcePreparationCancelled(RuntimeError):pass
class ProviderNotReady(RuntimeError):
 """The provider named a path but served no bytes, so the source was never opened."""
class ProviderReadInterrupted(RuntimeError):
 """The provider opened the file but stopped supplying data before the end."""
class MediaUnreadable(RuntimeError):
 """The bytes were readable, so the fault belongs to the media and not to a provider."""

def identity(path):
 s=Path(path).stat();return dict(path=str(Path(path).resolve()),bytes=s.st_size,mtimeNS=s.st_mtime_ns,device=s.st_dev,inode=s.st_ino)
def placeholder(path):return bool(getattr(Path(path).stat(),'st_flags',0)&0x40000000)
def provider(path):
 """Name the streaming owner of a path, or local. A folder name is a label, never proof of local data."""
 parts=[x.casefold() for x in (*Path(path).parts,*PureWindowsPath(str(path)).parts)]
 if str(path).startswith('\\\\'):return 'network'
 # Apple's CloudStorage container also holds Google Drive and OneDrive files, so the
 # provider name is read before that container name.
 for part in parts:
  if part in ('my drive','google drive') or part.startswith('googledrive'):return 'google-drive'
  if part.startswith('onedrive'):return 'onedrive'
 for part in parts:
  if part in ('cloudstorage','mobile documents') or part.startswith('com~apple~clouddocs'):return 'icloud'
 return 'local'
def cloud(path):return provider(path)!='local'
def windows_attributes(path):
 if os.name!='nt':return None
 return getattr(Path(path).stat(),'st_file_attributes',None)
# Microsoft OFFLINE / RECALL_ON_OPEN / RECALL_ON_DATA_ACCESS attributes.
RECALL_ATTRIBUTES=0x1000|0x40000|0x400000
def hydration_reason(path):
 """Why a source still needs a full provider read: network, recall-attributes,
 placeholder, provider-root-name, or empty when the bytes are already local."""
 if str(path).startswith('\\\\'):return 'network'
 attributes=windows_attributes(path)
 if attributes is not None:
  # Windows attributes are the proof: recall flags mean the provider still owns the bytes,
  # and their absence means no movie needs streaming. A folder name is never proof.
  if attributes & RECALL_ATTRIBUTES:return 'recall-attributes'
  return ''
 if placeholder(path):return 'placeholder'
 if provider(path)!='local':return 'provider-root-name'
 return ''
def requires_hydration(path):return bool(hydration_reason(path))
def local_window_readable(path,*,windows=6,chunk=65536,budget=20.0,clock=time.monotonic):
 """Sample small windows across the whole span. A File Provider answers at once only
 when the bytes are on this disk, so a fast full-span sample proves local data
 without copying a whole movie. An empty window, a slow window or an error keeps
 the full provider read on."""
 start=clock();handle=None
 try:
  size=path.stat().st_size
  if size<=chunk:return bool(path.open('rb').read(1))
  offsets=[int(size*ratio) for ratio in (0,.2,.4,.6,.8)]+[size-chunk]
  offsets=offsets[:max(2,min(windows,len(offsets)))]
  handle=path.open('rb')
  for offset in offsets:
   handle.seek(offset)
   if not handle.read(chunk):return False
   if clock()-start>budget:return False
  return True
 except OSError:return False
 finally:
  if handle is not None:
   try:handle.close()
   except OSError:pass
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
  reason=hydration_reason(self.source)
  self.state=dict(operationID=self.id,hostPID=self.owner,rowID=row_id,sourceName=self.source.name,phase='reading',state='preparing',bytesRead=0,totalBytes=0,started=time.time(),provider=provider(self.source),needsHydration=bool(reason),hydrationReason=reason)
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
      # The reader has no total deadline, so a quiet source is a question for the user and not
      # a fault. Carry that question into status.json for the interface. Only a provider read
      # owns a progress file; a plain probe or language capture must not read or report one.
      decide=bool(progress.get('waitingForDecision'))
      if count!=last or decide!=bool(self.state.get('waitingForDecision')) or time.time()-self.state['updated']>1:
       self.update(bytesRead=count,waitingSeconds=round(time.monotonic()-start),waitingForDecision=decide,idleSeconds=int(progress.get('idleSeconds') or 0));last=count
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
  if not requires_hydration(self.source):
   self.update(sourceReadPolicy='local-data',localDataAvailable=True);return
  reason=hydration_reason(self.source)
  # The path only looks like a provider file, and a full-span sample answers at once.
  # Then the bytes are already on this disk: no movie streams and no cache copy runs.
  if reason=='provider-root-name' and local_window_readable(self.source):
   self.update(sourceReadPolicy='local-window',localDataAvailable=True,bytesRead=before['bytes']);return
  self.update(sourceReadPolicy='provider-read')
  key=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest();receipt=self.root/'cache/source-readiness'/(key+'.json')
  with self.exclusive_read(receipt.with_suffix('.lock')):
   try:ready=json.loads(receipt.read_text())
   except (OSError,ValueError):ready={}
   if ready.get('identity')==before and ready.get('bytesRead')==before['bytes'] and ready.get('sha256') and not placeholder(self.source):
    self.update(bytesRead=before['bytes'],reusedReadiness=True);return
   request=dict(source=str(self.source),identity=before,progress=str(self.folder/'read-progress.json'),result=str(self.folder/'read-result.json'),wait=str(self.folder/WAIT_FILE))
   req=self.folder/'read-request.json';write_json(req,request)
   # The File Provider can block a read while downloading a large file. Keep the
   # parent responsive and cancellable; there is no total hydration deadline.
   self.capture([sys.executable,str(Path(__file__).resolve()),str(req)],reading=True)
   result=json.loads((self.folder/'read-result.json').read_text())
   if result.get('identity')!=before or result.get('bytesRead')!=before['bytes'] or identity(self.source)!=before:raise ProviderReadInterrupted(STALLED_ERROR)
   write_json(receipt,result);self.update(bytesRead=before['bytes'])
 # A finished run must not leave an old wait question on the screen.
 def finish(self):self.update(state='ready',phase='ready',waitingForDecision=False)
 def fail(self,error):self.update(state='cancelled' if isinstance(error,SourcePreparationCancelled) else 'failed',message=str(error)[:500],waitingForDecision=False)


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

def wait_path(root,operation_id):
 if not isinstance(operation_id,str) or not re.fullmatch(r'[A-Za-z0-9-]{1,64}',operation_id):raise ValueError('Invalid source preparation operation.')
 return Path(root)/'source-preparation'/operation_id/WAIT_FILE
def grant_wait(root,operation_id,seconds=WAIT_GRACE):
 """Record one user decision to keep waiting for a slow provider. The reader keeps its file
 offset, so bytes already read are never read again. The allowance is a wall-clock time,
 because the reader runs as a separate process."""
 seconds=max(1.0,float(seconds));until=time.time()+seconds
 write_json(wait_path(root,operation_id),dict(until=until,granted=time.time(),seconds=seconds))
 return dict(waitGrantedUntil=until)
def wait_grant_remaining(path,wall=time.time):
 """Seconds of waiting the user still allows, or 0 when no grant is open."""
 try:value=json.loads(Path(path).read_text())
 except (OSError,ValueError):return 0.0
 try:until=float(value.get('until',0))
 except (TypeError,ValueError):return 0.0
 return max(0.0,until-wall())

def read_source(request,*,max_idle=120,pause=time.sleep,clock=time.monotonic,opener=None):
 """Read a provider source without a total deadline. A quiet source with a `wait` path asks
 the interface to decide instead of failing: the progress file carries `waitingForDecision`,
 and a grant file buys `WAIT_GRACE` more quiet time. Without a `wait` path the idle limit
 still ends the read, because no interface can answer."""
 source=Path(request['source']);expected=request['identity'];count=0;sha=hashlib.sha256();last=0;stream=None;last_progress=clock();last_error=''
 wait_name=request.get('wait');ask_idle=WAIT_AFTER_IDLE if wait_name else max_idle;granted_until=0.0
 if identity(source)!=expected:raise RuntimeError('Source identity changed before reading.')
 open_source=opener or (lambda:source.open('rb'))
 try:
  while count<expected['bytes']:
   try:
    if stream is None:stream=open_source();stream.seek(count)
    block=stream.read(min(1024*1024,expected['bytes']-count))
   except OSError as error:
    last_error=str(error)[-500:]
    if stream is not None:
     try:stream.close()
     except OSError:pass
    stream=None;block=b''
   if not block:
    if stream is not None:stream.close();stream=None
    if identity(source)!=expected:raise RuntimeError('Source changed during reading.')
    # A quiet provider is a question for the interface, not a fault, when a wait path
    # exists. Without that path no interface can answer, so the idle limit ends the read.
    if clock()-last_progress>=ask_idle:
     if wait_name:
      remaining=wait_grant_remaining(wait_name)
      # A "keep waiting" answer extends the quiet window from now, so the panel is not
      # asked again inside the time the user already agreed to.
      if remaining>0:
       granted_until=clock()+remaining
       write_json(request['progress'],dict(bytesRead=count,totalBytes=expected['bytes'],waitingForData=True,waitingForDecision=False,waitSeconds=round(remaining),provider=provider(source)))
      elif clock()>=granted_until:
       write_json(request['progress'],dict(bytesRead=count,totalBytes=expected['bytes'],waitingForData=True,waitingForDecision=True,idleSeconds=round(clock()-last_progress),provider=provider(source)))
      pause(.5);continue
     if count:raise ProviderReadInterrupted('The provider supplied an incomplete source and made no read progress for '+str(max_idle)+' seconds. '+last_error)
     raise ProviderNotReady('The provider named this source but served no bytes for '+str(max_idle)+' seconds. '+last_error)
    write_json(request['progress'],dict(bytesRead=count,totalBytes=expected['bytes'],waitingForData=True))
    pause(.5);continue
   count+=len(block);sha.update(block);last_progress=clock()
   if clock()-last>.25 or count>=expected['bytes']:
    write_json(request['progress'],dict(bytesRead=count,totalBytes=expected['bytes'],waitingForData=False));last=clock()
 finally:
  if stream is not None:stream.close()
 if count!=expected['bytes'] or identity(source)!=expected:raise ProviderReadInterrupted('The provider supplied an incomplete or changed source.')
 write_json(request['result'],dict(identity=expected,bytesRead=count,sha256=sha.hexdigest(),completed=time.time()))
if __name__=='__main__':read_source(json.loads(Path(sys.argv[1]).read_text()))
