"""Decode owned audio to Whisper PCM without PyAV's version-specific open API.

faster-whisper 1.2.1 passes metadata_errors to av.open, which PyAV 19 removed.
All deployed runtimes already pin SoundFile, NumPy and SciPy. Passing waveform
arrays uses Whisper's supported PCM input and avoids patching third-party code.
"""
from pathlib import Path


def load(audio):
    import numpy as np
    if not isinstance(audio,(str,Path)):return audio
    import soundfile as sf
    from scipy.signal import resample_poly
    from math import gcd
    samples,rate=sf.read(audio,dtype='float32',always_2d=True)
    if not len(samples) or not rate:raise ValueError('The speech recording is empty.')
    mono=samples.mean(axis=1)
    if not np.isfinite(mono).all():raise ValueError('The speech recording contains invalid samples.')
    if rate!=16000:
        factor=gcd(int(rate),16000);mono=resample_poly(mono,16000//factor,int(rate)//factor)
    return np.ascontiguousarray(mono,dtype=np.float32)
