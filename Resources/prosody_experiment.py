"""Saved, opt-in phrase-prosody experiment. Never replaces a delivered take.

A native Cantonese reference supplies pronunciation. The Japanese sentence adds
only a bounded slow pitch offset, global duration adjustment and loudness curve.
This is proportional phrase mapping, not phoneme alignment or tone correction.
"""
import json,math,sys
from pathlib import Path

REVISION='bounded-phrase-prosody-1'


def transfer(baseline,japanese,output,strength=.65):
    import numpy as np,librosa,soundfile as sf
    from scipy.ndimage import gaussian_filter1d
    strength=float(strength)
    if not math.isfinite(strength) or not 0<=strength<=1:raise ValueError('實驗強度必須介乎 0–1。')
    y,sr=sf.read(baseline,dtype='float32',always_2d=True);y=y.mean(axis=1)
    source,jr=sf.read(japanese,dtype='float32',always_2d=True);source=source.mean(axis=1)
    if len(y)<sr*.35 or len(source)<jr*.35:raise ValueError('基準或日文對白太短，無法可靠分析表演。')
    if not np.isfinite(y).all() or not np.isfinite(source).all():raise ValueError('聲音包含無效樣本。')
    low=librosa.resample(source,orig_sr=jr,target_sr=16000)
    hop=160
    f0,voiced,prob=librosa.pyin(low,fmin=65,fmax=600,sr=16000,frame_length=1024,hop_length=hop)
    rms=librosa.feature.rms(y=low,frame_length=1024,hop_length=hop)[0][:len(f0)]
    valid=voiced & np.isfinite(f0) & (prob>=.3) & (rms>max(.003,float(np.max(rms))*.07))
    if np.count_nonzero(valid)<20:raise ValueError('日文有效有聲部分不足，請改選完整對白。')
    positions=np.arange(len(f0));logf=np.interp(positions,positions[valid],12*np.log2(f0[valid]))
    # ~0.55 second smoothing explicitly excludes copying Japanese syllable F0.
    slow=gaussian_filter1d(logf,55,mode='nearest');slow-=np.median(slow)
    offsets=np.clip(slow*strength,-1.0,1.0)
    energy=gaussian_filter1d(rms,35,mode='nearest')
    med=float(np.median(energy[valid]));gains=np.clip(1+strength*(energy/max(med,.001)-1)*.25,.85,1.15)
    # Match overall pace only within 10%; never transplant Japanese word pauses.
    rate=float(np.clip((len(y)/sr)/(len(source)/jr),.9,1.1))
    rate=1+strength*(rate-1)
    if abs(rate-1)>.001:y=librosa.effects.time_stretch(y,rate=rate,n_fft=1024,hop_length=256)
    if strength==0:
        result=y.copy()
    else:
        # Long overlapping windows and a slow offset reduce abrupt voice changes.
        size=round(sr*.8);step=round(sr*.2);pad=size//2
        padded=np.pad(y,(pad,pad));result=np.zeros_like(padded);weight=np.zeros_like(padded)
        window=np.hanning(size).astype('float32')
        for start in range(0,len(padded)-size+1,step):
            center=float(np.clip((start+size/2-pad)/max(1,len(y)-1),0,1))
            pitch=float(np.interp(center,np.linspace(0,1,len(offsets)),offsets))
            gain=float(np.interp(center,np.linspace(0,1,len(gains)),gains))
            chunk=padded[start:start+size]
            shifted=librosa.effects.pitch_shift(chunk,sr=sr,n_steps=pitch,n_fft=1024,hop_length=256) if abs(pitch)>.015 else chunk
            result[start:start+size]+=shifted*window*gain;weight[start:start+size]+=window
        result=result[pad:pad+len(y)]/np.maximum(weight[pad:pad+len(y)],1e-6)
    peak=float(np.max(np.abs(result)))
    if peak>.98:result*=.98/peak
    if not np.isfinite(result).all():raise ValueError('表演處理失敗；基準錄音保留。')
    sf.write(output,result,sr,subtype='PCM_16')
    return dict(revision=REVISION,strength=strength,sampleRate=sr,baselineSeconds=sf.info(baseline).duration,sourceSeconds=len(source)/jr,seconds=len(result)/sr,tempoRate=rate,maxPitchOffsetSemitones=float(np.max(np.abs(offsets))),gainBounds=[float(np.min(gains)),float(np.max(gains))],voicedFrames=int(np.count_nonzero(valid)),mapping='proportional phrase position; no phoneme alignment',toneStatus='not-certified; listening required',characterTimbre='native Cantonese baseline; Japanese timbre not transferred')


def generate(w,cfg,folder,cue):
    import hashlib,shutil,dubbing,speechcheck
    from runtime_paths import python_for
    from reference_quality import read
    folder=Path(folder)
    cfg=dict(cfg,ttsBackend='gpt-sovits',gsvVersion='v4',targetLanguage='yue',voiceStyleMode='natural',continueOnError=False,autoValidate=False)
    cue=dict(cue,preserveOriginalSpeech=False)
    for key in ('editorAudio','editorAudioBackend','editorAudioLanguage'):cue.pop(key,None)
    source=Path(cfg.get('dialoguePath',''))
    if not source.is_file():raise ValueError('需要已分離嘅日文對白音軌先可以測試。')
    if cue['end']-cue['start']>30:raise ValueError('實驗只支援 30 秒內嘅單句對白。')
    if not str(cue.get('cantonese','')).strip():raise ValueError('請先填寫廣東話稿。')
    cfg['voiceProfiles']=[dict(p,engineReferences={}) for p in cfg['voiceProfiles']]
    profile=dubbing.profile_for(cue,cfg)
    if profile.get('language')!='yue':raise ValueError('粵語基準必須用廣東話參考。')
    base=folder/'prosody-baseline.wav';out=folder/'prosody-performance.wav';original=folder/'prosody-japanese.wav'
    manifest=dict(revision=REVISION,engine='gpt-sovits',language='yue',segment=cue['editorID'],speakerId=cue['speakerId'],text=cue['cantonese'],start=cue['start'],end=cue['end'],baseline=None,processed=None,source=str(source),sourceMTime=source.stat().st_mtime_ns,sourceSize=source.stat().st_size,roleReferenceSHA256=hashlib.sha256(Path(next(p for p in cfg['voiceProfiles'] if p['id']==cue['speakerId'])['reference']).read_bytes()).hexdigest(),requiresReview=True,autoAdopt=False)
    def save():w.atomic_json(folder/'prosody-experiment.json',manifest)
    save()
    paths=dubbing.gsv_audio(cfg,folder,[cue],w.run,w.emit)
    path=paths[0]
    if not path.is_file() or path.name.startswith(('skipped-','failed-','original-vocalization-')):raise ValueError('GPT V4 未生成有效粵語基準；實驗未有套用。')
    shutil.copy2(path,base);manifest['baseline']=str(base);save()
    try:
        check=speechcheck.inspect(cfg,folder,[cue],[base],w.emit)[0];manifest['baselineCheck']=check;save()
        if not check.get('textMatches') or check.get('languageMismatch') or check.get('criticalDifferences'):
            raise ValueError('粵語基準覆聽未通過；已保存基準供試聽，未加入日文表演。')
        w.run([cfg['ffmpeg'],'-v','error','-y','-ss',str(cue['start']),'-i',str(source),'-t',str(cue['end']-cue['start']),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(original)])
        req=folder/'prosody-request.json';w.atomic_json(req,dict(baseline=str(base),japanese=str(original),output=str(out),strength=cfg.get('prosodyStrength',.65)))
        w.emit('日文表演實驗','分析本句日文，加入受限嘅句級音高、節奏同音量變化。',.88)
        metrics=json.loads(w.run([python_for(Path(cfg['storage']),'gsv-runtime'),Path(__file__),str(req)]))
        manifest.update(processed=str(out),metrics=metrics);save()
        manifest['processedCheck']=speechcheck.inspect(cfg,folder,[cue],[out],w.emit)[0];save()
    except Exception as error:
        manifest['error']=str(error);save()
    return manifest


if __name__=='__main__':
    request=json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(transfer(**request),ensure_ascii=False))
