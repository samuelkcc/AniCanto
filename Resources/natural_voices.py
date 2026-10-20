"""Stable target-language reference casting; never falls back to Japanese."""
import hashlib,json,math,wave,sys,re
from pathlib import Path

REVISION='target-language-casting-1'
def catalog():
    root=Path(__file__).parent/'natural-voices'
    return [dict(row,reference=str(root/row['file'])) for row in json.loads((root/'catalog.json').read_text())['voices']]

def pitch(path):
    from reference_quality import read
    try:
        return pitch_samples(*read(path))
    except (OSError,ValueError,wave.Error):return None

def pitch_samples(audio,sr):
    import numpy as np
    try:
        step=max(1,round(sr/4000));audio=audio[::step];rate=sr/step
        values=[];size=round(rate*.06)
        for start in range(0,len(audio)-size,max(1,round(rate*.08))):
            x=audio[start:start+size].astype('float64');x-=x.mean()
            if float(np.sqrt(np.mean(x*x)))<.012:continue
            x*=np.hanning(len(x));corr=np.correlate(x,x,mode='full')[len(x)-1:]
            lo=max(1,round(rate/360));hi=min(len(corr)-1,round(rate/75))
            peaks=[i for i in range(lo+1,hi) if corr[i]>corr[i-1] and corr[i]>=corr[i+1]]
            if not peaks or corr[0]<=0:continue
            lag=max(peaks,key=lambda i:corr[i]);strength=corr[lag]/corr[0]
            if strength>=.4:values.append(rate/lag)
        return float(np.median(values)) if values else None
    except (ValueError,IndexError):return None

def prepare_cast(cfg,job,cues,run):
    if cfg.get('voiceStyleMode')!='natural' or '_naturalRolePitch' in cfg:return
    cfg['_naturalRolePitch']={}
    source=Path(cfg.get('dialoguePath',''))
    if not source.is_file():return
    ranges={}
    for cue in sorted(cues,key=lambda c:c['end']-c['start'],reverse=True):
        text=re.sub(r'[^\wぁ-んァ-ヶ一-龥]','',cue.get('japanese',cue.get('text','')))
        ident=cue.get('speakerId')
        if not ident or not cue.get('enabled',True) or len(text)<4 or re.fullmatch(r'[あぁアァうぅウゥおぉオォえぇエェーっッ]+',text) or cue['end']-cue['start']<.7:continue
        if len(ranges.get(ident,[]))<8:ranges.setdefault(ident,[]).append([cue['start'],min(cue['end'],cue['start']+6)])
    key=hashlib.sha256(json.dumps([str(source),source.stat().st_mtime_ns,ranges,REVISION]).encode()).hexdigest()
    cache=Path(job)/'natural-pitch.json'
    old=json.loads(cache.read_text()) if cache.exists() else {}
    if old.get('key')==key:
        cfg['_naturalRolePitch']=old['pitches'];return
    from runtime_paths import python_for
    request=Path(job)/'natural-pitch-request.json';request.write_text(json.dumps(dict(audio=str(source),ranges=ranges)))
    values=json.loads(run([python_for(Path(cfg['storage']),'separator-runtime'),Path(__file__),request]))
    cfg['_naturalRolePitch']=values
    from worker import atomic_json
    atomic_json(cache,dict(key=key,pitches=values,method='Median vocal range from multiple own-role lexical utterances; no gender or identity inference'))

def resolve(profile,cfg):
    target=cfg.get('targetLanguage','yue')
    if target not in ('yue','en'):raise ValueError('自然配音只支援廣東話及英文。')
    # Explicit per-engine target-language imports take precedence.
    if profile.get('language')==target and profile.get('reference') and profile.get('promptText'):
        return dict(profile,naturalReferenceId='user-reference',referenceCandidates=[])
    choices=[row for row in catalog() if row['language']==target]
    selected=(profile.get('naturalVoices') or {}).get(target,'auto')
    if selected!='auto':
        row=next((row for row in choices if row['id']==selected),None)
        if not row:raise ValueError(f'{profile.get("name","")} 自然聲線選項已不存在，請重新選擇。')
    else:
        frequency=cfg.get('_naturalRolePitch',{}).get(profile['id'])
        source=Path(profile.get('reference',''))
        if frequency is None and source.is_file():
            fingerprint=hashlib.sha256(source.read_bytes()).hexdigest()
            cache=cfg.setdefault('_naturalPitchCache',{})
            if fingerprint not in cache:cache[fingerprint]=pitch(source)
            frequency=cache[fingerprint]
        # Match vocal range only, not biological sex, identity or Japanese prosody.
        row=min(choices,key=lambda row:abs(math.log(max(75,frequency or 170)/row['pitchHz'])))
    source=Path(row['reference'])
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=row['sha256']:
        raise ValueError('自然聲線素材未通過完整性檢查，請修復 App。')
    return dict(profile,reference=str(source),promptText=row['promptText'],language=target,
                referenceCandidates=[],referenceRanges=[],referenceQuality={},mixedReference=False,
                shortReference=False,transcriptSource='natural-voice-bank',naturalReferenceId=row['id'],
                naturalReferenceTitle=row['title'],voiceStyleMode='natural')

def record(cfg,job,profiles):
    from worker import atomic_json
    rows=[dict(roleId=p['id'],name=p.get('name',''),voiceId=p.get('naturalReferenceId','user-reference'),
               language=p['language'],reference=p['reference'],promptText=p['promptText']) for p in profiles]
    atomic_json(Path(job)/'natural-casting.json',dict(revision=REVISION,mode='natural',roles=rows))

if __name__=='__main__':
    import numpy as np,soundfile as sf
    request=json.loads(Path(sys.argv[1]).read_text());result={}
    with sf.SoundFile(request['audio']) as f:
        for ident,ranges in request['ranges'].items():
            values=[]
            for a,b in ranges:
                f.seek(max(0,round(a*f.samplerate)));audio=f.read(round((b-a)*f.samplerate),dtype='float32',always_2d=True).mean(axis=1)
                value=pitch_samples(audio,f.samplerate)
                if value is not None:values.append(value)
            if values:result[ident]=float(np.median(values))
    print(json.dumps(result))
