"""Bounded contextual ASR recovery, with original word clocks and durable evidence.

The recognizer's full-pass text is a hypothesis. OCR never supplies a clock.
Healthy adjacent turns and unresolved source audio remain available.
"""
import copy,hashlib,json,math,re
from pathlib import Path
from difflib import SequenceMatcher
REVISION='source-fragments-4-word-clock-guard'


def norm(s):return ''.join(c for c in s if c.isalnum()).casefold()
def suspect(row,language='ja'):
    a,b=row.get('start',0),row.get('end',0);text=norm(row.get('text',''))
    if not text:return False
    if 0<b-a<.18:return True
    if language!='ja':return False
    words=row.get('words',[]);weak=bool(words and sum(w.get('probability',1) for w in words)/len(words)<.3 and len(text)<=12 and b-a<4)
    return bool(weak or re.fullmatch(r'[a-z]{1,12}',text) or (b-a<.4 and len(text)<=3) or
                re.search(r'([あぁアァうぅウゥえぇエェおぉオォー])\1{5,}',text))


def windows(rows,duration,language='ja',maximum=64):
    wanted=[i for i,r in enumerate(rows) if suspect(r,language) and not r.get('manual') and not r.get('sourceClockRecovery')]
    grouped=[]
    for i in wanted:
        a=max(0,rows[i]['start']-4);b=min(duration,rows[i]['end']+4)
        # Context may not cut through an adjacent source turn. Recognition may
        # expand its listening window, never the delivered subtitle clock.
        for _ in range(2):
            a=min([a]+[max(0,r['start']-.15) for r in rows if r['start']<a<r['end']])
            b=max([b]+[min(duration,r['end']+.15) for r in rows if r['start']<b<r['end']])
        if b-a>26:continue
        if grouped and a<=grouped[-1]['end'] and b-grouped[-1]['start']<=26:
            grouped[-1]['end']=b;grouped[-1]['indices'].append(i)
        else:grouped.append(dict(start=a,end=b,indices=[i]))
    return grouped[:maximum],wanted


def stretched(row):
    return any(w.get('end',0)-w.get('start',0)>max(2.,.65*len(norm(w.get('word','')))) for w in row.get('words',[]))


def select(rows,decoded,window,independent,language='ja'):
    """Only replace suspicious evidence; never borrow a neighbour's sentence."""
    targets=set(window['indices']);good=[r for i,r in enumerate(rows) if i not in targets]
    selected=[];independent=norm(independent)
    for r in decoded:
        words=r.get('words',[])
        if not words or any(not all(type(w.get(k)) in (int,float) and math.isfinite(w[k]) for k in ('start','end')) or w['end']<w['start'] for w in words):continue
        positive=[w for w in words if w['end']>w['start']]
        if not positive or stretched(r):continue
        a,b=positive[0]['start'],positive[-1]['end'];text=norm(r.get('text',''));prob=sum(w.get('probability',0) for w in words)/len(words)
        if not window['start']-.01<=a<b<=window['end']+.01 or b-a<.18 or not text or suspect(r,language) or prob<.65:continue
        if any(min(b,x['end'])-max(a,x['start'])>.06 for x in good):continue
        # Independent hearing corroborates text, not its word timestamps.
        blocks=SequenceMatcher(None,text,independent,autojunk=False).get_matching_blocks()
        agreement=sum(m.size for m in blocks)/max(1,len(text))
        if not independent or agreement<.8 or max((m.size for m in blocks),default=0)/max(1,len(text))<.5:continue
        if not any(a<=rows[i]['end']+2.8 and b>=rows[i]['start']-2.8 for i in targets):continue
        selected.append(dict(r,start=a,end=b,sourceClockRepaired=True,sourceFragmentRepair=REVISION,independentSupport=round(agreement,3)))
    return selected


def apply(rows,selected,indices):
    """Keep untouched turns and the original clocks of unconfirmed residuals."""
    selected=sorted(selected,key=lambda r:r['start']);out=[];targets=set(indices)
    for i,row in enumerate(rows):
        if i not in targets:out.append(row);continue
        remaining=[w for w in row.get('words',[]) if not any(min(w['end'],s['end'])-max(w['start'],s['start'])>0 for s in selected)]
        positive=[w for w in remaining if w['end']>w['start']]
        if positive:
            out.append(dict(row,start=positive[0]['start'],end=positive[-1]['end'],words=remaining,text=''.join(w['word'] for w in remaining),sourceClockUnconfirmed=True,sourceFragmentRepair=REVISION))
        elif not selected or not any(min(row['end'],s['end'])-max(row['start'],s['start'])>0 for s in selected):
            out.append(dict(row,sourceClockUnconfirmed=True,sourceFragmentRepair=REVISION))
    for candidate in selected:
        if not any(abs(candidate['start']-r['start'])<.02 and norm(candidate['text'])==norm(r['text']) for r in out):out.append(candidate)
    return sorted(out,key=lambda r:(r['start'],r['end']))


def repair(model,audio,rows,cfg,job,emit):
    from worker import atomic_json
    from track_control import check,UserSkipped
    from dubbing import model_job
    job=Path(job);language=cfg.get('sourceLanguage','ja')
    if cfg.get('editorRender') or cfg.get('sourceFragmentRepair',True) is False:return rows
    groups,wanted=windows(rows,cfg['duration'],language)
    if not wanted:return rows
    identity=hashlib.sha256(json.dumps([REVISION,cfg.get('speechModel'),cfg.get('asrModel'),language,rows],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
    folder=job/'source-fragments'/identity;folder.mkdir(parents=True,exist_ok=True)
    ledger_path=folder/'ledger.json'
    try:ledger=json.loads(ledger_path.read_text())
    except (OSError,ValueError):ledger=dict(revision=REVISION,windows={},independentAttempted=False)
    request_cues=[dict(start=g['start'],end=g['end'],japanese=' '.join(rows[i]['text'] for i in g['indices']),text=' '.join(rows[i]['text'] for i in g['indices']),enabled=True) for g in groups]
    result_file=folder/'asr-verification.json'
    if groups and language=='ja' and not ledger['independentAttempted']:
        ledger['independentAttempted']=True;atomic_json(ledger_path,ledger)
        try:
            check(cfg);model_job(cfg,'asr',dict(storage=cfg['storage'],job=str(folder),audio=str(job/'japanese-original.wav'),cues=request_cues,asrModel=cfg.get('asrModel')),emit)
        except UserSkipped:raise
        except (OSError,ValueError,RuntimeError) as e:ledger['independentError']=str(e)[:300];atomic_json(ledger_path,ledger)
    try:independent=json.loads(result_file.read_text());heard=independent['rows'] if independent.get('identity')==[[g['start'],g['end'],True] for g in groups] else []
    except (OSError,ValueError,KeyError):heard=[]
    selected=[];handled=[]
    for n,g in enumerate(groups):
        key=str(n);record=ledger['windows'].get(key)
        if record is None:
            record=dict(status='reserved',attempts=1,start=g['start'],end=g['end'],sourceIndices=g['indices'],rows=[]);ledger['windows'][key]=record;atomic_json(ledger_path,ledger)
            try:
                check(cfg);emit('原聲分段覆核',f'局部重聽 {n+1}/{len(groups)} · {g["start"]:.2f}–{g["end"]:.2f} 秒；沿用整集已完成資料。',.27,workID='source-fragment-repair',workCompleted=n,workTotal=len(groups))
                paired=heard[n].get('text','') if n<len(heard) else ''
                def decode(window):
                    segments,_=model.transcribe(audio[round(window['start']*16000):round(window['end']*16000)],language=language,word_timestamps=True,vad_filter=False,condition_on_previous_text=False,beam_size=5,max_new_tokens=256)
                    fresh=[]
                    for s in segments:
                        words=[dict(start=float(w.start)+window['start'],end=float(w.end)+window['start'],word=w.word,probability=float(w.probability)) for w in (s.words or [])]
                        if words:fresh.append(dict(start=words[0]['start'],end=words[-1]['end'],text=''.join(w['word'] for w in words),words=words))
                    return fresh
                fresh=decode(g);chosen=select(rows,fresh,g,paired,language)
                record.update(raw=fresh,independentText=paired,rows=chosen)
                # A long stretch of corrupt full-pass text can derail local ASR.
                # One smaller context, anchored on a short Latin fragment, is
                # permitted only after the paired wider pass yields no candidate.
                anchors=[rows[i] for i in g['indices'] if re.fullmatch('[a-z]{1,12}',norm(rows[i]['text'])) and .18<=rows[i]['end']-rows[i]['start']<=3.5]
                if (not chosen or any(stretched(r) for r in fresh)) and paired and anchors and g['end']-g['start']>12:
                    anchor=max(anchors,key=lambda r:r['end']-r['start']);narrow=dict(g,start=max(g['start'],anchor['start']-1.8),end=min(g['end'],anchor['end']+3))
                    # Never cut through a healthy adjacent turn.
                    healthy=[r for i,r in enumerate(rows) if i not in g['indices']]
                    for _ in range(2):
                        narrow['start']=min([narrow['start']]+[max(g['start'],r['start']-.15) for r in healthy if r['start']<narrow['start']<r['end']])
                        narrow['end']=max([narrow['end']]+[min(g['end'],r['end']+.15) for r in healthy if r['start']<narrow['end']<r['end']])
                    if narrow['end']-narrow['start']<=12:
                        record.update(attempts=2,smallerContext=narrow);atomic_json(ledger_path,ledger);check(cfg)
                        retry=decode(narrow);record['smallerRaw']=retry
                        for candidate in select(rows,retry,narrow,paired,language):
                            if not any(min(candidate['end'],r['end'])-max(candidate['start'],r['start'])>.06 for r in chosen):chosen.append(candidate)
                record.update(status='complete',rows=chosen)
            except UserSkipped:raise
            except (OSError,RuntimeError,ValueError) as e:record.update(status='unconfirmed',error=str(e)[:300])
            atomic_json(ledger_path,ledger)
        selected+=record.get('rows',[]);handled+=g['indices']
    result=apply(rows,selected,wanted)
    summary=dict(revision=REVISION,sourceSegments=len(rows),suspectSegments=len(wanted),windows=len(groups),maximumWindows=64,maximumPrimaryAttemptsPerWindow=2,recoveredSegments=len(selected),unconfirmedSegments=sum(bool(r.get('sourceClockUnconfirmed')) for r in result),ledger=str(ledger_path),sourceClockAuthority='original-audio-word-timestamps',modelTimesAllowed=False,qualityCertified=False,independentError=ledger.get('independentError'),unprocessedSegments=len(set(wanted)-set(handled)))
    atomic_json(job/'source-fragment-report.json',summary);emit('原聲分段覆核',f'已檢查 {len(groups)} 個局部時段，恢復 {len(selected)} 段原聲文字；未確認部分保留原聲及覆核提示。',.28)
    return result
