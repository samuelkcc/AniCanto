"""Volume capacity for explicit downloads, with native APFS reclaimable space."""
import ctypes
import os
from pathlib import Path
import shutil
import sys


def important_capacity(path):
    """Use the public CFURL API. Never remove caches or reserve disk blocks."""
    ctypes.CDLL('/System/Library/Frameworks/Foundation.framework/Foundation')
    cf = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    pointer = ctypes.c_void_p
    cf.CFURLCreateFromFileSystemRepresentation.argtypes = [pointer, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool]
    cf.CFURLCreateFromFileSystemRepresentation.restype = pointer
    cf.CFURLCopyResourcePropertyForKey.argtypes = [pointer, pointer, ctypes.POINTER(pointer), ctypes.POINTER(pointer)]
    cf.CFURLCopyResourcePropertyForKey.restype = ctypes.c_bool
    cf.CFNumberGetValue.argtypes = [pointer, ctypes.c_int, pointer]
    cf.CFNumberGetValue.restype = ctypes.c_bool
    cf.CFRelease.argtypes = [pointer]
    cf.CFRelease.restype = None
    encoded = os.fsencode(path)
    url = cf.CFURLCreateFromFileSystemRepresentation(None, encoded, len(encoded), True)
    value, error = pointer(), pointer()
    if not url:
        return None
    try:
        key = pointer.in_dll(cf, 'kCFURLVolumeAvailableCapacityForImportantUsageKey')
        if not cf.CFURLCopyResourcePropertyForKey(url, key, ctypes.byref(value), ctypes.byref(error)) or not value:
            return None
        number = ctypes.c_longlong()
        if not cf.CFNumberGetValue(value, 4, ctypes.byref(number)):
            return None
        return number.value if number.value >= 0 else None
    finally:
        for item in (value, error, url):
            if item:
                cf.CFRelease(item)


def capacity(path):
    directory = Path(path).resolve()
    while not directory.exists() and directory != directory.parent:
        directory = directory.parent
    disk = shutil.disk_usage(directory)
    important = None
    if sys.platform == 'darwin':
        try:
            important = important_capacity(directory)
        except (OSError, ValueError, AttributeError):
            pass
    # Reject invalid native results. Restricted processes can report zero.
    if not isinstance(important, int) or isinstance(important, bool) or not 0 <= important <= disk.total:
        important = None
    return dict(volumePath=str(directory), ordinaryFreeBytes=disk.free,
                importantAvailableBytes=important,
                availableBytes=max(disk.free, important or 0), totalBytes=disk.total,
                method='important-usage' if important is not None and important > disk.free else 'ordinary-free')


def require_space(path, download_bytes, reserve_bytes=2_000_000_000):
    result = capacity(path)
    required = max(0, int(download_bytes)) + max(0, int(reserve_bytes))
    result.update(downloadBytes=max(0, int(download_bytes)), reserveBytes=max(0, int(reserve_bytes)), requiredBytes=required)
    if result['availableBytes'] < required:
        raise ValueError('Insufficient storage on '+result['volumePath']+': available '
                         + f"{result['availableBytes']/1e9:.1f} GB; required {required/1e9:.1f} GB"
                         + f" (includes {result['reserveBytes']/1e9:.1f} GB reserve).")
    return result


def remaining_bytes(files, base):
    required = 0
    for item in files:
        target = Path(base) / item['path']
        size = int(item.get('size', 0))
        if target.is_file() and target.stat().st_size == size:
            continue
        partial = target.with_name(target.name + '.partial')
        retained = min(size, partial.stat().st_size) if partial.is_file() else 0
        required += max(0, size - retained)
    return required
