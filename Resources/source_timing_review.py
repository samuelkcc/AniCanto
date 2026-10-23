"""Bounded source-ASR anomaly repair; never derive speech clocks from OCR."""
import hashlib,json,math,re,time
from pathlib import Path
REVISION='source-word-clock-1'

def abnormal(row,spans):
    words=row.get('words',[]);a=row.get('start',0);b=row.get('end',0)
    if b-a<7:return False
    units=sum(c.isalnum() for c in row.get('text',''))
    stretched=any(w.get('end',0)-w.get('start',0)>max(3.5,1.2*sum(c.isalnum() for c in w.get('word',''))) for w in words)
    turns=[s for s in spans if min(b,s['end'])-max(a,s['start'])>.2]
    # A slow drawn-out phrase alone is not a defect. The abnormal word clock
    # must also span separate acoustically witnessed turns and sparse text.
    return stretched and units/max(.1,b-a)<2 and len(turns)>=2

def unconfirmed(row,start,end):
    return dict(row,start=start,end=end,words=[dict(start=start,end=end,word=row.get('text',''),probability=0)],sourceClockUnconfirmed=True)

def repair(model,audio,spans,rows,cfg,job,emit):
    from worker import atomic_json
    from dialogue import merge_spans
    path=Path(job)/'source-timing-review.json'
    try:ledger=json.loads(path.read_text())
    except (OSError,ValueError):ledger={}
    result=[];windows_used=0;started=time.monotonic()
    for row in rows:
        if not abnormal(row,spans):result.append(row);continue
        a,b=row['start'],row['end'];others=[r for r in rows if r is not row]
        windows=merge_spans([dict(start=max(0,s['start']-.18),end=min(cfg['duration'],s['end']+.18)) for s in spans if min(b,s['end'])-max(a,s['start'])>.2])
        replacements=[]
        for window in windows:
            start,end=window['start'],window['end']
            # Existing good turns have priority over a suspicious broad segment.
            if any(min(end,r['end'])-max(start,r['start'])>.05 for r in others):continue
            key=hashlib.sha256(json.dumps([REVISION,cfg.get('speechModel'),cfg.get('sourceLanguage','ja'),cfg.get('_sourceClockModelRevision'),start,end,row],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            if key not in ledger:
                if windows_used>=12 or time.monotonic()-started>90:
                    replacements.append(unconfirmed(row,start,end));continue
                windows_used+=1;emit('原聲時間覆核',f'只重聽異常原聲時段 {start:.2f}–{end:.2f} 秒（{windows_used}/12）；唔重做整集。',.27)
                # Reserve before inference; cancellation cannot multiply attempts.
                ledger[key]=dict(status='attempted',start=start,end=end,rows=[]);atomic_json(path,ledger)
                try:
                    decoded,_=model.transcribe(audio[round(start*16000):round(end*16000)],language=cfg.get('sourceLanguage','ja'),word_timestamps=True,vad_filter=False,condition_on_previous_text=False,beam_size=5,max_new_tokens=256)
                    fresh=[]
                    for segment in decoded:
                        words=[dict(start=max(start,float(w.start)+start),end=min(end,float(w.end)+start),word=w.word,probability=float(w.probability)) for w in (segment.words or []) if w.end>=w.start]
                        if not words:continue
                        candidate=dict(start=words[0]['start'],end=words[-1]['end'],text=''.join(w['word'] for w in words),words=words,sourceClockRepaired=True)
                        if candidate['end']>candidate['start'] and not abnormal(candidate,spans) and not re.search(r'ご視聴ありがとうございました|チャンネル登録',candidate['text']):fresh.append(candidate)
                    ledger[key].update(status='complete',rows=fresh)
                except (RuntimeError,ValueError) as error:ledger[key].update(status='unconfirmed',error=str(error)[:200])
                atomic_json(path,ledger)
            fresh=ledger[key].get('rows',[])
            if fresh:replacements.extend(fresh)
            else:
                # A successful neighbouring window must not delete a failed
                # source turn. Retain its acoustic bounds and original audio.
                replacements.append(unconfirmed(row,start,end))
        if replacements:result.extend(replacements)
        else:result.append(dict(row,sourceClockUnconfirmed=True))
    return sorted(result,key=lambda r:r['start'])
