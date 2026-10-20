"""Bounded, pause-preserving speech gain. Active RMS is a proxy, not LUFS.

Never denoise, change timing, or turn silence into speech. Keep original takes
and conditioning recordings; derived WAVs and their measurements are auditable.
"""
import array, hashlib, json, math, sys, wave
from pathlib import Path

REVISION = 'active-rms-bounded-2'

def condition(samples, sr, reference=False, max_gain_db=None):
    x = [float(v) for v in samples]
    report = dict(revision=REVISION, metric='active-frame RMS dBFS (not LUFS)', gainDB=0.0, warnings=[])
    if sr <= 0 or not x or not all(math.isfinite(v) for v in x):
        report['warnings'] = ['invalid-audio']; return x, report
    peak = max(abs(v) for v in x)
    step = max(1, round(sr * .02))
    levels = [sum(v*v for v in x[i:i+step])/len(x[i:i+step]) for i in range(0,len(x),step)]
    threshold = max(.0005**2, max(levels)*.04)
    active = [v for v in levels if v >= threshold]
    rms = math.sqrt(sum(active)/len(active)) if active else 0
    db = lambda v: round(20*math.log10(max(1e-12,v)),2)
    report.update(inputPeakDB=db(peak), inputActiveRMSDB=db(rms), activeSeconds=round(len(active)*step/sr,3))
    if rms < .001 or len(active)*step/sr < .06:
        report['warnings'].append('insufficient-signal'); return x, report
    if sum(abs(v)>=.999 for v in x)/len(x) > .005:
        report['warnings'].append('source-clipping')
    # Preserve the energy of a clear original reference. The old upper edge
    # attenuated ordinary expressive speech by ~8 dB before voice cloning.
    # Output uses a narrower band, so -24 dBFS speech is no longer accepted
    # without compensation. Peak headroom still bounds every gain operation.
    target, low, high, maximum = (-20,-26,-14,6) if reference else (-19,-20.5,-16,12)
    if max_gain_db is not None and not reference:
        if not math.isfinite(max_gain_db) or not 0<=max_gain_db<=24:raise ValueError('Invalid bounded speech gain.')
        maximum=max_gain_db
    report['maximumGainDB']=maximum
    wanted = target-db(rms) if db(rms)<low or db(rms)>high else 0
    gain = min(maximum, max(-12,wanted), db(10**(-1.5/20)/max(peak,1e-12)))
    # A constant gain preserves expressive dynamics and exact silence positions.
    scale = 10**(gain/20)
    out = [v*scale for v in x]
    report.update(gainDB=round(gain,2), outputPeakDB=db(peak*scale), outputActiveRMSDB=db(rms*scale))
    if wanted > gain+.5: report['warnings'].append('gain-limited')
    return out, report

def prepare_file(source, folder, reference=False):
    source, folder = Path(source), Path(folder)
    identity = dict(sourceSHA=hashlib.sha256(source.read_bytes()).hexdigest(), revision=REVISION, reference=reference)
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24]
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/f'{key}.wav'; manifest=target.with_suffix('.level.json')
    if target.is_file() and manifest.is_file():return target,json.loads(manifest.read_text())
    with wave.open(str(source)) as f:
        if f.getsampwidth()!=2:raise ValueError('Speech conditioning requires PCM16 WAV.')
        params=f.getparams();pcm=array.array('h',f.readframes(f.getnframes()))
    if sys.byteorder!='little':pcm.byteswap()
    channels=params.nchannels
    mono=[sum(pcm[i:i+channels])/(32768*channels) for i in range(0,len(pcm),channels)]
    _,report=condition(mono,params.framerate,reference)
    ceiling=20*math.log10((32768*10**(-1.5/20))/max(1,max(abs(v) for v in pcm)))
    previous_gain=report['gainDB']
    report['gainDB']=round(min(previous_gain,ceiling),2)
    if previous_gain>report['gainDB']+.5 and 'gain-limited' not in report['warnings']:report['warnings'].append('gain-limited')
    report['inputPeakDB']=round(20*math.log10(max(1e-12,max(abs(v) for v in pcm)/32768)),2)
    report['outputPeakDB']=round(report['inputPeakDB']+report['gainDB'],2)
    if 'inputActiveRMSDB' in report:report['outputActiveRMSDB']=round(report['inputActiveRMSDB']+report['gainDB'],2)
    scale=10**(report['gainDB']/20)
    result=array.array('h',(max(-32768,min(32767,round(v*scale))) for v in pcm))
    if sys.byteorder!='little':result.byteswap()
    temporary=target.with_suffix('.partial.wav')
    with wave.open(str(temporary),'wb') as f:f.setparams(params);f.writeframes(result.tobytes())
    temporary.replace(target)
    report.update(identity, source=str(source), audio=str(target))
    temporary=manifest.with_suffix('.partial.json');temporary.write_text(json.dumps(report,indent=2));temporary.replace(manifest)
    return target,report


def condition_pcm(raw,sr):
    """Gain-stage the delivered mono PCM16 without changing sample positions."""
    pcm=array.array('h');pcm.frombytes(raw)
    if sys.byteorder!='little':pcm.byteswap()
    # The final delivery stage also handles older cached GPT takes that never
    # received generation gain. Keep a finite cap and the same signal floor /
    # peak ceiling, rather than lifting silence or limiting every engine.
    _,report=condition((v/32768 for v in pcm),sr,max_gain_db=24)
    if abs(report['gainDB'])<.001:return raw,report
    scale=10**(report['gainDB']/20)
    out=array.array('h',(max(-32768,min(32767,round(v*scale))) for v in pcm))
    if sys.byteorder!='little':out.byteswap()
    return out.tobytes(),report
