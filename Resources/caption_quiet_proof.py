"""Bounded paired sound evidence for a caption with no witnessed source words."""
import hashlib,json,math,time
from pathlib import Path
REVISION='paired-quiet-caption-270'
MAX_WINDOWS=2
MAX_SECONDS=120


def quiet(measure):
    if not measure:return False
    # Use the PCM16 delivery quantum, not floating-point separator residue.
    q=1/32768
    return all(isinstance(measure.get(k),(int,float)) and math.isfinite(measure[k]) for k in ('peak','rms')) and 0<=measure['peak']<=q and 0<=measure['rms']<=q/4


def confirms(rows,a,b,backend,original=False):
    from nonverbal import validate_classification,event_labels
    try:validate_classification(rows)
    except (ValueError,TypeError):return False
    # Model scores are not calibrated across implementations. Windows stays
    # conservative until an AST threshold has independent device evidence.
    if backend!='apple-soundanalysis-v1':return False
    selected=[r for r in rows if min(r['start']+r['duration'],b)>max(r['start'],a)]
    if not selected:return False
    end=a
    for r in sorted(selected,key=lambda r:r['start']):
        if r['start']>end+.001:return False
        end=max(end,r['start']+r['duration'])
        vocal=('speech','singing','choir_singing','rapping',*event_labels(r))
        if any(r.get(k,1)>.05 for k in vocal):return False
        if original and r['music']<.5:return False
    return end>=b-.001


def inspect(cfg,job,cue,evidence,measure,write,budget):
    import soundfile as sf
    from worker import run
    from nonverbal import classification_profile
    if not quiet(measure):return None
    a=max(0,float(cue['start'])-.25);b=min(evidence['duration'],float(cue['end'])+.25)
    if b-a>30 or b<=a:return None
    profile=classification_profile()
    if profile['backend']!='apple-soundanalysis-v1':return None
    identity=[REVISION,evidence['sourceSHA256'],evidence['stemSHA256'],a,b,profile,cfg.get('startOffset',0)]
    key=hashlib.sha256(json.dumps(identity).encode()).hexdigest();folder=Path(job)/'caption-quiet-proof';folder.mkdir(exist_ok=True)
    receipt=folder/(key+'.json')
    try:
        saved=json.loads(receipt.read_text())
        if saved.get('identity')==identity:
            if saved.get('complete') and not all(confirms(saved.get(n,[]),a-saved['start'],b-saved['start'],profile['backend'],original=n=='original') for n in ('original','stem')):return None
            return saved
    except (OSError,ValueError):pass
    if budget['windows']>=MAX_WINDOWS or time.monotonic()-budget['started']>=MAX_SECONDS:return None
    budget['windows']+=1
    # Cover SoundAnalysis's final analysis window with real extra samples.
    start=max(0,math.floor(a*2)/2);end=min(evidence['duration'],math.ceil((b+1)*2)/2)
    saved=dict(identity=identity,complete=False,start=start,end=end,backend=profile['backend'])
    write(receipt,saved)  # A failed or cancelled inspection cannot earn a retry.
    try:
        for name,source in [('original',evidence['sourcePath']),('stem',evidence['stemPath'])]:
            with sf.SoundFile(source) as f:
                rate=f.samplerate;f.seek(round(start*rate));x=f.read(round((end-start)*rate),dtype='float32',always_2d=True)
                if len(x)<round((end-start)*rate):return saved
            clip=folder/(key+'-'+name+'.wav');sf.write(clip,x,rate,subtype='FLOAT')
            remaining=MAX_SECONDS-(time.monotonic()-budget['started'])
            if remaining<=0:return saved
            rows=json.loads(run([cfg['executable'],'--classify-performance',clip],timeout=min(30,remaining)))
            saved[name]=rows
            if not confirms(rows,a-start,b-start,profile['backend'],original=name=='original'):
                write(receipt,saved);return saved
        saved['complete']=True;write(receipt,saved);return saved
    except (OSError,ValueError,TypeError,RuntimeError) as error:
        saved['error']=str(error)[:220];write(receipt,saved);return saved
