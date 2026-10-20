"""Conservative ASR spelling evidence, not pronunciation certification.

The full syllable sequence must match. Never use a high average text similarity
to forgive an omitted second clause, inserted words, a changed verb or negation.
Tone differences remain explicit warnings: they may be ASR spelling choices or
real pronunciation differences and cannot be certified from a transcript alone.
"""
import json
import re
import sys
import subprocess

REVISION='full-phonemes-and-independent-romanized-gap-2'

def romanized_gap(expected,heard):
    from speechcheck import text_key,critical_omissions
    from difflib import SequenceMatcher
    a,b=text_key(expected),text_key(heard)
    if not re.fullmatch(r'[\u3400-\u9fff]+',a) or critical_omissions(expected,heard):return None
    changes=[(kind,i,j,k,l) for kind,i,j,k,l in SequenceMatcher(None,a,b,autojunk=False).get_opcodes() if kind!='equal']
    if len(changes)!=1:return None
    kind,i,j,k,l=changes[0]
    if kind!='replace' or not 2<=j-i<=6 or not re.fullmatch(r'[a-z]{2,20}',b[k:l]) or len(a)-(j-i)<6:return None
    if i<2 or j+2>len(a):return None
    return dict(expected=a[i:j],romanized=b[k:l],left=a[i-2:i],right=a[j:j+2])

def corroborate(expected,heard,secondary):
    gap=romanized_gap(expected,heard)
    if not gap:return dict(accepted=False)
    from speechcheck import text_key
    pattern=re.escape(gap['left'])+r'([\u3400-\u9fff]{'+str(len(gap['expected']))+r'})'+re.escape(gap['right'])
    matches=re.findall(pattern,text_key(secondary))
    if len(matches)!=1:return dict(accepted=False)
    term=matches[0]
    result=align(gap['expected'],term) if gap['expected']!=term else dict(accepted=True,syllables=len(term),toneDifferences=0)
    return dict(result,gap=gap,secondaryTerm=term,method='Primary full text except one Romanized span; independent Chinese ASR anchors and full Jyutping sequence for that span; not meaning certification')


def align(expected,heard):
    from speechcheck import text_key,critical_omissions
    a,b=text_key(expected),text_key(heard)
    if not a or a==b or len(a)!=len(b) or critical_omissions(expected,heard):return dict(accepted=False)
    if not re.fullmatch(r'[\u3400-\u9fff]+',a+b):return dict(accepted=False)
    from ToJyutping import get_jyutping_list
    first=[p for c,p in get_jyutping_list(a)];second=[p for c,p in get_jyutping_list(b)]
    if len(first)!=len(a) or len(second)!=len(b) or any(not p for p in first+second):return dict(accepted=False)
    base=lambda p:re.sub(r'[1-6]$','',p)
    accepted=all(base(p)==base(q) for p,q in zip(first,second))
    return dict(accepted=accepted,syllables=len(first),toneDifferences=sum(p!=q for p,q in zip(first,second)),
                changedCharacters=sum(c!=d for c,d in zip(a,b)),method='full-sequence Jyutping comparison; tone/ASR ambiguity retained; not word meaning certification')


def verify(w,cfg,folder,cue,check,audio=None):
    if (cfg.get('targetLanguage','yue')!='yue' or check.get('languageMismatch') or
            check.get('languageUnverified') or check.get('detectedLanguage','').lower() not in ('yue','cantonese') or
            check.get('criticalDifferences')):return dict(accepted=False)
    from pathlib import Path
    from runtime_paths import python_for
    request=Path(folder)/'cantonese-alignment-request.json'
    w.atomic_json(request,dict(expected=cue['cantonese'],heard=check.get('heard','')))
    try:
        result=json.loads(w.run([python_for(cfg['storage'],'gsv-runtime'),Path(__file__).resolve(),request]))
        if isinstance(result,dict) and not result.get('accepted') and audio and romanized_gap(cue['cantonese'],check.get('heard','')):
            from secondary_speech import transcribe
            second=transcribe(w,cfg,folder,audio)
            if second:
                w.atomic_json(request,dict(expected=cue['cantonese'],heard=check.get('heard',''),secondary=second['heard']))
                result=json.loads(w.run([python_for(cfg['storage'],'gsv-runtime'),Path(__file__).resolve(),request]))
        w.atomic_json(Path(folder)/'cantonese-alignment.json',result)
        return result if isinstance(result,dict) else dict(accepted=False)
    except (OSError,RuntimeError,ValueError,TypeError,KeyError,subprocess.SubprocessError):return dict(accepted=False)


if __name__=='__main__':
    from pathlib import Path
    request=json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(corroborate(request['expected'],request['heard'],request['secondary']) if 'secondary' in request else align(request['expected'],request['heard']),ensure_ascii=False))
