"""Mix witnessed simultaneous roles; flag uncertainty without a Japanese fallback."""
import json
from pathlib import Path

def annotate(cues,job=None):
    pairs=[];ambiguous=[]
    for i,cue in enumerate(cues):
        if not cue.get('enabled',True):continue
        mixed=cue.get('mixedVoices') or '多個聲線' in cue.get('speakerNote','')
        if mixed and not cue.get('overlapReviewed'):
            note='多人聲線需覆核；保留目標語言配音，不自動改用日文。'
            if note not in cue.get('speakerNote',''):cue['speakerNote']=(cue.get('speakerNote','')+' '+note).strip()
            ambiguous.append(cue.get('reviewIndex',i)+1)
        cue['sourceOverlaps']=[]
    active=sorted(((i,c) for i,c in enumerate(cues) if c.get('enabled',True)),key=lambda x:x[1]['start'])
    for pos,(i,cue) in enumerate(active):
        for j,other in active[pos+1:]:
            if other['start']>=cue['end']:break
            if cue.get('speakerId') and other.get('speakerId') and cue['speakerId']!=other['speakerId']:
                a,b=max(cue['start'],other['start']),min(cue['end'],other['end'])
                if b-a<.06:continue
                first,second=cue.get('reviewIndex',i)+1,other.get('reviewIndex',j)+1
                cue['sourceOverlaps'].append(second);other['sourceOverlaps'].append(first)
                pairs.append(dict(indices=[first,second],start=a,end=b,status='witnessed-separate-roles'))
    result=dict(pairs=pairs,ambiguousIndices=ambiguous,policy='mix witnessed roles; flag uncertain identity; no automatic Japanese dialogue fallback')
    if job:
        from worker import atomic_json
        atomic_json(Path(job)/'overlap-analysis.json',result)
    return result

def expected(cue,other,start,end):
    return bool(cue.get('speakerId') and other.get('speakerId') and cue['speakerId']!=other['speakerId'] and cue['start']<other['end'] and other['start']<cue['end'] and start>=max(cue['start'],other['start'])-.08 and end<=min(cue['end'],other['end'])+.12)
