"""Vectorized PCM accumulation; bounded temporary memory and identical rounding."""
import array
import numpy as np

def add(timeline,pcm,offset,gain=1):
    count=min(len(pcm),len(timeline)-offset)
    if count<=0:return
    destination=np.frombuffer(timeline,dtype=np.int32,count=count,offset=offset*4)
    source=np.frombuffer(pcm,dtype=np.int16,count=count)
    destination+=source if gain==1 else np.rint(source.astype(np.float64)*gain).astype(np.int32)

def finish(timeline,ceiling=32000):
    view=np.frombuffer(timeline,dtype=np.int32)
    block=1_000_000
    peak=max((float(np.abs(view[i:i+block].astype(np.float64)).max()) for i in range(0,len(view),block)),default=0)
    gain=min(1,ceiling/max(1,peak));result=array.array('h')
    for i in range(0,len(view),block):
        result.frombytes(np.rint(view[i:i+block].astype(np.float64)*gain).astype('<i2').tobytes())
    return result,gain
