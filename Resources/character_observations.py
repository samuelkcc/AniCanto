"""Validate each visible head separately; appearance never proves source speech.

Local temporal pixel checks veto static portraits and camera/whole-head motion.
They are conservative evidence filters, not trained lip-sync recognition. Every
eligible dialogue is inventoried before inference; no first-160 cast truncation.
"""
import math


def eligible_indices(cues):
    return [i for i,c in enumerate(cues) if c.get('enabled',True) and
            math.isfinite(c.get('start',0)) and math.isfinite(c.get('end',0)) and
            c['end']-c['start']>=.25]


def inside(inner,outer):
    return (len(inner)==len(outer)==4 and outer[0]<=inner[0]<inner[2]<=outer[2]
            and outer[1]<=inner[1]<inner[3]<=outer[3])


def intersection(a,b):
    overlap=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-overlap
    return overlap/union if union>0 else 0


def normalized_box(box):
    return (isinstance(box,list) and len(box)==4 and
            all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=1 for v in box)
            and .005<=box[2]-box[0]<=.8 and .005<=box[3]-box[1]<=.9)


def temporal_evidence(storyboard,person):
    """Four actual frames, tracked head/mouth boxes; fail closed on cuts/motion.

    A changing lower face alone is insufficient. Require model-visible mouth
    opening/closing plus localized change exceeding the upper-head control.
    This cannot certify synchronization to the source voice or hidden mouths.
    """
    import numpy as np
    from PIL import Image
    heads=person.get('frameBoxes',[]);mouths=person.get('mouthBoxes',[])
    result=dict(status='unavailable',method='localized-mouth-motion-veto-1',certified=False)
    if len(heads)!=4 or len(mouths)!=4 or not all(normalized_box(h) and normalized_box(m) and inside(m,h) for h,m in zip(heads,mouths)):
        return result
    with Image.open(storyboard) as source:
        image=source.convert('RGB');width=image.width//4;height=image.height-26
        frames=[image.crop((j*width,24,(j+1)*width,24+height)) for j in range(4)]
    def patch(frame,box):
        a,b,c,d=box
        return np.asarray(frame.crop((round(a*width),round(b*height),round(c*width),round(d*height))).resize((32,32)).convert('L'),dtype=np.float32)/255
    whole=[np.asarray(f.resize((24,14)),dtype=np.float32)/255 for f in frames]
    scene=max(float(np.mean(abs(a-b))) for a,b in zip(whole,whole[1:]))
    lips=[patch(f,m) for f,m in zip(frames,mouths)]
    controls=[patch(f,[h[0],h[1],h[2],h[1]+(h[3]-h[1])*.4]) for f,h in zip(frames,heads)]
    mouth=max(float(np.mean(abs(a-b))) for a,b in zip(lips,lips[1:]))
    head=max(float(np.mean(abs(a-b))) for a,b in zip(controls,controls[1:]))
    status='supported' if scene<.28 and mouth>=.035 and mouth>=head*1.6+.012 else 'static-or-global-motion'
    return dict(result,status=status,mouthChange=round(mouth,4),headChange=round(head,4),sceneChange=round(scene,4))


def validate_people(row,known):
    """Keep independently bounded heads in crowds, reject duplicate/group boxes."""
    from visual_speakers import valid_box
    people=[]
    for p in row.get('characters',[]) if isinstance(row.get('characters'),list) else []:
        if not isinstance(p,dict):continue
        ident=p.get('visualId');box=p.get('characterBox');confidence=p.get('confidence')
        if (ident not in known or p.get('headVisible') is not True or not valid_box(box) or
                type(confidence) not in (int,float) or not .85<=confidence<=1):continue
        if any(other['visualId']==ident or intersection(box,other['characterBox'])>.5 for other in people):continue
        people.append(dict(p))
        if len(people)>=8:break
    return people


def apply_temporal_checks(rows,storyboards):
    for row in rows:
        if 'characters' not in row:continue  # Legacy records remain compatible.
        active=[]
        for person in row['characters']:
            try:proof=temporal_evidence(storyboards[row['index']],person)
            except (OSError,ValueError,KeyError):proof=dict(status='unavailable',certified=False)
            person['temporalEvidence']=proof
            if (row.get('continuousShot') is True and person.get('speaking') is True and
                    person.get('mouthChanged') is True and person.get('confidence',0)>=.95 and proof['status']=='supported'):
                active.append(person)
        row['visibleCharacterIds']=[p['visualId'] for p in row['characters']]
        row['activeCharacterIds']=[p['visualId'] for p in active]
        if len(active)==1 and not row.get('multipleSpeakers'):
            person=active[0]
            for name in ('visualId','characterBox','headVisible','confidence'):row[name]=person[name]
            row.update(speaking=True,mouthChanged=True,speakerEvidence='visible-localized-mouth-change; audio fusion still required')
        else:
            row.update(speaking=False,mouthChanged=False,speakerEvidence='multiple-or-no-temporally-supported-speakers')
            if len(active)>1:row['multipleSpeakers']=True
        # Portrait-only evidence can show a head, never force a voice assignment.
        if row.get('visualId')=='unknown' and len(row['characters'])==1:
            person=row['characters'][0]
            for name in ('visualId','characterBox','headVisible','confidence'):row[name]=person[name]
    return rows


def portrait_observations(rows):
    """Flatten appearance inventory separately from the row's selected speaker."""
    result=[]
    for row in rows:
        if 'characters' in row:
            for person in row['characters']:
                result.append(dict(row,**person,characters=[],multipleSpeakers=False,
                                   appearanceOnly=person['visualId'] not in row.get('activeCharacterIds',[])))
        else:result.append(row)
    return result
