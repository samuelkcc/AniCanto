"""Conservative digital-impulse evidence, not a perceptual rasp detector.

Isolated one-sample spikes are measurable. A gravelly character voice, consonants,
breaths and model timbre cannot reliably be diagnosed from this heuristic.
"""
import numpy as np

REVISION='isolated-digital-impulses-1'

def float_audio(audio):
    raw=np.asarray(audio)
    x=raw.astype(np.float32)
    if np.issubdtype(raw.dtype,np.integer):x/=max(abs(np.iinfo(raw.dtype).min),np.iinfo(raw.dtype).max)
    if x.ndim==2:x=x.mean(axis=1)
    return x.reshape(-1)

def measure(audio,sr):
    x=float_audio(audio)
    report=dict(revision=REVISION,metric='isolated sample impulses; not audible voice quality certification',valid=False,warnings=[])
    if sr<=0 or not len(x) or not np.isfinite(x).all():return report
    report.update(valid=True,seconds=round(len(x)/sr,4),peak=float(np.max(abs(x))),clippedFraction=float(np.mean(abs(x)>=.999)))
    if len(x)<5:return dict(report,impulses=0,impulsesPerSecond=0)
    centre=x[2:-2];left=x[1:-3];right=x[3:-1]
    # The centre must be large with both immediate and next neighbours quiet.
    # Periodic carriers, square edges, multi-sample bursts and broad frication
    # intentionally fail this narrow digital-corruption predicate.
    adjacent=np.maximum.reduce([abs(left),abs(right),abs(x[:-4]),abs(x[4:])])
    candidates=np.flatnonzero((abs(centre)>.35) & (adjacent<.06) & (abs(centre)>adjacent*10+.2))
    count=len(candidates);rate=count/max(.1,len(x)/sr)
    report.update(impulses=int(count),impulsesPerSecond=round(rate,3),impulseTimes=[round((int(n)+2)/sr,5) for n in candidates[:32]])
    if count>=3 and rate>=1:report['warnings'].append('repeated-digital-impulses')
    return report

def compare(raw,conditioned,sr,reference=None):
    before,after=measure(raw,sr),measure(conditioned,sr)
    evidence=dict(raw=before,conditioned=after,suspectedCauses=[],certifiedCause=False)
    if before.get('clippedFraction',0)>.005:evidence['suspectedCauses'].append('raw-generation-clipping')
    if before['warnings']:evidence['suspectedCauses'].append('raw-generation-digital-impulses')
    if not before['warnings'] and after['warnings']:evidence['suspectedCauses'].append('conditioning-digital-impulses')
    if reference is not None:
        evidence['reference']=reference
        if reference.get('warnings') or reference.get('clippedFraction',0)>.005:evidence['suspectedCauses'].append('reference-signal-risk')
    return evidence

def measure_file(path):
    import wave
    try:
        with wave.open(str(path)) as f:
            width,channels,sr=f.getsampwidth(),f.getnchannels(),f.getframerate()
            raw=f.readframes(f.getnframes())
        if width==1:samples=(np.frombuffer(raw,dtype=np.uint8).astype(np.float32)-128)/128
        elif width in (2,4):samples=float_audio(np.frombuffer(raw,dtype='<i2' if width==2 else '<i4'))
        elif width==3:
            b=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3).astype(np.int32)
            values=b[:,0]|(b[:,1]<<8)|(b[:,2]<<16);values=np.where(values&(1<<23),values-(1<<24),values)
            samples=values.astype(np.float32)/(1<<23)
        else:raise ValueError('Unsupported PCM sample width')
        return measure(samples.reshape(-1,channels),sr)
    except (wave.Error,ValueError):
        # Float WAV support is optional in the lightweight media worker. The
        # heavy TTS runtime has soundfile, but ordinary PCM needs only stdlib.
        try:
            import soundfile as sf
            samples,sr=sf.read(path,dtype='float32')
            return measure(samples,sr)
        except (ImportError,OSError,ValueError,RuntimeError) as error:
            return dict(revision=REVISION,valid=False,status='measurement-unavailable',warnings=[],error=str(error)[:200])
    except (OSError,RuntimeError) as error:
        # This supplemental diagnostic must not discard media that FFmpeg can
        # decode. Unavailable is explicitly different from a passed measurement.
        return dict(revision=REVISION,valid=False,status='measurement-unavailable',warnings=[],error=str(error)[:200])
