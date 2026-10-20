"""Deterministic presentation of newly received workflow events; raw evidence is kept.

No model or network call. Unknown diagnostics are explicitly labelled, with the
original retained in the journal and raw process stream instead of guessed text.
"""
import json,re
from functools import lru_cache
from pathlib import Path

CJK=re.compile(r'[\u3400-\u9fff]')
@lru_cache(maxsize=1)
def catalog():
    base=Path(__file__).resolve().parent
    data=json.loads((base/'workflow-localization.json').read_text(encoding='utf-8'))
    exact={}
    source=(base/'en.lproj/Localizable.strings').read_text(encoding='utf-8')
    for a,b in re.findall(r'("(?:[^"\\]|\\.)*")\s*=\s*("(?:[^"\\]|\\.)*")\s*;',source):
        try:exact[json.loads(a)]=json.loads(b)
        except ValueError:continue
    exact.update(data['exact'])
    return exact,data['patterns']

def english(text,stage=False):
    exact,patterns=catalog()
    if text in exact:return exact[text],True
    if not CJK.search(text):return text,True
    track=re.match(r'^音軌 (\d+)/(\d+) · ([^·]+) · ([^·]+) · (.*)$',text)
    if track:
        tail,known=english(track[5]);label,_=english(track[3].strip())
        return f'Audio track {track[1]}/{track[2]} · {label} · {track[4].strip()} · {tail}',known
    for pattern,replacement in patterns:
        if re.search(pattern,text):
            template=re.sub(r'\$(\d+)',lambda m:r'\g<'+m[1]+'>',replacement)
            value=re.sub(pattern,template,text)
            value=value.replace('未標示語言','language not tagged')
            if CJK.search(value):
                parts=[english(p) for p in value.split(' · ')] if ' · ' in value else []
                if parts and all(known for _,known in parts):return ' · '.join(p for p,_ in parts),True
                return ('Processing' if stage else 'Worker diagnostic received; see Detailed process log for the original text.'),False
            return value,True
    if ' · ' in text:
        parts=[english(p) for p in text.split(' · ')]
        if all(known for _,known in parts):return ' · '.join(p for p,_ in parts),True
    return ('Processing' if stage else 'Worker diagnostic received; see Detailed process log for the original text.'),False

def present(stage,message,language):
    if language=='en':
        a,known_a=english(stage,True);b,known_b=english(message)
        return dict(stage=a,message=b,localized=known_a and known_b)
    # Most workers already emit Chinese. Exact known English interface messages
    # can also be presented in Chinese without touching technical output.
    exact,_=catalog();reverse={v:k for k,v in exact.items()}
    return dict(stage=reverse.get(stage,stage),message=reverse.get(message,message),localized=True)
