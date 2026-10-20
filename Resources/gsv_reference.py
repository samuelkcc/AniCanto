"""Continuous same-role originals for V4; never changes an approved role card.

Only automatic, genuinely concatenated recordings are eligible. Transcribe the
actual extracted audio in a separate CPU process before conditioning V4. Source
and user-selected engine recordings remain immutable.
"""
from whisper_audio import load as whisper_pcm
import hashlib,json,math,os,sys,wave,re,difflib
from pathlib import Path

REVISION='v4-continuous-original-2'

def transcript_check(expected,actual):
    clean=lambda text:re.sub(r'[^\wぁ-んァ-ヶ一-龥]','',text)
    a,b=clean(expected),clean(actual)
    if a and re.fullmatch(r'[あぁアァうぅウゥおぉオォえぇエェーっッ]+',a):return False,'nonlexical-source-reference'
    if a and b and difflib.SequenceMatcher(None,a,b).ratio()<.5:return False,'reference-transcript-disagreement'
    return bool(b),'' if b else 'empty-reference-transcript'


def candidate(profile,folder):
    if profile.get('transcriptSource')!='original-japanese-words' or profile.get('language','ja')!='ja' or profile.get('mixedReference'):return None
    ranges=profile.get('referenceRanges') or []
    if len(ranges)<2:return None
    source=Path(profile['reference'])
    try:
        spans=[float(b)-float(a) for a,b in ranges]
        if not all(math.isfinite(n) and n>0 for n in spans):return None
        with wave.open(str(source)) as f:
            rate=f.getframerate();channels=f.getnchannels();width=f.getsampwidth();frames=f.getnframes();raw=f.readframes(frames)
        if channels!=1 or width!=2 or abs(frames/rate-sum(spans))>.04:return None
        # A small tail of silence satisfies upstream's 3-second minimum. Never
        # repeat speech or borrow a different role to reach that minimum.
        choice=max(range(len(spans)),key=lambda i:spans[i])
        if not 2.5<=spans[choice]<=8:return None
        start=sum(round(n*rate) for n in spans[:choice]);count=round(spans[choice]*rate)
        clip=raw[start*2:(start+count)*2]
        from reference_quality import read,measure
        original_quality=measure(*read(source))
        key=hashlib.sha256(source.read_bytes()+json.dumps([ranges,choice,REVISION]).encode()).hexdigest()[:24]
        folder=Path(folder)/'continuous-references';folder.mkdir(parents=True,exist_ok=True);target=folder/(key+'.wav')
        if not target.exists():
            with wave.open(str(target),'wb') as f:
                f.setparams((1,2,rate,0,'NONE','not compressed'))
                f.writeframes(clip+bytes(max(0,round(3.1*rate)-len(clip)//2)*2))
        quality=measure(*read(target))
        if quality['warnings'] or quality['score']<original_quality['score']-12:return None
        return dict(key=key,id=profile['id'],reference=str(target),source=str(source),sourceSHA=hashlib.sha256(source.read_bytes()).hexdigest(),sourceRange=ranges[choice],quality=quality)
    except (OSError,wave.Error,ValueError,KeyError,TypeError):return None


def prepare(cfg,job,profiles,run,emit):
    if not cfg.get('storage') or not profiles or not cfg.get('ttsBackend','').startswith('gpt-sovits') or cfg.get('gsvReferenceMode','original')!='original':return {}
    from model_catalog import selected
    model=cfg.get('referenceSpeechModel') or selected(cfg['storage'],'referenceSpeech')
    folder=Path(job);cache=folder/'continuous-reference-transcripts.json'
    saved=json.loads(cache.read_text()) if cache.exists() else {};pending=[];choices=[]
    for profile in profiles:
        row=candidate(profile,folder)
        if not row:continue
        evidence=Path(cfg.get('_referenceAnalysisFile') or folder/'japanese-analysis.json')
        if evidence.exists():
            words=[w for segment in json.loads(evidence.read_text()).get('segments',[]) for w in segment.get('words',[])]
            a,b=row['sourceRange'];row['expectedText']=''.join(w['word'] for w in words if a<=(w['start']+w['end'])/2<b).strip()
        row['cacheKey']=hashlib.sha256(json.dumps([row['key'],model,REVISION,row.get('expectedText','')]).encode()).hexdigest()
        choices.append((profile,row))
        if row['cacheKey'] not in saved:pending.append(row)
    if pending:
        from runtime_paths import python_for
        request=folder/'continuous-reference-request.json'
        request.write_text(json.dumps(dict(storage=cfg['storage'],model=model,items=pending),ensure_ascii=False))
        emit('角色參考核對',f'{len(pending)} 個 V4 拼接參考改用同角色連續原聲，逐段核對實際日語原文；舊參考保留。')
        try:
            result=json.loads(run([python_for(Path(cfg['storage']),'runtime'),Path(__file__),request]))
            for row in result['rows']:
                valid,reason=transcript_check(row.get('expectedText',''),row.get('promptText',''))
                row['verified']=bool(row.get('verified') and valid)
                if reason:row['referenceIssue']=reason
                saved[row['cacheKey']]=row
            from worker import atomic_json
            atomic_json(cache,saved)
        except (RuntimeError,ValueError,OSError,KeyError,TypeError) as error:
            emit('角色參考待覆核','連續原聲核對未完成，沿用原參考：'+str(error)[:180])
            # Do not reload a failing ASR model on every generation sub-batch.
            for row in pending:saved[row['cacheKey']]=dict(row,verified=False,error=str(error)[:180])
            from worker import atomic_json
            atomic_json(cache,saved)
    result={}
    for profile,row in choices:
        checked=saved.get(row['cacheKey'],{})
        if checked.get('verified') and checked.get('sourceSHA')==row['sourceSHA'] and checked.get('promptText'):
            result[profile['id']]=dict(profile,reference=row['reference'],promptText=checked['promptText'],referenceRanges=[row['sourceRange']],shortReference=False,referenceCandidates=[],referenceQuality=row['quality'],transcriptSource='continuous-reference-local-ASR',referencePreparation=REVISION,originalReference=profile['reference'])
    return result


def transcribe(request):
    from faster_whisper import WhisperModel
    from model_catalog import resolve
    model=WhisperModel(str(resolve(Path(request['storage']),request['model'])),device='cpu',compute_type='int8',local_files_only=True,cpu_threads=6)
    rows=[]
    for item in request['items']:
        segments,_=model.transcribe(whisper_pcm(item['reference']),language='ja',beam_size=5,vad_filter=False,condition_on_previous_text=False)
        segments=list(segments);text=''.join(s.text for s in segments).strip()
        with wave.open(item['reference']) as f:duration=f.getnframes()/f.getframerate()
        usable=bool(text and len(text)<=duration*35 and segments and max(s.no_speech_prob for s in segments)<.8)
        rows.append(dict(item,promptText=text,verified=usable,method='actual continuous original, local Japanese ASR; transcript and native accent require audition'))
    print(json.dumps(dict(rows=rows),ensure_ascii=False))


if __name__=='__main__':
    os.environ.update(PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
    transcribe(json.loads(Path(sys.argv[1]).read_text()))
