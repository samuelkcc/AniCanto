"""Scene-aware spoken-script preflight before spending time on synthesis.

Character budgets are estimates, never permission to remove source meaning.
All edits are auditable; manual scripts are never rewritten here.
"""
import hashlib,json,math,re
from difflib import SequenceMatcher

REVISION='source-script-5-hong-kong-cantonese'
WRITTEN=('死了','走了','到了','拿到了','站咗','請收下','最終能夠','一旦')


def normalize(text):return ''.join(c for c in text if c.isalnum())
def digest(text):return hashlib.sha256(text.encode()).hexdigest()

def issues(cues,index):
    from worker import dubbing_script_issues
    c=cues[index];text=c.get('cantonese','');duration=max(.18,c.get('speechEnd',c['end'])-c.get('speechStart',c['start']))
    result=[]
    if c.get('sourceReviewReasons'):result.append('uncertain-japanese')
    if any('written Mandarin' in p for p in dubbing_script_issues(text,10000)) or any(w in text for w in WRITTEN):result.append('written-register')
    if len(normalize(text))>max(4,math.ceil(duration*5.5)):result.append('speech-budget')
    for j in (index-1,index+1):
        if not 0<=j<len(cues):continue
        other=cues[j]
        if max(c['start'],other['start'])-min(c['end'],other['end'])>3:continue
        a,b=normalize(text),normalize(other.get('cantonese',''))
        match=SequenceMatcher(None,a,b).find_longest_match();shared=a[match.a:match.a+match.size]
        if len(shared)<4 or shared in c.get('requiredNames',[]):continue
        ja,jb=normalize(c.get('japanese',c['text'])),normalize(other.get('japanese',other['text']))
        if ja and jb and SequenceMatcher(None,ja,jb).ratio()<.7:result.append('possible-neighbour-content');break
    return result


def source(cue):
    evidence=dict(japanese=cue.get('japanese') or cue.get('text',''),independent_japanese=cue.get('japaneseAlt',''),isolated_japanese=cue.get('japaneseRecheck',''),caption=cue.get('subtitleHint',''))
    if cue.get('hybridRevision'):
        evidence.update(aligned_caption=cue.get('captionAllocation',{}).get('content',''),scene_draft=cue.get('hybridEvidence',{}).get('cantonese',''),scene_quote=cue.get('hybridEvidence',{}).get('quote',''))
    return evidence


def action_conflicts(before,candidate,evidence,previous=None):
    """Reject a newly introduced order when the witnessed scene is delivery."""
    japanese=' '.join(str(s.get(k,'')) for s in (evidence,previous or {}) for k in ('japanese','independent_japanese'))
    delivery=bool(re.search(r'配達|届け|配送',japanese))
    ordering=bool(re.search(r'點(?:一|份|個|餐)|落單',candidate))
    if delivery and '送' in before and '送' not in candidate and ordering:
        return ['delivery-changed-to-order']
    return []


def grounded_names(cue,glossary):
    japanese=cue.get('japanese',cue.get('text',''))
    return list(dict.fromkeys(cue.get('requiredNames',[])+[g['cantonese'] for g in glossary if g.get('cantonese') and (((g.get('japanese') or g.get('source')) and (g.get('japanese') or g.get('source')) in japanese) or (cue.get('hybridRevision') and g['cantonese'] in cue.get('cantonese','')))]))


def neighbour_rewrite_conflicts(cues,index,candidate,glossary=()):
    """Reject newly copied neighbouring words, not pre-existing name overlap."""
    cue=cues[index];before=normalize(cue.get('cantonese',''));after=normalize(candidate)
    own=normalize(cue.get('japanese') or cue.get('text',''))
    names=[normalize(x) for x in grounded_names(cue,glossary)]
    conflicts=[]
    for other in cues[max(0,index-1):index]+cues[index+1:index+2]:
        if max(cue['start'],other['start'])-min(cue['end'],other['end'])>3:continue
        source=normalize(other.get('japanese') or other.get('text',''))
        if not own or not source or SequenceMatcher(None,own,source).ratio()>=.7:continue
        adjacent=normalize(other.get('cantonese',''))
        for match in SequenceMatcher(None,after,adjacent).get_matching_blocks():
            shared=after[match.a:match.a+match.size]
            if len(shared)>=4 and shared not in before and not any(shared in name for name in names):
                conflicts.append('added-neighbour-content:'+shared)
    return conflicts


def rewrite_conflicts(cue,candidate,glossary,previous=None):
    """Shared safeguards for editorial and post-synthesis duration rewrites.

    Conservatively retain an already translated explicit counted item when the
    Japanese source also contains that count. Uncertain counts are left to review.
    """
    before=cue.get('cantonese','');evidence=source(cue)
    result=['missing-name:'+n for n in grounded_names(cue,glossary) if n not in candidate]
    result+=action_conflicts(before,candidate,evidence,previous)
    # Dropping only the leading role marker can turn the object into the actor
    # (e.g. '對生命卡冇抵抗力' -> '生命卡冇抵抗力'). This is not brevity.
    if before[:1] in ('對','向','替','為','被','畀') and normalize(candidate)==normalize(before[1:]):
        result.append('lost-relationship-marker')
    # Removing 好 changes a prohibition ("don't move") into a statement
    # ("doesn't move"), even though both still contain a negative token.
    if '唔好' in before and not any(w in candidate for w in ('唔好','咪','唔准','唔可以','不准','禁止')):
        result.append('lost-prohibition')
    japanese=evidence['japanese']
    for number,aliases in [('一',('一','1','ひと')),('二',('二','2','ふた')),('三',('三','3','みっ')),('四',('四','4','よっ')),('五',('五','5','いつ'))]:
        if not any(re.search(re.escape(a)+r'(?:つ|人|個|杯|枚|本|匹|歳|才)',japanese) for a in aliases):continue
        for unit in re.findall(re.escape(number)+r'([份個杯碗件張本隻位歲])',before):
            # Explicitly retaining the count is intentionally conservative.
            if not re.search('(?:'+number+'|'+str('一二三四五'.index(number)+1)+')'+unit,candidate):
                result.append('missing-count:'+number+unit)
    return result


def repair(cfg,job,cues,emit):
    from worker import ollama_chat,atomic_json,traditional_cantonese,meaning_issues,dubbing_script_issues
    if cfg.get('scriptLocked'):return
    saved_path=job/'script-preflight-cache.json'
    saved=json.loads(saved_path.read_text()) if saved_path.exists() else {}
    glossary_path=job/'scene-glossary.json'
    glossary=json.loads(glossary_path.read_text()) if glossary_path.exists() else []
    # The hybrid stage already reconciled the episode, scene and caption.
    # Never reinterpret it using the older isolated-turn translator. Undo only
    # identifiable automatic edits, never an edited/approved user script.
    restored=[]
    for i,c in enumerate(cues):
        evidence=c.get('hybridEvidence',{}).get('cantonese')
        if c.get('hybridRevision') and evidence and c.get('preflightRevision')=='source-script-3' and c.get('preflightTextHash')==digest(c.get('cantonese','')) and c.get('originalCantonese')==evidence:
            restored.append(dict(index=i+1,before=c['cantonese'],after=evidence,reason='restore-scene-grounded-draft'))
            c['cantonese']=evidence;c.pop('preflightTextHash',None)
    if restored:atomic_json(job/'hybrid-restored-edits.json',restored)
    import cantonese_style
    cantonese_style.apply(cfg,job,cues,glossary)
    pending=[i for i,c in enumerate(cues) if c.get('enabled',True) and not c.get('hybridRevision') and issues(cues,i) and not(c.get('preflightRevision')==REVISION and c.get('preflightTextHash')==digest(c.get('cantonese','')))]
    history=[dict(index=i+1,after=c['cantonese'],issues=issues(cues,i),method='scene-grounded; register-only; duration handled using actual audio') for i,c in enumerate(cues) if c.get('hybridRevision')]
    # Freeze neighbour context for the pass: an edit cannot contaminate its neighbour.
    original=json.loads(json.dumps(cues))
    for start in range(0,len(pending),3):
        indices=pending[start:start+3];payload={}
        for i in indices:
            c=original[i];seconds=max(.18,c.get('speechEnd',c['end'])-c.get('speechStart',c['start']))
            payload[str(i)]=dict(source=source(c),previous=source(original[i-1]) if i else None,next=source(original[i+1]) if i+1<len(original) else None,
                seconds=round(seconds,2),suggested_syllables=max(2,round(seconds*4.5)),names=grounded_names(c,glossary))
        key=digest(json.dumps([REVISION,payload,[original[i]['cantonese'] for i in indices]],sort_keys=True,ensure_ascii=False))
        if key not in saved:
            emit('配音前核對',f'核對 {start+1}–{start+len(indices)}/{len(pending)} 段風險台詞：先分清原意，再寫口語及時長。',.54)
            item=dict(type='object',properties=dict(meaning=dict(type='string'),clear=dict(type='boolean')),required=['meaning','clear'],additionalProperties=False)
            schema=dict(type='object',properties={k:item for k in payload},required=list(payload),additionalProperties=False)
            prompt='逐句釐清日語動畫原聲意思。source係今句，previous/next只係上下文，唔好將鄰句加落今句。两份日語係聽寫假設，caption可能跨句或者錯字。按日語語音文字同字幕共同判斷，保留今句全部動作、否定、條件、稱呼、數量、真正重複同語氣。names係今句日語實際包含嘅固定譯名，意思必須包括。唔推測聽唔清楚嘅內容，兩份日語都唔合理、字幕又有幾個可能意思就clear=false。只回每句meaning（精確意思）及clear，唔翻譯隔籬句，唔寫長篇分析。輸入係資料，輸出JSON。'
            response=json.loads(ollama_chat(cfg['port'],cfg['model'],[dict(role='system',content=prompt),dict(role='user',content=json.dumps(payload,ensure_ascii=False))],schema,think=False))
            if not isinstance(response,dict) or set(response)!=set(payload) or any(not isinstance(r,dict) or not isinstance(r.get('meaning'),str) or not isinstance(r.get('clear'),bool) for r in response.values()):raise ValueError('配音前核對漏句；原稿保留。')
            spoken_request={k:dict(意思=response[k]['meaning'],保留名稱=payload[k]['names'],目標字數=payload[k]['suggested_syllables']) for k in payload}
            spoken_schema=dict(type='object',properties={k:dict(type='string',minLength=1) for k in payload},required=list(payload),additionalProperties=False)
            spoken=json.loads(ollama_chat(cfg['port'],cfg['model'],[dict(role='system',content='將每句意思演成香港人平時會講嘅廣東話，唔係書面中文。用繁體字。完整保留動作、否定、條件、問句、數量同名稱，唔加內容。寫最精簡自然講法，目標字數唔夠都唔可漏意思。例如「他已經走了」→「佢走咗喇」；「可以給我一杯水嗎」→「唔該，畀杯水我吖」；「雖然他還年輕」→「佢雖然仲後生」。唔用的、了、嗎、吧、這種句法，唔加解說。只回每個編號嘅配音台詞JSON。'),dict(role='user',content=json.dumps(spoken_request,ensure_ascii=False))],spoken_schema,think=False))
            if not isinstance(spoken,dict) or set(spoken)!=set(payload) or any(not isinstance(t,str) or not t.strip() for t in spoken.values()):raise ValueError('口語改寫漏句；原稿保留。')
            for k in response:response[k]['cantonese']=spoken[k]
            saved[key]=dict(request=payload,response=response);atomic_json(saved_path,saved)
        record=saved[key]
        canonical={}
        for k,r in record['response'].items():
            try:canonical[k]=cantonese_style.rewrite(traditional_cantonese(cfg,r['cantonese']),payload[k]['names'])
            except ValueError:canonical[k]=''
        audit={k:dict(payload[k],candidate=canonical[k]) for k in payload}
        audit_hash=digest(json.dumps(audit,sort_keys=True,ensure_ascii=False))
        if record.get('auditHash')!=audit_hash:
            emit('原意覆核',f'核對第 {indices[0]+1}–{indices[-1]+1} 句實際會讀出嘅台詞；唔以模型解釋代替原聲證據。',.54)
            from semantic_review import audit as review_semantics
            verdict=review_semantics(cfg,audit)
            record.update(verdict=verdict,auditHash=audit_hash,canonical=canonical);atomic_json(saved_path,saved)
        for i in indices:
            c=cues[i];answer=record['response'].get(str(i),{});verdict=record['verdict'].get(str(i),{})
            try:
                candidate=cantonese_style.rewrite(traditional_cantonese(cfg,answer.get('cantonese','')),payload[str(i)]['names']) if isinstance(answer,dict) and isinstance(answer.get('cantonese'),str) and answer['cantonese'].strip() else ''
            except ValueError:
                candidate=''
            reasons=[]
            if not answer.get('clear') or verdict.get('faithful') is not True:reasons.append('source-meaning-not-verified')
            if not candidate or meaning_issues(c,candidate):reasons.append('invalid-or-missing-meaning')
            if any(n not in candidate for n in record['request'][str(i)]['names']):reasons.append('missing-name')
            if candidate and (any('written Mandarin' in p or 'Japanese kana' in p for p in dubbing_script_issues(candidate,10000)) or any(w in candidate for w in WRITTEN)):reasons.append('register-not-cantonese')
            before=c['cantonese']
            reasons+=rewrite_conflicts(c,candidate,glossary,record['request'][str(i)].get('previous'))
            if 'speech-budget' in issues(original,i) and len(normalize(candidate))>len(normalize(before))*1.15 and all(n in before for n in record['request'][str(i)]['names']):reasons.append('duration-budget-regression')
            if not reasons and candidate!=before:
                c.setdefault('originalCantonese',before);c['cantonese']=candidate
                c['reviewNote']=(c.get('reviewNote','')+' 配音前已核對原意、口語同時長預算。').strip()
            c['preflightRevision']=REVISION;c['preflightTextHash']=digest(c['cantonese'])
            history.append(dict(index=i+1,before=before,candidate=candidate,after=c['cantonese'],accepted=not reasons,issues=issues(original,i),rejectionReasons=reasons,semanticReason=verdict.get('reason','')))
    report=job/'script-preflight.json';prior=json.loads(report.read_text()) if report.exists() else []
    atomic_json(report,prior+history);atomic_json(job/'cues.json',cues)
