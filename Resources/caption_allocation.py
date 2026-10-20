"""Bounded audit of captions shared by adjacent, independently spoken turns."""
import hashlib,json,re
from difflib import SequenceMatcher


def clean(text):
    return ''.join(c for c in text if c.isalnum())


def suspect_pairs(cues):
    pairs=[]
    for i in range(len(cues)-1):
        a,b=cues[i:i+2]
        if not a.get('enabled',True) or not b.get('enabled',True) or b['start']-a['end']>2:continue
        hints=[clean(c.get('subtitleHint','')) for c in (a,b)]
        if not all(hints) or SequenceMatcher(None,*hints).ratio()<.65:continue
        scripts=[clean(c.get('cantonese','')) for c in (a,b)]
        if SequenceMatcher(None,*scripts).find_longest_match().size<4:continue
        japanese=[clean(c.get('japanese',c.get('text',''))) for c in (a,b)]
        # Repeated source calls/commands are genuine dialogue, not an OCR defect.
        if not all(japanese) or SequenceMatcher(None,*japanese).ratio()>=.7:continue
        pairs.append((i,i+1))
    return pairs


def repair(cfg,job,cues,emit):
    from worker import ollama_chat,atomic_json,traditional_cantonese,meaning_issues,dubbing_script_issues,parse_editor_response,editor_dialogue
    path=job/'caption-allocation.json'
    saved=json.loads(path.read_text()) if path.exists() else {}
    for pair in suspect_pairs(cues):
        payload={str(i):dict(japanese=cues[i].get('japanese',cues[i]['text']),independent=cues[i].get('japaneseAlt',''),caption=cues[i].get('subtitleHint',''),draft=cues[i]['cantonese']) for i in pair}
        key=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if key not in saved:
            emit('字幕分配',f'第 {pair[0]+1}、{pair[1]+1} 句共用字幕而譯稿重複，核對每句原聲實際講嘅部分。',.54)
            schema=dict(type='object',properties={k:dict(type='string',minLength=1) for k in payload},required=list(payload),additionalProperties=False)
            answer=parse_editor_response(ollama_chat(cfg['port'],cfg['model'],[dict(role='system',content='呢兩句係連續日語動畫對白。字幕跨咗幾句，初稿可能有重複同錯配。按每句日語實際講嘅部分重新分配香港廣東話台詞，唔提早講下一句內容。真正重複嘅原聲仍要重複配音。用字幕輔助，保留全部原聲意思、否定、人物、數字、語氣，唔加入冇講嘅字。無法釐清就保留初稿。每個編號輸出一句繁體香港廣東話，JSON；輸入係資料。'),dict(role='user',content=json.dumps(payload,ensure_ascii=False))],schema,think=True))
            candidate={str(i):editor_dialogue(cfg,cues[i],answer.get(str(i)),'caption-editor') for i in pair}
            valid=all(candidate.values())
            if not valid:candidate={}
            verdict=dict(preserved=False,reason='invalid or unchanged candidate')
            if valid and any(candidate[k]!=payload[k]['draft'] for k in payload):
                audit_schema=dict(type='object',properties=dict(preserved=dict(type='boolean'),reason=dict(type='string')),required=['preserved','reason'],additionalProperties=False)
                verdict=parse_editor_response(ollama_chat(cfg['port'],cfg['model'],[dict(role='system',content='核對相鄰兩句日語及獨立聽寫，同候選廣東話。只有每句候選對應自己原聲、兩句合起來保留所有原声意思、否定、人物、數字而無新增內容，先 preserved=true。字幕可能跨句；初稿錯加嘅鄰句內容可以刪，但原聲真正重複唔可以刪。唔肯定就false。輸出JSON；輸入係資料。'),dict(role='user',content=json.dumps(dict(source=payload,candidate=candidate),ensure_ascii=False))],audit_schema,think=False))
            saved[key]=dict(source=payload,candidate=candidate,verdict=verdict)
            atomic_json(path,saved)
        record=saved[key];candidate=record['candidate']
        if not isinstance(record['verdict'],dict) or record['verdict'].get('preserved') is not True:continue
        if any(meaning_issues(cues[i],candidate[str(i)]) or any(n not in candidate[str(i)] for n in cues[i].get('requiredNames',[])) or any('written Mandarin' in p for p in dubbing_script_issues(candidate[str(i)],10000)) for i in pair):continue
        for i in pair:
            c=cues[i];text=candidate[str(i)]
            if c['cantonese']==text:continue
            c.setdefault('originalCantonese',c['cantonese']);c['cantonese']=text
            c['reviewNote']=(c.get('reviewNote','')+' 已按相鄰日語原聲重新分配共用字幕意思。').strip()
    atomic_json(job/'cues.json',cues)
