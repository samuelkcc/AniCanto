"""Speech-keyed background reduction; original Japanese is never ducked.

Automatic repair measures the delivered foreground, not the movie's peak.
It can reduce masking without amplifying peak-limited speech into clipping.
"""
import hashlib,json,math,subprocess,uuid,wave
from pathlib import Path


def levels(pcm,channels=1,sr=24000):
    import numpy as np
    x=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
    if not len(x):return None
    x=x.reshape(-1,channels)
    power=np.mean(x*x,axis=1)
    frame=max(1,round(sr*.02));usable=len(power)//frame*frame
    powers=power[:usable].reshape(-1,frame).mean(axis=1) if usable else power
    active=powers[powers>=max(.0005**2,float(powers.max())*.04)]
    if not len(active) or float(np.sqrt(active.mean()))<.001:return None
    return dict(activeRMSDB=round(10*math.log10(float(active.mean())),2),peakDB=round(20*math.log10(max(1e-12,float(np.max(abs(x))))),2))


def automatic_enabled(cfg):
    """Basic mix audibility belongs to Normal production, without AI review."""
    return cfg.get('productionMode')=='normal' or bool(cfg.get('aiAutoFix'))


def resolve(cfg,job,background):
    """Measure the delivered voice; no model/ASR inference or retakes."""
    manual=bool(cfg.get('backgroundDucking'))
    if not automatic_enabled(cfg):
        (Path(job)/'mix-audibility.json').unlink(missing_ok=True)
        return manual
    from audio_fallback import read_json
    result=dict(method='PCM active power, not LUFS or perceptual certification',status='checked',automatic=False,manual=manual,rows=[],errors=[])
    try:
        analysis=Path(background)
        try:
            with wave.open(str(analysis)) as check:
                if check.getsampwidth()!=2:raise wave.Error('Needs analysis PCM')
        except wave.Error:
            # Separator stems are often float WAVs. Decode once for analysis;
            # mixing continues to use the untouched original full-rate stem.
            source=analysis.stat()
            key=hashlib.sha256(json.dumps([str(analysis),source.st_size,source.st_mtime_ns,'audibility-pcm16-1']).encode()).hexdigest()[:24]
            folder=Path(cfg.get('_referenceRecoveryRoot') or job)/'mix-balance';folder.mkdir(parents=True,exist_ok=True)
            converted=folder/(key+'.wav')
            if not converted.is_file():
                temporary=folder/(key+'-'+uuid.uuid4().hex+'.partial.wav')
                try:
                    process=subprocess.run([cfg['ffmpeg'],'-v','error','-y','-i',str(analysis),'-vn','-ar','16000','-ac','2','-c:a','pcm_s16le',str(temporary)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=120)
                    if process.returncode:raise ValueError(process.stderr.decode(errors='replace')[-600:])
                    temporary.replace(converted)
                finally:temporary.unlink(missing_ok=True)
            analysis=converted
        with wave.open(str(analysis)) as bg:
            if bg.getsampwidth()!=2:raise ValueError('Background is not PCM16')
            sr=bg.getframerate()
            for row in read_json(Path(job)/'timing.json',[]):
                path=row.get('renderedAudio')
                if row.get('skipped') or not path:continue
                try:
                    with wave.open(str(path)) as voice:
                        if voice.getsampwidth()!=2:raise ValueError('Voice is not PCM16')
                        measured=levels(voice.readframes(voice.getnframes()),voice.getnchannels(),voice.getframerate())
                    if measured is None:continue
                    # A safety gain may have been applied to the whole foreground
                    # after accumulating overlapping takes. Measure its delivered
                    # level rather than treating the original take as the mix.
                    gain=float(row.get('mixGain',1))
                    measured=dict(measured,takeActiveRMSDB=measured['activeRMSDB'],timelineGain=gain,
                        activeRMSDB=round(measured['activeRMSDB']+20*math.log10(max(gain,1e-12)),2))
                    start=row.get('renderedStart',row.get('start',0));end=row.get('renderedEnd',row.get('end',start))
                    if end<=start:continue
                    bg.setpos(min(bg.getnframes(),max(0,round(start*sr))))
                    bed=levels(bg.readframes(round((end-start)*sr)),bg.getnchannels(),sr)
                    if bed is None:continue
                    bed_db=bed['activeRMSDB']+20*math.log10(max(1e-12,float(cfg.get('backgroundGain',.8))))
                    margin=measured['activeRMSDB']-bed_db
                    masked=measured['activeRMSDB']<-18 and margin<6
                    result['rows'].append(dict(index=row['index'],voice=measured,backgroundDB=round(bed_db,2),marginDB=round(margin,2),masked=masked))
                except (OSError,wave.Error,ValueError) as error:result['errors'].append(dict(index=row['index'],error=str(error)))
    except (OSError,wave.Error,ValueError,subprocess.TimeoutExpired) as error:result.update(status='measurement-unavailable',error=str(error))
    result['automatic']=not manual and any(row['masked'] for row in result['rows'])
    from worker import atomic_json
    atomic_json(Path(job)/'mix-audibility.json',result)
    return True if manual else 'auto' if result['automatic'] else False


def separated_filter(gain, label='dub', duck=False):
    mix=f'[3:a:0]volume={gain}[bg];[1:a:0]pan=stereo|c0=c0|c1=c0[voice];'
    if duck:
        # The dry background fraction caps automatic attenuation at ~8 dB.
        blend=':mix=0.6' if duck=='auto' else ''
        mix+='[voice]asplit=2[dry][key];[bg][key]sidechaincompress=threshold=0.015:ratio=4:attack=25:release=350:makeup=1'+blend+'[reduced];'
        voice,bg='dry','reduced'
    else:voice,bg='voice','bg'
    return mix+f'[{voice}][{bg}]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0:latency=1[{label}]'
