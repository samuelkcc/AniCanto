"""Resumable HTTPS transfers with distinct verification/reuse/download states."""
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.request


def progress(path,state,received,total,speed=0,attempt=1):
    print(json.dumps(dict(stage='Download',message=Path(path).name,download=dict(
        file=Path(path).name,state=state,receivedBytes=received,totalBytes=total,
        bytesPerSecond=round(speed),attempt=attempt)),ensure_ascii=False),flush=True)


def sha256(path,on_progress=None):
    h=hashlib.sha256();size=Path(path).stat().st_size;received=0;last=0
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(4*1024*1024),b''):
            h.update(chunk);received+=len(chunk);now=time.monotonic()
            if on_progress and (now-last>=.5 or received==size):on_progress(received,size);last=now
    return h.hexdigest()


def verified(path,digest,expected_size,display):
    if not path.is_file():return False
    size=path.stat().st_size
    if expected_size is not None and size!=expected_size:return False
    progress(display,'verifying',0,size)
    return not digest or sha256(path,lambda n,total:progress(display,'verifying',n,total))==digest


def download(url,path,digest='',expected_size=None):
    if not url.startswith('https://'):raise ValueError('Downloads require HTTPS.')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if verified(path,digest,expected_size,path):
        progress(path,'reused',path.stat().st_size,path.stat().st_size);return
    partial=path.with_name(path.name+'.partial')
    # A fully saved file needs verification, not another HTTP request after relaunch.
    if digest and expected_size is not None and verified(partial,digest,expected_size,path):
        partial.replace(path);progress(path,'complete',path.stat().st_size,path.stat().st_size);return
    if partial.is_file() and expected_size is not None and partial.stat().st_size>=expected_size:
        partial.replace(partial.with_name(partial.name+f'.rejected-{time.time_ns()}'))
    for attempt in range(3):
        offset=partial.stat().st_size if partial.is_file() else 0
        progress(path,'resuming' if offset else 'downloading',offset,expected_size or 0,attempt=attempt+1)
        request=urllib.request.Request(url,headers={'Range':f'bytes={offset}-'} if offset else {})
        try:
            with urllib.request.urlopen(request,timeout=60) as response:
                if response.status==206:
                    if not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'):
                        raise ValueError('Server returned an incorrect resume offset.')
                elif response.status!=200:raise ValueError('Unexpected download response.')
                mode='ab' if response.status==206 else 'wb'
                started=time.monotonic();last=0;initial=offset if mode=='ab' else 0
                length=response.headers.get('Content-Length',0)
                try:length=int(length) if isinstance(length,(str,int)) else 0
                except ValueError:length=0
                total=expected_size or (length+initial if length else 0)
                with partial.open(mode) as output:
                    for chunk in iter(lambda:response.read(1024*1024),b''):
                        output.write(chunk);now=time.monotonic()
                        if now-last>=1:
                            received=output.tell();speed=(received-initial)/max(.001,now-started)
                            progress(path,'downloading',received,total,speed,attempt+1);last=now
            if expected_size is not None and partial.stat().st_size!=expected_size:
                raise ValueError('Download size differs from the pinned manifest.')
            if not verified(partial,digest,expected_size,path):
                partial.replace(partial.with_name(partial.name+f'.rejected-{time.time_ns()}'))
                raise ValueError('SHA-256 mismatch; downloaded bytes were rejected.')
            partial.replace(path);progress(path,'complete',path.stat().st_size,path.stat().st_size);return
        except urllib.error.HTTPError as error:
            if error.code==416 and digest and verified(partial,digest,expected_size,path):
                partial.replace(path);progress(path,'complete',path.stat().st_size,path.stat().st_size);return
            if error.code not in (408,429,500,502,503,504) or attempt==2:raise
        except (urllib.error.URLError,TimeoutError,OSError):
            if attempt==2:raise
        time.sleep(attempt+1)
