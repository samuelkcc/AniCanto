"""Targeted pre-TTS verbosity checks; captions are hints, never a hard limit.

Only anomalous turns spend one cached rewrite/semantic-check batch. This is not
full AI certification. Japanese/recognized source speech remains authoritative
when OCR is wrong; legitimate repetitions, names and facts must survive edits.
"""
import hashlib
import json
import math
from pathlib import Path
import re

REVISION='caption-guided-brevity-1'


def key_text(text):return ''.join(c.casefold() for c in text if c.isalnum())


def caption_reference(cfg,cues,index):
    from translation_source import audio_only,audio_primary
    if audio_only(cfg):return dict(status='audio-only',text='')
    cue=cues[index];allocation=cue.get('captionAllocation') or {}
    own=allocation.get('content','') if not allocation.get('blocked') else ''
    own=own.strip() if isinstance(own,str) else ''
    if own:
        text=own;status='allocated-own-turn'
    else:
        if allocation.get('blocked'):return dict(status='ambiguous-allocation',text='')
        # A full caption shared by several independent speech turns must not be
        # treated as the expected length of each individual turn.
        text=cue.get('subtitleHint','').strip();status='single-caption-hint'
        if not text:return dict(status='absent',text='')
        if '／' in text or '\n' in text:return dict(status='multiple-caption-context',text='')
        normalized=key_text(text)
        for other in cues[max(0,index-1):index]+cues[index+1:index+2]:
            if key_text(other.get('subtitleHint',''))==normalized:return dict(status='shared-caption-context',text='')
        a,b=cue.get('speechStart',cue['start']),cue.get('speechEnd',cue['end'])
        records=cue.get('captionRecords',[])
        if len(records)>1:return dict(status='multiple-caption-records',text='')
        if records:
            record=records[0]
            if record.get('end',b)<=a or record.get('start',a)>=b:return dict(status='outside-own-turn',text='')
            # Explicit OCR confidence can reject a reference; absence of a score
            # is unknown quality, never an assertion that OCR has been verified.
            confidence=record.get('confidence',record.get('ocrConfidence'))
            if isinstance(confidence,(int,float)) and confidence<.75:return dict(status='low-confidence-caption',text='')
            ra,rb=record.get('start',a),record.get('end',b)
            if any(other is not cue and other.get('enabled',True) and min(rb,other.get('speechEnd',other['end']))-max(ra,other.get('speechStart',other['start']))>.15 for other in cues):
                return dict(status='caption-spans-multiple-turns',text='')
    cleaned=key_text(text)
    if len(cleaned)<3 or len(cleaned)>250 or '\ufffd' in text:return dict(status='unusable-caption',text='')
    kana=bool(re.search(r'[\u3041-\u30fa]',text))
    chinese=sum('\u3400'<=c<='\u9fff' for c in cleaned)
    language='ja' if kana else 'zh' if chinese>=len(cleaned)*.6 else 'en' if re.search(r'[A-Za-z]{2}',text) else 'unknown'
    return dict(status=status,text=text,language=language,auxiliary=audio_primary(cfg,cue),quality='unverified-reference')


def repeated_phrase(text,language):
    if language=='en':
        words=re.findall(r"[a-z0-9]+(?:['’-][a-z0-9]+)*",text.casefold())
        return any(words[i:i+4]==words[j:j+4] for i in range(max(0,len(words)-7)) for j in range(i+4,len(words)-3))
    text=key_text(text)
    return any(text[i:i+5] in text[i+5:] for i in range(max(0,len(text)-9)))


def assess(cfg,cues,index,language):
    from concise_dialogue import units,budget
    cue=cues[index];field='english' if language=='en' else 'cantonese'
    text=cue.get(field,'');count=units(text,language);seconds=cue.get('speechEnd',cue['end'])-cue.get('speechStart',cue['start'])
    reference=caption_reference(cfg,cues,index);reasons=[]
    # This nominates a review; it does not establish a translation defect.
    if repeated_phrase(text,language):reasons.append('repeated-phrase')
    target=budget(seconds,language)
    if count>max(target*1.8,target+(5 if language=='en' else 8)):reasons.append('large-spoken-duration-expansion')
    caption=reference.get('text','');ref_language=reference.get('language')
    if caption and ref_language in ('zh','en'):
        if language=='yue' and ref_language=='zh':expected=units(caption,'yue')
        elif language=='en' and ref_language=='en':expected=units(caption,'en')
        else:
            # Cross-language comparison uses a rough spoken-duration estimate,
            # not equality between Chinese characters and English word counts.
            reference_units=units(caption,'yue' if ref_language=='zh' else 'en')
            expected=reference_units/(4.5 if ref_language=='zh' else 2.4)*(4.5 if language=='yue' else 2.4)
        if count>max(expected*1.5,expected+(3 if language=='en' else 4)):
            reasons.append('caption-relative-expansion')
    return dict(reference=reference,reasons=reasons,units=count,sourceSpeechSeconds=round(seconds,3),
        # Ask for a modest edit first; meaning verification can retain the full
        # draft when brevity would remove a substantive clause.
        targetUnits=max(1,math.floor(count*.75)))


def review(w,cfg,job,cues,languages):
    if cfg.get('editorRender') or cfg.get('repairOnly') or (cfg.get('scriptLocked') and not cfg.get('automaticDurationRewrite')):return []
    from concise_dialogue import compact
    from normal_mode import valid
    from translation_source import audio_primary
    path=Path(job)/'translation-brevity.json'
    try:saved=json.loads(path.read_text())
    except (OSError,ValueError):saved={}
    cache=saved.get('cache',{});changed=[]
    for language in sorted(languages):
        field='english' if language=='en' else 'cantonese';pending=[];targets={};keys={}
        for i,cue in enumerate(cues):
            if not cue.get('enabled',True) or cue.get('preserveOriginalSpeech') or cue.get('editorAudio') or not valid(cue.get(field,''),language):continue
            evidence=assess(cfg,cues,i,language)
            if not evidence['reasons']:continue
            # Exclude the current draft from the identity: a resume or later
            # duration edit must not start a fresh verbosity-review loop.
            identity=[REVISION,cfg.get('model'),language,cue.get('reviewIndex',i),cue['start'],cue['end'],cue.get('japanese') or cue.get('text',''),evidence['reference']]
            key=hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest();keys[i]=key
            if key in cache:
                record=cache[key]
                if record.get('after') and record.get('before')==cue[field]:
                    cue.setdefault('preBrevityEnglish' if language=='en' else 'preBrevityCantonese',cue[field]);cue[field]=record['after'];changed.append(i)
                continue
            cache[key]=dict(index=cue.get('reviewIndex',i)+1,language=language,before=cue[field],status='attempted',**evidence)
            pending.append(i);targets[i]=evidence['targetUnits']
        if not pending:continue
        w.atomic_json(path,dict(revision=REVISION,cache=cache,qualityCertified=False))
        w.emit('翻譯精簡核對',f'{language} · 只核對 {len(pending)} 句疑似冗長／重複譯稿；字幕長度只供參考，保留原聲意思。',.54)
        local=dict(cfg,targetLanguage=language)
        if any(audio_primary(cfg,cues[i]) for i in pending):local['ocrEvidenceOnly']=True
        accepted=compact(w,local,job,cues,pending,targets,field=field)
        for i in pending:
            record=cache[keys[i]];record['status']='accepted' if i in accepted else 'retained-original'
            if i in accepted:
                cue=cues[i];cue.setdefault('preBrevityEnglish' if language=='en' else 'preBrevityCantonese',record['before'])
                record['after']=cue[field];changed.append(i)
        w.atomic_json(path,dict(revision=REVISION,cache=cache,qualityCertified=False))
    if changed:w.atomic_json(Path(job)/'cues.json',cues)
    return sorted(set(changed))
