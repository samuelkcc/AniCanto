"""Report a named setup step while its bounded check or installer runs."""
import threading,time


def step(emit,name,phase,operation,*args,interval=5,**kwargs):
    started=time.monotonic();done=threading.Event()
    def update(state):
        emit(phase,setupStep='runtime',runtimeProgress=dict(name=name,phase=phase,
             state=state,elapsedSeconds=round(time.monotonic()-started)))
    update('running')
    def heartbeat():
        while not done.wait(interval):update('running')
    monitor=threading.Thread(target=heartbeat,daemon=True);monitor.start()
    try:
        result=operation(*args,**kwargs)
    except BaseException:
        done.set();monitor.join();update('failed');raise
    done.set();monitor.join();update('complete');return result
