"""UI-neutral desktop operations, used verbatim by macOS and Windows.

One short-lived JSON request per native IPC call. Playback never invokes this
module. Long model/media tasks are separate owned processes, not RPC handlers.
The native host serializes state writes. Existing worker inputs remain immutable.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SHARED = Path(os.environ.get('CANTOSYNC_SHARED_RESOURCES', BASE/'Resources'))
WINDOWS = Path(os.environ.get('CANTOSYNC_WINDOWS_PACKAGE', BASE/'windows'))
sys.path[:0] = [str(WINDOWS), str(SHARED)]
from desktop_state import Store, defaults, read, write, job_snapshot, editor_draft, review_fingerprint
from workflow_settings import validated

VIDEO_TYPES = {'.mkv','.mp4','.mov','.m4v','.avi','.webm','.ts'}
SUBTITLE_TYPES = {'.srt','.ass','.ssa','.vtt'}
SETTING_KEYS = set(defaults()) | {'model','visualModel','asrModel','speechModel','referenceSpeechModel',
    'drama3Model','cosyModel','qwenModel','voxcpmModel','wsyueModel','gsvDevice','voiceProfiles','defaultSpeaker',
    'backgroundGain','backgroundDucking','appearance','animeTheme','controlDensity',
    'subtitle','subtitleStream','ocrRect','ocr','ocrAutoRegion','exportFolder','translationSource','allowCrossEngineRepair',
    'randomAnimeTheme','themeSession','voiceStyleMode','roleAnalysisMode','visualRoleAnalysisEnabled','deploymentModels',
    'sourceWorkflow','defaultSubtitleWorkflow','defaultOCRWorkflow','failedVoicePolicy','dramaBackend','normalRepairPolicy','independentAsrBackend','speechAcceleration'}
from voice_parameters import keys as voice_parameter_keys, validate as validate_voice_parameters
SETTING_KEYS.update(voice_parameter_keys())
SETTING_KEYS.add('cosyExpression')


class Studio:
    def __init__(self, root, shared=SHARED, platform=None, helper=None):
        self.root=Path(root).resolve();self.shared=Path(shared).resolve()
        self.platform=platform or sys.platform;self.helper=Path(helper) if helper else None
        # A distinct metadata file imports prior libraries without changing a
        # running legacy UI's queue/settings or its in-flight request.
        self.store=Store(self.root/'studio',recover_running=False)
        self.store.root=self.root
        self.store.path=self.root/'studio/desktop-state.json'
        self.import_existing()
        normal_marker=self.root/'studio/normal-workflow-v1.json'
        if not normal_marker.exists():
            # This one-time pass never chose the work mode. Since work-modes
            # revision 2 the stored work mode is always the single standard mode.
            self.store.settings.update(roleAnalysisMode='independent',visualRoleAnalysisEnabled=False,autoSkipOP=True,translateOPED=False)
            self.store.save();write(normal_marker,dict(futureSubmissionsOnly=True))

    def recover_orphans(self):
        """Called once by the exclusive native host, before it owns any worker.

        Never run this on ordinary polls: RPC adapters are short lived while the
        real conversion child belongs to the native host.
        """
        changed=False
        for row in self.store.queue:
            if row.get('status')!='running':continue
            attempt=row.get('attempt') or {}
            path=Path(attempt.get('path') or self.root/'attempts/nonexistent').resolve()
            receipt=read(path/'attempt.json',{}) if path.is_relative_to(self.root/'attempts') else {}
            preview=row.pop('previewAttempt',False)
            if preview:
                row['status']=row.pop('previousStatus','attention')
                if row['status']=='running':row['status']='paused'
            elif receipt.get('endedAt') and receipt.get('id')==attempt.get('id'):
                row['attempt']=receipt
                row['status']='paused' if receipt.get('status')=='paused' else 'complete' if receipt.get('exitCode')==0 and Path(row.get('outputThisAttempt') or '').is_file() and not row.get('partial') else 'attention'
            else:
                row['status']='paused'
            row['recovery']=dict(reason='interrupted-host',at=time.time(),requestRetained=bool(row.get('request')))
            changed=True
        if changed:
            self.store.ui.update(autoQueue=False,autoQueueAttention=False)
            self.store.save()

    def import_existing(self):
        marker=self.root/'studio/import-v1.json'
        if marker.exists():return
        old=read(self.root/'desktop-state.json',{})
        if old:
            self.store.settings=validated(dict(defaults(old.get('language','en')),**old.get('settings',{})))
            self.store.language=old.get('language','en');self.store.mode=old.get('mode','basic')
            self.store.queue=copy.deepcopy(old.get('queue',[]));self.store.selected=old.get('selected')
            for row in self.store.queue:
                if row.get('status')=='running':row['status']='paused'
        # Mac projects are discovered without opening, re-saving or replacing
        # their review/configuration. No import starts a conversion.
        known={r.get('review') for r in self.store.queue}
        for path in sorted((self.root/'jobs').glob('*/review.json')):
            if str(path) in known:continue
            review=read(path,{});cfg=review.get('config',{});video=cfg.get('video')
            if not video:continue
            report=read(path.parent/'report.json',{});output=report.get('exportedOutput') or report.get('output')
            self.store.queue.append(dict(id=uuid.uuid4().hex,video=video,review=str(path),job=str(path.parent),
                status='complete' if output and Path(output).is_file() else 'attention',output=output,progress=1 if output else 0))
        selected=read(self.root/'model-selections.json',{})
        for role,key in [('text','model'),('visual','visualModel'),('asr','asrModel'),('speech','speechModel'),
                         ('referenceSpeech','referenceSpeechModel'),('drama3','drama3Model'),('cosyvoice3','cosyModel')]:
            if selected.get(role):self.store.settings[key]=selected[role]
        if not self.store.selected and self.store.queue:self.store.selected=self.store.queue[-1]['id']
        self.store.save();write(marker,dict(importedAt=time.time(),projects=len(self.store.queue)))

    def row(self, ident=None):
        row=self.store.row(ident)
        if row is None:raise ValueError('Select a video first.')
        return row

    def state(self):
        from use_terms import accepted
        from output_delivery import presentation
        selected=next((r for r in self.store.queue if r['id']==self.store.selected),None)
        return dict(schemaVersion=1,language=self.store.language,mode=self.store.mode,settings=self.store.settings,productionSettings=self.store.settings_for(selected),
            queue=[presentation(self.root,r,self.store.settings.get('exportFolder','')) for r in self.store.queue],selected=self.store.selected,ui=self.store.ui,storage=str(self.root),platform=self.platform,useTermsAccepted=accepted(self.root))

    def review_path(self,row):
        path=Path(row.get('review') or Path(row.get('job','/nonexistent'))/'review.json').resolve()
        if not path.is_relative_to(self.root/'jobs') or not path.is_file():raise ValueError('This video has no script yet.')
        return path

    def draft(self,row):
        path=self.review_path(row);review=read(path,{})
        saved=read(path.parent/'editor-draft-studio.json',{})
        if saved.get('baseFingerprint')==review_fingerprint(review):return saved
        # Do not discard a draft merely because processing produced a new source.
        if saved:
            archive=path.parent/('editor-draft-studio-superseded-'+hashlib.sha256(json.dumps(saved,sort_keys=True).encode()).hexdigest()[:16]+'.json')
            if not archive.exists():write(archive,saved)
        return editor_draft(path,review,dict(review.get('config',{}),**self.store.settings))

    def tools(self):
        if self.platform=='win32':return read(self.root/'native-ready.json',{})
        return dict(ffmpeg=str(self.shared/'bin/ffmpeg'),ffprobe=str(self.shared/'bin/ffprobe'),
                    executable=str(self.helper or ''),port=11447)

    def task(self,action,request,row=None,preview=False):
        if self.platform=='win32':
            python=self.root/'runtimes/worker/Scripts/python.exe'
            program=str(python);args=[str(WINDOWS/'native_worker.py'),action,str(request)]
        else:
            if not self.helper or not self.helper.is_file():raise ValueError('The Mac processing adapter is missing. Repair the app package.')
            program=str(self.helper);args=['--studio-task',action,str(request)]
        if not Path(program).is_file():raise ValueError('Deploy the processing runtime in Welcome before converting.')
        result=dict(program=program,args=args,action=action,preview=preview,root=str(self.root))
        if row:
            from diagnostics import start
            row['previousStatus']=row.get('status','attention')
            result.update(rowID=row['id'],attempt=start(self.root,row,action,request))
            for key in ('lastEventAt','lastProgressAt','activitySignature'):row.pop(key,None)
            row['status']='running';row['previewAttempt']=preview;self.store.save()
        return result

    def selected_model_ids(self):
        selections=read(self.root/'model-selections.json',{})
        engines=set(self.store.settings.get('selectedEngines',[]))|{self.store.settings.get('ttsBackend')}
        roles={'text','visual','asr','speech','referenceSpeech','voice'}|engines
        return {v for k,v in selections.items() if k in roles and isinstance(v,str)}

    def model_inventory(self):
        from model_maintenance import catalog_paths
        models,folder=catalog_paths(self.platform)
        from model_ownership import removed_ids
        removed=removed_ids(self.root,models)
        rows=[]
        for row in models:
            if row['id'] in removed:continue
            path=folder(self.root,row);saved=0;installed=bool(row.get('files'));missing=[]
            for file in row.get('files',[]):
                p=path/file['path'];size=p.stat().st_size if p.is_file() else 0
                expected=file.get('size',0);complete=size==expected if expected else size>0;installed &= complete
                if not complete:missing.append(dict(path=file['path'],expectedBytes=expected,actualBytes=size))
                partial=path/(file['path']+'.partial')
                saved+=min(expected,size or (partial.stat().st_size if partial.is_file() else 0)) if expected else size
            if installed or saved:
                rows.append(dict(id=row['id'],title=row['title'],category=row['category'],bytes=row['bytes'],savedBytes=saved,installed=bool(installed),missingFiles=missing,missingBytes=sum(f['expectedBytes'] for f in missing),engine=row.get('engine'),retired=bool(row.get('retired'))))
        from model_maintenance import removal_plan
        selected=self.selected_model_ids()
        for row in rows:
            removal=removal_plan(self.root,row['id'],self.platform,selected)
            row.update(selected=row['id'] in selected,canRemove=removal['canRemove'],removeReason=removal['reason'],removableBytes=removal['bytes'])
        return rows

    def log_sources(self):
        row=self.store.row() or {};candidates=[]
        attempt=Path(row.get('attempt',{}).get('path',self.root/'logs'))
        candidates.append(('Process output',attempt/'process.log'))
        candidates.append(('Model / setup output',self.root/'logs/studio/process.log'))
        for title,name in [('Application process','developer-process.log'),('MLX translation','mlx-text.log'),('Ollama translation','logs/native-ollama.log' if self.platform=='win32' else 'ollama.log')]:
            candidates.append((title,self.root/name))
        if self.platform=='win32' and (self.root/'ollama.log').is_file():candidates.append(('Ollama translation · earlier',self.root/'ollama.log'))
        job=Path(row.get('job') or self.root/'jobs/nonexistent')
        if job.resolve().is_relative_to((self.root/'jobs').resolve()):
            for path in sorted(job.rglob('*.log'))[:40]:
                candidates.append(('Job · '+str(path.relative_to(job)),path))
        result=[dict(id='@summary',title='Workflow summary',bytes=0,available=True),dict(id='@state',title='Current status (JSON)',bytes=0,available=True),dict(id='@conversion',title='File conversion details',bytes=0,available=True)];seen=set()
        for title,path in candidates:
            path=path.resolve()
            if not path.is_relative_to(self.root) or str(path) in seen:continue
            seen.add(str(path));result.append(dict(id=path.relative_to(self.root).as_posix(),title=title,bytes=path.stat().st_size if path.is_file() else 0,available=path.is_file()))
        return result

    def log_text(self,source,limit):
        if source['id']=='@conversion':
            from conversion_details import build
            return json.dumps(build(self.root,self.store.row() or {}),ensure_ascii=False,indent=2)[:limit]
        if source['id']=='@summary':
            from workflow_log import summary
            return summary(self.root,self.store.row() or {},self.store.language,limit)
        if source['id']=='@state':
            row=self.store.row() or {}
            return json.dumps({k:row.get(k) for k in ('video','status','stage','message','progress','processingSeconds','resultSummary','lastError')},ensure_ascii=False,indent=2) if row else ''
        path=(self.root/source['id']).resolve()
        if not path.is_file():return ''
        try:
            with path.open('rb') as handle:
                size=path.stat().st_size;handle.seek(max(0,size-limit));data=handle.read(limit)
            return ('[Earlier bytes omitted]\n' if size>limit else '')+data.decode('utf-8','replace')
        except OSError as error:return '[Log unavailable: '+str(error)+']'

    def debug_report(self):
        from desktop_debug import report
        return report(self)

    def dispatch(self,op,p):
        if op=='use-terms':
            from use_terms import document,accepted
            return dict(document(),accepted=accepted(self.root))
        if op=='accept-use-terms':
            from use_terms import accept
            return accept(self.root,p)
        if op=='revoke-use-terms':
            from use_terms import revoke
            return revoke(self.root)
        if op in ('start','render','retake','setup','maintain-model','maintain-models','retry-review'):
            from use_terms import require
            require(self.root)
        if op=='speech-library':
            from speech_library import listing
            result=listing(self.root,self.store.language)
            installed=self.model_inventory()
            current=self.tools().get('textModel',self.store.settings.get('model')) if self.platform=='win32' else self.store.settings.get('model')
            result['textModels']=[dict(id=r['id'],title=r['title']) for r in installed if r.get('category')=='text' and r.get('installed')]
            if current and not any(r['id']==current for r in result['textModels']):result['textModels'].insert(0,dict(id=current,title=current))
            result['defaultTextModel']=current
            from desktop_state import ENGINES
            result['engines']=[dict(id=key,title=title,installed=any(r.get('engine')==key and r.get('installed') and not r.get('retired') for r in installed)) for key,title in ENGINES]
            return result
        if op=='speech-upload':
            from speech_library import upload
            return upload(self.root,p.get('data'),p.get('mime'))
        if op=='speech-import':
            from speech_library import import_audio
            return import_audio(self.root,p.get('path',''))
        if op=='speech-save':
            from speech_library import save
            save(self.root,p.get('id'),bool(p.get('acceptReview')))
            return self.dispatch('speech-library',{})
        if op=='speech-draft':
            from speech_library import save_draft
            return save_draft(self.root,p)
        if op=='speech-new':
            from speech_library import new_document
            return new_document(self.root,p)
        if op in ('speech-select','speech-load','speech-delete','speech-rename','speech-export-file'):
            if any(r.get('status')=='running' for r in self.store.queue):raise ValueError('Pause the video conversion before changing saved speech recordings.')
            import speech_library as library
            if op=='speech-select':library.select(self.root,p.get('id'))
            elif op=='speech-load':library.load_take(self.root,p.get('id'))
            elif op=='speech-delete':library.delete(self.root,p.get('id'))
            elif op=='speech-rename':library.rename(self.root,p.get('projectID'),p.get('title',''))
            else:
                audio=library.verified_audio(self.root,p.get('id'),bool(p.get('source')))
                row=library.read(library.folder(self.root,p.get('id'))/'result.json',{})
                meta=library.read(library.owned(self.root,'documents',row.get('projectID') or p.get('id'))/'document.json',{})
                return dict(path=str(audio),title=meta.get('title') or row.get('title') or 'AniCanto recording',extension=audio.suffix.lstrip('.'))
            return self.dispatch('speech-library',{})
        if op=='speech-finish':
            from speech_library import folder,read as load,write as save
            job=folder(self.root,p.get('id'));result=load(job/'result.json',{})
            if result.get('status') in ('waiting','running'):
                result.update(status='stopped' if p.get('paused') else 'failed',error='Generation stopped. Your input is kept.' if p.get('paused') else str(p.get('stderr') or 'The local model task ended before producing a result.')[-2000:])
                save(job/'result.json',result)
            return result
        if op=='speech-studio':
            from use_terms import require
            require(self.root)
            if any(r.get('status')=='running' for r in self.store.queue):raise ValueError('Pause the video conversion before generating speech.')
            from speech_library import submit
            cfg=dict(self.store.settings,**self.tools())
            selected=read(self.root/'model-selections.json',{})
            for role,key in [('text','model'),('speech','speechModel'),('drama3','drama3Model')]:
                if selected.get(role):cfg.setdefault(key,selected[role])
            if p.get('textModel'):
                options=self.dispatch('speech-library',{}).get('textModels',[])
                if p['textModel'] not in {r['id'] for r in options}:raise ValueError('Deploy the selected text model before using it in Dubbing studio.')
            path=submit(self.root,cfg,p)
            return dict(self.task('speech-studio',path),speechClipID=path.parent.name)
        if op=='compute-status':
            from compute_policy import summary
            return summary(self.root)
        if op=='state':return self.state()
        if op=='performance-choice':
            row=self.row(p.get('id'))
            if row.get('status')=='running':raise ValueError('Pause before choosing a source performance.')
            snapshot=job_snapshot(row);event=next((x for x in snapshot.get('performance',{}).get('notes',[]) if x['id']==p.get('eventID')),None)
            if not event or event['label']=='unavailable':raise ValueError('The source performance evidence changed. Refresh and listen again.')
            draft=self.draft(row);ranges=draft.setdefault('settings',{}).setdefault('performanceOverrides',[])
            ranges=[x for x in ranges if x.get('id')!=event['id']]
            if p.get('keep'):
                ranges.append(dict(id=event['id'],start=event['start'],end=event['end'],userConfirmed=True))
            draft['settings']['performanceOverrides']=ranges
            self.dispatch('save-draft',dict(id=row['id'],draft=draft));return dict(draft=draft,snapshot=job_snapshot(row))
        if op in ('project-terms','set-project-terms'):
            row=self.row(p.get('id'))
            from terminology import validate as validate_terms
            if op=='set-project-terms':
                if row.get('status') in ('running','paused'):raise ValueError('Finish this conversion before changing its frozen terminology.')
                rules=validate_terms(p.get('rules',[]));row['termRules']=rules;self.store.save()
                if row.get('review'):
                    draft=self.draft(row);draft.setdefault('settings',{})['termRules']=rules
                    self.dispatch('save-draft',dict(id=row['id'],draft=draft))
            suggestions=[]
            if row.get('review'):
                base=Path(row['review']).parent
                for file in [base/'normal-names.json']+list(base.glob('tracks/*/normal-names.json')):
                    suggestions.extend(read(file,{}).get('names',[]))
            return dict(rules=row.get('termRules',[]),suggestions=list({t['source']:t for t in suggestions if t.get('source')}.values()))
        if op=='source-language':
            if any(r.get('status')=='running' for r in self.store.queue):raise ValueError('Pause processing before checking another source language.')
            row=self.row(p.get('id'))
            from source_language import preflight
            settings=self.store.settings_for(row)
            if p.get('stream') is not None:
                if type(p['stream']) is not int:raise ValueError('Invalid source audio stream.')
                row['sourceAudioStream']=p['stream']
            if p.get('language') is not None:row['sourceLanguageOverride']=p['language']
            settings.update({k:row[k] for k in ('sourceAudioStream','sourceLanguageOverride') if k in row})
            if self.store.mode=='basic':settings['selectedEngines']=[settings['ttsBackend']]
            result=preflight(self.root,row['video'],self.tools(),settings)
            row.update(sourceLanguage=result.get('language'),sourcePreflight=result)
            self.store.save();return result
        if op=='configure':
            scope=p.get('scope','global')
            if scope not in ('global','video'):raise ValueError('Unknown production settings scope.')
            target=self.row(p.get('id')) if scope=='video' else None
            if target and target.get('status')=='running':raise ValueError('Pause processing before changing this video settings.')
            if target and any(k in p for k in ('mode','language','ui')):raise ValueError('Interface settings are global.')
            if 'useGlobalSettings' in p:
                if target is None or not isinstance(p['useGlobalSettings'],bool) or p.get('settings'):raise ValueError('Invalid production scope change.')
                if p['useGlobalSettings']:
                    target.pop('productionSettings',None);target['useGlobalSettings']=True
                elif target.get('useGlobalSettings',True):
                    target['productionSettings']=__import__('production_scope').snapshot(self.store.settings);target['useGlobalSettings']=False
                self.store.save();return self.state()
            if target and not __import__('production_scope').individual(target):raise ValueError('Turn off Global settings before editing individual settings.')
            base=self.store.settings_for(target) if target else self.store.settings
            patch=p.get('settings',{})
            if not isinstance(patch,dict) or set(patch)-SETTING_KEYS:raise ValueError('Unsupported production setting.')
            patch=dict(patch)
            if target and set(patch)&__import__('production_scope').GLOBAL_ONLY:raise ValueError('This setting applies globally.')
            # Since work_modes revision 2 there is one work mode. Basic and Expert
            # differ only in which controls are shown.
            # Saved paused requests are immutable snapshots, not a global lock.
            if patch.get('normalRepairPolicy','missing-only') not in ('missing-only','verified'):raise ValueError('Unknown normal repair policy.')
            if patch.get('speechAcceleration','auto') not in ('auto','cpu'):raise ValueError('Unknown speech acceleration mode.')
            if patch.get('independentAsrBackend','auto') not in ('auto','mlx','cpu'):raise ValueError('Unknown independent ASR backend.')
            if (any(k in patch and patch[k]!=base.get(k) for k in ('productionMode','workMode','fullAIReview','aiAutoFix','limitSpeechDuration','contentChecks','repairExcessiveAudibleOverlap','skipNonDialogueCaptions'))
                    and any(r.get('status')=='running' and r.get('request') for r in self.store.queue)):
                raise ValueError('Production mode is locked until processing finishes.')
            if 'failedVoicePolicy' in patch and any(r.get('status')=='running' and r.get('request') for r in self.store.queue):
                raise ValueError('Failed voice fallback is locked until processing finishes.')
            if set(patch).intersection(voice_parameter_keys() | {'cosyExpression'}) and any(
                    r.get('status')=='running' and r.get('request') for r in self.store.queue):
                raise ValueError('Voice parameters are locked until processing finishes.')
            if 'subtitleModes' in patch and 'subtitleSelection' not in patch:patch['subtitleSelection']='custom'
            if patch.get('subtitleSelection','automatic') not in ('automatic','custom'):raise ValueError('Unknown subtitle selection policy.')
            cfg=validated(dict(base,**patch))
            if set(patch)&{'workMode','fullAIReview','aiAutoFix','limitSpeechDuration','contentChecks','repairExcessiveAudibleOverlap'}:
                cfg['workModeRevision']=__import__('work_modes').REVISION
                __import__('work_modes').configure(cfg)
            if cfg.get('failedVoicePolicy') not in ('first-take','source','generic'):
                raise ValueError('Unknown failed voice fallback policy.')
            validate_voice_parameters(cfg)
            if 'ttsBackend' in patch and 'selectedEngines' not in patch:
                cfg.update(selectedEngines=[patch['ttsBackend']],defaultAudioEngine=patch['ttsBackend'])
            if set(patch).intersection({'ttsBackend','selectedEngines'}):
                from engine_availability import require
                for engine in cfg.get('selectedEngines',[cfg.get('ttsBackend')]):require(engine,self.root,self.platform)
            supported={e[0] for e in __import__('desktop_state').ENGINES}
            engines=cfg.get('selectedEngines')
            if not isinstance(engines,list) or not engines or any(not isinstance(e,str) or e not in supported for e in engines):
                raise ValueError('Select at least one supported voice engine.')
            cfg['selectedEngines']=list(dict.fromkeys(engines))
            if cfg.get('ttsBackend') not in cfg['selectedEngines']:
                raise ValueError('The default voice engine must be selected.')
            cfg['defaultAudioEngine']=cfg['ttsBackend']
            if cfg.get('ttsBackend') not in [e[0] for e in __import__('desktop_state').ENGINES]:raise ValueError('Unknown voice engine.')
            if not cfg.get('dubLanguages') or set(cfg['dubLanguages'])-{'yue','zh','en'}:raise ValueError('Select a supported dubbing language.')
            if any(l!='yue' for l in cfg.get('dubLanguages',[])) and 'wsyue' in cfg['selectedEngines']:
                raise ValueError('WenetSpeech-Yue supports Cantonese only. Choose another engine for English or bilingual dubbing.')
            if 'visualRoleAnalysisEnabled' in patch and ('roleAnalysisMode' not in patch or patch['visualRoleAnalysisEnabled']):cfg['roleAnalysisMode']='audiovisual' if patch['visualRoleAnalysisEnabled'] else 'audio'
            if p.get('mode') is not None:
                if p['mode'] not in ('basic','expert'):raise ValueError('Unknown interface mode.')
                self.store.mode=p['mode']
            if self.store.mode=='basic':cfg.update(preferFirstAudibleTake=True)
            if p.get('language') is not None:
                if p['language'] not in ('en','zh-HK','zh-CN','ja'):raise ValueError('Unknown interface language.')
                self.store.language=p['language']
                self.store.ui['interfaceLanguageInitialized']=True
            from subtitle_policy import configure as subtitle_policy
            subtitle_policy(cfg)
            if target:target['productionSettings']=__import__('production_scope').snapshot(cfg)
            else:self.store.settings=cfg
            if isinstance(p.get('ui'),dict):self.store.ui.update(p['ui'])
            self.store.save();return self.state()
        if op=='add':
            paths=p.get('paths',[])
            if not isinstance(paths,list) or not paths:raise ValueError('Choose one or more videos.')
            for path in paths:
                f=Path(path)
                if not f.is_file() or f.suffix.lower() not in VIDEO_TYPES:raise ValueError('Unsupported or missing video: '+str(f))
            self.store.add(paths);return self.state()
        if op=='set-subtitle-source':
            row=self.row(p.get('id'))
            if row.get('status') in ('running','paused'):raise ValueError('Finish this saved conversion before changing its subtitle source.')
            choice=p.get('choice','auto')
            if choice not in ('auto','external','audio-only','ocr') and not (isinstance(choice,str) and choice.startswith('embedded:') and choice[9:].isdigit()):raise ValueError('Invalid conversion subtitle source.')
            if choice=='external' and not row.get('externalSubtitle'):raise ValueError('Import a subtitle file first.')
            if choice=='ocr' and self.store.mode!='expert':raise ValueError('OCR is an Expert mode option.')
            if choice.startswith('embedded:'):
                from playback_subtitles import read as subtitle_tracks
                available=subtitle_tracks(self.root,row,self.tools(),'list')['tracks']
                if not any(t['id']==choice and t['supported'] for t in available):raise ValueError('This subtitle track is unavailable or uses image subtitles unsupported by this player.')
            row['conversionSubtitleChoice']=choice;self.store.save();return self.state()
        if op=='set-external-subtitle':
            row=self.row(p.get('id'))
            if row.get('status') in ('running','paused'):
                raise ValueError('Pause and finish this conversion before changing its subtitle file.')
            path=p.get('path')
            if path is not None:
                if not isinstance(path,str) or not path.strip():raise ValueError('Choose a subtitle file.')
                subtitle=Path(path).expanduser().resolve()
                if subtitle.suffix.lower() not in SUBTITLE_TYPES or not subtitle.is_file():
                    raise ValueError('Choose an existing SRT, ASS, SSA or VTT subtitle file.')
                if not subtitle.stat().st_size:raise ValueError('The subtitle file is empty.')
                row['externalSubtitle']=str(subtitle);row['conversionSubtitleChoice']='external'
            else:
                row.pop('externalSubtitle',None)
                if row.get('conversionSubtitleChoice')=='external':row['conversionSubtitleChoice']='auto'
            self.store.save();return self.state()
        if op=='select':self.row(p['id']);self.store.selected=p['id'];self.store.save();return self.state()
        if op in ('reset-video-plan','reset-video'):
            from project_reset import preview,reset
            row=self.row(p.get('id'))
            return preview(row) if op=='reset-video-plan' else reset(self,row,p.get('token'))
        if op=='move-video':
            # Native RPCs serialize this write with progress/finalization. Move
            # by identity rather than accepting a stale replacement queue.
            ident=p.get('id');before=p.get('beforeID')
            if not isinstance(ident,str) or not any(r['id']==ident for r in self.store.queue):
                raise ValueError('The video list changed. Try moving the video again.')
            if before is not None and (not isinstance(before,str) or not any(r['id']==before for r in self.store.queue)):
                raise ValueError('The video list changed. Try moving the video again.')
            if before!=ident:
                row=self.row(ident);queue=[r for r in self.store.queue if r['id']!=ident]
                index=next((i for i,r in enumerate(queue) if r['id']==before),len(queue))
                queue.insert(index,row)
                if queue!=self.store.queue:self.store.queue=queue;self.store.save()
            return self.state()
        if op in ('queue-arm','queue-next','queue-stop'):
            from native_queue import dispatch
            return dispatch(self,op,p)
        if op in ('recording-impact','audio-waveforms','boundary-proposals','apply-boundary'):
            from editing_tools import impact,waveform,boundaries,boundary_token,apply_boundary
            row=self.row(p.get('id'));path=self.review_path(row);review=read(path,{})
            draft=copy.deepcopy(p.get('draft') or self.draft(row))
            if draft.get('baseFingerprint')!=review_fingerprint(review):raise ValueError('The source script changed. Reload this project.')
            if op=='recording-impact':return impact(review,draft,p)
            if op in ('boundary-proposals','apply-boundary'):
                analysis=read(path.parent/'japanese-analysis.json',{})
                if op=='apply-boundary':return dict(draft=apply_boundary(review,analysis,draft,p))
                return dict(proposals=boundaries(review,analysis),token=boundary_token(review,analysis,draft),wordClocksRequired=True)
            snapshot=job_snapshot(row);index=p.get('index')
            if not isinstance(index,int) or not 0<=index<len(review.get('cues',[])):raise ValueError('Select a dialogue.')
            cue=review['cues'][index];a=max(0,float(cue['start'])-.25);b=min(float(review.get('config',{}).get('duration') or float(cue['end'])+.25),float(cue['end'])+.25)
            sources=snapshot.get('reviewSources',{});items=[]
            for label,source in sources.items():
                file=Path(source).resolve()
                if file.is_relative_to(self.root) and file.is_file():items.append(dict(label=label,**waveform(file,a,b,self.tools()['ffmpeg'],self.root/'cache/waveforms')))
            takes=[x for x in snapshot.get('takes',[]) if x.get('index')==index+1 and x.get('engine')==p.get('engine') and x.get('language')==p.get('language')]
            if takes:
                file=Path(takes[-1]['audio']).resolve()
                if file.is_relative_to(self.root) and file.is_file():
                    measured=subprocess.check_output([self.tools()['ffprobe'],'-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(file)],timeout=15)
                    seconds=min(180,float(measured.decode().strip()))
                    items.append(dict(label='generated',**waveform(file,0,seconds,self.tools()['ffmpeg'],self.root/'cache/waveforms')))
            return dict(rows=items,index=index)
        if op in ('subtitle-alignment-preview','set-subtitle-alignment'):
            row=self.row(p.get('id'))
            if not row.get('externalSubtitle'):raise ValueError('Import a subtitle file first.')
            from playback_subtitles import read as read_captions
            from editing_tools import alignment,fingerprint
            original=dict(row);original.pop('subtitleAlignment',None)
            evidence=read_captions(self.root,original,self.tools(),choice='external')
            params=p.get('alignment',{});result=alignment(evidence['cues'],params)
            sha=hashlib.sha256(Path(row['externalSubtitle']).read_bytes()).hexdigest();token=fingerprint([row['id'],sha,params])
            if op=='set-subtitle-alignment':
                if row.get('status') in ('running','paused'):raise ValueError('Finish this saved conversion before changing subtitle timing.')
                if p.get('token')!=token:raise ValueError('Subtitle timing changed. Preview the adjustment again.')
                row['subtitleAlignment']=params;self.store.save()
            return dict(state=self.state(),token=token,scale=result['scale'],offset=result['offset'],count=len(result['cues']),sample=result['cues'][:8]+result['cues'][-2:])
        if op=='remove-videos':
            from queue_library import detach
            result=detach(self.store,p.get('ids'),self.root/'studio'/'removed-videos.json')
            return dict(state=self.state(),**result)
        if op=='restore-videos':
            from queue_library import restore
            result=restore(self.store,p.get('batch'),self.root/'studio'/'removed-videos.json')
            return dict(state=self.state(),**result)
        if op=='remove':
            row=self.row(p.get('id'))
            if row['status']=='running':raise ValueError('Pause this video before removing it.')
            from desktop_cleanup import remove
            # A stale or unsafe legacy work path must not trap a finished video
            # in the list. The cleaner refuses unsafe deletion; detach the row
            # and report that its work files were retained for manual recovery.
            try:
                saved=remove(self.root,row,[r for r in self.store.queue if r['id']!=row['id']])
                cleanup_warning=None
            except Exception as error:
                saved=[];cleanup_warning=str(error)
            self.store.queue.remove(row)
            if self.store.selected==row['id']:self.store.selected=self.store.queue[0]['id'] if self.store.queue else None
            self.store.save();return dict(state=self.state(),preservedExports=saved,cleanupWarning=cleanup_warning)
        if op=='snapshot':
            row=self.row(p.get('id'));snapshot=job_snapshot(row)
            seconds=snapshot.get('time',{}).get('seconds')
            if isinstance(seconds,(float,int)) and seconds!=row.get('processingSeconds'):
                row['processingSeconds']=seconds;self.store.save()
            if row.get('review') and snapshot.get('review') and Path(row['review']).parent==Path(snapshot['root']):
                try:
                    snapshot['draft']=self.draft(row)
                    choices=[(index,key,value) for index,segment in enumerate(snapshot['draft'].get('segments',[])) for key,value in segment.get('reviewDecisions',{}).items()]
                    applied=False
                    if choices and row.get('output'):
                        output=Path(row['output']).resolve()
                        for version_path in Path(row['review']).parent.glob('versions/*/version.json'):
                            version=read(version_path,{})
                            if version.get('status')!='complete' or Path(version.get('output') or '/nonexistent').resolve()!=output:continue
                            rendered=read(version_path.parent/'review.json',{}).get('cues',[])
                            applied=all(index<len(rendered) and rendered[index].get('editorDecisions',{}).get(key)==value for index,key,value in choices)
                            if applied:break
                    snapshot.setdefault('reviewState',{})['userChoicesApplied']=applied
                    for record in snapshot.get('reportRows',[]):record['pendingExport']=bool(record.get('pendingExport') and not applied)
                except ValueError:pass
            snapshot['rowID']=row['id']
            from review_workbench import project
            result=project(snapshot.get('root',str(Path(row.get('review') or row.get('job') or self.root/'jobs/nonexistent').parent)),snapshot)
            from editing_tools import coverage
            result['coverage']=coverage(result)
            return result
        if op=='review-triage':
            row=self.row(p.get('id'))
            if row.get('status')=='running':raise ValueError('Pause and save before reviewing a line.')
            path=self.review_path(row)
            snapshot=self.dispatch('snapshot',dict(id=row['id']))
            from review_workbench import mark
            return mark(path.parent,snapshot,p.get('issueID'),p.get('fingerprint'),p.get('state'))
        if op=='review-resolution':
            row=self.row(p.get('id'))
            if row.get('status')=='running':raise ValueError('Pause and save before making an explicit review choice.')
            path=self.review_path(row);review=read(path,{})
            if p.get('baseFingerprint')!=review_fingerprint(review):raise ValueError('The source script changed. Refresh before making a review choice.')
            draft=self.draft(row)
            from review_choices import select
            draft=select(path.parent,review,draft,job_snapshot(row),p.get('index'),p.get('engine'),p.get('language'),p.get('action'),p.get('audio'),p.get('confirmDefect',False))
            self.dispatch('save-draft',dict(id=row['id'],draft=draft))
            return dict(draft=draft,snapshot=job_snapshot(row),saved=True)
        if op=='save-draft':
            row=self.row(p.get('id'));path=self.review_path(row);draft=copy.deepcopy(p['draft'])
            source=read(path,{})
            if draft.get('review')!=str(path) or draft.get('baseFingerprint')!=review_fingerprint(source):raise ValueError('The source script changed. Reload this project before saving.')
            from project_edit import materialize,spans_for
            materialize(source,draft);spans_for(draft,source['config']['duration'])
            write(path.parent/'editor-draft-studio.json',draft);return dict(saved=True)
        if op=='start':
            row=self.row(p.get('id'))
            row.pop('queueNotice',None)
            restart=bool(p.get('freshVersion') and p.get('reanalyze'))
            resuming=row.get('status')=='paused' and not restart
            if row.get('status')=='running':raise ValueError('This video is already processing.')
            if not resuming and Path(row.get('output') or '/nonexistent').is_file() and not p.get('freshVersion'):
                if any(issue.get('status')!='user-choice-saved' and issue.get('repairEligible') is not False for issue in job_snapshot(row).get('issues',[])):
                    return self.dispatch('retry-review',dict(id=row['id'],mode='pending'))
                raise ValueError('This video already has an output. Choose Produce a new version to rerun the whole video.')
            from engine_availability import require
            frozen=read(Path(row.get('request') or '/nonexistent'),{}) if resuming else {}
            selected=frozen or self.store.settings_for(row)
            engines=selected.get('selectedEngines',[selected.get('ttsBackend')]) if frozen or self.store.mode=='expert' else [selected.get('ttsBackend')]
            for engine in engines:require(engine,self.root,self.platform)
            if not Path(row['video']).is_file():raise ValueError('The source video is missing. Reconnect its drive or import it again.')
            selected_models=read(self.root/'model-selections.json',{})
            selected_voice=selected.get('drama3Model') or selected_models.get('drama3') or selected_models.get('voice')
            if not resuming and 'drama3' in selected.get('selectedEngines',[selected.get('ttsBackend')]) and selected_voice=='drama3-small-iq3':raise ValueError('Drama3-small has been retired. Choose a compatible quality preset in Welcome before starting a new conversion.')
            source=row.get('sourcePreflight') or {}
            if not resuming and source.get('needsConfirmation'):
                if not source.get('supported'):raise ValueError(source.get('reason') or 'Unsupported source language.')
                if p.get('sourceConfirmed')!=source.get('token'):raise ValueError('Confirm the detected source language before conversion.')
            # Keep all frozen requests, including an older audiovisual choice.
            request=self.store.submit(row,force_new=True) if restart else self.store.submit(row)
            cfg=read(request,{})
            if not resuming:
                if source.get('language'):
                    from source_language import apply
                    apply(cfg,source['language']);cfg['sourceAudioStream']=source.get('stream')
                cfg.update(self.tools());cfg['storage']=str(self.root)
                if p.get('reanalyze'):cfg.update(forceRetranslate=True,rebuildDialogue=True,analysisRerunToken=uuid.uuid4().hex)
                if self.platform!='win32':
                    selected=read(self.root/'model-selections.json',{})
                    for role,key in [('text','model'),('visual','visualModel'),('asr','asrModel'),('speech','speechModel'),('referenceSpeech','referenceSpeechModel'),('drama3','drama3Model'),('cosyvoice3','cosyModel')]:
                        if selected.get(role):cfg.setdefault(key,selected[role])
                    if not cfg.get('model'):
                        # The platform adapter performs model availability
                        # checks; an absent selection must never become a
                        # misleading TTS failure deep inside translation.
                        cfg['model']='mlx:qwen3.5-4b:4bit'
                if self.store.mode=='basic':cfg.update(roleAnalysisMode='audio',visualRoleAnalysisEnabled=False,selectedEngines=[cfg['ttsBackend']],defaultAudioEngine=cfg['ttsBackend'])
                if cfg.get('productionMode') in ('fast','normal'):
                    from fast_mode import configure
                    configure(cfg)
                write(request,cfg)
            return self.task('batch',request,row)
        if op=='retry-review':
            row=self.row(p.get('id'))
            if any(r.get('status')=='running' for r in self.store.queue):raise ValueError('Pause processing before retrying review.')
            from review_retry import submission
            draft=submission(self.root,self.review_path(row),self.dispatch('snapshot',dict(id=row['id'])),p.get('mode','pending'),self.draft(row))
            requests=self.root/'requests';requests.mkdir(exist_ok=True)
            path=requests/('review-retry-'+draft['id']+'.json');write(path,draft)
            cfg=dict(draft['settings'],storage=str(self.root),submission=str(path),**self.tools())
            request=requests/('review-retry-config-'+draft['id']+'.json');write(request,cfg)
            return self.task('render-project',request,row)
        if op=='update-recording-plan':
            row=self.row(p.get('id'))
            if any(x.get('status')=='running' for x in self.store.queue):raise ValueError('Pause before preparing a recording update.')
            from update_plan import build
            from editing_tools import impact
            if p.get('impactToken')!=impact(read(self.review_path(row),{}),p.get('draft') or self.draft(row),p)['token']:raise ValueError('Preview the recording changes before continuing.')
            draft=copy.deepcopy(p.get('draft') or self.draft(row));self.dispatch('save-draft',dict(id=row['id'],draft=draft))
            return build(self.review_path(row),draft,p.get('operation'),p.get('engine'),p.get('language'),p.get('replaced'))
        if op=='render':
            row=self.row(p.get('id'));draft=copy.deepcopy(p.get('draft') or self.draft(row));self.dispatch('save-draft',dict(id=row['id'],draft=draft))
            draft['id']=uuid.uuid4().hex;draft['created']=time.time()
            preview=bool(p.get('segment'))
            if preview:
                if p['segment'] not in {r['id'] for r in draft['segments']}:raise ValueError('Unknown dialogue.')
                draft.update(previewSegment=p['segment'],previewEngine=p.get('engine') or self.store.settings['ttsBackend'],previewLanguage=p.get('language','yue'))
            request_dir=self.root/'requests';request_dir.mkdir(exist_ok=True)
            submission=request_dir/('studio-edit-'+uuid.uuid4().hex+'.json');write(submission,draft)
            config=dict(draft['settings'],storage=str(self.root),submission=str(submission),**self.tools())
            request=request_dir/('studio-render-'+uuid.uuid4().hex+'.json');write(request,config)
            return self.task('render-project',request,row,preview)
        if op=='record-event':
            row=self.row(p['id']);event=p['event']
            from workflow_log import record
            try:record(self.root,row,event,self.store.language)
            except (OSError,ValueError,TypeError) as error:row['workflowLogWarning']=str(error)[:300]
            if row.get('previewAttempt'):
                if event.get('job'):row['previewJob']=event['job']
                if event.get('output'):row['previewOutput']=event['output']
                self.store.event(row,{k:v for k,v in event.items() if k not in ('job','output','review','journey','progress','partial')})
            else:self.store.event(row,event)
            return {}
        if op=='finish':
            row=self.row(p['id']);preview=row.pop('previewAttempt',False)
            from diagnostics import finish
            try:
                finish(self.root,row,p['code'],p.get('paused',False),p.get('stderr',''),success_without_movie=preview)
            except (OSError,ValueError,TypeError,KeyError) as error:
                # A missing attempt folder must not leave a dead child locking
                # the queue or model management indefinitely.
                row['diagnosticsWarning']=str(error)[:500]
            if preview:row['status']=row.pop('previousStatus','complete' if row.get('output') else 'attention')
            else:self.store.finish(row,p['code'],p.get('paused',False),finalize_diagnostics=False)
            self.store.save()
            try:
                from conversion_details import finish as conversion_finish
                conversion_finish(self.root,row)
            except (OSError,ValueError,TypeError,KeyError) as error:
                row['conversionDetailsWarning']=str(error)[:500];self.store.save()
            return self.state()
        if op=='media-subtitles':
            from playback_subtitles import read as movie_subtitles
            return movie_subtitles(self.root,self.row(p.get('id')),self.tools(),p.get('choice','auto'),bool(p.get('output')))
        if op in ('media','media-status','media-thumbnail'):
            row=self.row(p.get('id'));source=Path((row.get('output') if p.get('output') else row['video']) or '').resolve()
            if not source.is_file():raise ValueError('The selected media file is missing.')
            import studio_preview
            if op=='media-thumbnail':return studio_preview.thumbnail(self.root,source,self.tools(),p.get('seconds',0))
            if op=='media-status':return studio_preview.status(self.root,source,p.get('compatible',False),p.get('audioStream'))
            return studio_preview.prepare(self.root,source,self.tools(),self.platform,p.get('compatible',False),p.get('audioStream'))
        if op=='project-cache-status':
            from project_cache import cleanup_status
            return cleanup_status(self.root,p.get('operationID'))
        if op in ('project-cache-plan','clear-project-cache'):
            if any(row.get('status')=='running' for row in self.store.queue):raise ValueError('Pause processing before clearing cache.')
            from project_cache import plan,tracked_execute
            return plan(self.root,self.store.queue,self.store.settings) if op=='project-cache-plan' else tracked_execute(self.root,self.store.queue,p.get('token'),p.get('orphanIDs',[]),self.store.settings,p.get('operationID'))
        if op=='models':return self.model_inventory()
        if op in ('model-removal-plan','remove-model'):
            if any(r.get('status')=='running' for r in self.store.queue):raise ValueError('Pause processing before removing a model.')
            from model_maintenance import removal_plan,remove_model
            function=removal_plan if op=='model-removal-plan' else remove_model
            return function(self.root,p['id'],self.platform,self.selected_model_ids())
        if op=='remove-retired-model':
            if any(r.get('status')=='running' for r in self.store.queue):raise ValueError('Pause processing before removing a model.')
            from model_maintenance import remove_retired
            return remove_retired(self.root,p['id'],self.platform)
        if op=='finish-current':
            row=self.row(p.get('id'))
            if row.get('status')!='running':raise ValueError('No conversion is running for this video.')
            job=self.review_path(row).parent
            tracks=read(job/'track-progress.json',{}).get('tracks',[])
            active=[t for t in tracks if t.get('state')=='running' and t.get('token')]
            if not active:raise ValueError('There is no active voice track to finish.')
            for track in active:
                folder=Path(track['folder']).resolve()
                if not folder.is_relative_to((job/'tracks').resolve()):raise ValueError('Invalid active track folder.')
                write(folder/'finish-with-current.json',dict(token=track['token'],requestedAt=time.time(),retainRecordings=True,qualityCertified=False))
            return dict(status='finishing-saved-recordings',tracks=len(active))
        if op=='model-choices':
            if self.platform=='win32':
                from native_setup import catalog
                rows=catalog()
                rows=[r for r in rows if r.get('nativeFormat')]
            else:
                from model_catalog import catalog
                rows=catalog()
                rows=[r for r in rows if r.get('engine') not in ('ollama',) and not str(r['id']).startswith('asr-native')]
            import re
            from engine_policy import ACTIVE
            rows=[r for r in rows if r.get('category')!='text' or re.fullmatch(r'(?:mlx:qwen3\.5-(?:9b|35b-a3b):[^:]+|qwen3\.5:(?:9b|35b))',r['id'])]
            return [{k:r.get(k) for k in ('id','title','category','engine','bytes','estimatedMemoryGB','license')} for r in rows if not r.get('retired') and not r.get('licenseReviewRequired') and r.get('category') in ('text','voice','speech','asr') and (r.get('category')!='voice' or r.get('engine') in ACTIVE) and r.get('files') and r.get('bytes')]
        if op=='maintain-model':
            from model_maintenance import model
            ident=p.get('id');mode=p.get('mode','repair')
            if mode not in ('repair','redownload'):raise ValueError('Unknown model maintenance operation.')
            row,folder=model(self.root,ident,self.platform)
            if row.get('retired'):raise ValueError('This model has been retired. Remove it in model management and choose a supported preset.')
            # Repair/download is storage-only. Hardware eligibility is checked
            # separately before selecting the model for inference.
            if any(r.get('status')=='running' for r in self.store.queue):raise ValueError('Pause conversion before repairing models.')
            program=Path(sys.executable)
            return dict(program=str(program),args=[str(self.shared/'model_maintenance.py'),'--root',str(self.root),'--id',ident,'--mode',mode,'--platform',self.platform],action='model-maintenance',modelID=ident,root=str(self.root))
        if op=='maintain-models':
            from model_maintenance import model
            ids=p.get('ids')
            if not isinstance(ids,list) or not ids or len(ids)>32 or any(not isinstance(ident,str) for ident in ids) or len(set(ids))!=len(ids):
                raise ValueError('Select between 1 and 32 different voice models.')
            if any(r.get('status')=='running' for r in self.store.queue):
                raise ValueError('Pause conversion before downloading models.')
            for ident in ids:
                row,_=model(self.root,ident,self.platform)
                if row.get('category')!='voice' or row.get('retired') or row.get('licenseReviewRequired'):
                    raise ValueError('This voice model is unavailable for download: '+ident)
            return dict(program=str(Path(sys.executable)),args=[str(self.shared/'model_maintenance.py'),'--root',str(self.root),'--ids-json',json.dumps(ids),'--mode','repair','--platform',self.platform],action='model-maintenance',modelIDs=ids,root=str(self.root))
        if op=='setup':
            engine=p.get('engine') or self.store.settings['ttsBackend']
            requested=p.get('models',self.store.settings.get('deploymentModels',{}))
            if engine=='wsyue' and any(l!='yue' for l in self.store.settings.get('dubLanguages',[])):raise ValueError('WenetSpeech-Yue supports Cantonese only. Choose another engine for English or bilingual dubbing.')
            drama_backend=p.get('dramaBackend',self.store.settings.get('dramaBackend','auto'))
            plan=self.dispatch('plan',dict(engine=engine,models=requested,dramaBackend=drama_backend,backend=p.get('backend','auto')))
            from model_switch import begin
            token=begin(self.root,plan,requested,p.get('removeOld',False),self.store.mode=='expert')
            if self.platform=='win32':
                python=self.root/'runtimes/ui/Scripts/python.exe'
                return dict(program=str(python),args=[str(WINDOWS/'native_setup.py'),'--engine',engine,'--models-json',json.dumps(requested),'--drama-backend',drama_backend,'--backend',p.get('backend',plan.get('setupBackend','auto'))],action='setup',root=str(self.root),modelSwitchToken=token)
            return dict(program=str(self.helper),args=['--studio-setup',engine,json.dumps(requested)],action='setup',root=str(self.root),modelSwitchToken=token)
        if op=='finish-model-switch':
            from model_switch import finish
            if self.platform=='win32':
                from native_setup import catalog,folder
            else:
                from model_catalog import catalog,folder
            result=finish(self.root,p['token'],catalog(),folder,bool(p.get('success')))
            if result['status']=='complete':
                roles=result['plan']['roles'];engine=result['plan']['engine']
                engines=list(dict.fromkeys([engine]+self.store.settings.get('selectedEngines',[]))) if self.store.mode=='expert' else [engine]
                settings=dict(ttsBackend=engine,selectedEngines=engines,defaultAudioEngine=engine,deploymentModels=result['requested'])
                for role,key in [('text','model'),('asr','asrModel'),('speech','speechModel'),('referenceSpeech','referenceSpeechModel')]:
                    if roles.get(role):settings[key]=roles[role]
                if roles.get('voice'):settings[{'drama3':'drama3Model','cosyvoice3':'cosyModel','voxcpm2':'voxcpmModel','wsyue':'wsyueModel'}.get(engine,'voiceModel')]=roles['voice']
                if self.platform=='win32':
                    receipt=read(self.root/'native-ready.json',{})
                    settings.update(model=receipt.get('textModel',settings.get('model')),dramaBackend=receipt.get('dramaBackend',result['plan'].get('dramaBackend','auto')))
                self.store.settings.update(settings);self.store.save()
            return result
        if op=='plan':
            engine=p.get('engine') or self.store.settings['ttsBackend'];requested=p.get('models',self.store.settings.get('deploymentModels',{}))
            from model_switch import ROLES
            if not isinstance(requested,dict) or set(requested)-ROLES or any(not isinstance(v,str) for v in requested.values()):raise ValueError('Unknown model choice.')
            if self.platform=='win32':
                from native_setup import plan
                return plan(engine,requested=requested,backend=p.get('backend','auto'),drama_backend=p.get('dramaBackend',self.store.settings.get('dramaBackend','auto')))
            response=subprocess.check_output([str(self.helper),'--studio-plan',engine,json.dumps(requested)],timeout=60)
            return json.loads(response.decode().strip().splitlines()[-1])
        if op=='log-sources':return self.log_sources()
        if op=='export-logs':return self.debug_report()
        if op=='logs':
            sources=self.log_sources()
            source=next((r for r in sources if r['id']==p.get('source')),None)
            if p.get('source') and source is None:raise ValueError('Unknown log source.')
            return self.log_text(source or sources[0],262144) if sources else ''
        if op=='licenses':
            rows=read(self.shared/'license-inventory.json',[])
            if self.platform=='win32':
                from native_licenses import inventory
                rows+=inventory(self.root)
            else:
                runtime_rows=read(self.root/'runtime-license-inventory.json',[])
                if isinstance(runtime_rows,list):rows.extend(r for r in runtime_rows if isinstance(r,dict))
            for row in rows:
                texts=[n.get('text','') for n in row.get('notices',[]) if n.get('text')];seen=set()
                base=self.root if row.get('fileRoot')=='applicationSupport' else self.shared
                for name in row.get('files',[]):
                    path=(base/name).resolve()
                    if path.is_relative_to(base) and path.is_file() and path.stat().st_size<5000000:
                        text=path.read_text(errors='replace');digest=hashlib.sha256(text.encode()).hexdigest()
                        if digest not in seen:texts.append(text);seen.add(digest)
                row['text']='\n\n'.join(texts)
            return rows
        raise ValueError('Unsupported desktop operation: '+str(op))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--shared',required=True);parser.add_argument('--helper');args=parser.parse_args()
    try:
        packet=json.load(sys.stdin);studio=Studio(args.root,args.shared,helper=args.helper)
        if packet.get('recoverOrphans') is True:studio.recover_orphans()
        result=studio.dispatch(packet['op'],packet.get('params',{}))
        print(json.dumps(dict(ok=True,result=result),ensure_ascii=False))
    except Exception as error:
        print(json.dumps(dict(ok=False,error=str(error)),ensure_ascii=False));return 1
    return 0

if __name__=='__main__':sys.exit(main())
