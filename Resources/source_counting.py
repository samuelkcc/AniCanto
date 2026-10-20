"""Repair copied captions over a clear consecutive spoken counting sequence.

An isolated ASR digit is ambiguous. Require at least three short consecutive
source numbers and an identical multi-character translation across the run.
Manual scripts are never rewritten. No extra model or inference is needed.
"""
import json,math,re,unicodedata
from pathlib import Path

REVISION='source-counting-2-confirmed-source-only'

def value(cue):
    source=unicodedata.normalize('NFKC',cue.get('japanese') or cue.get('text','')).strip(' .。!！,，?？')
    return int(source) if re.fullmatch(r'\d{1,2}',source) and 0<=int(source)<=99 else None

def spoken(n,language):
    if language=='yue':
        digits='零一二三四五六七八九'
        return digits[n] if n<10 else ('十' if n//10==1 else digits[n//10]+'十')+(digits[n%10] if n%10 else '')
    small=['zero','one','two','three','four','five','six','seven','eight','nine','ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen']
    tens=['','','twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety']
    return small[n] if n<20 else tens[n//10]+('-'+small[n%10] if n%10 else '')

def confirmed(cue,language):
    # A run of digits is not independent evidence: music/chanting hallucinations
    # can look like counting. Contradictory captions and ASR warnings veto it.
    score=cue.get('asrConfidence')
    if cue.get('sourceReviewReasons') or not isinstance(score,(int,float)) or not math.isfinite(score) or score<.85:return False
    number=value(cue)
    if number is None:return False
    witnesses=[str(cue.get(k,'')).strip(' .。!！,，?？') for k in ('japaneseAlt','japaneseRecheck')]
    if str(number) not in witnesses:return False
    caption=re.sub(r'\W','',unicodedata.normalize('NFKC',cue.get('subtitleHint','')))
    return not caption or caption in (str(number),spoken(number,'yue'),spoken(number,language))


def repair(cfg,job,cues):
    if cfg.get('productionMode')!='normal' or cfg.get('editorRender') or cfg.get('repairOnly') or (cfg.get('scriptLocked') and not cfg.get('automaticDurationRewrite')):return []
    field='cantonese';language=cfg.get('targetLanguage','yue');runs=[];run=[]
    changed=[];records=[]
    # Resume must also undo our earlier speculative auto-rewrite. Restore only
    # an unchanged machine-produced numeral, never a later human edit.
    for i,c in enumerate(cues):
        previous=c.get('preCountingRepair');n=value(c)
        if previous and n is not None and not confirmed(c,language) and c.get(field)==spoken(n,language):
            before=c[field];c[field]=previous
            if language=='en' and c.get('english')==before:c['english']=previous
            if not c.get('captionOverride') and c.get('captionText')==before:c['captionText']=previous
            c['countingRepairReverted']=True;changed.append(i)
            records.append(dict(index=c.get('reviewIndex',i)+1,source=c.get('japanese') or c.get('text'),before=before,after=previous,method='restore-uncertain-counting-rewrite',qualityCertified=False))
    for i,c in enumerate(cues):
        n=value(c)
        eligible=confirmed(c,language) and n is not None and c.get('enabled',True) and not c.get('editorAudio') and not c.get('preserveOriginalSpeech') and .08<=c['end']-c['start']<=1.5
        if run and (not eligible or n!=value(cues[run[-1]])+1 or c['start']-cues[run[-1]]['end']>1.5):runs.append(run);run=[]
        if eligible:run.append(i)
    if run:runs.append(run)
    for run in runs:
        if len(run)<3:continue
        texts=[re.sub(r'\W','',cues[i].get(field,'')) for i in run]
        if len(set(texts))!=1 or len(texts[0])<3:continue
        for i in run:
            c=cues[i];before=c.get(field,'');text=spoken(value(c),language)
            c.setdefault('preCountingRepair',before);c[field]=text
            if language=='en':c['english']=text
            if not c.get('captionOverride'):c['captionText']=text
            changed.append(i);records.append(dict(index=c.get('reviewIndex',i)+1,source=c.get('japanese') or c.get('text'),before=before,after=text,method='consecutive-source-counting',qualityCertified=False))
    if changed:
        from worker import atomic_json
        job=Path(job);atomic_json(job/'source-counting-repair.json',dict(revision=REVISION,rows=records));atomic_json(job/'cues.json',cues)
        review=job/'review.json'
        if review.is_file():
            data=json.loads(review.read_text());mapping={c.get('reviewIndex',i):c for i,c in enumerate(cues)}
            for i,c in enumerate(data.get('cues',[])):
                if (revised:=mapping.get(c.get('reviewIndex',i))) is not None:c.update({k:revised[k] for k in ('cantonese','english','captionText','preCountingRepair') if k in revised})
            atomic_json(review,data)
    return changed
