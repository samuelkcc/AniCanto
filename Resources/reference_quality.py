"""Reference ranking and bounded hiss reduction, not certified source purity.

Background-stem energy is a risk indicator, never proof of another speaker.
Measurements do not change speech timing or use another engine's generated voice.
"""
import math,wave,subprocess
from pathlib import Path
import numpy as np

REVISION='reference-quality-2'

def measure(samples,sr,background=None):
    x=np.asarray(samples,dtype=np.float32)
    if x.ndim>1:x=x.mean(axis=1)
    report=dict(revision=REVISION,score=0.,warnings=[],duration=round(len(x)/sr,3) if sr>0 else 0)
    if sr<=0 or len(x)<sr*.1 or not np.isfinite(x).all():
        report['warnings']=['invalid-audio'];return report
    step=max(1,round(sr*.02));frames=x[:len(x)//step*step].reshape(-1,step)
    levels=np.sqrt(np.mean(frames*frames,axis=1))
    active=levels>=max(.001,float(np.max(levels))*.2)
    fraction=float(np.mean(active));rms=float(np.sqrt(np.mean(levels[active]**2))) if np.any(active) else 0
    floor=float(np.quantile(levels,.15));db=lambda v:round(20*math.log10(max(1e-9,v)),2)
    fft=np.abs(np.fft.rfft(frames*np.hanning(step),axis=1))**2+1e-12
    frequencies=np.fft.rfftfreq(step,1/sr);band=fft[:,(frequencies>=300)&(frequencies<=min(8000,sr/2))]
    flatness=float(np.median(np.exp(np.mean(np.log(band),axis=1))/np.mean(band,axis=1)))
    clipping=float(np.mean(np.abs(x)>=.999));contrast=db(rms)-db(floor)
    score=100-min(35,(1-fraction)*35)-min(50,clipping*3000)
    warnings=report['warnings']
    if rms<.001 or fraction<.15:warnings.append('insufficient-speech');score-=60
    if fraction<.4:warnings.append('mostly-silence');score-=15
    if clipping>.005:warnings.append('source-clipping')
    # Require broadband, persistent energy: loud speech alone isn't noise.
    if floor>.008 and contrast<16 and flatness>.12:
        warnings.append('stationary-noise-risk');score-=25
    if background is not None:
        b=np.asarray(background,dtype=np.float32)
        if b.ndim>1:b=b.mean(axis=1)
        n=min(len(b),len(x));bg=float(np.sqrt(np.mean(b[:n]**2))) if n else 0
        ratio=db(bg)-db(rms)
        report['backgroundToVoiceDB']=round(ratio,2)
        if ratio>6:warnings.append('loud-background-in-source');score-=min(20,ratio)
        # Waveform correlation is evidence of a shared residual component,
        # unlike background volume alone. It is not speaker/speech separation.
        if n and bg>.001 and rms>.001:
            a=x[:n]-np.mean(x[:n]);bb=b[:n]-np.mean(b[:n])
            correlation=abs(float(a@bb))/max(1e-12,float(np.linalg.norm(a)*np.linalg.norm(bb)))
            report['backgroundCorrelation']=round(correlation,4)
            if correlation>.55 and ratio>-8:
                warnings.append('shared-background-residual');score-=30
    report.update(score=round(max(0,score),2),activeFraction=round(fraction,3),activeRMSDB=db(rms),noiseFloorDB=db(floor),contrastDB=round(contrast,2),spectralFlatness=round(flatness,4),clippedFraction=round(clipping,5))
    return report

def conditioned_quality(measured,evidence=None):
    """Retain separation evidence after reading a standalone reference WAV.

    Engine conditioning cannot reconstruct the original background comparison
    from the cropped WAV. Dropping that evidence would promote contaminated
    automatic references above their clean, same-role alternatives.
    """
    result=dict(measured);result['warnings']=list(measured.get('warnings',[]))
    if isinstance(evidence,dict):
        for key in ('backgroundToVoiceDB','backgroundCorrelation'):
            if key in evidence:result[key]=evidence[key]
        residual=[w for w in evidence.get('warnings',[]) if w in ('loud-background-in-source','shared-background-residual')]
        for warning in residual:
            if warning not in result['warnings']:result['warnings'].append(warning)
        if residual:result['score']=min(result.get('score',0),evidence.get('score',0))
    return result

def read(path):
    with wave.open(str(path)) as f:
        width=f.getsampwidth();raw=f.readframes(f.getnframes())
        if width==1:x=(np.frombuffer(raw,dtype=np.uint8).astype(np.float32)-128)/128
        elif width==2:x=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
        elif width==3:
            b=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3).astype(np.int32)
            values=b[:,0] | (b[:,1]<<8) | (b[:,2]<<16)
            x=((values^0x800000)-0x800000).astype(np.float32)/8388608
        elif width==4:x=np.frombuffer(raw,dtype='<i4').astype(np.float32)/2147483648
        else:raise ValueError('Unsupported integer PCM reference.')
        return x.reshape(-1,f.getnchannels()).mean(axis=1),f.getframerate()

def clean(source,folder,ffmpeg,run):
    source=Path(source);samples,sr=read(source);before=measure(samples,sr)
    report=dict(before=before,after=before,applied=False,method='unchanged-original')
    if 'stationary-noise-risk' not in before['warnings']:return source,report
    target=Path(folder)/'denoised.wav'
    # Six dB maximum reduction on the reference only; no aggressive music gate.
    try:
        run([ffmpeg,'-v','error','-y','-i',source,'-af','highpass=f=70,afftdn=nr=6:nf=-35:tn=1','-c:a','pcm_s16le',target])
        changed,rate=read(target);after=measure(changed,rate)
        if (len(changed)==len(samples) and rate==sr and after['activeFraction']>=before['activeFraction']*.8
            and after['activeRMSDB']>=before['activeRMSDB']-4 and after['noiseFloorDB']<before['noiseFloorDB']-.5
            and 'source-clipping' not in after['warnings']):
            report.update(after=after,applied=True,method='bounded-6dB-reference-hiss-reduction');return target,report
        report['reason']='cleaning-did-not-preserve-sufficient-speech'
    except (ValueError,OSError,RuntimeError,subprocess.SubprocessError) as error:report['reason']=str(error)[:200]
    return source,report
