"""Apple media-engine encoding with one software retry; stream-copy is untouched."""
from functools import lru_cache
import subprocess,sys

@lru_cache(maxsize=4)
def available(ffmpeg):
    if sys.platform!='darwin':return False
    try:
        p=subprocess.run([str(ffmpeg),'-v','error','-encoders'],capture_output=True,timeout=5)
        return p.returncode==0 and b'h264_videotoolbox' in p.stdout
    except (OSError,subprocess.TimeoutExpired):return False

def hardware_command(command):
    result=[];i=0
    while i<len(command):
        value=command[i]
        if value in ('-preset','-crf'):
            i+=2;continue
        result.append('h264_videotoolbox' if value=='libx264' else value);i+=1
    return result[:-1]+['-q:v','65','-allow_sw','0']+result[-1:]

def encode(run,command,cfg,emit):
    if sys.platform=='win32':
        from native_video import encode as native_encode
        return native_encode(run,command,cfg,emit)
    if 'libx264' not in command or cfg.get('videoAcceleration','auto')=='software' or not available(cfg['ffmpeg']):
        return run(command)
    emit('影片加速','使用 Apple 硬件編碼；保留音軌同字幕設定。')
    try:return run(hardware_command(command))
    except RuntimeError as error:
        message=str(error).lower()
        if not any(t in message for t in ('videotoolbox','vtcompression','cannot create compression session','encoder not found')):raise
        emit('影片加速','硬件編碼未能使用，改用軟件編碼一次：'+str(error)[:200])
        return run(command)
