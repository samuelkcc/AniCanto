"""Recover corrupt broad source clocks in finite audio windows. No OCR clocks."""
import hashlib,json,math,re,time
from pathlib import Path
REVISION='bounded-source-clock-263'
MAX_WINDOWS=12
WINDOW_SECONDS=8.0

def enabled(cfg):return cfg.get('sourceClockRecoveryRevision')==REVISION

def suspect(row,language='ja'):
 a,b=row.get('start',0),row.get('end',0);text=''.join(c for c in row.get('text','') if c.isalnum())
 if not text or b-a<7 or row.get('manual'):return False
 # A sustained cry or sung vowel is not a defective dialogue clock.
 if re.fullmatch(r'[あぁアァうぅウゥえぇエェおぉオォんンー]+',text):return False
 stretched=any(w.get('end',0)-w.get('start',0)>max(3.5,1.2*sum(c.isalnum() for c in w.get('word',''))) for w in row.get('words',[]))
 foreign=language=='ja' and bool(re.search(r'[\u0400-\u04ff]',text))
 return stretched and (len(text)/(b-a)<2 or foreign)

def windows(row,duration):
 a=max(0.,float(row['start']));b=min(float(duration),float(row['end']));result=[]
 while a<b-.001:
  end=min(b,a+WINDOW_SECONDS);result.append(dict(start=a,end=end,listenStart=max(0,a-.35),listenEnd=min(float(duration),end+.35)));a=end
 return result

def accepted(segments,window,healthy):
 result=[]
 for segment in segments:
  words=[]
  for w in segment.words or []:
   a=float(w.start)+window['listenStart'];b=float(w.end)+window['listenStart'];mid=(a+b)/2
   if not all(math.isfinite(x) for x in (a,b)) or b<a:continue
   if not window['start']<=mid<window['end']:continue
   if a<window['listenStart'] or b>window['listenEnd']+.01:continue
   if any(min(b,r['end'])-max(a,r['start'])>.04 for r in healthy):continue
   words.append(dict(start=a,end=b,word=w.word,probability=float(w.probability)))
  if not words or not any(w['end']>w['start'] for w in words):continue
  if any(words[i]['start']<words[i-1]['start'] or words[i]['start']<words[i-1]['end']-.04 for i in range(1,len(words))):continue
  row=dict(start=words[0]['start'],end=words[-1]['end'],text=''.join(w['word'] for w in words),words=words)
  if row['end']<=row['start'] or suspect(row) or any(w['end']-w['start']>max(2.,.65*sum(c.isalnum() for c in w['word'])) for w in words):continue
  if sum(w['probability'] for w in words)/len(words)<.55 or re.search(r'ご視聴ありがとうございました|チャンネル登録|[\u0400-\u04ff]',row['text']):continue
  result.append(dict(row,sourceClockRepaired=True,sourceClockRecovery=REVISION))
 return result

def repair(model,audio,rows,cfg,job,emit):
 if not enabled(cfg) or cfg.get('editorRender'):return rows
 from atomic_files import write_json
 from track_control import check,UserSkipped
 path=Path(job)/'source-clock-recovery.json'
 try:saved=json.loads(path.read_text())
 except (OSError,ValueError):saved=dict(revision=REVISION,attempts=0,spentSeconds=0,windows={})
 if saved.get('activeSince') is not None:
  saved['spentSeconds']+=max(0,time.time()-saved.pop('activeSince'));write_json(path,saved)
 result=[];healthy=[r for r in rows if not suspect(r,cfg.get('sourceLanguage','ja'))]
 for row in rows:
  if not suspect(row,cfg.get('sourceLanguage','ja')):result.append(row);continue
  replacements=[];unresolved=[]
  for window in windows(row,cfg['duration']):
   key=hashlib.sha256(json.dumps([REVISION,cfg.get('speechModel'),cfg.get('_sourceClockModelRevision'),cfg.get('sourceLanguage','ja'),row,window],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
   record=saved['windows'].get(key)
   if record is None:
    if saved['attempts']>=MAX_WINDOWS or saved['spentSeconds']>=90:
     unresolved.append(window);continue
    # Reserve first. Resume cannot refund a failed or interrupted inference.
    record=dict(status='reserved',window=window,rows=[]);saved['windows'][key]=record;saved['attempts']+=1;saved['activeSince']=time.time();write_json(path,saved)
    started=time.monotonic()
    try:
     check(cfg);emit('原聲時間覆核',f"局部辨識 {saved['attempts']}/{MAX_WINDOWS} · {window['start']:.2f}–{window['end']:.2f} 秒；保留已完成資料。",.27)
     decoded,_=model.transcribe(audio[round(window['listenStart']*16000):round(window['listenEnd']*16000)],language=cfg.get('sourceLanguage','ja'),word_timestamps=True,vad_filter=False,condition_on_previous_text=False,beam_size=5,max_new_tokens=256)
     fresh=accepted(decoded,window,healthy);record.update(status='complete' if fresh else 'unconfirmed',rows=fresh)
    except UserSkipped:raise
    except (OSError,RuntimeError,ValueError) as error:record.update(status='unconfirmed',error=str(error)[:200])
    finally:saved['spentSeconds']+=time.monotonic()-started;saved.pop('activeSince',None);write_json(path,saved)
   if record.get('status')=='complete' and record.get('rows'):replacements.extend(record['rows'])
   else:unresolved.append(window)
  result.extend(replacements)
  for window in unresolved:
   # These are explicit unresolved AUDIO windows, not fabricated word clocks.
   # Keep the original hypothesis for diagnostics, never translate its corrupt text.
   result.append(dict(start=window['start'],end=window['end'],text='',words=[],sourceClockOriginal=row,
    sourceClockUnconfirmed=True,sourceClockRecovery=REVISION,sourceClockRecoveryIncomplete=True))
 return sorted(result,key=lambda x:(x['start'],x['end']))
