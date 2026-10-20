"""Conservative acoustic edges around ASR anchors; never a speech recognizer."""
import math
from pathlib import Path
import numpy as np


def activity(audio, sr, floor=.003, relative=.04):
    """10 ms RMS, retaining soft edges around sustained energy, not single clicks."""
    x=np.asarray(audio,dtype=np.float32)
    if x.ndim>1:x=x.mean(axis=1)
    step=max(1,round(sr*.01));n=len(x)//step
    if not n:return []
    rms=np.sqrt(np.mean(x[:n*step].reshape(n,step)**2,axis=1))
    threshold=max(floor,float(rms.max())*relative)
    if not math.isfinite(threshold):return []
    indices=np.flatnonzero(rms>threshold);groups=[]
    for i in indices:
        if groups and i-groups[-1][1]<=12:groups[-1][1]=int(i)
        else:groups.append([int(i),int(i)])
    return [(a*step/sr,(b+1)*step/sr) for a,b in groups if b-a>=5]


def refine(cues, spans, duration):
    """Snap only nearby witnessed edges; retain ASR anchors when ambiguous.

    ASR text and user-approved cue IDs remain unchanged. A measured edge is
    evidence of vocal activity, not proof that a particular word was spoken.
    """
    starts=[]
    for c in cues:
        a=c['start']
        nearby=[s for s,e in spans if a-.35<=s<=a+1.2 and s<c['end']-.12]
        starts.append(min(nearby,key=lambda s:abs(s-a)) if nearby else a)
    for i,c in enumerate(cues):
        a=starts[i];b=c['end'];ceiling=max(0,starts[i+1]-.04) if i+1<len(cues) else duration
        # Preserve witnessed simultaneous speakers instead of clipping the first
        # speaker to the next speaker's onset. Ambiguous same-role turns stay bounded.
        if i+1<len(cues) and cues[i+1]['start']<b and c.get('speakerId') and cues[i+1].get('speakerId') and c['speakerId']!=cues[i+1]['speakerId']:
            ceiling=duration
        endings=[e for s,e in spans if e>a+.12 and b-.5<=e<=min(b+.4,ceiling)]
        end=min(endings,key=lambda e:abs(e-b)) if endings else min(b,ceiling)
        if end-a<.18:continue
        # 40 ms protection for soft consonants, bounded by the adjacent turn.
        c['speechStart']=round(max(0,a-.04),3)
        c['speechEnd']=round(min(duration,ceiling,end+.04),3)
        c['deliveryEnd']=round(min(duration,ceiling,end+.35),3)
        c['acousticStart']=round(a,3);c['acousticEnd']=round(end,3)
        c['acousticAdjusted']=abs(a-c['start'])>.08 or abs(end-c['end'])>.08
    return cues


def align(cfg,cues,run):
    path=cfg.get('dialoguePath')
    if not cfg.get('speechTiming') or not path or not Path(path).is_file():return cues
    raw=run([cfg['ffmpeg'],'-v','error','-i',path,'-ar','16000','-ac','1','-f','f32le','pipe:1'])
    spans=activity(np.frombuffer(raw,dtype=np.float32),16000)
    if not spans:return cues
    refine(cues,spans,cfg['duration'])
    for c in cues:
        regions=[]
        for a,b in spans:
            a=max(a,c.get('speechStart',c['start']));b=min(b,c.get('speechEnd',c['end']))
            if b-a<.06:continue
            if regions and a-regions[-1]['end']<.45:regions[-1]['end']=b
            else:regions.append(dict(start=a,end=b))
        # A tiny acoustic burst can be a syllable inside a word. Do not ask
        # the language model to place a whole clause into that burst.
        i=0
        while len(regions)>1 and i<len(regions):
            if regions[i]['end']-regions[i]['start']>=.75:i+=1;continue
            if i:regions[i-1]['end']=regions[i]['end'];regions.pop(i)
            else:regions[1]['start']=regions[0]['start'];regions.pop(0)
        c['speechRegions']=regions if 2<=len(regions)<=4 else []
        parts=c.get('recognitionParts') or c.get('sourceParts')
        if parts:
            # Keep independent ASR parts for semantics; use measured parts only
            # for placing a verified punctuation split in the delivery stage.
            adjusted=refine([dict(p) for p in parts],spans,cfg['duration'])
            c['acousticParts']=[dict(p,start=p.get('speechStart',p['start']),end=p.get('speechEnd',p['end'])) for p in adjusted]
    return cues


def trim_generated(audio, sr):
    """Remove outer low-level padding only, keeping 60 ms and all inner pauses."""
    spans=activity(audio,sr,floor=.003,relative=.04)
    if not spans:return audio
    a=max(0,round((spans[0][0]-.06)*sr));b=min(len(audio),round((spans[-1][1]+.06)*sr))
    return audio[a:b]
