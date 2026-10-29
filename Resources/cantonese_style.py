"""Conservative register edits, separate from translation or source correction.

These substitutions preserve the existing draft's meaning; they do not certify
that the draft is a faithful translation. Quoted text and names are protected.
"""
import hashlib,json,re

REVISION='hk-register-3-spoken-particles'
RULES=(('請讓我幫您','等我幫你'),('讓我為您','等我幫你'),('讓我為你','等我幫你'),
       ('讓我幫您','等我幫你'),('讓我幫你','等我幫你'),('讓我來','等我嚟'),
       ('死了','死咗'),('拿到了','攞到咗'),('拿到','攞到'),('拿走','攞走'),
       ('唔好動','唔好郁'),('歡迎來到','歡迎嚟到'),('請收下','唔該收低'),
       ('這個','呢個'),('這裡','呢度'),('你們','你哋'),('我們','我哋'),('他們','佢哋'),
       ('來得','嚟得'),('站喺','企喺'),('站在','企喺'),('站咗','企咗'),
       ('那個','嗰個'),('那裏','嗰度'),('這裡','呢度'),('為什麼','點解'),('現在','而家'),
       ('剛剛','啱啱'),('不知道','唔知'),('不記得','唔記得'),('不會','唔會'),('不要','唔好'),
       ('不能','唔可以'),('沒有','冇'),('沒有了','冇咗'),('什麼','乜嘢'),('非常謝','好謝'),
       ('讓我們','我哋'),('想要','想'),('感覺','覺得'))


def rewrite(text,names=()):
    protected=list(re.finditer(r'「[^」]*」|『[^』]*』|“[^”]*”|"[^"]*"',text))
    spans=[m.span() for m in protected]
    for name in names:
        if name:spans += [m.span() for m in re.finditer(re.escape(name),text)]
    matches=[]
    pattern='|'.join(re.escape(a) for a,b in RULES)
    lookup=dict(RULES)
    for m in re.finditer(pattern,text):
        if any(m.start()<b and m.end()>a for a,b in spans):continue
        matches.append((m.start(),m.end(),lookup[m.group()]))
    for a,b,replacement in reversed(matches):text=text[:a]+replacement+text[b:]
    return text


def apply(cfg,job,cues,glossary):
    if cfg.get('scriptLocked'):return
    from worker import atomic_json
    names=[g.get('cantonese','') for g in glossary]
    changes=[]
    for i,c in enumerate(cues):
        if not c.get('enabled',True):continue
        before=c.get('cantonese','');after=rewrite(before,names+c.get('requiredNames',[]))
        if before!=after:
            if c.get('preflightTextHash')==hashlib.sha256(before.encode()).hexdigest():
                c['preflightTextHash']=hashlib.sha256(after.encode()).hexdigest()
            c.setdefault('originalCantonese',before);c['cantonese']=after
            changes.append(dict(index=i+1,before=before,after=after,method=REVISION,scope='register-only; source meaning not certified'))
    path=job/'register-edits.json'
    previous=json.loads(path.read_text()) if path.exists() else []
    atomic_json(path,previous+changes)
