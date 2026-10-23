"""Cantonese ASR advises delivery; a single transcript cannot replace a voice.

Physical audio/timing failures remain mandatory repairs elsewhere. Full spoken
syllable matches apply equally to clones and fallback voices. Major transcript
failures require independent, unprompted corroboration before automatic retakes.
"""
import hashlib,json,subprocess
from pathlib import Path
from types import SimpleNamespace

REVISION='yue-advisory-two-witnesses-5-mandarin-confirmation'
ACCEPTANCES=('cantonese-phonetic-variant','cantonese-independent-transcript')


def verified(check):
    return bool((check.get('deliveryAccepted') and check.get('deliveryAcceptance') in ACCEPTANCES) or
                (check.get('textMatches') and not any(check.get(k) for k in ('requiresReview','languageMismatch','languageUnverified'))))


def retain_original(check):
    return check.get('cantoneseReviewPolicy')==REVISION and check.get('contentDecision') in ('accept','retain-with-note')


def needs_repair(cue,check,language='yue'):
    if language=='yue' and check.get('cantoneseReviewPolicy')!=REVISION:return False
    from repair_budget import clear_content_problem
    return clear_content_problem(cue,check)


def annotate(check,decision,reason,**extra):
    return dict(check,cantoneseReviewPolicy=REVISION,contentDecision=decision,
                confirmedContentFailure=decision=='repair',reviewReason=reason,**extra)


def corroborated(expected,first,second):
    """Two disagreeing spellings or one foreign label do not establish failure."""
    from speechcheck import critical_omissions,text_key,similarity
    n=len(text_key(expected));a=text_key(first.get('heard',''));b=text_key(second.get('heard',''))
    neg_a=set(critical_omissions(expected,first.get('heard','')))
    neg_b=set(critical_omissions(expected,second.get('heard','')))
    # Foreign transliterations omit every Chinese negative by construction.
    # They cannot independently establish a specific missing Cantonese word.
    if n>=3 and neg_a & neg_b and min(similarity(expected,first.get('heard','')),similarity(expected,second.get('heard','')))>=.5:return 'independently-confirmed-negation-difference'
    if n>=3 and not a and not b:return 'independently-unrecognized-lexical-audio'
    aliases={'en':'english','ja':'japanese','ko':'korean','th':'thai','zh':'chinese','yue':'cantonese'}
    lang=lambda row:aliases.get(str(row.get('detectedLanguage','')).lower(),str(row.get('detectedLanguage','')).lower())
    la,lb=lang(first),lang(second)
    # The same Chinese characters can be pronounced in Cantonese or Mandarin.
    # Two independent explicit Mandarin labels are acoustic evidence even when
    # both transcripts match the approved Chinese text exactly.
    if n>=6 and la in ('mandarin','cmn') and lb in ('mandarin','cmn') and a and b:
        return 'independently-confirmed-mandarin'
    foreign=lambda language:language not in ('','none','unknown','chinese','cantonese')
    if n>=6 and foreign(la) and la==lb and similarity(expected,first.get('heard',''))<.45 and similarity(expected,second.get('heard',''))<.45:
        return 'independently-confirmed-wrong-language'
    # Whole missing clauses need evidence in BOTH transcripts; mere paraphrase,
    # names, particles and equal-length homophones cannot trigger this branch.
    if n>=8 and len(a)<n*.6 and len(b)<n*.6 and similarity(expected,first.get('heard',''))<.45 and similarity(expected,second.get('heard',''))<.45:
        return 'independently-confirmed-major-omission'
    return None


def review(cfg,job,cues,paths,checks,emit):
    if cfg.get('targetLanguage','yue')!='yue':return checks
    if not len(cues)==len(paths)==len(checks):raise ValueError('廣東話核對數量不完整；原錄音保留，未假報通過。')
    from repair_budget import clear_content_problem
    from cantonese_alignment import verify as phonetic
    from secondary_speech import transcribe
    from speechcheck import evidence
    from worker import atomic_json
    def run(args):return subprocess.check_output([str(a) for a in args],stderr=subprocess.PIPE,timeout=1200)
    w=SimpleNamespace(run=run,atomic_json=atomic_json,emit=emit)
    prepared=[];pending=[]
    for cue,path,raw in zip(cues,paths,checks):
        if verified(raw):
            prepared.append(dict(row=annotate(raw,'accept','primary-transcript-matches'),raw=raw));continue
        expected=raw.get('expected',cue['cantonese'])
        identity=[REVISION,hashlib.sha256(Path(path).read_bytes()).hexdigest(),expected,raw,cfg.get('asrModel'),cfg.get('referenceSpeechModel','whisper-large-v3')]
        key=hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
        folder=Path(job)/'cantonese-review'/key;folder.mkdir(parents=True,exist_ok=True);cache=folder/'decision.json'
        try:saved=json.loads(cache.read_text())
        except (OSError,ValueError):saved=None
        if saved is not None:
            prepared.append(dict(row=saved,raw=raw));continue
        row=annotate(raw,'retain-with-note','single-ASR-difference-is-advisory')
        alignment=phonetic(w,cfg,folder,dict(cue,cantonese=expected),raw,audio=path)
        entry=dict(row=row,raw=raw,expected=expected,folder=folder,audio=path,cache=cache)
        if alignment.get('accepted'):
            entry['row']=annotate(raw,'accept','full-cantonese-syllable-sequence-matches',deliveryAccepted=True,
                         deliveryAcceptance='cantonese-phonetic-variant',phoneticAlignment=alignment,
                         warning='完整粵語音節相符；保留字形／聲調提示，未認證表演或原角色身分。')
        elif clear_content_problem(dict(cantonese=expected),raw) or (
            len(expected)>=6 and str(raw.get('detectedLanguage','')).lower() in ('mandarin','cmn','普通話','普通话')
            and bool(raw.get('heard'))):pending.append(entry)
        prepared.append(entry)
    if pending:
        emit('廣東話核對',f'{len(pending)} 段較大差異合併獨立核對；只載入一次模型，原角色錄音保留。',None)
        try:
            if len(pending)==1:
                e=pending[0];seconds=[transcribe(w,cfg,e['folder'],e['audio'],auto_language=True)]
            else:
                from secondary_speech import transcribe_batch
                seconds=transcribe_batch(w,cfg,[(e['folder'],e['audio']) for e in pending],auto_language=True)
            if len(seconds)!=len(pending):raise ValueError('Independent speech result count mismatch')
        except (OSError,RuntimeError,ValueError,KeyError,subprocess.SubprocessError) as error:
            seconds=[None]*len(pending)
            for e in pending:e['row']['secondaryError']=str(error)[:500]
        for entry,second in zip(pending,seconds):
            row,raw,expected=entry['row'],entry['raw'],entry['expected']
            if second:
                witness=evidence(expected,second.get('heard',''),second.get('language',''),'yue')
                row['independentCheck']=witness
                target_label=second.get('language','').lower() in ('yue','cantonese')
                supported_text=(raw.get('detectedLanguage','').lower() in ('yue','cantonese') and second.get('language','').lower() in ('zh','chinese'))
                if witness.get('textMatches') and (target_label or supported_text):
                    row=annotate(row,'accept','independent-full-transcript-matches',deliveryAccepted=True,deliveryAcceptance='cantonese-independent-transcript')
                else:
                    reason=corroborated(expected,raw,witness)
                    if reason:row=annotate(row,'repair',reason)
            else:row['reviewReason']='independent-ASR-unavailable-retain-original'
            entry['row']=row
    result=[]
    for entry in prepared:
        row,raw=entry['row'],entry['raw']
        if raw.get('detectedLanguage','').lower() in ('zh','chinese','mandarin') and row.get('contentDecision')!='repair':
            row.update(languageStatus='unconfirmed-cantonese',languageUnverified=True,requiresReview=True,
                       warning='辨識結果未能確認廣東話；文字吻合亦不能證明口音正確。原錄音保留供試聽，未認證語言。')
        if entry.get('cache'):atomic_json(entry['cache'],row)
        result.append(row)
    return result
