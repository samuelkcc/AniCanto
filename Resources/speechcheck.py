"""Offline, cached ASR evidence for delivered Cantonese; not a semantic oracle."""
import hashlib,json,os,re,subprocess,sys,unicodedata
from difflib import SequenceMatcher
from pathlib import Path


def text_key(text):
    # ASR often writes the copula as 系. This spelling normalization is only
    # for text comparison; it neither changes audio nor certifies its tone.
    return ''.join(c for c in unicodedata.normalize('NFKC',text).lower().replace('系','係') if c.isalnum())


def similarity(expected,heard):
    a,b=text_key(expected),text_key(heard)
    return SequenceMatcher(None,a,b).ratio() if a and b else 0.0


def critical_omissions(expected,heard):
    if re.search(r"[A-Za-z]",expected) and not re.search(r"[\u3400-\u9fff]",expected):
        def negatives(text):
            text=text.lower().replace("’", "\'")
            return len(re.findall(r"\b(?:no|not|never|neither|nor|without)\b|n\'t\b",text))
        return ["negation:english"] if negatives(expected)!=negatives(heard) else []
    # A long line can score > .95 even after losing its only negation.
    # 唔該 is a courtesy expression, not a negation. Its stammered EP07 form
    # was being treated as two missing negatives when ASR transliterated it.
    courtesy=lambda text:re.sub(r'唔(?:[…\.，,\s]+唔)?該(?:晒)?','',text)
    expected,heard=courtesy(expected),courtesy(heard)
    groups=[('唔','不'),('冇','無','没','沒'),('未',)]
    return ['negation:'+group[0] for group in groups if sum(expected.count(x) for x in group)!=sum(heard.count(x) for x in group)]


def evidence(expected,heard,detected,target='yue'):
    detected=str(detected or '').lower()
    accepted={'english','en','eng'} if target=='en' else {'zh','zho','cmn','chinese','mandarin','普通话','普通話'} if target=='zh' else {'cantonese','yue'}
    mismatch=bool(detected and detected not in accepted)
    unverified=detected in ('','none','unknown')
    matches=bool(text_key(expected)) and text_key(expected)==text_key(heard)
    critical=critical_omissions(expected,heard)
    # A high character score can hide a wrong word or name in a long sentence.
    # Uncertain differences remain visible; only substantial failures trigger
    # bounded retakes, so strict review does not regenerate every short name.
    return dict(expected=expected,heard=heard,similarity=round(similarity(expected,heard),4),textMatches=matches,criticalDifferences=critical,detectedLanguage=detected,languageMismatch=mismatch,languageUnverified=unverified,requiresReview=not matches or bool(critical) or mismatch or unverified,acceptancePolicy='same-normalized-text-and-target-language',method='independent-local-ASR; pronunciation/meaning not certified')


def inspect(cfg,job,cues,paths,emit):
    from runtime_paths import python_for
    from model_catalog import selected
    cfg=dict(cfg,asrModel=cfg.get('asrModel') or selected(cfg['storage'],'asr'))
    cachefile=Path(job)/'speech-check-cache.json'
    cache=json.loads(cachefile.read_text()) if cachefile.exists() else {}
    keys=[];pending=[];queued=set()
    from pronunciation import spoken
    for cue,path in zip(cues,paths):
        expected=cue['cantonese'] if cfg.get('targetLanguage')=='en' else spoken(cfg,cue['cantonese'])
        key=hashlib.sha256(Path(path).read_bytes()+expected.encode()+cfg.get('targetLanguage','yue').encode()+str(cfg.get('asrModel','asr-1.7b-bf16')).encode()+b'qwen-speech-check-auto-language-7-full-text').hexdigest()
        keys.append(key)
        if key not in cache and key not in queued:
            pending.append(dict(key=key,path=str(path),expected=expected));queued.add(key)
    if pending:
        emit('配音核對',f'本機重新聽 {len(pending)} 段配音，檢查漏字／重複；聽寫差異會保留供覆核。',.87)
        request=Path(job)/'speech-check-request.json'
        request.write_text(json.dumps(dict(storage=cfg['storage'],ffmpeg=cfg['ffmpeg'],executable=cfg.get('executable'),items=pending,cache=str(cachefile),targetLanguage=cfg.get('targetLanguage','yue'),asrModel=cfg.get('asrModel')),ensure_ascii=False))
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
        with (Path(job)/'speech-check.log').open('a') as log:
            p=subprocess.Popen([str(python_for(Path(cfg['storage']),'asr-runtime')),str(Path(__file__).resolve()),str(request)],env=env,stdout=subprocess.PIPE,stderr=log,text=True)
            for line in p.stdout:
                log.write(line);log.flush()
                try:
                    event=json.loads(line)
                    if event.get('stage'):emit(event['stage'],event['message'],event.get('progress'))
                except (ValueError,KeyError):pass
            code=p.wait()
        if code:raise RuntimeError('本機配音覆聽程序失敗，音檔已保存；詳見 speech-check.log。')
        cache=json.loads(cachefile.read_text())
    # Re-evaluate cheap textual policy from cached raw ASR; a policy update
    # must not require loading the acoustic model again for unchanged audio.
    checks=[dict(cache[k],**evidence(cache[k]['expected'],cache[k].get('heard',''),cache[k].get('detectedLanguage',''),cfg.get('targetLanguage','yue'))) for k in keys]
    from cantonese_review import review
    return review(cfg,job,cues,paths,checks,emit)


def verify(request):
    import contextlib
    from asr_verify import load_model,audio_array
    import numpy as np
    with contextlib.redirect_stdout(sys.stderr):model=load_model(request['storage'],request.get('asrModel'))
    file=Path(request['cache']);cache=json.loads(file.read_text()) if file.exists() else {}
    for index,item in enumerate(request['items']):
        raw=subprocess.check_output([request['ffmpeg'],'-v','error','-i',item['path'],'-ar','16000','-ac','1','-f','f32le','pipe:1'])
        audio=np.frombuffer(raw,dtype=np.float32).copy()
        with contextlib.redirect_stdout(sys.stderr):
            result=model.generate(audio_array(audio),max_tokens=min(384,max(48,round(len(audio)/16000*20))),verbose=False)
        heard=result.text.strip()
        if request.get('executable') and request.get('targetLanguage')!='en':
            heard=subprocess.check_output([request['executable'],'--simplified-text' if request.get('targetLanguage')=='zh' else '--traditional-text'],input=heard.encode()).decode().strip()
        detected=getattr(result,'language','') or ''
        if isinstance(detected,(list,tuple)):detected=detected[0] if detected else ''
        cache[item['key']]=evidence(item['expected'],heard,detected,request.get('targetLanguage','yue'))
        temp=file.with_suffix('.tmp');temp.write_text(json.dumps(cache,ensure_ascii=False,indent=2));temp.replace(file)
        print(json.dumps(dict(stage='配音核對',message=f'已覆聽第 {index+1}/{len(request["items"])} 段配音。',progress=.87+.01*(index+1)/len(request['items']),result=cache[item['key']]),ensure_ascii=False),flush=True)


if __name__=='__main__':verify(json.loads(Path(sys.argv[1]).read_text()))
