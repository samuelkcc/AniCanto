"""Keep provider media readable by FFmpeg without changing the user's original."""
import hashlib
import os
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import time

from source_preparation import (
    MediaUnreadable,
    ProviderReadInterrupted,
    hydration_reason,
    provider,
)

# The reader gets one short window, then one longer window, before any full local copy.
FIRST_WINDOW = 45
SECOND_WINDOW = 90
# A stalled provider is judged by idle time only; a large movie may stream for an hour.
# No idle limit ends this copy. A one gigabyte provider movie can take several minutes per
# stretch, so the idle count only changes what the user is told. The user stops the job to
# end the wait; a provider that fails outright still raises when its file cannot be opened.
IDLE_STALLS = 60
STALL_PAUSE = 3
# Once the provider is quiet, one notice goes out every this many stalls.
QUIET_REPORT_STALLS = 20
SOURCE_PHRASE = {
    'icloud': 'iCloud Drive file',
    'google-drive': 'Google Drive file',
    'onedrive': 'OneDrive file',
    'network': 'network share file',
    'local': 'local file',
}


def source_phrase(kind):
    return SOURCE_PHRASE.get(kind, kind)


def needs_local_stage(source, storage):
    """True when a provider still owns the bytes, so a local cache copy can help."""
    if cloud_or_remote(source, storage):
        return True
    try:
        return bool(hydration_reason(source))
    except OSError:
        return False


def cloud_or_remote(source, storage):
    path = PureWindowsPath(str(source))
    store = PureWindowsPath(str(storage))
    parts = {part.casefold() for part in path.parts}
    cloud = bool(parts & {'my drive', 'google drive', 'onedrive'})
    other_drive = bool(path.drive and store.drive and path.drive.casefold() != store.drive.casefold())
    return cloud or other_drive or str(source).startswith('\\\\')


def probe(source, ffprobe, timeout=FIRST_WINDOW):
    """Read metadata. A slow provider and damaged media are reported as different faults."""
    command = [str(ffprobe), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(source)]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        kind = provider(source)
        raise ProviderReadInterrupted(
            f'The {source_phrase(kind)} did not answer the media reader within {timeout} seconds. '
            'The provider may still be sending the video.'
        ) from error
    if result.returncode:
        detail = result.stderr.decode('utf-8', errors='replace').strip()[-1000:]
        raise MediaUnreadable(f'Cannot read video metadata: {source}\n{detail or f"ffprobe exit code {result.returncode}"}')
    return result.stdout


def probe_with_second_window(source, ffprobe, *, first=FIRST_WINDOW, second=SECOND_WINDOW):
    """A big provider movie can answer after a short probe. One longer window comes before any copy."""
    try:
        return probe(source, ffprobe, first)
    except ProviderReadInterrupted:
        return probe(source, ffprobe, second)


def accessible(source, ffprobe, storage, emit=None, *, allow_copy=True):
    """Probe a source, then stage a source the provider has not released into the owned cache."""
    source = Path(source)
    remote = needs_local_stage(source, storage)
    phrase = source_phrase(provider(source))
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
        return source, probe_with_second_window(source, ffprobe)
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
            raise RuntimeError(f'{original_error}\nA local copy may fix provider access, but there is not enough free disk space.')
        if emit: emit('Preparing source video', f'Reading the {phrase} into local cache before conversion.', 0)
        partial = directory/f'source.{os.getpid()}.partial'
        try:
            with partial.open('wb') as local:
                copied=0;next_report=0;stalls=0
                original=source.open('rb')
                try:
                    while copied<stat.st_size:
                        try:chunk=original.read(min(4*1024*1024,stat.st_size-copied))
                        except OSError:chunk=b''
                        if chunk:
                            local.write(chunk);copied+=len(chunk);stalls=0
                            if emit and (copied>=next_report or copied>=stat.st_size):
                                emit('Preparing source video', f'Reading the {phrase} into local cache before conversion.', min(1,copied/max(1,stat.st_size)))
                                next_report=copied+32*1024*1024
                            continue
                        stalls+=1
                        # The bytes already copied stay in the partial file, so a slow provider
                        # never restarts the download and never fails the job on its own.
                        if emit and (stalls<IDLE_STALLS or stalls%QUIET_REPORT_STALLS==0):
                            message=(f'Waiting for the {phrase} to supply the remaining video.'
                                     if stalls<IDLE_STALLS else
                                     f'The {phrase} has sent {copied:,} of {stat.st_size:,} bytes and nothing for {stalls*STALL_PAUSE} seconds. AniCanto keeps these bytes and does not time out. Stop this video in the queue to end the wait.')
                            emit('Preparing source video', message, min(1,copied/max(1,stat.st_size)))
                        original.close()
                        time.sleep(STALL_PAUSE)
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
    if emit: emit('Preparing source video', f'The {phrase} is readable from local cache.', 1)
    return target, data
