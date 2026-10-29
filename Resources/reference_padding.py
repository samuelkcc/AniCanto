"""Fill a short voice reference with scene room tone instead of digital silence.

Most lines in an episode are shorter than the reference floor the voice engines
accept. The previous pass padded them with digital silence. A reference that
ends in two or three seconds of silence gives the engine no room ambience and no
speech energy at the end, which is one reason a finished take can sound flat.

This pass fills the same length with real room tone taken from the nearest quiet
gap in the same scene. A candidate is accepted only when it is measurably quieter
than the speech in the reference, so music, sound effects and other speakers are
never pulled into a reference. When no candidate is safe, the old silence padding
is used unchanged.
"""
import math

REVISION = 'scene-tone-padding-245'
MINIMUM_SECONDS = 3.1
GUARD_SECONDS = .06
FADE_MILLISECONDS = 18
MAX_TONE_TO_SPEECH = .12      # Median fill level stays about 18 dB under speech level.
MAX_TONE_PEAK = .3            # No fill frame may approach speech level.
MIN_TONE_LEVEL = 4e-4


def levels(samples, sr):
    """Short-time RMS in 20 ms frames."""
    import numpy as np
    x = np.asarray(samples, dtype=np.float32).reshape(-1)
    if sr <= 0 or not len(x):
        return np.zeros(0, dtype=np.float32)
    step = max(1, round(sr * .02))
    frames = x[:len(x) // step * step].reshape(-1, step) if len(x) >= step else x.reshape(1, len(x))
    return np.sqrt(np.mean(frames * frames, axis=1))


def speech_ranges(cues, duration):
    """Source intervals that hold a witnessed line, subtitle window included."""
    spans = []
    for cue in cues:
        a = min(float(cue.get('start', 0) or 0), float(cue.get('speechStart', cue.get('start', 0)) or 0))
        b = max(float(cue.get('end', 0) or 0), float(cue.get('speechEnd', cue.get('end', 0)) or 0))
        if b > a:
            spans.append((max(0., a), min(duration, b)))
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1] + GUARD_SECONDS * 2:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def tone_candidates(ranges, clip_end, duration, need_seconds):
    """Fill windows inside a gap, ordered by distance from the end of the clip."""
    gaps = []
    cursor = 0.
    for a, b in list(ranges) + [(duration, duration)]:
        if a > cursor:
            gaps.append((cursor, min(a, duration)))
        cursor = max(cursor, b)
    scored = []
    for a, b in gaps:
        if b - a < need_seconds:
            continue
        for start, end in ((a, a + need_seconds), (b - need_seconds, b)):
            scored.append((min(abs(start - clip_end), abs(end - clip_end)), start, end))
    scored.sort()
    return [(start, end) for _, start, end in scored]


def is_quiet(fill, sr, speech_rms):
    """True when the fill is room tone, not music, an effect or somebody speaking."""
    import numpy as np
    frame_levels = levels(fill, sr)
    if not len(frame_levels):
        return False
    speech_rms = max(1e-4, float(speech_rms))
    if float(np.median(frame_levels)) > max(MIN_TONE_LEVEL, MAX_TONE_TO_SPEECH * speech_rms):
        return False
    if float(np.quantile(frame_levels, .95)) > max(MIN_TONE_LEVEL * 4, MAX_TONE_PEAK * speech_rms):
        return False
    return True


def crossfade(head, tail, sr):
    """Equal-power seam between the clip and the fill; total length is kept."""
    import numpy as np
    n = min(len(head), len(tail), max(0, round(sr * FADE_MILLISECONDS / 1000)))
    head = np.asarray(head, dtype=np.float32)
    tail = np.asarray(tail, dtype=np.float32)
    if n <= 0:
        return np.concatenate([head, tail])
    ramp = np.linspace(0., 1., n, dtype=np.float32)
    return np.concatenate([head[:-n], head[-n:] * (1 - ramp) + tail[:n] * ramp, tail[n:]]).astype(np.float32)


def pad(clip, sr, clip_end, need_frames, read, cues, duration):
    """Return (samples, method, sourceRange). Silence remains the fallback."""
    import numpy as np
    if need_frames <= 0:
        return clip, 'none', None
    speech_rms = float(np.sqrt(np.mean(np.asarray(clip, dtype=np.float32) ** 2))) if len(clip) else 0.
    # The seam is shared by both blocks, so the fill is read slightly longer and the
    # finished reference keeps the exact engine floor.
    seam = min(len(clip), max(0, round(sr * FADE_MILLISECONDS / 1000)))
    fill_frames = int(need_frames) + seam
    for start, end in tone_candidates(speech_ranges(cues, duration), clip_end, duration, fill_frames / sr + .02):
        try:
            fill = read(start, end)
        except (ValueError, OSError, RuntimeError):
            continue
        if fill is None or len(fill) < fill_frames:
            continue
        if not is_quiet(fill[:fill_frames], sr, speech_rms):
            continue
        return crossfade(clip, fill[:fill_frames], sr), 'scene-tone', [round(start, 3), round(end, 3)]
    return np.pad(np.asarray(clip, dtype=np.float32), (0, int(need_frames))), 'silence', None
