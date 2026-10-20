"""Compose source/translated subtitle tracks on their own witnessed timelines."""
import math
from source_evidence import caption_records

MODES=('none','yue','english','dual','all','original','original-yue','original-english','complete','separate')

def source_cues(job, duration):
    result=[]
    captions=caption_records(job)
    for row in captions:
        a=max(0,row['start']);b=min(duration,row['end'])
        if b>a:result.append(dict(start=a,end=b,text=row['text'],cantonese=row['text']))
    return result

def labels(track):
    mode=track['mode']
    if mode=='original':
        language=track.get('sourceLanguage') or 'zho'
        if track.get('sourceTitle'):return language,'Original / 原片 · '+track['sourceTitle']
        if language in ('jpn','ja'):return 'jpn','Original Japanese / 日文原字幕'
        if language in ('eng','en'):return 'eng','Original English subtitles'
        return 'zho','Original Chinese / 原裝中文字幕'
    if mode=='english':return 'eng','English translation / 英文譯文'
    if mode=='yue':return 'yue','Cantonese translation / 廣東話譯文'
    return 'zho',{'dual':'Cantonese + English (learning) / 廣東話＋英文（學習）','original-yue':'Original Chinese + Hong Kong Cantonese','original-english':'Original Chinese + English'}.get(mode,mode)

def ordered(tracks):
    return sorted(tracks,key=lambda t:({'yue':0,'english':1,'dual':2,'original-yue':3,'original-english':4,'original':5}.get(t['mode'],3),t['language']!='yue'))

def matching_cue(cue,cues):
    """Dropped draft rows cannot shift the translations of later subtitle rows."""
    candidates=[c for c in cues if c.get('enabled',True) and min(cue['end'],c.get('subtitleEnd',c['end']))>max(cue['start'],c.get('subtitleStart',c['start']))]
    if not candidates:return {}
    return min(candidates,key=lambda c:abs(cue['start']-c.get('subtitleStart',c['start']))+abs(cue['end']-c.get('subtitleEnd',c['end'])))

def combine(first, second):
    # Split at real changes in either track. No nearest-neighbour text copying:
    # a source caption must not linger after its original end time.
    rows=[]
    boundaries=sorted({float(c[k]) for track in (first,second) for c in track for k in ('start','end') if math.isfinite(float(c[k]))})
    for a,b in zip(boundaries,boundaries[1:]):
        if b-a<.001:continue
        lines=[]
        for track in (first,second):
            texts=list(dict.fromkeys(c.get('cantonese',c.get('text','')).strip().replace('\n',' ') for c in track if c['start']<b and c['end']>a))
            line=' '.join(t for t in texts if t)
            if line:lines.append(line)
        if not lines:continue
        text='\n'.join(lines)
        if rows and abs(rows[-1]['end']-a)<.001 and rows[-1]['text']==text:rows[-1]['end']=b
        else:rows.append(dict(start=a,end=b,text=text,cantonese=text))
    return rows
