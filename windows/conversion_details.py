"""Bounded per-file evidence for comparing real conversions across computers.

Frozen submissions and generated track reports are distinct from current UI
settings. An absent fact stays unknown; no audio, credentials or arbitrary files
are added to the debug report.
"""
import json,platform,sys,time
from pathlib import Path

SETTINGS=('sourceLanguage','sourceAudioStream','speechRatePolicy','naturalTimingPolicy','subtitleSelection','automaticDurationRewrite','automaticRecovery','autoPreviewIncomplete','productionMode','translationSource','ttsBackend','selectedEngines','dubLanguages','subtitleModes','includeOriginal','model','asrModel','speechModel','referenceSpeechModel','drama3Model','drama3Backend','cosyModel','roleAnalysisMode','voiceStyleMode','visualRoleAnalysisEnabled','normalPolicyRevision','fastReferenceRevision','requireCompleteDubbing','fillMissingVoiceScripts','fallbackToRoleVoice','allowCrossEngineRepair','automaticAlternateVoice','preferFirstAudibleTake','autoValidate','aiAutoFix','backgroundGain','backgroundDucking','separateBackground','mixOriginal','startOffset','limit')
RUNTIME=('engine','requestedEngine','backend','device','gpu','textModel','voiceModel','model','variant','speechInferencePassed','modelLoadPassed','voiceBackend','dramaBackend','cudaFailure','hardware','roles','drama3Memory','warnings','analysisFallbackReason')

def read(path,default=None,limit=4*1024*1024):
    try:
        if not path.is_file() or path.stat().st_size>limit:return default
        return json.loads(path.read_text())
    except (OSError,ValueError,UnicodeError):return default

def take(obj,keys):return {k:obj[k] for k in keys if isinstance(obj,dict) and k in obj}

def owned(root,path):
    try:
        p=Path(path).resolve()
        return p if p.is_relative_to(Path(root).resolve()) else None
    except (TypeError,OSError,ValueError):return None

def write(path,data):
    from desktop_state import write as atomic_write
    atomic_write(path,data)

def start(root,row,request,attempt):
    root=Path(root);path=owned(root,request);cfg=read(path,{}) if path else {}
    version={}
    here=Path(__file__).resolve().parent
    for p in [here.parent/'VERSION.json',here/'shared/version.json',here.parent/'version.json']:
        version=read(p,{})
        if version:break
    result=dict(schemaVersion=1,capturedAt=time.time(),application=version,
        computer=dict(platform=sys.platform,system=platform.system(),release=platform.release(),machine=platform.machine(),python=platform.python_version()),
        project=dict(id=row['id'],video=row.get('video'),attemptID=attempt['id']),
        submittedSettings=take(cfg,SETTINGS),settingsSource='immutable submitted request',
        runtimeReceiptAtStart=take(read(root/'native-ready.json',{}) or {},RUNTIME))
    write(Path(attempt['path'])/'conversion-details.json',result)
    return result

def build(root,row):
    root=Path(root).resolve();attempt=row.get('attempt',{});attempt_folder=owned(root,attempt.get('path'))
    saved=read(attempt_folder/'conversion-details.json',{}) if attempt_folder else {}
    if isinstance(saved,dict) and saved.get('finalized') and row.get('status')!='running':return dict(saved,status=take(row,('status','stage','partial','output','lastError','resultSummary')))
    details=dict(saved or {},schemaVersion=1,project=dict(id=row.get('id'),video=row.get('video'),attemptID=attempt.get('id')),
        status=take(row,('status','stage','partial','output','lastError','resultSummary')))
    if not saved:
        request=owned(root,row.get('request'));cfg=read(request,{}) if request else {}
        details.update(submittedSettings=take(cfg or {},SETTINGS),settingsSource='saved submitted request; start-time computer details unavailable')
    # A failed new run must not quietly use the previous run's successful report.
    job=owned(root,row.get('job'))
    if not job:
        review=owned(root,row.get('review'));job=review.parent if review else None
    if not job:return details
    report_file=job/'report.json'
    if attempt.get('startedAt') and report_file.is_file() and report_file.stat().st_mtime<attempt['startedAt'] and not row.get('outputThisAttempt'):
        details['resultsEvidence']='Earlier job data; no result has been published by this attempt.'
        return details
    report=read(job/'report.json',{}) or {};review=read(job/'review.json',{}) or {}
    cfg=review.get('config',{}) or {}
    details['effectiveJobSettings']=take(cfg,SETTINGS)
    meta=review.get('meta',{}) or {}
    details['sourceMedia']=dict(format=take(meta.get('format',{}),('duration','size','bit_rate','format_name')),streams=[take(s,('index','codec_type','codec_name','pix_fmt','sample_rate','channels','width','height')) for s in meta.get('streams',[])])
    details['result']=take(report,('cues','qualityStatus','qualityChecked','deliveryKind','previewDelivery','automaticRecovery','dialogueDelivery','normalScriptRescue','scriptGapRecovery','failedEngines','trackQuality','normalUnresolved','subtitleTracks','originalSpeechIndices','audioFallbacks','fastModeDefects','processingSeconds','categorySeconds','milestones'))
    details['timing']=read(job/'processing-time.json',{}) or {}
    details['ocr']=dict(metrics=read(job/'ocr-metrics.json',{}) or {},status=read(job/'ocr-status.json',{}) or {},source=read(job/'input-source.json',{}) or {},discovery=read(job/'ocr-discovery/ocr-progress.json',{}) or {})
    details['ocr'].update(details['ocr']['metrics'])
    details['sourceCues']=[dict(index=i+1,**take(c,('start','end','japanese','text','cantonese','english','speakerId','enabled','missingScript','preserveOriginalSpeech','normalDefects','sourceReviewReasons'))) for i,c in enumerate(review.get('cues',[])[:1000])]
    details['issues']=read(job/'segment-issues.json',[]) or []
    details['translationBrevity']=read(job/'translation-brevity.json',{}) or {}
    tracks=[];running=row.get('status')=='running'
    records=report.get('tracks') or [dict(engine=cfg.get('ttsBackend'),language=cfg.get('targetLanguage','yue'),model=cfg.get('drama3Model'),report=str(job/'report.json'))]
    for row in records[:20]:
        track=dict(take(row,('engine','language','model')))
        path=owned(root,row.get('report'));folder=path.parent if path else None
        if folder:
            server=read(folder/'native-drama-server.json',{}) or {}
            track['actualNativeRuntime']=take(server,('backend','device','threads'))
            config=(read(folder/'review.json',{}) or {}).get('config',{})
            track['effectiveSettings']=take(config,SETTINGS)
            track['normalChecks']=read(folder/'normal-checks.json',{}) or {}
            track['translationBrevity']=read(folder/'translation-brevity.json',{}) or {}
            track['automaticRecovery']=read(folder/'automatic-recovery.json',{}) or {}
            track['naturalRepair']=read(folder/'natural-repair.json',{}) or {}
            track['naturalPlacement']=read(folder/'natural-placement.json',{}) or {}
            track['conciseDialogue']=read(folder/'concise-dialogue.json',{}) or {}
            track['englishOverlap']=read(folder/'english-overlap.json',{}) or {}
            track['timing']=read(folder/'timing.json',[]) or []
            track['speechLevels']=read(folder/'speech-levels.json',[]) or []
            track['speechMixLevel']=read(folder/'speech-mix-level.json',{}) or {}
            track['mixAudibility']=read(folder/'mix-audibility.json',{}) or {}
            # Sampling is known only when persisted by the generator. Earlier
            # native runs used server defaults; never label those as .7/.7.
            traces=[]
            limit=30 if running else 500
            for p in sorted(folder.glob('*.generation.json'))[:limit]:
                trace=read(p,{}) or {}
                if trace:traces.append(dict(file=p.name,**take(trace,('policy','backend','modelVariant','sampling','status','seed','targetLanguage','deliveryStyle','plannedParts','referenceSHA256','targetSeconds','parts'))))
            track['generationTraces']=traces
            track['samplingEvidence']='recorded in generation traces' if any(t.get('sampling') for t in traces) else 'not recorded; historical backend defaults may differ'
        tracks.append(track)
    details['actualTracks']=tracks
    details['qualityMeaning']='100% is processing completion, not proof of complete or correct speech. Missing dialogue and unresolved checks remain explicit.'
    return details

def finish(root,row):
    folder=owned(root,row.get('attempt',{}).get('path'))
    if folder:
        data=build(root,row);data['finalized']=True
        write(folder/'conversion-details.json',data)
