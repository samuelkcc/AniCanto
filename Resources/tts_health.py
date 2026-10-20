"""Signal health gates, not a language or speaker-identity certification."""
import math
import numpy as np
from acoustics import activity

def duration_limit(text,target=None):
    count=sum(c.isalnum() for c in text)
    return min(90,max(12,count*.6+6,3*float(target or 0)))

def problems(audio,sr,text='',target=None,tokens=None,budget=None):
    x=np.asarray(audio)
    if np.issubdtype(x.dtype,np.integer):x=x.astype(np.float32)/max(abs(np.iinfo(x.dtype).min),np.iinfo(x.dtype).max)
    x=x.astype(np.float32).reshape(-1)
    if sr<=0 or not len(x) or not np.isfinite(x).all():return ['invalid-audio']
    result=[]
    if len(x)/sr<.1 or not activity(x,sr):result.append('no-audible-voice')
    if np.mean(np.abs(x)>=.999)>.005:result.append('clipping')
    from signal_quality import measure
    result.extend(measure(x,sr)['warnings'])
    if len(x)/sr>duration_limit(text,target):result.append('runaway-duration')
    if tokens is not None and budget is not None and tokens>=budget:result.append('generation-limit')
    return result
