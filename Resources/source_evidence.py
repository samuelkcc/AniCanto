"""Time-indexed subtitle evidence and bounded contextual re-listening."""
import hashlib,json,math,re
from pathlib import Path

def caption_records(job):
    path=job/'subtitle-context.json'
    if not path.exists():return []
    rows=json.loads(path.read_text());result=[]
    for i,c in enumerate(rows):
        a,b=float(c['start']),float(c['end'])
        if math.isfinite(a+b) and b>a and c.get('text','').strip():
            result.append(dict(id=f'caption_{i+1}',start=a,end=b,text=c['text']))
    return result

def chinese_caption(row):
    text=row.get('text','')
    return bool(any('\u3400'<=c<='\u9fff' for c in text) and not re.search(r'[\u3040-\u30ff]',text))

def chinese_captions(captions,cfg=None):
    language=str((cfg or {}).get('sourceCaptionLanguage','')).lower()
    if language in ('jpn','ja','eng','en'):return []
    if language.startswith(('zh','chi','yue')):
        return [r for r in captions if any('\u3400'<=c<='\u9fff' for c in r.get('text',''))]
    # Kanji-only lines in a Japanese track do not make it a Chinese track.
    kana=sum(bool(re.search(r'[\u3040-\u30ff]',r.get('text',''))) for r in captions)
    chinese=[r for r in captions if chinese_caption(r)]
    return [] if kana>len(chinese) else chinese

def merge_ranges(rows):
    result=[]
    for r in sorted(rows,key=lambda r:r['start']):
        if r['end']<=r['start']:continue
        if result and r['start']<=result[-1]['end']:
            result[-1]['end']=max(result[-1]['end'],r['end'])
        else:result.append(dict(start=r['start'],end=r['end']))
    return result

def complement(rows,duration):
    result=[];previous=0
    for r in merge_ranges(rows):
        a,b=max(0,r['start']),min(duration,r['end'])
        if a>previous:result.append(dict(start=previous,end=a))
        previous=max(previous,b)
    if previous<duration:result.append(dict(start=previous,end=duration))
    return result

def apply_caption_policy(cfg,captions,cues):
    """Chinese captions authorize speech windows; ASR alone cannot add dialogue.

    No Chinese captions at all retains the subtitle-free ASR workflow. Source
    captions keep their own timestamps, independently of recognized word bounds.
    """
    if __import__('primary_source').enabled(cfg):
        for c in cues:
            if c.get('captionPolicyExcluded')=='outside-original-chinese':
                c.pop('captionPolicyExcluded',None);c['enabled']=c.pop('captionPolicyWasEnabled',True)
            c['captionRecords']=[r for r in captions if min(c['end'],r['end'])>max(c['start'],r['start'])]
        cfg['_captionPreserveRanges']=[]
        cfg['captionPolicy']=dict(revision=5,mode='subtitle-first-with-audio-gaps',captionCount=len(captions))
        return dict(**cfg['captionPolicy'],excluded=[],preservedRanges=[])
    # OCR misses must not suppress independently heard Japanese dialogue.
    # Its text remains available below as context, not a permission mask.
    chinese=[] if cfg.get('ocrEvidenceOnly') or cfg.get('ocr') else chinese_captions(captions,cfg)
    mode='original-chinese' if chinese else 'audio-only'
    import opening
    translated_openings=opening.detected_local_ranges(cfg) if cfg.get('translateOPED') else []
    cfg['captionPolicy']=dict(revision=4,mode=mode,captionCount=len(chinese),translateOPED=bool(cfg.get('translateOPED')))
    cfg['_captionPreserveRanges']=complement(chinese,float(cfg.get('duration',max((c['end'] for c in cues),default=0)))) if chinese else []
    cfg['_captionPreserveRanges']=opening.subtract_ranges(cfg['_captionPreserveRanges'],translated_openings)
    for c in cues:
        lexical=''.join(x for x in c.get('japanese',c.get('text','')) if x.isalnum() and x not in 'ーｰ')
        c['nonlexicalTail']=bool(c.get('japanese',c.get('text','')) and not lexical and c['end']-c['start']<.8 and not c.get('captionSpeechRescue'))
        a,b=c.get('speechStart',c['start']),c.get('speechEnd',c['end'])
        local=[r for r in (chinese if chinese else captions) if r['end']>a and r['start']<b]
        # Independent ASR/caption clocks can miss a short lexical reaction by
        # a few frames. Retain its original audio bounds and nearby caption
        # evidence; do not expand speech into a neighbouring turn or admit hums.
        if chinese and not local and len(lexical)>=2 and not c['nonlexicalTail'] and isinstance(c.get('asrConfidence'),(int,float)) and c['asrConfidence']>=.55:
            nearby=[r for r in chinese if 0<=r['start']-b<=.12 or 0<=a-r['end']<=.12]
            if nearby:
                local=nearby;c['captionBoundaryRescue']=True
        # Drop tiny boundary crumbs only when a substantial caption also exists.
        strong=[r for r in local if min(b,r['end'])-max(a,r['start'])>=min(.3,.25*(r['end']-r['start']))]
        if strong:local=strong
        c['captionRecords']=local
        # Opt-in OP/ED translation admits lexical Japanese even when the
        # Chinese subtitle track omits song lyrics. Body-caption authority and
        # explicit user disables remain unchanged.
        c['openingTranslation']=bool(lexical and opening.excludes(c,translated_openings))
        reason='nonlexical-asr-tail' if c['nonlexicalTail'] else ('outside-original-chinese' if chinese and not local and not c['openingTranslation'] else '')
        if reason:
            if not c.get('captionPolicyExcluded'):c['captionPolicyWasEnabled']=c.get('enabled',True)
            c.update(enabled=False,captionPolicyExcluded=reason,cantonese='',english='',hybridNeedsReview=False)
            c['reviewNote']='非對白尾音，保留原聲。' if c['nonlexicalTail'] else '本時段冇原裝中文字幕；按字幕範圍保留原聲，不生成配音。'
        else:
            if c.pop('captionPolicyExcluded',None):c['enabled']=c.pop('captionPolicyWasEnabled',True)
    # Caption display clocks authorize dialogue, but do not delimit its audio.
    # EP06 speech can start a full second before the corresponding caption.
    # Restoring Japanese in that gap used to erase an already completed dub.
    cfg['_captionPreserveRanges']=protect_speech(cfg,cfg['_captionPreserveRanges'],cues)
    return dict(**cfg['captionPolicy'],excluded=[i+1 for i,c in enumerate(cues) if c.get('captionPolicyExcluded')],preservedRanges=cfg['_captionPreserveRanges'])

def protect_speech(cfg,ranges,cues,timing=()):
    import opening
    protected=[]
    duration=float(cfg.get('duration',max((c['end'] for c in cues),default=0)))
    rows={r['index']:r for r in timing if r.get('index') is not None}
    for n,c in enumerate(cues):
        if not c.get('enabled',True) or c.get('captionPolicyExcluded') or c.get('preserveOriginalSpeech'):continue
        a=float(c.get('speechStart',c['start']));b=float(c.get('speechEnd',c['end']))
        row=rows.get(c.get('reviewIndex',n)+1,{})
        if not row.get('skipped') and row.get('renderedSeconds',0)>0:
            a=min(a,float(row.get('renderedStart',a)));b=max(b,float(row.get('renderedEnd',b)))
        a=max(0.,a);b=min(duration,b)
        if b>a:protected.append(dict(start=a,end=b))
    return opening.subtract_ranges(ranges,protected)

def effective_caption_config(cfg,job):
    """Also protect old saved projects; they predate caption policy revision 4."""
    from audio_fallback import read_json
    review=read_json(Path(job)/'review.json',{})
    if not review.get('cues'):return cfg
    ranges=protect_speech(cfg,cfg.get('_captionPreserveRanges',[]),review['cues'],read_json(Path(job)/'timing.json',[]))
    return dict(cfg,_captionPreserveRanges=ranges)

def recover_caption_base(cfg,job,native,run,emit):
    """Repair pre-v4 exports from dry speech, preserving the old movie untouched."""
    from audio_fallback import read_json
    cfg= dict(read_json(Path(job)/'review.json',{}).get('config',{}),**cfg)
    if cfg.get('captionPolicy',{}).get('mode')!='original-chinese' or not Path(native).is_file():return Path(native)
    effective=effective_caption_config(cfg,job)
    if effective.get('_captionPreserveRanges')==cfg.get('_captionPreserveRanges'):return Path(native)
    job=Path(job);ledger=job/'caption-base-recovery.json';old=read_json(ledger,{})
    source=Path(old.get('originalOutput',str(native)))
    voice=next((p for p in (job/'cantonese-performance.wav',job/'cantonese.wav') if p.is_file()),None)
    if voice is None:raise ValueError('缺少原始配音混音，未能修正舊字幕遮罩；未覆寫現有影片。')
    background=Path(cfg.get('backgroundPath',''))
    inputs=[source,voice]+([background] if background.is_file() else [])
    signature=[[(str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in inputs],
               effective.get('_captionPreserveRanges'),cfg.get('opRanges'),cfg.get('translateOPED'),
               cfg.get('autoSkipOP'),cfg.get('backgroundGain',.8),cfg.get('backgroundDucking'),cfg.get('aiAutoFix'),'speech-protected-caption-mask-1']
    key=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
    output=job/'caption-corrected-base.mp4'
    if old.get('key')==key and output.is_file():return output
    from types import SimpleNamespace
    emit('混音修復','修正舊版字幕顯示遮罩；保護完整日文發聲時段內嘅廣東話，保留原始錄音及舊影片。',.94)
    audio=mix_caption_audio(SimpleNamespace(run=run,emit=emit),cfg,job,voice,background if background.is_file() else None)
    temporary=job/'caption-corrected-base.partial.mp4'
    run([cfg['ffmpeg'],'-v','error','-y','-i',source,'-i',audio,'-map','0:v:0','-map','1:a:0',
         '-map','0:a:1?','-map','0:s?','-map_metadata','0','-map_chapters','0','-c:v','copy','-c:a','aac',
         '-ac','2','-c:s','copy','-t',str(cfg['duration']),temporary])
    temporary.replace(output)
    from worker import atomic_json
    atomic_json(ledger,dict(key=key,originalOutput=str(source),output=str(output),reason='Subtitle display clocks must never replace required dubbed speech.'))
    return output

def mix_caption_audio(w,cfg,job,audio,background=None):
    """Replace audio outside caption windows using a fixed-size PCM mask graph.

    Failed real dialogue inside a caption window never gets Japanese fallback.
    This also prevents delivered TTS from leaking into the next music interval.
    """
    import opening,nonverbal
    cfg=effective_caption_config(cfg,job)
    base=audio
    if background is not None:
        gain=float(cfg.get('backgroundGain',.8))
        if not math.isfinite(gain) or not 0<=gain<=1.5:raise ValueError('背景音量設定無效。')
        from mix_balance import separated_filter,resolve as resolve_mix_balance
        balance=resolve_mix_balance(cfg,job,background)
        if balance=='auto':w.emit('混音自動修復','偵測到細聲配音被背景掩蓋；說話期間有限降低背景，保留原裝日文音軌。')
        graph=separated_filter(gain,'dub',balance).replace('[1:a:0]','[0:a:0]').replace('[3:a:0]','[1:a:0]')
        base=job/'caption-mixed.wav'
        w.run([cfg['ffmpeg'],'-v','error','-y','-i',audio,'-i',background,'-filter_complex',graph,'-map','[dub]','-ar','48000','-ac','2',base])
    elif cfg.get('mixOriginal'):
        base=job/'caption-mixed.wav'
        graph='['+__import__('source_language').audio_label(cfg,1)+']volume=0.12[bg];[0:a:0][bg]amix=inputs=2:duration=first:normalize=0[dub]'
        w.run([cfg['ffmpeg'],'-v','error','-y','-i',audio,'-ss',str(cfg.get('startOffset',0)),'-t',str(cfg['duration']),'-i',cfg['video'],'-filter_complex',graph,'-map','[dub]','-ar','48000','-ac','2',base])
    ranges=[(r['start'],r['end']) for r in opening.local_ranges(cfg)]
    return nonverbal.preserve_background(dict(cfg,_originalSoundRanges=ranges),job,base,w.run,w.emit)

def windows(cues,duration):
    result=[]
    for i,c in enumerate(cues):
        score=c.get('asrConfidence');agreement=c.get('asrAgreement')
        if not c.get('enabled',True) or not ((score is not None and score<.55) or (agreement is not None and agreement<.5)):continue
        a=max(0,c['start']-1.5);b=min(duration,c['end']+1.5)
        if result and a<=result[-1]['end'] and b-result[-1]['start']<=24:
            result[-1]['end']=b;result[-1]['indices'].append(i)
        else:result.append(dict(start=a,end=b,indices=[i],text='',japanese=''))
    return result

def prepare(w,cfg,job,cues):
    from translation_source import audio_only,remove_caption_evidence
    remove_caption_evidence(cfg,cues)
    if audio_only(cfg):
        return
    captions=caption_records(job)
    policy=apply_caption_policy(cfg,captions,cues)
    w.atomic_json(job/'caption-policy.json',policy) if hasattr(w,'atomic_json') else None
    if hasattr(w,'emit'):
        w.emit('原字幕配音範圍',f"{len(policy['excluded'])} 段按原字幕時段或非對白尾音排除；冇中文字幕嘅全片使用日語辨識。",.30)
    candidates=windows(cues,cfg.get('duration',max((c['end'] for c in cues),default=0)))
    audio=Path(cfg.get('dialoguePath') or job/'japanese-original.wav')
    if not candidates or not audio.is_file() or not (Path(cfg.get('storage',''))/'asr-ready.json').exists():return
    signature=[str(audio),audio.stat().st_size,audio.stat().st_mtime_ns,candidates,'context-asr-1']
    key=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()[:20]
    folder=job/('context-listen-'+key);folder.mkdir(exist_ok=True)
    cache=folder/'result.json'
    if cache.exists():result=json.loads(cache.read_text())
    else:
        from dubbing import model_job
        converted=folder/'audio.wav'
        w.emit('日語局部重聽',f'只重聽 {len(candidates)} 段有疑點原聲，加入前後語境；保留原有起止時間。',.30)
        w.run([cfg['ffmpeg'],'-v','error','-y','-i',audio,'-ar','16000','-ac','1',converted])
        model_job(cfg,'asr',dict(storage=cfg['storage'],job=str(folder),audio=str(converted),cues=candidates),w.emit)
        result=json.loads((folder/'asr-verification.json').read_text())
        if len(result.get('rows',[]))!=len(candidates):raise ValueError('語境重聽漏段；已保存進度。')
        w.atomic_json(cache,result)
        converted.unlink(missing_ok=True)
    for window,row in zip(candidates,result['rows']):
        for i in window['indices']:
            cues[i]['contextHearing']=dict(start=window['start'],end=window['end'],text=row['text'])
    w.atomic_json(job/'context-listen-report.json',dict(windows=len(candidates),affected=sum(len(r['indices']) for r in candidates)))

def refine_allocation(allocation,source):
    """Remove a duplicated suffix from shared-caption allocations, not real repeats."""
    import re
    clean=lambda t:''.join(c for c in t if c.isalnum())
    by_id={r['id']:r for r in source}
    changes=[]
    keys=list(allocation)
    for left,right in zip(keys,keys[1:]):
        a,b=allocation[left],allocation[right]
        if not set(a['caption_ids'])&set(b['caption_ids']):continue
        x,y=clean(a['content']),clean(b['content'])
        if not y or x==y or not x.endswith(y):continue
        # Only trim whitespace-delimited caption fragments (e.g. two name calls).
        parts=a['content'].split()
        if len(parts)<2 or clean(parts[-1])!=y:continue
        ja,jb=by_id[left]['japanese'],by_id[right]['japanese']
        if ja and jb and clean(ja)==clean(jb):continue
        a['content']=' '.join(parts[:-1]);changes.append(dict(id=left,removed=y,assignedTo=right))
    return changes

def clean_text(text):
    return ''.join(c for c in text if c.isalnum())

def temporal_captions(turn):
    """Only captions intersecting this voice interval may supply its words.

    Context captions remain available to understand the scene, never as words
    for another timestamp. Do not attach the nearest caption to uncaptained cries.
    """
    if turn.get('caption_policy_excluded') or turn.get('caption_auxiliary'):return []
    return [r for r in turn.get('caption_records',[])
            if r['end']>turn['start'] and r['start']<turn['end']]

def reaction_only(turn):
    import re
    return bool(not turn.get('raw_asr_unreliable') and re.fullmatch(r'(?:いや[ーぁ]*|え[ーぇえ]*|あ[ーぁあ]*|お[ーぉお]*|う[ーぅう]*|はい|うん|へ[ーぇへ]*|ん[ーん]*)[、。？！!?\s]*',turn.get('japanese','')))

def repeated_short_call(a,b,content):
    from difflib import SequenceMatcher
    x,y=clean_text(a.get('raw_japanese',a.get('japanese',''))),clean_text(b.get('raw_japanese',b.get('japanese','')))
    return bool(x and y and len(clean_text(content))<=8 and len(x)<=16 and len(y)<=16
                and min(a.get('end',0)-a.get('start',0),b.get('end',0)-b.get('start',0))>=.6
                and re.fullmatch(r'[\u30a0-\u30ff]+',x+y) and SequenceMatcher(None,x,y).ratio()>=.55)

def allocation_errors(allocation,source,keys):
    by_id={r['id']:r for r in source};errors={}
    owners={}
    for turn in source:
        for r in temporal_captions(turn):owners.setdefault(r['id'],set()).add(turn['id'])
    for k in keys:
        row=allocation.get(k);local=temporal_captions(by_id[k]);allowed={r['id']:r for r in local}
        if (not isinstance(row,dict) or not isinstance(row.get('content'),str) or
            not isinstance(row.get('caption_ids'),list) or not isinstance(row.get('uncertain'),bool)):
            errors[k]='invalid-allocation';continue
        ids=row['caption_ids'];content=clean_text(row['content'])
        if any(not isinstance(i,str) or i not in allowed for i in ids):
            errors[k]='caption-outside-speech-interval';continue
        own_reaction=bool(reaction_only(by_id[k]) and not ids and content==clean_text(by_id[k].get('japanese','')) and all(len(owners[r['id']])>1 for r in local))
        if own_reaction:continue
        if local and (not ids or not content):
            errors[k]='missing-local-caption';continue
        text=''.join(clean_text(allowed[i]['text']) for i in ids)
        if ids and content not in text:
            errors[k]='content-not-extracted-from-caption';continue
        exclusive=[r for r in local if owners[r['id']]=={k}]
        if any(r['id'] not in ids or clean_text(r['text']) not in content for r in exclusive):
            errors[k]='omitted-exclusive-caption'
    # A shared caption must be divided, not read in full at every ASR fragment.
    # Preserve actual repeated spoken calls; merely sharing the caption is not proof.
    for left,right in zip(keys,keys[1:]):
        a,b=allocation.get(left,{}),allocation.get(right,{})
        ja,jb=clean_text(by_id[left].get('raw_japanese',by_id[left].get('japanese',''))),clean_text(by_id[right].get('raw_japanese',by_id[right].get('japanese','')))
        # A whole caption can be repeated inside a longer, otherwise different
        # allocation. Timestamp overlap alone cannot establish which utterance
        # owns it: subtitles commonly lag the sound. Reconcile BOTH turns using
        # their transcripts instead of silently deleting the weaker overlap.
        common=set(a.get('caption_ids',[]))&set(b.get('caption_ids',[]))
        local={r['id']:r for r in temporal_captions(by_id[left])}
        x,y=clean_text(a.get('content','')),clean_text(b.get('content',''))
        repeated=False
        if ja and jb:
            from difflib import SequenceMatcher
            repeated=SequenceMatcher(None,ja,jb).ratio()>=.85
        clauses=[clean_text(local[cid]['text']) for cid in common if cid in local]
        if (x!=y and ja and jb and not repeated and
                any(len(t)>=4 and t in x and t in y and
                    not repeated_short_call(by_id[left],by_id[right],t) for t in clauses)):
            errors[left]=errors[right]='duplicated-caption-clause'
        if (a.get('caption_ids') and set(a['caption_ids'])&set(b.get('caption_ids',[]))
            and clean_text(a.get('content','')) and clean_text(a.get('content',''))==clean_text(b.get('content',''))
            and ja and jb and ja!=jb and not repeated_short_call(by_id[left],by_id[right],a.get('content',''))):
            # Reject the weaker duplicate only. One ambiguous fragment must not
            # erase the complete, time-owned line as happened with long-vowel tails.
            score=lambda k:sum(max(0,min(by_id[k]['end'],r['end'])-max(by_id[k]['start'],r['start'])) for r in temporal_captions(by_id[k]))
            loser=right if score(left)>=score(right) else left
            errors[loser]='duplicated-shared-caption'
    return errors

def audit_allocations(cues):
    """Review saved source allocations without changing approved scripts/clocks.

    These are evidence warnings, not proof of a generated speech defect. A
    user may already have corrected the spoken text while old allocation
    metadata remains; preserve that text and expose the quotes for review.
    """
    from hybrid_script import evidence
    source=[evidence(c,i) for i,c in enumerate(cues)]
    allocation={str(i+1):c['captionAllocation'] for i,c in enumerate(cues)
                if c.get('enabled',True) and c.get('captionAllocation') and not c.get('captionPolicyExcluded')}
    errors=allocation_errors(allocation,source,list(allocation))
    return [dict(index=cues[int(k)-1].get('reviewIndex',int(k)-1)+1,
                 start=cues[int(k)-1]['start'],end=cues[int(k)-1]['end'],
                 reason=reason,japanese=cues[int(k)-1].get('japanese',''),
                 captionQuote=allocation[k].get('content',''),
                 script=cues[int(k)-1].get('cantonese','')) for k,reason in errors.items()]

def anchor_allocation(allocation,source,keys):
    """Repair exclusive captions directly; shared captions need scene-level retry."""
    by_id={r['id']:r for r in source};owners={};changes=[]
    for turn in source:
        for r in temporal_captions(turn):owners.setdefault(r['id'],set()).add(turn['id'])
    for k in keys:
        turn=by_id[k];local=temporal_captions(turn)
        if local and reaction_only(turn) and all(len(owners[r['id']])>1 for r in local):
            original=dict(allocation.get(k,{}))
            allocation[k]=dict(content=turn['japanese'],caption_ids=[],uncertain=False,reactionOnly=True)
            if original!=allocation[k]:changes.append(dict(id=k,reason='shared-caption-does-not-replace-spoken-reaction',action='restore-own-transcription',caption_ids=[]))
    for k,reason in allocation_errors(allocation,source,keys).items():
        turn=by_id[k];local=temporal_captions(turn)
        if local and all(owners[r['id']]=={k} for r in local):
            allocation[k]=dict(content=' '.join(r['text'] for r in sorted(local,key=lambda r:r['start'])),caption_ids=[r['id'] for r in local],uncertain=False)
            changes.append(dict(id=k,reason=reason,action='restore-timed-caption',caption_ids=allocation[k]['caption_ids']))
        elif not local:
            allocation[k]=dict(content=turn.get('japanese') or turn.get('second_hearing') or '',caption_ids=[],uncertain=bool(turn.get('raw_asr_unreliable')))
            changes.append(dict(id=k,reason=reason,action='restore-own-transcription',caption_ids=[]))
    return changes

def grounded_line(k,row,source,allocation):
    """A real quote from a different turn is still invalid evidence."""
    if not isinstance(row,dict):return False
    by_id={r['id']:r for r in source};turn=by_id.get(k)
    if not turn:return False
    assigned=allocation.get(k,{})
    if assigned.get('blocked'):return False
    if assigned.get('reactionOnly') and (row.get('evidence_id')!=k or clean_text(row.get('quote',''))!=clean_text(assigned.get('content',''))):return False
    ident=row.get('evidence_id');quote=row.get('quote')
    if not isinstance(quote,str) or not quote.strip():return False
    local={r['id']:r for r in temporal_captions(turn)}
    # Caption extraction/allocation can format whitespace differently. Preserve
    # the actual characters and timestamp ownership; spacing is not meaning.
    same_words=lambda text:''.join(text.split())
    normalized=same_words(quote)
    if not normalized:return False
    if assigned.get('caption_ids') and any(ident not in local for ident in assigned['caption_ids']):return False
    if ident in local:
        grounded=normalized in same_words(local[ident]['text'])
    elif ident==k:
        fields=('japanese','second_hearing') if turn.get('caption_auxiliary') else ('caption',) if assigned.get('caption_ids') else ('caption','japanese','second_hearing')
        grounded=any(normalized in same_words(turn.get(f,'')) for f in fields)
    else:return False
    if assigned.get('caption_ids'):
        q,c=clean_text(quote),clean_text(assigned.get('content',''))
        grounded=grounded and bool(q and c and c in q)
        if ident in local:grounded=grounded and ident in assigned['caption_ids']
    return grounded
