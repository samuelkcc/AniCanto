"""Reconcile oversized automatic caption allocations with actual speech turns.

A caption can span several speakers/turns. Being grounded in that caption does
not imply its entire sentence belongs in a one-word Japanese speech window.
Manual editor scripts and source clocks are never rewritten by this pass.
"""
import json,math,re
from pathlib import Path
from script_gap_recovery import evidence,repeated_terms,valid

REVISION='caption-speech-fragment-audit-1'

def automatic(c):
    return c.get('enabled',True) and not c.get('editorID') and not c.get('manual') and not c.get('preserveOriginalSpeech') and not c.get('captionPolicyExcluded')

def suspects(cues):
    terms=repeated_terms(cues);result=[]
    for i,c in enumerate(cues):
        if not automatic(c):continue
        if c.get('captionTimingAlignment',{}).get('revision')==REVISION:continue
        text=c.get('cantonese','');n=sum(x.isalnum() for x in text)
        ja=re.sub(r'\W','',c.get('japanese',c.get('text','')))
        seconds=c.get('speechEnd',c['end'])-c.get('speechStart',c['start'])
        if seconds<=0 or not n or not ja:continue
        local=evidence(c)['captions']
        spanning=any(r.get('end',c['end'])-r.get('start',c['start'])>seconds*1.6 for r in local)
        if ((i in terms and n>len(terms[i])+2) or
            (n>max(8,math.ceil(seconds*7.5)) and n>len(ja)*1.3) or
            (len(ja)<=5 and n>max(6,len(ja)*2.2) and spanning)):
            result.append(i)
    return result


def audit(w,cfg,job,cues):
    from translation_source import audio_only
    if audio_only(cfg):return []
    """Expose bad source allocation; do not apply unverified model rewrites.

    Real EP06 trials showed that another decision-model pass could remove a
    negation or move a whole clause into the wrong speaker slot. Keep the
    approved script intact and report the specific structural evidence instead.
    """
    rows=[]
    for i in suspects(cues):
        cue=cues[i];source=evidence(cue);text=cue.get('cantonese','')
        characters=sum(c.isalnum() for c in text)
        rows.append(dict(index=cue.get('reviewIndex',i)+1,start=cue['start'],end=cue['end'],
            speechStart=cue.get('speechStart',cue['start']),speechEnd=cue.get('speechEnd',cue['end']),
            characters=characters,charactersPerSecond=round(characters/max(.01,source['seconds']),2),
            japanese=source['japanese'],script=text,captions=source['captions'],
            reason='caption-spans-multiple-speech-turns',
            message='配音稿可能包含鄰句字幕意思；未有經驗證嘅重新配對，保留原稿、角色及時間，唔採用模型臆測。'))
    w.atomic_json(Path(job)/'caption-timing-audit.json',dict(revision=REVISION,status='allocation-warning' if rows else 'no-structural-warning',rows=rows,
        method='Deterministic source-window and script-length evidence; not semantic certification'))
    if rows:w.emit('台詞時段檢查',f'{len(rows)} 段可能將跨句字幕放入短發聲時段；具體原文、字幕及字數已記錄，未任意改稿。',.54)
    return rows
