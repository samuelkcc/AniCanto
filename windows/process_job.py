"""Windows job ownership: closing/killing a worker also stops its own descendants."""
import ctypes
import os
import subprocess
import sys

class OwnedJob:
    def __init__(self,pid):
        self.handle=None
        if sys.platform!='win32':return
        from ctypes import wintypes as w
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);self.kernel=kernel
        U32=ctypes.c_uint32;S=ctypes.c_size_t;I64=ctypes.c_int64
        class Basic(ctypes.Structure):
            _fields_=[('processTime',I64),('jobTime',I64),('flags',U32),('minWorkingSet',S),('maxWorkingSet',S),('activeProcesses',U32),('affinity',S),('priority',U32),('scheduling',U32)]
        class IO(ctypes.Structure):_fields_=[(n,ctypes.c_uint64) for n in ('readOps','writeOps','otherOps','readBytes','writeBytes','otherBytes')]
        class Limits(ctypes.Structure):_fields_=[('basic',Basic),('io',IO),('processMemory',S),('jobMemory',S),('peakProcessMemory',S),('peakJobMemory',S)]
        kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];kernel.CreateJobObjectW.restype=w.HANDLE
        kernel.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,U32];kernel.SetInformationJobObject.restype=w.BOOL
        kernel.OpenProcess.argtypes=[U32,w.BOOL,U32];kernel.OpenProcess.restype=w.HANDLE
        kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE];kernel.AssignProcessToJobObject.restype=w.BOOL
        kernel.CloseHandle.argtypes=[w.HANDLE];kernel.CloseHandle.restype=w.BOOL
        job=kernel.CreateJobObjectW(None,None)
        if not job:raise ctypes.WinError(ctypes.get_last_error())
        self.handle=job
        try:
            limits=Limits();limits.basic.flags=0x2000 # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not kernel.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)):raise ctypes.WinError(ctypes.get_last_error())
            process=kernel.OpenProcess(0x0101|0x0400,False,int(pid))
            if not process:raise ctypes.WinError(ctypes.get_last_error())
            try:
                if not kernel.AssignProcessToJobObject(job,process):raise ctypes.WinError(ctypes.get_last_error())
            finally:kernel.CloseHandle(process)
        except BaseException:self.close();raise
    def close(self):
        if self.handle is not None:self.kernel.CloseHandle(self.handle);self.handle=None
    def __del__(self):self.close()


def install():
    """Worker process only; no global changes in the GUI or other applications."""
    if sys.platform!='win32':return
    original=subprocess.Popen
    class OwnedPopen(original):
        def __init__(self,*args,**kwargs):
            self._canto_job=None
            kwargs['creationflags']=kwargs.get('creationflags',0)|subprocess.CREATE_NO_WINDOW
            super().__init__(*args,**kwargs)
            try:self._canto_job=OwnedJob(self.pid)
            except OSError:
                if self.poll() is None:self.terminate();self.wait();raise
        def __del__(self):
            if self._canto_job is not None:self._canto_job.close()
            super().__del__()
    subprocess.Popen=OwnedPopen
