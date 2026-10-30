"""Keep cloud-drive media readable by FFmpeg without changing the user's original."""
import hashlib
import os
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import time


def cloud_or_remote(source, storage):
    path = PureWindowsPath(str(source))
    store = PureWindowsPath(str(storage))
    parts = {part.casefold() for part in path.parts}
    cloud = bool(parts & {'my drive', 'google drive', 'onedrive'})
    other_drive = bool(path.drive and store.drive and path.drive.casefold() != store.drive.casefold())
    return cloud or other_drive or str(source).startswith('\\\\')


def probe(source, ffprobe, timeout=45):
    command = [str(ffprobe), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(source)]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError('Video metadata could not be read in time. If the video is in a cloud folder, make it available offline and retry.') from error
    if result.returncode:
        detail = result.stderr.decode('utf-8', errors='replace').strip()[-1000:]
        raise RuntimeError(f'Cannot read video metadata: {source}\n{detail or f"ffprobe exit code {result.returncode}"}')
    return result.stdout


def accessible(source, ffprobe, storage, emit=None, *, allow_copy=True):
    """Probe a source, then stage a failing remote source into the owned cache."""
    source = Path(source)
    remote = cloud_or_remote(source, storage)
    stat = source.stat()
    key = hashlib.sha256(f'{source}|{stat.st_size}|{stat.st_mtime_ns}'.encode()).hexdigest()[:24]
    directory = Path(storage)/'cache'/'source-media'/key
    target = directory/source.name
    if remote and target.is_file() and target.stat().st_size == stat.st_size:
        try:
            return target, probe(target, ffprobe)
        except RuntimeError:
            target.unlink(missing_ok=True)
    original_error = None
    try:
        return source, probe(source, ffprobe)
    except RuntimeError as error:
        if not allow_copy or not remote:
            raise
        original_error = str(error)
    directory.mkdir(parents=True, exist_ok=True)
    # Retain the filename so exports and same-folder subtitle discovery keep
    # the original episode identity after moving the media into local cache.
    if not target.is_file() or target.stat().st_size != stat.st_size:
        free = shutil.disk_usage(directory).free
        if free < stat.st_size + 1024**3:
            raise RuntimeError(f'{original_error}\nA local copy may fix cloud-drive access, but there is not enough free disk space.')
        if emit: emit('Preparing source video', 'Reading the cloud-drive video into local cache before conversion.', 0)
        partial = directory/f'source.{os.getpid()}.partial'
        try:
            with partial.open('wb') as local:
                copied=0;next_report=0;stalls=0
                deadline=time.monotonic()+180
                original=source.open('rb')
                try:
                    while copied<stat.st_size:
                        try:chunk=original.read(min(4*1024*1024,stat.st_size-copied))
                        except OSError:chunk=b''
                        if chunk:
                            local.write(chunk);copied+=len(chunk);stalls=0
                            if emit and (copied>=next_report or copied>=stat.st_size):
                                emit('Preparing source video', 'Reading the cloud-drive video into local cache before conversion.', min(1,copied/max(1,stat.st_size)))
                                next_report=copied+32*1024*1024
                            continue
                        stalls+=1
                        if stalls>=30 or time.monotonic()>=deadline:
                            raise OSError(f'The cloud drive supplied only {copied:,} of {stat.st_size:,} bytes. Wait for the file to finish syncing or make it available offline, then retry.')
                        if emit:emit('Preparing source video', 'Waiting for the cloud drive to supply the remaining video.', copied/max(1,stat.st_size))
                        original.close()
                        time.sleep(3)
                        original=source.open('rb')
                        original.seek(copied)
                finally:original.close()
            if partial.stat().st_size != stat.st_size:
                raise OSError('The copied video is incomplete.')
            partial.replace(target)
            for extension in ('.srt', '.ass', '.vtt'):
                sidecar = source.with_suffix(extension)
                if sidecar.is_file():
                    shutil.copy2(sidecar, target.with_suffix(extension))
        except OSError as error:
            partial.unlink(missing_ok=True)
            raise RuntimeError(f'{original_error}\nLocal cache copy also failed: {error}') from error
    try:
        data = probe(target, ffprobe)
    except RuntimeError as error:
        target.unlink(missing_ok=True)
        raise RuntimeError(f'{original_error}\nLocal cache retry failed: {error}') from error
    if emit: emit('Preparing source video', 'The cloud-drive video is readable from local cache.', 1)
    return target, data
