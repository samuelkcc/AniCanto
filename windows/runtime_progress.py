"""Report bounded setup commands and actual installer transfer progress."""
import collections,os,queue,re,subprocess,sys,threading,time

_context=threading.local()


def step(emit,name,phase,operation,*args,interval=5,**kwargs):
    started=time.monotonic();done=threading.Event();state={'phase':phase,'detail':'','download':None};lock=threading.Lock()
    previous=getattr(_context,'report',None)
    def update(status,heartbeat=False):
        with lock:current=dict(state)
        extra=dict(setupStep='runtime',heartbeat=heartbeat,runtimeProgress=dict(name=name,phase=current['phase'],
            state=status,elapsedSeconds=round(time.monotonic()-started),detail=current['detail']))
        if current['download']:extra['download']=current['download']
        emit(current['detail'] or current['phase'],**extra)
    def report(line,download=None,phase=None):
        with lock:
            state.update(detail=line,download=download)
            if phase:state['phase']=phase
        update('running')
    _context.report=report
    update('running')
    def heartbeat():
        while not done.wait(interval):update('running',True)
    monitor=threading.Thread(target=heartbeat,daemon=True);monitor.start()
    try:result=operation(*args,**kwargs)
    except BaseException:
        done.set();monitor.join();update('failed');raise
    finally:_context.report=previous
    done.set();monitor.join();update('complete');return result


class InstallerOutput:
    def __init__(self,report):
        self.report=report;self.file='';self.started=None;self.last=0
    def line(self,line):
        line=line.strip()
        if not line:return
        progress=re.fullmatch(r'Progress (\d+) of (\d+)',line)
        now=time.monotonic()
        if progress:
            n,total=map(int,progress.groups())
            if self.started is None:self.started=now
            if now-self.last<.4 and n<total:return
            self.last=now
            self.report(self.file or 'Downloading runtime package',dict(file=self.file,state='downloading',receivedBytes=n,totalBytes=total,
                bytesPerSecond=round(n/max(.001,now-self.started))), 'Downloading runtime packages')
            return
        if line.startswith('Downloading '):
            self.file=line[len('Downloading '):].split(' (',1)[0].rsplit('/',1)[-1];self.started=now;self.last=0
            self.report(line,None,'Downloading runtime packages')
        elif line.startswith('Using cached '):self.report(line,None,'Reusing cached runtime packages')
        elif line.startswith('Installing collected packages:'):self.report(line,None,'Installing downloaded runtime packages')
        else:self.report(line,None,None)


def stream_command(args,*,env=None,timeout=2700):
    command=list(map(str,args))
    # Bundled pip reports exact byte counts in raw mode, including redirected output.
    if any('pip' in x.lower() for x in command[:5]) and 'install' in command and '--progress-bar' not in command:
        command[command.index('install')+1:command.index('install')+1]=['--progress-bar','raw']
    environment=dict(os.environ if env is None else env,PYTHONUNBUFFERED='1',PYTHONIOENCODING='utf-8')
    child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',env=environment)
    lines=queue.Queue();tail=collections.deque(maxlen=30)
    def reader():
        try:
            for line in child.stdout:lines.put(line.rstrip('\r\n'))
        finally:lines.put(None)
    thread=threading.Thread(target=reader,daemon=True);thread.start();started=time.monotonic()
    report=getattr(_context,'report',None)
    def output(line,download=None,phase=None):
        if report:report(line,download,phase)
        else:print(line,flush=True)
    parser=InstallerOutput(output)
    try:
        while True:
            remaining=timeout-(time.monotonic()-started)
            if remaining<=0:raise subprocess.TimeoutExpired(command,timeout,output='\n'.join(tail))
            try:line=lines.get(timeout=min(.25,remaining))
            except queue.Empty:continue
            if line is None:break
            tail.append(line);parser.line(line)
        result=child.wait(timeout=max(.001,timeout-(time.monotonic()-started)))
        if result:raise subprocess.CalledProcessError(result,command,output='\n'.join(tail))
    finally:
        if child.poll() is None:child.kill();child.wait()
        if child.stdout:child.stdout.close()
        thread.join(timeout=1)
