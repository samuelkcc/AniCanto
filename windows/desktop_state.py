"""Desktop state shared by Basic and Expert; no model or UI imports.

Queued requests are immutable. Views only select/edit future settings. Disk
snapshots run on the desktop's I/O pool, never in the playback callback.
"""
import copy
import hashlib
import json
from pathlib import Path
import time
import uuid
from workflow_settings import COMBINED,migrate,validated

ENGINES=[('drama3','Drama 3'),('gpt-sovits-v2','GPT V2 Pro+'),
         ('gpt-sovits','GPT V4'),('cosyvoice3','CosyVoice 3'),
         ('voxcpm2','VoxCPM2'),('wsyue','WenetSpeech-Yue')]
PHASES=['prepare','recognition','roles','translation','voice','repair','export']

def read(path,default=None):
    try:return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError):return copy.deepcopy(default)

def write(path,value):
    from atomic_files import write_json
    write_json(path,value,indent=2)

def defaults(language='en'):
    return dict(animeTheme='studio',randomAnimeTheme=False,selectedEngines=['drama3'],ttsBackend='drama3',defaultAudioEngine='drama3',
        dubLanguages=['yue','en'] if language=='en' else ['yue'],includeOriginal=True,
        subtitleModes=['yue','english','dual','original'] if language=='en' else ['yue','original'],subtitleSelection='automatic',
        subtitleSource='embedded',batchAutoSubtitles=True,productionMode='normal',normalRepairPolicy='missing-only',independentAsrBackend='auto',
        translationSource=COMBINED,roleAnalysisMode='independent',visualRoleAnalysisEnabled=False,translate=True,autoApprove=True,autoSpeakers=True,
        speechTiming=True,speechRatePolicy='natural',autoFit=True,aiAutoFix=True,continueOnError=True,
        fillMissingVoiceScripts=True,requireCompleteDubbing=True,fallbackToRoleVoice=True,automaticAlternateVoice=True,preferFirstAudibleTake=True,
        failedVoicePolicy='generic',
        separateBackground=True,independentReferences=True,voiceStyleMode='clone',
        cantoneseLocale='yue-HK',maxNaturalCandidates=0,autoSkipOP=True,translateOPED=False,
        burnOutputCaptions=False,startOffset=0,limit=0,mixOriginal=0,subtitleOutput='none')

def restore_requested_drama(store,ready,small_capable):
    """One upgrade migration for the old automatic GPT fallback, not queued jobs."""
    marker=store.root/'migrations/drama-small-default-v1.json'
    previous=ready.get('engine')
    if not small_capable or marker.exists() or ready.get('requestedEngine')!='drama3' or previous in (None,'drama3'):return False
    if store.settings.get('ttsBackend')!=previous or store.settings.get('selectedEngines')!=[previous]:return False
    store.settings.update(ttsBackend='drama3',selectedEngines=['drama3'],defaultAudioEngine='drama3')
    store.save();write(marker,dict(previous=previous,requested='drama3',reason='Compatible Drama3-small adapter is now available'))
    return True

class Store:
    def __init__(self,root,recover_running=True):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        (self.root/'exports').mkdir(exist_ok=True)
        self.path=self.root/'desktop-state.json'
        saved=read(self.path,{})
        self.language=saved.get('language','en');self.mode=saved.get('mode','basic')
        self.settings=migrate(dict(defaults(self.language),**saved.get('settings',{})))
        from subtitle_policy import configure
        # Older selections become the new automatic defaults for future work.
        configure(self.settings)
        if not self.settings.get('visualRoleAnalysisEnabled') and self.settings.get('roleAnalysisMode')=='audiovisual':self.settings['roleAnalysisMode']='audio'
        self.queue=saved.get('queue',[])
        for row in self.queue:
            if recover_running and row.get('status')=='running':row['status']='paused'
        self.selected=saved.get('selected');self.ui=saved.get('ui',{})
        self.ui.setdefault('interfaceLanguageInitialized',saved.get('language') in ('en','zh-HK','zh-CN','ja'))
        if not self.ui.get('aniCantoThemeDefaultApplied'):
            self.settings.update(animeTheme='studio',randomAnimeTheme=False)
            self.ui['aniCantoThemeDefaultApplied']=True
    def save(self):write(self.path,dict(language=self.language,mode=self.mode,settings=self.settings,queue=self.queue,selected=self.selected,ui=self.ui))
    def language_default(self,language):
        # Welcome selection changes defaults for future jobs, never submissions.
        self.language=language
        self.settings.update({k:v for k,v in defaults(language).items() if k in ('dubLanguages','includeOriginal','subtitleModes')})
        self.save()
    def add(self,paths):
        for file in paths:
            path=str(Path(file).resolve())
            if not any(row['video']==path for row in self.queue):
                self.queue.append(dict(id=uuid.uuid4().hex,video=path,status='waiting',progress=0))
        if self.queue and not any(r['id']==self.selected for r in self.queue):self.selected=self.queue[0]['id']
        self.save()
    def row(self,ident=None):return next((r for r in self.queue if r['id']==(ident or self.selected)),None)
    def submit(self,row):
        if row.get('request') and row['status']=='paused':return Path(row['request'])
        settings=validated(self.settings)
        from voice_parameters import validate as validate_voice_parameters
        validate_voice_parameters(settings)
        if settings.get('failedVoicePolicy') not in ('first-take','source','generic'):
            raise ValueError('Unknown failed voice fallback policy.')
        if self.mode=='basic':settings.update(preferFirstAudibleTake=True)
        if 'en' in settings.get('dubLanguages',[]) and 'wsyue' in settings.get('selectedEngines',[settings.get('ttsBackend')]):
            raise ValueError('WenetSpeech-Yue supports Cantonese only. Choose another engine for English or bilingual dubbing.')
        from subtitle_policy import configure
        configure(settings,basic=self.mode=='basic')
        settings.update(storage=str(self.root),video=row['video'],exportFolder=settings.get('exportFolder') or str(self.root/'exports'),
                        interfaceMode=self.mode,targetLanguage=settings['dubLanguages'][0],
                        defaultDubLanguage=settings['dubLanguages'][0],automaticDurationRewrite=True)
        if row.get('externalSubtitle'):
            subtitle=Path(row['externalSubtitle'])
            if not subtitle.is_file():raise ValueError('The imported subtitle file is missing. Choose it again before converting.')
            settings.update(translationSource=COMBINED,subtitleSource='external',subtitle=str(subtitle),
                            batchAutoSubtitles=False,batchExplicitSubtitle=True,ocr=False)
        if self.mode=='basic' and settings.get('roleAnalysisMode')=='audiovisual':settings.update(roleAnalysisMode='independent',visualRoleAnalysisEnabled=False)
        settings['videos']=[dict(id=row['id'],video=row['video'])]
        path=self.root/'requests'/('submitted-'+uuid.uuid4().hex+'.json');write(path,settings)
        row.update(request=str(path),progress=0,partial=False);self.save();return path
    def event(self,row,event):
        from output_delivery import public_event
        event=public_event(self.root,event)
        if event.get('trackOutput'):row['workingOutput']=event['trackOutput']
        from diagnostics import failure
        error=failure(event)
        if error:row['lastError']=error
        if event.get('output'):row['outputThisAttempt']=event['output']
        if event.get('deliveryKind'):
            row['deliveryKind']=event['deliveryKind']
            if event.get('output') and event.get('artifactRole') in ('published','labelled-preview'):row.pop('lastError',None)
            if event['deliveryKind']=='complete':
                row.pop('previewOutput',None);row.pop('missingDialogue',None);row.pop('incompleteDialogue',None)
                if event.get('artifactRole')=='published':row['partial']=False
        for key in ('previewOutput','missingDialogue','incompleteDialogue'):
            if key in event:row[key]=event[key]
        if event.get('stage')=='結果摘要':row['resultSummary']=event.get('message','')
        for key in ('review','output','job','nativeEngineFallback'):
            if event.get(key):row[key]=event[key]
        journey=event.get('journey')
        if isinstance(journey,dict):
            row['progress']=max(row.get('progress',0),min(1,journey.get('progress',0)))
            row['journey']=dict(journey,progress=row['progress'])
        if event.get('partial'):row['partial']=True
        row['stage']=event.get('stage','');row['message']=event.get('message','')
        if event.get('batchStatus'):row['batchStatus']=event['batchStatus']
        self.save()
    def finish(self,row,code,paused=False,finalize_diagnostics=True):
        output=Path(row.get('output') or '')
        if row.get('attempt'):
            from diagnostics import finish
            if finalize_diagnostics:finish(self.root,row,code,paused)
            output=Path(row.get('outputThisAttempt') or '')
        row['status']='paused' if paused else 'complete' if code==0 and output.is_file() and not row.get('partial') else 'attention'
        if code==0 and not paused and output.is_file():row['progress']=1
        self.save()

def job_snapshot(row):
    """Bounded off-thread disk projection; cue indices never inferred from words."""
    review_path=Path(row.get('review',''))
    root=review_path.parent if review_path.is_file() else Path(row.get('job','/nonexistent'))
    active_root=Path(row.get('job','/nonexistent'))
    if row.get('status')=='running' and not row.get('previewAttempt') and active_root.is_dir() and active_root!=root:
        # A new attempt can publish its job before translation has produced a
        # review. Never project the previous conversion's voices as this job.
        root=active_root;review_path=root/'review.json'
    review=read(review_path,{}) or read(root/'review.json',{}) or {}
    result=dict(portraitAtlas=read(root/'visual-photo-atlas.json',{}),originalCaptions=read(root/'subtitle-context.json',[]),review=review,root=str(root),takes=[],history=[],recordingCandidates=[],roles=review.get('config',{}).get('voiceProfiles',[]),
                journey=read(root/'production-progress.json',{}),time=read(root/'processing-time.json',{}),
                report=read(root/'report.json',{}),issues=read(root/'segment-issues.json',[]))
    journey=result['journey'];report=result['report'];last=(result['time'].get('runs') or [{}])[-1]
    output=report.get('exportedOutput') or report.get('output')
    if journey.get('progress',0)>=.94 and not journey.get('complete') and last.get('status')=='finished' and output and Path(output).is_file() and any(r.get('id')=='export' and r.get('seconds',0)>0 for r in journey.get('milestones',[])):
        journey.update(progress=1,complete=True,qualityStatus=report.get('qualityStatus','needs-review'))
        for r in journey['milestones']:
            if r['id']=='export':r['state']='complete'
    paths=([root]+sorted((root/'tracks').glob('*'))+sorted((root/'versions').glob('*'))+
           sorted((root/'versions').glob('*/tracks/*'))) if root.is_dir() else []
    seen_candidates=set()
    def add_candidate(path,index,engine,language,kind,reason='',created=0,spoken_text=None):
        if type(index) is not int or index<1 or not path:return
        try:
            file=Path(path).resolve()
            if not file.is_relative_to(root.resolve()) or not file.is_file():return
        except (OSError,ValueError):return
        identity=(str(file),index,language)
        if identity in seen_candidates:return
        seen_candidates.add(identity)
        cue=review.get('cues',[])[index-1] if index<=len(review.get('cues',[])) else {}
        text=spoken_text if spoken_text is not None else cue.get('english' if language=='en' else 'cantonese','')
        result['recordingCandidates'].append(dict(path=str(file),index=index,engine=engine,language=language,kind=kind,reason=reason,created=created,text=text))
    for folder in paths:
        local_review=read(folder/'review.json',{});cfg=local_review.get('config',{})
        local_cues_by_index={c.get('reviewIndex',n):c for n,c in enumerate(local_review.get('cues',[]))}
        profiles_by_id={p.get('id'):p for p in cfg.get('voiceProfiles',[])}
        manifest=read(folder/'audio-preview.json',{})
        engine=manifest.get('engine',cfg.get('ttsBackend'));language=manifest.get('language',cfg.get('targetLanguage','yue'))
        # Fitted timing takes precedence over earlier model outputs.
        rows=read(folder/'timing.json',[]) or manifest.get('rows',[])
        version=read(folder/'version.json',{})
        if not version and folder.parent.name=='tracks' and folder.parent.parent.parent.name=='versions':
            version=read(folder.parent.parent/'version.json',{})
        engine=engine or version.get('engine');language=version.get('language',language)
        for n,take in enumerate(manifest.get('rows',[])):
            add_candidate(take.get('audio'),take.get('index',take.get('reviewIndex',n)+1),engine,language,'first',spoken_text=take.get('text'))
        checks=read(folder/'normal-checks.json',{})
        for row in checks.get('repairs',[])+checks.get('advisories',[]):
            index=row.get('index')
            add_candidate(row.get('originalAudio'),index,engine,language,'first',row.get('reason',''))
            for attempt in row.get('attempts',[]):
                add_candidate(attempt.get('candidateAudio'),index,engine,language,'generated' if attempt.get('repaired') else 'rejected',row.get('reason',''))
        for record in read(folder/'automatic-recovery.json',{}).get('rows',{}).values():
            for attempt in record.get('attempts',[]):
                add_candidate(attempt.get('candidateAudio') or attempt.get('selectedAudio'),record.get('index'),attempt.get('engine') or engine,language,'generated' if attempt.get('status')=='adopted' else 'rejected',attempt.get('reason',''),spoken_text=attempt.get('text') or record.get('initialText'))
        for manifest_path in sorted(folder.rglob('recording-history/*/take.json')):
            if 'tracks' in manifest_path.relative_to(folder).parts:continue
            archived=read(manifest_path,{})
            add_candidate(manifest_path.parent/archived.get('audio','audio.wav'),archived.get('index'),archived.get('engine') or engine,archived.get('language') or language,'rejected',archived.get('reason',''),archived.get('created',0),archived.get('text'))
        for index,take in enumerate(rows):
            audio=take.get('renderedAudio') or take.get('audio')
            if audio and not take.get('skipped') and Path(audio).is_file():
                cue_id=version.get('segment')
                cue_index=next((n+1 for n,c in enumerate(review.get('cues',[])) if c.get('editorID',f'cue-{n}')==cue_id),None)
                local_index=take.get('reviewIndex',index)
                local_cue=local_cues_by_index.get(local_index,{})
                profile=profiles_by_id.get(local_cue.get('speakerId'))
                from review_workbench import reference_signature
                provenance=dict(speakerId=local_cue['speakerId']) if 'speakerId' in local_cue else {}
                if profile:provenance['reference']=reference_signature(profile)
                spoken_key='english' if language=='en' else 'cantonese'
                if spoken_key in local_cue:provenance['text']=local_cue[spoken_key]
                result['takes'].append(dict(take,audio=audio,engine=engine,language=language,index=cue_index or take.get('index',take.get('reviewIndex',index)+1),versionOutput=version.get('output'),versionStatus=version.get('status'),recordingProvenance=provenance))
        for path in sorted((folder/'recording-history').glob('*/take.json')):
            history=read(path,{})
            if history:
                history['path']=str(path.parent/history.get('audio','audio.wav'));result['history'].append(history)
    from review_report import project
    result.update(project(root,review,row))
    result['currentOutput']=row.get('output')
    # One source pair serves every dialogue row, including lines without a
    # quality warning. Only advertise audio that is actually present.
    from review_diagnostics import managed_separated
    config=review.get('config',{})
    original=root/'japanese-original.wav'
    separated=managed_separated(config,root) if config.get('dialoguePath') else None
    result['reviewSources']={}
    if original.is_file():result['reviewSources']['original']=str(original)
    if separated:result['reviewSources']['separated']=separated
    return result

def review_fingerprint(review):
    cfg=review.get('config',{})
    data=dict(config={key:cfg.get(key) for key in ('video','duration','ttsBackend','selectedEngines','dubLanguages')},
        cues=[{key:cue.get(key) for key in ('start','end','text','japanese','cantonese','english','speakerId','enabled')} for cue in review.get('cues',[])])
    return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def editor_draft(review_path,review,settings):
    cues=review.get('cues',[])
    return dict(id=uuid.uuid4().hex,review=str(review_path),baseFingerprint=review_fingerprint(review),created=time.time(),settings=copy.deepcopy(settings),
        segments=[dict(id=c.get('editorID') or 'cue-'+str(i),sources=[i],start=c['start'],end=c['end'],
                       original=c.get('japanese',c.get('text','')),text=c.get('cantonese',''),english=c.get('english',''),
                       speakerId=c.get('speakerId',''),enabled=c.get('enabled',True),
                       captionStart=c.get('subtitleStart',c['start']),captionEnd=c.get('subtitleEnd',c['end']),
                       captionText=c.get('captionText',''),take=c.get('_seed',42),rate=c.get('editorRate',1),
                       trimStart=c.get('editorTrimStart',0),trimEnd=c.get('editorTrimEnd',0),
                       preserveOriginalSpeech=c.get('preserveOriginalSpeech',False)) for i,c in enumerate(cues)],clips=[])

def load_draft(review_path,review,settings):
    root=Path(review_path).parent;saved=read(root/'editor-draft-windows.json',{})
    if saved.get('review')==str(review_path) and saved.get('baseFingerprint')==review_fingerprint(review):return saved
    if saved:
        # Preserve user edits as evidence. Never apply an older source draft to
        # newly translated/timed cues merely because review.json has one name.
        write(root/('editor-draft-superseded-'+uuid.uuid4().hex+'.json'),saved)
    return editor_draft(review_path,review,settings)

def find_take(snapshot,index,engine,language):
    return next((r for r in reversed(snapshot.get('takes',[])) if r.get('index')==index+1 and r.get('engine')==engine and r.get('language')==language),None)

def accept_history(root,history,text):
    """Explicit user decision; a short/capped fragment cannot replace a whole line."""
    import shutil
    generation=history.get('generation',{})
    if history.get('text')!=text:raise ValueError('The words have changed. Generate a new take first.')
    if generation.get('capped') or generation.get('complete') is False or 'generation-limit' in history.get('reason',''):
        raise ValueError('This recording is incomplete. It remains available for comparison; regenerate the full line.')
    source=Path(history['path']).resolve();root=Path(root).resolve()
    if not source.is_relative_to(root):raise ValueError('The recording does not belong to this project.')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if digest!=history['audioSHA256']:raise ValueError('The diagnostic recording has changed.')
    ident=uuid.uuid4().hex;folder=root/'accepted-recordings'/ident;folder.mkdir(parents=True)
    target=folder/'audio.wav';shutil.copy2(source,target)
    write(folder/'acceptance.json',dict(historyID=history['id'],acceptedByUser=True,acceptedAt=time.time(),
        engine=history['engine'],language=history['language'],text=text,reason=history.get('reason',''),
        audioSHA256=digest,source=str(source)))
    return str(target),history['id']
