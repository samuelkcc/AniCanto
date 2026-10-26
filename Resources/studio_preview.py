"""On-demand desktop preview. Video remuxing precedes lightweight transcoding.

A per-source OS lock prevents duplicate work across concurrent IPC adapters.
Progress and scratch media stay inside app-managed cache and belong to a source.
"""
from contextlib import contextmanager
import hashlib,json,math,os,subprocess,time
from pathlib import Path

REVISION='preview-3-selected-audio'

def folder(root,source,compatible=False,audio_stream=None):
    source=Path(source).resolve();stat=source.stat()
    key=hashlib.sha256(json.dumps([REVISION,str(source),stat.st_size,stat.st_mtime_ns,bool(compatible),audio_stream]).encode()).hexdigest()[:24]
    return Path(root)/'cache/studio-preview'/key

def write(path,data):
    from worker import atomic_json
    atomic_json(path,data)

@contextmanager
def exclusive(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        if os.name=='nt':
            import msvcrt
            stream.seek(0);stream.write(b'0');stream.flush()
            while True:
                try:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1);break
                except OSError:time.sleep(.1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
        try:yield
        finally:
            if os.name=='nt':stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)

def status(root,source,compatible=False,audio_stream=None):
    directory=folder(root,source,compatible,audio_stream)
    try:data=json.loads((directory/'status.json').read_text())
    except (OSError,ValueError):return dict(stage='probing',progress=0)
    progress={}
    try:
        for line in (directory/'progress.txt').read_text().splitlines():
            if '=' in line:
                key,value=line.split('=',1);progress[key]=value
        if data.get('stage') in ('remux','encode') and 'out_time_us' in progress:
            seconds=max(0,float(progress['out_time_us'])/1_000_000)
            data['progress']=min(.99,seconds/max(.01,data.get('duration',0)))
            data['secondsPrepared']=seconds
    except (OSError,ValueError):pass
    if data.get('stage')=='ready':data['progress']=1
    return data

def prepare(root,source,tools,platform,compatible=False,audio_stream=None):
    source=Path(source).resolve();directory=folder(root,source,compatible,audio_stream)
    with exclusive(directory/'prepare.lock'):
        target=directory/'preview.mp4';metadata=directory/'metadata.json'
        if target.is_file() and target.stat().st_size and metadata.is_file():
            result=json.loads(metadata.read_text());result['path']=str(target);return result
        write(directory/'status.json',dict(stage='probing',source=str(source),duration=0))
        if platform=='win32':
            from source_access import accessible
            def source_progress(_stage,_message,progress=None):
                write(directory/'status.json',dict(stage='copying',source=str(source),duration=0,progress=progress or 0))
            try:media_source,raw=accessible(source,tools['ffprobe'],root,source_progress)
            except (OSError,RuntimeError) as error:
                write(directory/'status.json',dict(stage='failed',source=str(source),duration=0,error=str(error)[:1200]))
                raise
            info=json.loads(raw)
        else:
            media_source=source
            info=json.loads(subprocess.check_output([tools['ffprobe'],'-v','error','-show_format','-show_streams','-of','json',str(source)],timeout=30))
        streams=info.get('streams',[]);video=next((s for s in streams if s.get('codec_type')=='video'),{})
        audio_tracks=[s for s in streams if s.get('codec_type')=='audio']
        if audio_stream is not None and (type(audio_stream) is not int or not any(s['index']==audio_stream for s in audio_tracks)):raise ValueError('Invalid preview audio track.')
        audio=next((s for s in audio_tracks if s['index']==audio_stream),audio_tracks[0] if audio_tracks else {})
        first_audio=not audio_tracks or audio.get('index')==audio_tracks[0]['index']
        duration=float(info['format']['duration'])
        if not math.isfinite(duration) or duration<=0:raise ValueError('Invalid preview duration.')
        copy_video=not compatible and (video.get('codec_name')=='h264' and video.get('pix_fmt')=='yuv420p' or platform=='darwin' and video.get('codec_name')=='hevc')
        direct=copy_video and first_audio and source.suffix.lower() in ('.mp4','.m4v','.mov') and (not audio or audio.get('codec_name') in ('aac','mp3','alac'))
        result=dict(path=str(media_source),duration=duration,streams=streams,fallbackAvailable=bool(copy_video),mode='direct',selectedAudioStream=audio.get('index'))
        if direct:
            write(directory/'status.json',dict(stage='ready',source=str(source),duration=duration));return result
        try:
            modes=['remux','encode'] if copy_video else ['encode']
            for mode in modes:
                temp=directory/f'preview.{os.getpid()}.partial.mp4'
                (directory/'progress.txt').unlink(missing_ok=True)
                write(directory/'status.json',dict(stage=mode,source=str(source),duration=duration))
                args=[tools['ffmpeg'],'-v','error','-nostdin','-y','-i',str(media_source),'-map','0:v:0','-map',f"0:{audio['index']}?" if audio else '0:a:0?']
                if mode=='remux':
                    args+=['-c:v','copy']
                    if video.get('codec_name')=='hevc':args+=['-tag:v','hvc1']
                else:
                    args+=['-c:v','libx264','-preset','ultrafast','-crf','28','-threads','2','-vf',"scale=w='min(960,iw)':h=-2",'-pix_fmt','yuv420p']
                args+=['-c:a','aac','-b:a','128k','-ac','2','-sn','-movflags','+faststart','-progress',str(directory/'progress.txt'),str(temp)]
                try:subprocess.run(args,check=True,timeout=1800,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                except subprocess.CalledProcessError:
                    temp.unlink(missing_ok=True)
                    if mode=='remux':continue
                    raise
                temp.replace(target);result.update(path=str(target),mode=mode,fallbackAvailable=mode=='remux')
                write(metadata,result);write(directory/'status.json',dict(stage='ready',source=str(source),duration=duration));return result
        except BaseException as error:
            for p in directory.glob('*.partial.mp4'):p.unlink(missing_ok=True)
            write(directory/'status.json',dict(stage='failed',source=str(source),duration=duration,error=str(error)[:500]))
            raise


def thumbnail(root,source,tools,seconds):
    """One lazy thumbnail per five source seconds; no conversion-state mutation."""
    source=Path(source).resolve()
    if isinstance(seconds,bool) or not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or seconds<0:raise ValueError('Invalid thumbnail time.')
    info=json.loads(subprocess.check_output([tools['ffprobe'],'-v','error','-show_format','-of','json',str(source)],timeout=8))
    duration=float(info['format']['duration'])
    if not math.isfinite(duration) or not 0<duration<=14400:raise ValueError('Invalid thumbnail duration.')
    point=min(max(0,duration-.1),int(seconds/5)*5)
    directory=folder(root,source)/'thumbnails';directory.mkdir(parents=True,exist_ok=True)
    target=directory/f'{int(point*1000)}.jpg'
    with exclusive(directory/'thumbnail.lock'):
        if not target.is_file():
            temp=target.with_suffix('.partial.jpg')
            try:
                subprocess.run([tools['ffmpeg'],'-v','error','-nostdin','-y','-ss',f'{point:.3f}','-i',str(source),'-map','0:v:0','-frames:v','1','-threads','2','-vf','scale=256:-2','-q:v','4',str(temp)],check=True,timeout=8,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                temp.replace(target)
            finally:temp.unlink(missing_ok=True)
    return dict(path=str(target),seconds=point)
