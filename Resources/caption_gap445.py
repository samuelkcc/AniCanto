"""Reuse existing source recognition and sound evidence for automatic caption gaps."""
import hashlib, json, math, re, time, unicodedata, wave
from pathlib import Path

REVISION = 'automatic-gap-filler-agreement-445'
LABELS = ('silence','music','breathing','sigh','gasp','artillery_fire','fire','fire_crackle','firecracker','fireworks','glass_breaking','glass_clink','gunshot_gunfire','slap_smack','thump_thud','thunder','thunderstorm','whoosh_swoosh_swish','wind_rustling_leaves')
UNKNOWN = 'caption-gap-unconfirmed-445'
CONFIRMED = 'confirmed-nondialogue-original-444'
MESSAGE = 'Dialogue could not be confirmed between the two source recognitions. Original audio is retained.'

def enabled(cfg):
    return (cfg.get('captionGapPolicyRevision') == REVISION and cfg.get('sourceWorkflow','auto') == 'auto'
            and cfg.get('sourceWorkflowEffective') == 'subtitles-speech')

def lexical(text):
    return ''.join(c for c in unicodedata.normalize('NFKC',str(text)).casefold() if c.isalnum())

def nonverbal(text):
    return lexical(text) in ('','nospeech','音楽','音樂','音乐','music','silence')

def agrees(first, second, language):
    a,b = lexical(first),lexical(second)
    if a and a == b:return True
    pattern = (r'^(?:(?:ああ|あー|あっ|ええ|えー|えっ|えっと|えーと|うーん)[、，,\s]+){1,2}' if language == 'ja'
               else r'^(?:(?:uh|um|ah|erm|er)[,\s]+){1,2}' if language == 'en' else None)
    if pattern is None:return False
    left,right = (re.sub(pattern,'',x.strip(),flags=re.I) for x in (first,second))
    a,b = lexical(left),lexical(right)
    return a == b and (len(a)>=8 if language=='ja' else len(a)>=12 and len(left.split())>=3 and len(right.split())>=3)

def bounds(cue, captions, duration):
    a,b = cue['start'],cue['end']
    if not all(type(v) in (int,float) and math.isfinite(v) for v in (a,b,duration)):return False
    return 0<=a<b<=duration+.001 and b-a<=28.001 and not any(min(b,r['end'])>max(a,r['start'])+.001 for r in captions)

def audio_digest(path, start, end):
    """Hash exactly the mono PCM samples supplied to the existing independent ASR."""
    with wave.open(str(path)) as f:
        if f.getnchannels()!=1 or f.getframerate()!=16000 or f.getsampwidth()!=2:raise ValueError('Invalid owned source PCM')
        a,b=round(start*16000),round(end*16000)
        if not 0<=a<b<=f.getnframes():raise ValueError('Source window exceeds owned PCM')
        f.setpos(a);data=f.readframes(b-a)
        if len(data)!=(b-a)*2:raise ValueError('Incomplete source window')
    return hashlib.sha256(data).hexdigest()

def independent(cfg, job, cue, row, model):
    if not enabled(cfg) or cue.get('captionRecords'):return
    if not bounds(cue,[],float(cfg['duration'])):return
    try:digest=audio_digest(Path(job)/'japanese-original.wav',cue['start'],cue['end'])
    except (OSError,ValueError,wave.Error):return
    cue['captionGapIndependent445']=dict(start=cue['start'],end=cue['end'],text=row['text'],model=model,
        complete=True,audioSHA256=digest)

def sound_rows(rows, a, b):
    selected=[r for r in rows if r['start'] < b and r['start']+r['duration'] > a]
    return sorted(selected,key=lambda r:r['start'])

def evidence(rows, a, b, first, second):
    """Require positive, fully covered sound evidence. Empty ASR alone proves nothing."""
    if not nonverbal(first) or not nonverbal(second) or b-a<.45:return None
    covered=a;labels=[];confidence=1.;speech=0.;singing=0.
    for row in sound_rows(rows,a,b):
        if row.get('gapTaxonomyComplete445') != 1 or row['start']>covered+.021:return None
        if row['start']<a-.021 or row['start']+row['duration']>b+.021:return None
        numbers=[row.get(k) for k in ('speech','singing','music')]
        if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in numbers):return None
        if max(row['speech'],row['singing'],row.get('choir_singing',1),row.get('rapping',1))>.08:return None
        known=[(row[k],k) for k in LABELS if type(row.get(k)) in (int,float) and math.isfinite(row[k]) and 0<=row[k]<=1]
        score,label=max(known,default=(0.,''))
        if score<.90:return None
        covered=max(covered,min(b,row['start']+row['duration']));labels.append(label)
        confidence=min(confidence,score);speech=max(speech,row['speech']);singing=max(singing,row['singing'])
    if covered<b-.021 or not labels:return None
    return dict(labels=sorted(set(labels)),minimumConfidence=confidence,maximumSpeech=speech,maximumSinging=singing)

def speech_evidence(rows,a,b):
    selected=sound_rows(rows,a,b)
    if any(row.get('singing',1)>=.5 for row in selected):return False
    good=[row for row in selected if row.get('speech',0)>=.6 and row.get('singing',1)<.25 or
          row.get('speech',0)>=.3 and row.get('speech',0)>=row.get('music',1)+.05 and row.get('speech',0)>=row.get('singing',1)+.05]
    return any(x['start']<=a+.021 and x['start']+x['duration']>=b-.021 and b-a>=.45 for x in good) or any(x['start']<y['start'] and y['start']-x['start']<=2.5+.001 for x,y in zip(good,good[1:]))

def ledger_for(w,job):
    """An unreadable or interrupted ledger cannot create another allowance."""
    from source_clock_recovery import REVISION as clock_revision
    ledger_path=Path(job)/'source-clock-recovery.json'
    try:ledger=json.loads(ledger_path.read_text())
    except FileNotFoundError:ledger=dict(revision=clock_revision,attempts=0,spentSeconds=0,windows={})
    except (OSError,ValueError):return None
    if (not isinstance(ledger,dict) or ledger.get('revision')!=clock_revision or not isinstance(ledger.get('windows'),dict)
            or type(ledger.get('attempts')) is not int or ledger['attempts']<0
            or type(ledger.get('spentSeconds')) not in (int,float) or not math.isfinite(ledger['spentSeconds']) or ledger['spentSeconds']<0):return None
    if ledger.get('activeSince') is not None:
        active=ledger['activeSince']
        if type(active) not in (int,float) or not math.isfinite(active):return None
        ledger['spentSeconds']+=max(0,time.time()-active);ledger.pop('activeSince')
        w.atomic_json(ledger_path,ledger)
    return ledger

def corroborate(model,audio,cfg,job,cues,captions,variant,write,emit):
    """Fast production reuses its loaded Whisper for bounded local gap hypotheses."""
    if not enabled(cfg) or not captions:return cues
    from types import SimpleNamespace
    from source_clock_recovery import MAX_WINDOWS
    from track_control import check,UserSkipped
    w=SimpleNamespace(atomic_json=write);ledger=ledger_for(w,job)
    if ledger is None:return cues
    # Keep half the remaining reservations for the required acoustic checks.
    available=max(0,(MAX_WINDOWS-ledger['attempts'])//2);started_windows=0
    source=Path(job)/'japanese-original.wav';path=Path(job)/'source-clock-recovery.json'
    for cue in cues:
        if not bounds(cue,captions,cfg['duration']) or cue.get('sourceClockUnconfirmed'):continue
        a,b=cue['start'],cue['end']
        try:digest=audio_digest(source,a,b)
        except (OSError,ValueError,wave.Error):continue
        key=hashlib.sha256(json.dumps([REVISION,'loaded-whisper-gap',variant,cfg.get('_sourceClockModelRevision'),cfg.get('sourceLanguage','ja'),a,b,digest],sort_keys=True).encode()).hexdigest()
        record=ledger['windows'].get(key)
        if record is None:
            if model is None or started_windows>=available or ledger['spentSeconds']>=90:continue
            check(cfg);record=dict(kind='caption-gap-asr445',status='reserved',start=a,end=b,audioSHA256=digest)
            ledger['windows'][key]=record;ledger['attempts']+=1;started_windows+=1;ledger['activeSince']=time.time()
            write(path,ledger);started=time.monotonic()
            try:
                emit('日語原聲','覆核原聲遺漏片段。',.29)
                segments,_=model.transcribe(audio[round(a*16000):round(b*16000)],language=cfg.get('sourceLanguage','ja'),word_timestamps=False,vad_filter=False,condition_on_previous_text=False,beam_size=5,max_new_tokens=256)
                text=''.join(s.text for s in segments).strip()
                check(cfg)
                if audio_digest(source,a,b)!=digest:raise ValueError('Source window changed during local recognition')
                record.update(status='complete',text=text)
            except UserSkipped:raise
            except (OSError,RuntimeError,ValueError) as error:record.update(status='unconfirmed',error=str(error)[:300])
            finally:
                ledger['spentSeconds']+=time.monotonic()-started;ledger.pop('activeSince',None);write(path,ledger)
        if record.get('status')=='complete':independent(cfg,job,cue,dict(text=record['text']),variant+'|loaded-whisper-gap')
    return cues

def sound_for(w,cfg,job,source,a,b,audio_sha):
    """Use one exact sound window within the existing twelve-window source allowance."""
    from source_clock_recovery import MAX_WINDOWS
    from nonverbal import classification_profile
    from track_control import check,UserSkipped
    profile=classification_profile();ledger_path=Path(job)/'source-clock-recovery.json'
    ledger=ledger_for(w,job)
    if ledger is None:return []
    key=hashlib.sha256(json.dumps([REVISION,'exact-gap-sound',audio_sha,a,b,profile],sort_keys=True).encode()).hexdigest()
    saved=ledger['windows'].get(key)
    if saved is not None:return saved.get('soundRows',[]) if saved.get('status')=='complete' else []
    if ledger.get('attempts',0)>=MAX_WINDOWS or ledger.get('spentSeconds',0)>=90:return []
    check(cfg)
    # A reserved window remains spent if execution stops before a result is saved.
    saved=dict(kind='caption-gap-sound445',status='reserved',start=a,end=b,audioSHA256=audio_sha,rows=[])
    ledger['windows'][key]=saved;ledger['attempts']=ledger.get('attempts',0)+1;ledger['activeSince']=time.time()
    w.atomic_json(ledger_path,ledger);started=time.monotonic()
    try:
        directory=Path(job)/'caption-gap-sound445';directory.mkdir(exist_ok=True);clip=directory/(key+'.wav')
        with wave.open(str(source)) as original:
            original.setpos(round(a*16000));pcm=original.readframes(round(b*16000)-round(a*16000))
        if hashlib.sha256(pcm).hexdigest()!=audio_sha:raise ValueError('Source window changed before sound classification')
        with wave.open(str(clip),'wb') as output:output.setparams((1,2,16000,0,'NONE','not compressed'));output.writeframes(pcm)
        raw=w.run([cfg['executable'],'--classify-performance',clip],timeout=max(.1,90-ledger.get('spentSeconds',0)))
        rows=json.loads(raw)
        __import__('nonverbal').validate_classification(rows)
        rows=[dict(r,start=r['start']+a) for r in rows]
        if audio_digest(source,a,b)!=audio_sha:raise ValueError('Source window changed during sound classification')
        saved.update(status='complete',soundRows=rows)
        check(cfg)
    except UserSkipped:raise
    except (OSError,ValueError,RuntimeError) as error:saved.update(status='unconfirmed',error=str(error)[:300])
    finally:
        ledger['spentSeconds']=ledger.get('spentSeconds',0)+time.monotonic()-started;ledger.pop('activeSince',None)
        w.atomic_json(ledger_path,ledger)
    return saved.get('soundRows',[]) if saved.get('status')=='complete' else []

def prepare(w,cfg,job,cues,captions):
    if not enabled(cfg) or not captions or cfg.get('editorRender'):return
    selected=[c for c in cues if bounds(c,captions,cfg['duration']) and not c.get('editorAudio')
              and c.get('originalSpeechReason') not in ('confirmed-source-song','confirmed-nonlexical-performance','sustained-source-vocalization','user-original')]
    if not selected:return
    source=Path(job)/'japanese-original.wav'
    decisions=[]
    for cue in selected:
        # Do not change authored, edited or already translated content on resume.
        if any(cue.get(k) for k in ('cantonese','english','mandarin')):continue
        a,b=cue['start'],cue['end'];paired=cue.get('captionGapIndependent445',{})
        first=cue.get('japanese') or cue.get('text','');second=paired.get('text','')
        bound=paired.get('complete') is True and paired.get('start')==a and paired.get('end')==b
        if bound:
            try:bound=paired.get('audioSHA256')==audio_digest(source,a,b)
            except (OSError,ValueError,wave.Error):bound=False
        proof=None;rows=[]
        if bound and not cue.get('sourceClockUnconfirmed') and ((nonverbal(first) and nonverbal(second)) or agrees(first,second,cfg.get('sourceLanguage','ja'))):
            rows=sound_for(w,cfg,job,source,a,b,paired['audioSHA256'])
            proof=evidence(rows,a,b,first,second)
        if proof:
            cue.update(captionGapNonDialogue445=dict(proof,revision=REVISION,start=a,end=b,audioSHA256=paired['audioSHA256']),
                preserveOriginalSpeech=True,originalSpeechReason=CONFIRMED,sourcePolicyBlocked=False,subtitleContentOnlyGap=True,cantonese='',
                reviewNote='Confirmed non-dialogue sound. Original audio is retained.')
        elif bound and not cue.get('sourceClockUnconfirmed') and not nonverbal(first) and not nonverbal(second) and agrees(first,second,cfg.get('sourceLanguage','ja')) and speech_evidence(rows,a,b):
            cue.update(captionGapSpeech445=True,captionGapAcceptedText445=second)
        else:
            cue.update(sourcePolicyBlocked=True,preserveOriginalSpeech=True,originalSpeechReason=UNKNOWN,subtitleContentOnlyGap=True,cantonese='',reviewNote=MESSAGE)
        decisions.append(dict(start=a,end=b,state='confirmed-nondialogue' if proof else 'confirmed-speech' if cue.get('captionGapSpeech445') else 'source-unconfirmed',independentBound=bound))
    try:ledger=json.loads((Path(job)/'source-clock-recovery.json').read_text())
    except (OSError,ValueError):ledger={}
    local=sum(r.get('kind')=='caption-gap-asr445' for r in ledger.get('windows',{}).values()) if isinstance(ledger,dict) and isinstance(ledger.get('windows',{}),dict) else 0
    w.atomic_json(Path(job)/'caption-gap-policy445.json',dict(revision=REVISION,rows=decisions,
        additionalWholeFileRecognitionRounds=0,boundedGapRecognitionReservations=local,sourceClockChanged=False,qualityCertified=False))

def display_issue(cue):
    if cue.get('originalSpeechReason')==UNKNOWN:return MESSAGE
    return None
