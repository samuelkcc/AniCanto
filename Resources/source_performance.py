"""Evidence-based source preservation before translation; no spelling-only bypass."""
import re,json
from pathlib import Path
from atomic_files import write_json

VOWELS=set('あぁアァうぅウゥえぇエェおぉオォーｰはハっッ')

def candidate(c,cfg):
    text=''.join(x for x in c.get('japanese',c.get('text','')) if x.isalnum() or x in 'ーｰ')
    repeated= len(text)>=3 and set(text)<=VOWELS
    # A song that straddles a detector boundary remains a candidate, never an
    # automatic preservation based on repeated lyric spelling alone.
    near_song=not cfg.get('translateOPED') and any(c['start']<r['end']-cfg.get('startOffset',0)+4 and c['end']>r['start']-cfg.get('startOffset',0)-4 for r in cfg.get('opRanges',[]))
    return repeated or near_song

def decision(c,original,stem,cfg):
    duration=c['end']-c['start']
    if duration<=0:return None
    def evidence(rows,key):
        intervals=[]
        for r in rows:
            a=max(c['start'],r['start']);b=min(c['end'],r['start']+r['duration'])
            if b<=a:continue
            if key=='song':ok=max(r.get('singing',0),r.get('choir_singing',0))>=.5 and r.get('speech',1)<.35
            else:ok=max(r.get(k,0) for k in ('laughter','baby_laughter','belly_laugh','crying_sobbing','screaming','sigh','gasp','moaning_groaning'))>=.65 and r.get('speech',1)<.3 and r.get('singing',1)<.2
            if ok:intervals.append((a,b))
        from source_evidence import merge_ranges
        return sum(r['end']-r['start'] for r in merge_ranges([dict(start=a,end=b) for a,b in intervals]))/duration
    if not cfg.get('translateOPED') and min(evidence(original,'song'),evidence(stem,'song'))>=.65:return 'confirmed-source-song'
    lexical=re.sub(r'[\s\Wあぁアァうぅウゥえぇエェおぉオォーｰはハっッ啊呀哇哈]+','',c.get('subtitleHint',''))
    if not lexical and candidate(c,dict(cfg,opRanges=[])) and min(evidence(original,'event'),evidence(stem,'event'))>=.65:return 'confirmed-nonlexical-performance'
    return None

def apply(cfg,job,cues,run,emit):
    targets=[c for c in cues if candidate(c,cfg) and c.get('enabled',True) and not c.get('preserveOriginalSpeech') and not any(c.get(k) for k in ('cantonese','english','mandarin','editorAudio'))]
    if not targets or not cfg.get('preserveNonverbal') or not cfg.get('dialoguePath'):return cues
    original=Path(job)/'japanese-original.wav'
    if not original.is_file():return cues
    try:
        from nonverbal import classification
        emit('原聲表演分類','核對叫聲／歌曲候選；重用同一份原聲分類，唔因重複字就跳過對白。',.29)
        from track_control import check
        check(cfg)
        stem=classification(cfg,job,run)
        check(cfg)
        folder=Path(job)/'original-performance';folder.mkdir(exist_ok=True)
        heard=classification(dict(cfg,dialoguePath=str(original)),folder,run)
    except (RuntimeError,OSError,ValueError) as e:
        from track_control import UserSkipped
        if isinstance(e,UserSkipped):raise
        write_json(Path(job)/'source-performance-policy.json',dict(status='unavailable',error=str(e),rows=[]));return cues
    result=[]
    for n,c in enumerate(cues,1):
        if not any(c is t for t in targets):continue
        reason=decision(c,heard,stem,cfg)
        if reason:
            c.update(preserveOriginalSpeech=True,originalSpeechReason=reason,sourcePerformance=reason,
                     reviewNote='原片及分離聲分類共同確認：保留原聲表演／歌曲，唔當缺配音。')
            result.append(dict(index=c.get('reviewIndex',n-1)+1,start=c['start'],end=c['end'],reason=reason,evidence='paired-original-and-separated-classification'))
    write_json(Path(job)/'source-performance-policy.json',dict(status='complete',rows=result,qualityCertified=False))
    return cues
