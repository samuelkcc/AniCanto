from primary_source import content as primary_content
"""Scene-bounded caption evidence, stable IDs and honest allocation diagnostics.

No AI-proposed clocks or automatic global script replacement. Translation uses
small requested ranges with read-only neighbouring speech and a shared pool.
"""
import hashlib,json
from pathlib import Path
REVISION='caption-scene-evidence-2-gap-bounded'
MAX_PROMPT_BYTES=14000


def batches(cues,max_rows=8,max_bytes=MAX_PROMPT_BYTES):
    start=0
    while start<len(cues):
        end=start;size=0
        while end<len(cues) and end-start<max_rows:
            c=cues[end]
            if end>start and c.get('start',0)-cues[end-1].get('end',0)>4:break
            n=len(json.dumps({k:c.get(k) for k in ('japanese','text','subtitleHint','captionCandidates','japaneseAlt')},ensure_ascii=False).encode())
            if end>start and size+n>max_bytes:break
            size+=n;end+=1
        yield start,end;start=end


def prepare(cfg,job,cues):
    from translation_source import audio_only
    if audio_only(cfg):return
    from worker import atomic_json
    base=Path(job)
    try:pool=json.loads((base/'subtitle-context.json').read_text())
    except (OSError,ValueError):pool=[]
    rows=[dict(id=i+1,start=c['start'],end=c['end'],text=c['text']) for i,c in enumerate(pool) if c.get('text','').strip()]
    summary=[]
    for n,cue in enumerate(cues):
        if cue.get('manual') or cue.get('editorID'):continue
        a,b=cue.get('speechStart',cue['start']),cue.get('speechEnd',cue['end'])
        local=[c for c in rows if c['end']>=a-2 and c['start']<=b+2]
        local.sort(key=lambda c:(-max(0,min(b,c['end'])-max(a,c['start'])),min(abs(c['start']-a),abs(c['end']-b))))
        cue['captionCandidates']=sorted(local[:4],key=lambda c:(c['start'],c['id']))
        cue['captionAlignmentRevision']=REVISION
        cue['captionEvidenceOnly']=bool(cfg.get('ocr') or cfg.get('translationSource')=='audio-and-ocr') if __import__('primary_source').enabled(cfg) else True
        cue['captionAlignment']=dict(status='candidate-evidence-only',sourceStart=a,sourceEnd=b,candidateIDs=[c['id'] for c in cue['captionCandidates']],omittedCandidates=max(0,len(local)-4),clocksChanged=False)
        if not cue.get('subtitleHint') and cue['captionCandidates']:cue['subtitleHint']=' ／ '.join(c['text'] for c in cue['captionCandidates'])
        if len(local)>4 or any(c['end']-c['start']>max(1,b-a)*1.6 for c in local) or (cue.get('sourceClockUnconfirmed') and local):
            summary.append(dict(index=cue.get('reviewIndex',n)+1,start=a,end=b,kind='caption-source-allocation',message='畫面字幕可能跨越多段原聲；配音只取本段原聲意思，字幕時間未當作配音時間。',candidateIDs=cue['captionAlignment']['candidateIDs']))
    atomic_json(base/'caption-alignment.json',dict(revision=REVISION,sourceCues=len(cues),captionRows=len(rows),maximumRows=8,maximumInputBytes=MAX_PROMPT_BYTES,issues=summary,sourceClocksChanged=False,semanticQualityCertified=False))


def payload(rows,cues,start,end,names):
    context=[];pool={}
    for i in range(max(0,start-2),min(len(cues),end+2)):
        c=cues[i]
        if (i<start and c.get('end',0)<cues[start]['start']-4) or (i>=end and c.get('start',0)>cues[end-1]['end']+4):continue
        context.append(dict(id=str(i),start=c['start'],end=c['end'],source=primary_content(c),requested=str(i) in rows))
        for caption in c.get('captionCandidates',[]):pool[caption['id']]=caption
    return dict(requested=rows,readOnlyContext=context,captionPool=list(pool.values()),names=names)


def record_batch(w,job,language,rows,result):
    path=Path(job)/'caption-batches.json'
    try:value=json.loads(path.read_text())
    except (OSError,ValueError):value=dict(revision=REVISION,batches={})
    identity=hashlib.sha256(json.dumps([language,rows],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
    value['batches'][identity]=dict(language=language,requested=list(rows),returned=[k for k in rows if isinstance(result.get(k),str) and result[k].strip()],status='complete' if all(isinstance(result.get(k),str) and result[k].strip() for k in rows) else 'partial',qualityCertified=False)
    w.atomic_json(path,value)


def glossary(w,cfg,job,corpus,prompt,schema):
    """Whole rows, persistent bounded requests; never slice JSON mid-episode."""
    path=Path(job)/'glossary-batches.json'
    try:ledger=json.loads(path.read_text())
    except (OSError,ValueError):ledger={}
    parts=[];part=[];size=0
    for row in corpus:
        length=len(json.dumps(row,ensure_ascii=False).encode())
        if part and size+length>18000:parts.append(part);part=[];size=0
        part.append(row);size+=length
    if part:parts.append(part)
    names=[]
    for n,part in enumerate(parts):
        key=hashlib.sha256(json.dumps([REVISION,cfg.get('model'),part],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24];saved=ledger.get(key,{})
        if saved.get('status')!='complete' and saved.get('attempts',0)<2:
            saved.update(status='reserved',attempts=saved.get('attempts',0)+1);ledger[key]=saved;w.atomic_json(path,ledger)
            try:
                answer=json.loads(w.ollama_chat(cfg['port'],cfg['model'],[dict(role='system',content=prompt),dict(role='user',content=json.dumps(dict(evidence=part,known_terms=names[-32:]),ensure_ascii=False))],structured=schema,think=False))
                if not isinstance(answer,dict) or not isinstance(answer.get('names'),list):raise ValueError('Invalid glossary response')
                saved.update(status='complete',names=answer['names'])
            except (OSError,ValueError,RuntimeError,TypeError) as error:saved.update(status='incomplete',error=str(error)[:300])
            w.atomic_json(path,ledger)
        names.extend(saved.get('names',[]));w.emit('人名用字',f'已整理場景詞彙 {n+1}/{len(parts)}；保留全片資料及已完成批次。',.30)
    return dict(names=names)
