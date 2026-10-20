"""Consolidate evidenced same-speaker ASR fragments before scene translation.

Only literal duplicated prefixes or grammatical continuations of a shared caption
are joined. Different/overlapping speakers and complete repeated lines remain.
"""
import copy,re
from source_evidence import clean_text,caption_records

def consolidate(cues,captions):
    result=[];changes=[]
    for original in cues:
        c=copy.deepcopy(original);previous=result[-1] if result else None
        if previous:
            a=clean_text(previous.get('japanese',previous.get('text','')))
            b=clean_text(c.get('japanese',c.get('text','')))
            gap=c['start']-previous['end']
            same=bool(previous.get('speakerId') and previous.get('speakerId')==c.get('speakerId'))
            safe=same and previous.get('enabled',True) and c.get('enabled',True) and not previous.get('mixedVoices') and not c.get('mixedVoices') and -.001<=gap<=.6 and c['end']-previous['start']<=12
            prefix=bool(a and b.startswith(a) and len(b)>len(a) and len(a)<=3 and previous['end']-previous['start']<=.6 and gap<=.15)
            shared=[r for r in captions if r['start']<previous['end'] and r['end']>c['start']]
            continuation=bool(re.search(r'(?:ともかく|けど|から|ので|[はをにのともがへ])[、。\s]*$',previous.get('japanese','')))
            if safe and (prefix or (shared and continuation)):
                previous.setdefault('recognitionParts',[dict(start=previous['start'],end=previous['end'],japanese=previous.get('japanese',''))])
                previous['recognitionParts']+=c.get('recognitionParts',[dict(start=c['start'],end=c['end'],japanese=c.get('japanese',''))])
                previous['japanese']=c.get('japanese',c.get('text','')) if prefix else previous.get('japanese','')+' '+c.get('japanese','')
                previous['text']=previous['japanese']
                for key in ('end','speechEnd','deliveryEnd','sourceEnd'):previous[key]=c.get(key,c['end'])
                previous['subtitleHint']=' ／ '.join(r['text'] for r in captions if r['start']<previous['end'] and r['end']>previous['start'])
                previous['asrConfidence']=max(previous.get('asrConfidence',0),c.get('asrConfidence',0)) if prefix else min(previous.get('asrConfidence',1),c.get('asrConfidence',1))
                previous['cantonese']='';previous.pop('captionAllocation',None)
                previous['sourceParts']=previous['recognitionParts']
                changes.append(dict(start=previous['start'],end=previous['end'],reason='duplicate-ASR-prefix' if prefix else 'same-speaker-caption-continuation'))
                continue
        result.append(c)
    return result,changes

def prepare(job,cues):
    from worker import atomic_json
    result,changes=consolidate(cues,caption_records(job))
    atomic_json(job/'dialogue-unit-report.json',dict(changes=changes,input=len(cues),output=len(result)))
    return result
