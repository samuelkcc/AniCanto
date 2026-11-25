"""Check picture coverage independently of the movie and soundtrack clocks."""
import math
from fractions import Fraction


class PictureCoverageError(ValueError):
    pass


def primary_picture(streams):
    return next((stream for stream in streams if stream.get('codec_type') == 'video'
                 and not stream.get('disposition', {}).get('attached_pic')), None)


def verify(streams, expected):
    picture = primary_picture(streams)
    if picture is None:
        raise PictureCoverageError('輸出驗證失敗：找不到可播放的畫面。')
    try:
        start = float(picture.get('start_time', 0))
        if picture.get('duration_ts') not in (None, 'N/A') and picture.get('time_base'):
            duration = float(int(picture['duration_ts']) * Fraction(picture['time_base']))
        else:
            duration = float(picture['duration'])
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError) as error:
        raise PictureCoverageError('輸出驗證失敗：無法確認畫面長度。') from error
    if (not math.isfinite(start + duration) or duration <= 0
            or abs(start) > .5 or duration < expected - .5
            or start + duration < expected - .5):
        raise PictureCoverageError('輸出驗證失敗：畫面未覆蓋預定片長。')
    return dict(start=start, duration=duration, end=start + duration)


def reencode(command):
    """Use the saved export retry to recover a failed packet copy."""
    command = list(command)
    for index in range(len(command) - 1):
        if command[index:index + 2] == ['-c:v', 'copy']:
            command[index + 1:index + 2] = ['libx264', '-preset', 'veryfast',
                                           '-crf', '20', '-pix_fmt', 'yuv420p']
            if '-tag:v' in command:
                tag = command.index('-tag:v')
                del command[tag:tag + 2]
            return command
    return command
