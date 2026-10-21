"""Immutable editorial submissions, versioned renders and linked non-destructive cuts.

The UI owns editor-draft.json. Workers only read submitted snapshots and write their
own version directory. Existing conversion jobs are never modified by this module.
"""
import copy
import json
import math
from pathlib import Path
import shutil
import uuid


def number(value, lo, hi, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(label + '無效。')
    return float(value)


def materialize(review, draft):
    duration = float(review['config']['duration'])
    originals = review['cues']
    result = []
    ids = set()
    for row in draft['segments']:
        if row['id'] in ids: raise ValueError('片段 ID 重複。')
        ids.add(row['id'])
        indices = row.get('sources', [row.get('sourceIndex')])
        if (not indices and not row.get('manual')) or any(type(i) is not int or not 0 <= i < len(originals) for i in indices):
            raise ValueError('片段原稿關聯無效。')
        cue = copy.deepcopy(originals[indices[0]]) if indices else dict(text=row.get('original',''),japanese=row.get('original',''),timingSource='manual',manual=True)
        a = number(row['start'], 0, duration, '配音開始時間')
        b = number(row['end'], 0, duration, '配音結束時間')
        if b <= a: raise ValueError('片段結束必須遲過開始。')
        ca = number(row.get('captionStart', a), 0, duration, '字幕開始時間')
        cb = number(row.get('captionEnd', b), 0, duration, '字幕結束時間')
        if cb <= ca: raise ValueError('字幕結束必須遲過開始。')
        text = row['text']
        languages=draft.get('settings',{}).get('dubLanguages',draft.get('dubLanguages') or review['config'].get('dubLanguages',['yue']))
        english_only=languages==['en'] and isinstance(row.get('english'),str) and bool(row['english'].strip())
        missing_script=isinstance(text,str) and not text.strip() and not english_only
        existing_empty=bool(indices) and not row.get('manual') and all(
            not str(originals[i].get('cantonese') or '').strip() and
            (languages!=['en'] or not str(originals[i].get('english') or '').strip()) for i in indices)
        if not isinstance(text,str) or (missing_script and row.get('enabled',True) and not existing_empty and not draft.get('settings',{}).get('subtitlesOnly')):
            raise ValueError('所選語言嘅台詞不可空白。')
        cue.update(start=a, end=b, text=row.get('original',cue['text']),japanese=row.get('original',cue.get('japanese',cue['text'])),english=row.get('english') or cue.get('english',''), originalEvidence=cue['text'], cantonese=text, speakerId=row.get('speakerId', ''),
                   enabled=row.get('enabled', True), editorID=row['id'], editorSources=indices,
                   subtitleStart=ca, subtitleEnd=cb, captionText=row.get('captionText') or text)
        changed = (len(indices) != 1 or text != originals[indices[0]].get('cantonese') or
                   a != originals[indices[0]]['start'] or b != originals[indices[0]]['end'])
        if changed:
            for key in ('deliveryPlan','deliveryParts','speechRegions','acousticParts','recognitionParts','sourceParts','nonlexicalTail'):
                cue.pop(key, None)
            cue.update(speechStart=a, speechEnd=b, deliveryEnd=b)
        cue['_seed'] = int(number(row.get('take', 42), 0, 2147483647, '配音版本'))
        if row.get('preserveOriginalSpeech') is not None:
            cue.update(preserveOriginalSpeech=bool(row['preserveOriginalSpeech']),overlapReviewed=True)
        if missing_script and row.get('enabled',True):
            cue.update(missingScript=True,originalSpeechReason='missing-script',preserveOriginalSpeech=False)
        elif not missing_script:
            cue.pop('missingScript',None)
            if cue.get('originalSpeechReason')=='missing-script':
                cue.pop('originalSpeechReason',None)
                cue['preserveOriginalSpeech']=bool(row.get('preserveOriginalSpeech',False))
        # The submitted snapshot owns take selection. A rendered review can
        # contain an old editorAudio field; never inherit it after reassignment.
        for key in ('editorAudio','editorAudioBackend','editorAudioLanguage','userAcceptedRecording'):cue.pop(key,None)
        if row.get('audioTake'):
            cue['editorAudio']=row['audioTake']
            if row.get('audioAcceptedHistoryID'):
                cue['userAcceptedRecording']=row['audioAcceptedHistoryID']
        cue['editorDecisions']=copy.deepcopy(row.get('reviewDecisions',{}))
        cue['editorRate'] = number(row.get('rate', 1), .5, 2, '語速')
        cue['editorTrimStart'] = number(row.get('trimStart', 0), 0, 3600, '聲音裁切')
        cue['editorTrimEnd'] = number(row.get('trimEnd', 0), 0, 3600, '聲音裁切')
        result.append(cue)
    if not result or not any(c.get('enabled', True) for c in result): raise ValueError('請保留至少一句台詞。')
    result.sort(key=lambda c: (c['start'], c['end']))
    return result


def spans_for(draft, duration):
    spans = draft.get('clips') or [dict(start=0, end=duration, enabled=True, ripple=True)]
    result = []; cursor = 0
    for clip in spans:
        a = number(clip['start'], 0, duration, '剪輯開始')
        b = number(clip['end'], 0, duration, '剪輯結束')
        if b <= a: raise ValueError('剪輯片段長度必須大於零。')
        if not clip.get('enabled', True) and clip.get('ripple', True): continue
        result.append(dict(start=a, end=b, outputStart=cursor, blank=not clip.get('enabled', True)))
        cursor += b-a
    if not result: raise ValueError('請保留至少一個影片片段。')
    return result


def map_captions(cues, spans):
    result = []
    for span in spans:
        if span['blank']: continue
        for cue in cues:
            a, b = max(cue['start'], span['start']), min(cue['end'], span['end'])
            if b > a:
                result.append(dict(cue, start=span['outputStart']+a-span['start'], end=span['outputStart']+b-span['start']))
    return sorted(result, key=lambda c:c['start'])


def seed_cache(source, target):
    """Copy only content-addressed raw takes; never reuse stale mixed audio/reports."""
    target.mkdir(parents=True, exist_ok=True)
    for prefix in ('cosyvoice3-', 'gpt-sovits-v2-', 'gpt-sovits-v3-', 'gpt-sovits-', 'qwen-tts-', 'voxcpm2-', 'wsyue-', 'drama3-'):
        for path in source.rglob(prefix+'*.wav'):
            if path.name.endswith(('.rejected.wav','.raw.wav','.rejected-raw.wav','.partial.wav')): continue
            dest = target/path.name
            if not dest.exists(): shutil.copy2(path, dest)
    # Evidence keys include audio bytes, exact expected text and model/policy
    # identity. Moving an unchanged take to a new track must not re-run ASR.
    def read(path):
        try:
            value=json.loads(path.read_text())
            return value if isinstance(value,dict) else {}
        except (OSError,ValueError):return {}
    original=source/'speech-check-cache.json';destination=target/'speech-check-cache.json'
    if original.is_file():
        merged=read(original);merged.update(read(destination))
        if merged:
            temp=destination.with_suffix('.merge.tmp');temp.write_text(json.dumps(merged,ensure_ascii=False));temp.replace(destination)
    # Only copy completed content-addressed decisions. Other checkpoint paths
    # can reference stale request files and must not be cloned as proof.
    for decision in (source/'cantonese-review').glob('*/decision.json'):
        folder=target/'cantonese-review'/decision.parent.name
        if (folder/'decision.json').exists():continue
        folder.mkdir(parents=True,exist_ok=True)
        shutil.copy2(decision,folder/'decision.json')


def apply_cuts(w, cfg, folder, output, draft):
    meta = json.loads(w.run([cfg['ffprobe'],'-v','error','-show_streams','-show_format','-of','json',output]))
    duration = float(meta['format']['duration'])
    draft=copy.deepcopy(draft)
    for clip in draft.get('clips',[]):
        if clip['end']==cfg.get('duration') and duration>clip['end']:clip['end']=duration
    spans = spans_for(draft, duration)
    if len(spans)==1 and spans[0]['start']==0 and abs(spans[0]['end']-duration)<.06 and not spans[0]['blank']:
        return output, spans
    audios = [s for s in meta['streams'] if s['codec_type']=='audio']
    subtitles = [s for s in meta['streams'] if s['codec_type']=='subtitle']
    filters=[]; inputs=[]
    for i, span in enumerate(spans):
        a,b=span['start'],span['end']
        vf=f'[0:v:0]trim=start={a}:end={b},setpts=PTS-STARTPTS'
        if span['blank']: vf+=',drawbox=color=black:t=fill'
        filters.append(vf+f'[v{i}]')
        inputs.append(f'[v{i}]')
        for j in range(len(audios)):
            af=f'[0:a:{j}]atrim=start={a}:end={b},asetpts=PTS-STARTPTS,apad,atrim=duration={b-a}'
            if span['blank']:af+=',volume=0'
            filters.append(af+f'[a{i}_{j}]'); inputs.append(f'[a{i}_{j}]')
    filters.append(''.join(inputs)+f'concat=n={len(spans)}:v=1:a={len(audios)}[v]'+''.join(f'[a{j}]' for j in range(len(audios))))
    cmd=[cfg['ffmpeg'],'-v','error','-y','-i',output]
    mapped=[]
    for i, stream in enumerate(subtitles):
        raw=w.run([cfg['ffmpeg'],'-v','error','-i',output,'-map',f'0:s:{i}','-f','srt','-']).decode()
        cues=map_captions(w.parse_srt(raw),spans)
        path=folder/f'edited-{i}.srt'; w.save_srt(path,cues); mapped.append(path)
        # An empty subtitle file is not a valid FFmpeg input. Omit empty tracks.
        if cues:cmd+=['-i',path]
    cmd+=['-filter_complex',';'.join(filters),'-map','[v]']
    for j, stream in enumerate(audios):
        cmd+=['-map',f'[a{j}]']
        for k,v in stream.get('tags',{}).items():
            if k in ('language','title','handler_name'):cmd += [f'-metadata:s:a:{j}',f'{k}={v}']
        cmd += [f'-disposition:a:{j}', 'default' if stream.get('disposition',{}).get('default') else '0']
    next_input=1; output_index=0
    for path,stream in zip(mapped,subtitles):
        if not w.parse_srt(path.read_text()):continue
        cmd+=['-map',f'{next_input}:s:0'];next_input+=1
        for k,v in stream.get('tags',{}).items():
            if k in ('language','title','handler_name'):cmd += [f'-metadata:s:s:{output_index}',f'{k}={v}']
        cmd += [f'-disposition:s:{output_index}', 'default' if stream.get('disposition',{}).get('default') else '0'];output_index+=1
    cmd+=['-map_metadata','0','-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-c:s','mov_text','-movflags','+faststart']
    from video_acceleration import encode
    temp=folder/'cut.partial.mp4';encode(w.run,cmd+[temp],cfg,w.emit)
    w.run([cfg['ffmpeg'],'-v','error','-i',temp,'-map','0:v','-map','0:a?','-f','null','-'])
    check=json.loads(w.run([cfg['ffprobe'],'-v','error','-show_streams','-show_format','-of','json',temp]))
    expected=sum(s['end']-s['start'] for s in spans)
    if abs(float(check['format']['duration'])-expected)>.15 or sum(s['codec_type']=='audio' for s in check['streams'])!=len(audios):
        raise ValueError('剪輯輸出時間或音軌數量不符合，保留舊成品。')
    temp.replace(output)
    return output, spans


def render(w, request):
    submission=Path(request['submission']).resolve()
    draft=json.loads(submission.read_text())
    if draft.get('automaticReviewRetry'):
        from review_retry import render as retry_review
        return retry_review(w,request,draft)
    root=Path(draft['review']).resolve().parent
    source_review=json.loads((root/('editor-base.json' if (root/'editor-base.json').exists() else 'review.json')).read_text())
    folder=root/'versions'/draft['id']
    if folder.parent != root/'versions' or not draft['id'].replace('-','').isalnum():raise ValueError('版本 ID 無效。')
    folder.mkdir(parents=True,exist_ok=True)
    state=folder/'version.json'
    record=dict(id=draft['id'],status='running',created=draft.get('created',''),submission=str(submission),review=str(root/'review.json'))
    w.atomic_json(state,record)
    original_emit=w.emit
    try:
        cues=materialize(source_review,draft)
        if draft.get('settings',{}).get('subtitlesOnly'):
            cfg=dict(source_review['config'],**draft['settings'])
            cfg.update({k:request[k] for k in ('port','ffmpeg','ffprobe','executable') if k in request})
            from script_revision import save
            generated,missing,subtitles=save(w,cfg,folder,draft,cues)
            w.atomic_json(folder/'review.json',dict(source_review,config=cfg,cues=generated,status='pending'))
            record.update(status='script-partial' if missing else 'script-ready',scriptLanguages=cfg['scriptLanguages'],subtitleDraft=str(folder/'subtitle-draft.json'),subtitles=subtitles,missing=missing)
            w.atomic_json(state,record)
            original_emit('字幕草稿完成','新字幕已保存；請比較並套用草稿，再生成配音。' if not missing else '部分字幕未完成；已保存可用草稿，請覆核缺少台詞。',1,job=str(folder))
            return
        for cue in cues:
            if draft.get('settings',{}).get('audioRerunToken') or draft.get('settings',{}).get('voiceSamplesOnly'):
                for key in ('editorAudio','editorAudioBackend','editorAudioLanguage','userAcceptedRecording'):cue.pop(key,None)
            if cue.get('editorAudio'):
                audio=Path(cue['editorAudio']).resolve()
                if not audio.is_relative_to(root) or not audio.is_file() or audio.suffix!='.wav':raise ValueError('所選聲音 take 已移走或不屬於呢個工作。')
                if cue.get('userAcceptedRecording'):
                    acceptance=json.loads((audio.parent/'acceptance.json').read_text())
                    expected=cue.get('english','') if acceptance['language']=='en' else cue.get('cantonese','')
                    if acceptance['text']!=expected:
                        cue.pop('editorAudio',None);cue.pop('userAcceptedRecording',None)
                        continue
                    import hashlib
                    if hashlib.sha256(audio.read_bytes()).hexdigest()!=acceptance['audioSHA256']:
                        raise ValueError('用戶採用嘅錄音已改動；原歷史版本仍保留，請重新選擇。')
                for parent in audio.parents:
                    if not parent.is_relative_to(root):break
                    provenance=parent/'review.json'
                    if provenance.is_file():
                        provenance_config=json.loads(provenance.read_text()).get('config',{})
                        cue['editorAudioBackend']=provenance_config.get('ttsBackend')
                        cue['editorAudioLanguage']=provenance_config.get('targetLanguage','yue')
                        cue['editorAudioVersion']=provenance_config.get('gsvVersion','v2')
                        break
        cfg=dict(source_review['config'],**draft.get('settings',{}))
        from fast_mode import configure
        configure(cfg)
        from engine_policy import migrate
        migrate(cfg)
        from studio_core import freeze
        freeze(cfg)
        if request.get('aiDecisionUnavailable'):cfg['aiDecisionUnavailable']=True
        if request.get('aiRepairModel'):cfg['aiRepairModel']=request['aiRepairModel']
        cfg.update(scriptLocked=True,autoApprove=False,exportFolder='',editorRender=True,_editorSourceRoot=str(root))
        if cfg.get('ttsBackend','').startswith('gpt-sovits'):cfg['gsvVersion']=__import__('gsv_versions').version(cfg)
        from cantonese_pronunciation import rules as pronunciation_rules
        pronunciation_rules(cfg.get('cantonesePronunciationText',''))
        if cfg.get('audioRerunToken'):
            for cue in cues:
                for key in ('editorAudio','editorAudioBackend','editorAudioLanguage'):cue.pop(key,None)
        cfg.update({k:request[k] for k in ('ffmpeg','ffprobe','executable','port') if k in request})
        if not cfg.get('voiceSamplesOnly') and not cfg.get('previewScriptOnly') and not (draft.get('previewSegment') and cfg.get('previewNativeAudio')) and not Path(cfg['video']).is_file():raise ValueError('原片遺失，請重新連結原片。')
        cfg['editorCache']=str(root/'editor-cache')
        cfg['_referenceCueFile']=str(folder/'cues.json')
        seed_cache(root,Path(cfg['editorCache']))
        number(cfg.get('captionBottom',.045),0,.8,'字幕位置')
        number(cfg.get('captionSize',.043),.015,.12,'字幕大小')
        for name in ('dual-asr-cues.json','japanese-analysis.json','nonverbal-classification-v2.json','source-cues.json','subtitle-cues.json','subtitle-context.json','source-coverage.json'):
            if (root/name).exists():shutil.copy2(root/name,folder/name)
        def relay(stage,message,progress=None,**extra):
            original_emit(stage,message,progress,job=str(folder),**{k:extra[k] for k in ('partial','autoRepair','workID','workCompleted','workTotal') if k in extra})
        w.emit=relay
        if cfg.get('reanalyzeRoles'):
            if draft.get('previewSegment') or cfg.get('voiceSamplesOnly'):
                raise ValueError('人物重新分析只適用於整片新版匯出。')
            from role_reanalysis import prepare as prepare_roles
            # editor-base can predate automatic role recovery. Use the current
            # source role plan to distinguish automatic recovery from manual edits.
            identity_source=json.loads((root/'review.json').read_text())
            cues=prepare_roles(w,cfg,folder,cues,identity_source)
        if cfg.get('fillMissingVoiceScripts'):
            from script_gap_recovery import recover as fill_missing
            added=fill_missing(w,cfg,folder,cues)
            missing=[i+1 for i,c in enumerate(cues) if c.get('enabled',True) and not c.get('cantonese','').strip()]
            w.atomic_json(folder/'filled-script-gaps.json',dict(rows=added,missing=missing,method='Caption-first recovery; existing scripts and Japanese clocks preserved'))
        review=dict(source_review,config=cfg,cues=cues,status='approved')
        w.atomic_json(folder/'cues.json',cues);w.atomic_json(folder/'review.json',review)
        if cfg.get('voiceSamplesOnly'):
            from voice_samples import generate
            if cfg.get('singleCueComparison'):
                from voice_samples import compare
                result=compare(w,cfg,folder,cues,draft.get('previewSegment'))
            else:result=generate(w,cfg,folder,cues)
            record.update(status='voice-samples',samples=str(folder/'voice-samples.json'),sampleCount=len(result['rows']),errors=result['errors'])
            w.atomic_json(state,record)
            original_emit('試音組完成','試音已保存；請覆聽字詞、聲調及角色聲線，未替換成品。',1,job=str(folder))
            return
        if draft.get('previewSegment'):
            if draft.get('previewEngine')=='gpt-sovits-v3':raise ValueError('GPT V3 已停用；請選擇 V2 Pro Plus 或 V4 重新試音。')
            if cfg.get('previewNativeAudio'):
                from natural_voices import prepare_cast
                prepare_cast(cfg,folder,cues,w.run)
            chosen=[c for c in cues if c['editorID']==draft['previewSegment'] and c.get('enabled',True)]
            if len(chosen)!=1:raise ValueError('請選擇一個啟用嘅配音片段。')
            cfg['continueOnError']=False
            cfg.update(previewLooseTiming=True,autoValidate=False,ttsBackend=draft.get('previewEngine') or cfg.get('ttsBackend'))
            import dubbing,dub_languages
            cfg['targetLanguage']=draft.get('previewLanguage','yue')
            if cfg['ttsBackend'].startswith('gpt-sovits'):cfg['gsvVersion']=__import__('gsv_versions').version(cfg)
            if cfg.get('auditionSeed') is not None:chosen[0]['_seed']=int(number(cfg['auditionSeed'],0,2147483647,'試音種子'))
            if cfg['targetLanguage']=='en':
                dub_languages.english_script(w,cfg,folder,chosen)
            chosen=dub_languages.track_cues(chosen,cfg['targetLanguage'])
            w.atomic_json(folder/'review.json',dict(review,config=cfg,cues=chosen))
            if cfg.get('previewScriptOnly'):
                record.update(status='preview-script',language=cfg['targetLanguage'],segment=draft.get('previewSegment'))
                w.atomic_json(state,record)
                original_emit('英文稿完成','所選對白英文稿已保存，可修改後試音。',1,job=str(folder))
                return
            if cfg.get('experimentalProsody'):
                from prosody_experiment import generate
                result=generate(w,cfg,folder,chosen[0])
                record.update(status='prosody-experiment',engine='gpt-sovits',language='yue',segment=draft['previewSegment'],experiment=str(folder/'prosody-experiment.json'),error=result.get('error',''))
                w.atomic_json(state,record)
                original_emit('表演實驗已保存',result.get('error') or '粵語基準同日文表演版本已保存；請逐句覆聽，未替換成品。',1,job=str(folder))
                return
            if cfg.get('previewNativeAudio'):
                from audio_audition import generate
                record.update(engine=cfg['ttsBackend'],language=cfg['targetLanguage'],segment=draft.get('previewSegment'))
                from audio_audition import AuditionRejected
                try:preview,length=generate(w,cfg,folder,chosen[0])
                except AuditionRejected as error:
                    record.update(status='audition-review',output=str(error.audio),timing=str(folder/'timing.json'),report=str(folder/'report.json'),error=str(error))
                    w.atomic_json(state,record)
                    original_emit('試音待覆核',str(error)+'；音檔已保存，可在字幕面板試聽。',1,job=str(folder))
                    return
                record.update(engine=cfg['ttsBackend'],language=cfg['targetLanguage'],segment=draft.get('previewSegment'),status='preview',timing=str(folder/'timing.json'),output=str(preview),report=str(folder/'report.json'))
                w.atomic_json(state,record)
                original_emit('試音完成','新錄音已保存，請覆聽後決定是否採用。',1,job=str(folder))
                return
            audio,warnings=dubbing.synthesize(cfg,folder,chosen,w.run,relay)
            timing=json.loads((folder/'timing.json').read_text())[0]
            preview=folder/'preview.mp4'
            length=float(timing['renderedSeconds'])
            subtitle=folder/'preview.srt'
            w.save_srt(subtitle,[dict(start=0,end=length,text=chosen[0].get('captionText',chosen[0]['cantonese']))])
            w.run([cfg['ffmpeg'],'-v','error','-y','-ss',str(cfg.get('startOffset',0)+chosen[0]['start']),'-i',cfg['video'],'-i',timing['renderedAudio'],'-i',subtitle,'-map','0:v:0','-map','1:a:0','-map','2:s:0','-vf',f'tpad=stop_mode=clone:stop_duration={length}','-t',str(length),'-c:v','libx264','-preset','veryfast','-c:a','aac','-c:s','mov_text',preview])
            w.run([cfg['ffmpeg'],'-v','error','-i',preview,'-f','null','-'])
            w.atomic_json(folder/'report.json',dict(duration=length,preview=True,sourceStart=chosen[0]['start']))
            record.update(engine=cfg['ttsBackend'],language=cfg['targetLanguage'],segment=draft.get('previewSegment'),status='preview',timing=str(folder/'timing.json'),output=str(preview),report=str(folder/'report.json'))
            w.atomic_json(state,record)
            original_emit('試音完成','片段試音已保存，可比較各個 take；未替換成品。',1,job=str(folder))
            return
        w.render_review(dict(review=str(folder/'review.json'),lockScript=True))
        report=json.loads((folder/'report.json').read_text())
        output=Path(report['output'])
        output,spans=apply_cuts(w,cfg,folder,output,draft)
        remap_reports(w,folder,spans)
        final_meta=json.loads(w.run([cfg['ffprobe'],'-v','error','-show_streams','-of','json',output]))
        if any(s['codec_type']=='subtitle' for s in final_meta['streams']):
            output.with_suffix('.srt').write_bytes(w.run([cfg['ffmpeg'],'-v','error','-i',output,'-map','0:s:0','-f','srt','-']))
        elif (folder/'cantonese.srt').exists():
            w.save_srt(output.with_suffix('.srt'),map_captions(w.parse_srt((folder/'cantonese.srt').read_text()),spans))
        report['userReviewChoices']=[dict(index=i+1,choices=c.get('editorDecisions')) for i,c in enumerate(cues) if c.get('editorDecisions')]
        if report['userReviewChoices']:report.update(qualityStatus='user-reviewed-with-explicit-choices',qualityCertified=False)
        from dialogue_delivery import incomplete
        quality_defects=False if __import__("fast_mode").enabled(cfg) else incomplete(report)
        report['qualityDefects']=bool(report.get('qualityDefects') or quality_defects)
        report.update(editSpans=spans,sourceReview=str(root/'review.json'),editorVersion=draft['id'],duration=sum(s['end']-s['start'] for s in spans))
        w.atomic_json(folder/'report.json',report)
        from multitrack import export_copy
        destination=export_copy(output,dict(cfg,exportFolder=draft.get('settings',{}).get('exportFolder',source_review['config'].get('exportFolder',''))),[(folder/'report.json','.report.json'),(folder/'validation.json','.validation.json'),(folder/'nonverbal-report.json','.nonverbal-report.json'),(output.with_suffix('.srt'),'.srt')])
        report['exportedOutput']=str(destination);w.atomic_json(folder/'report.json',report)
        ai_result=report.get('aiAutoFix')
        record.update(status='complete',output=str(destination),report=str(folder/'report.json'))
        w.atomic_json(state,record)
        from project_store import sync
        sync(cfg['storage'],root/'review.json',destination,record['status'])
        role_result=cfg.get('roleReanalysisResult') if cfg.get('reanalyzeRoles') else None
        if role_result:report['roleReanalysis']=role_result;w.atomic_json(folder/'report.json',report)
        if ai_result or role_result:
            from ai_result_repair import summary as ai_summary
            from role_reanalysis import summary_text as role_summary
            text=('人物分析：\n'+role_summary(role_result)+'\n\n' if role_result else '')+(ai_summary(ai_result) if ai_result else '')+f'\n配音音軌：{len(report.get("tracks", []))}；字幕軌：{len(report.get("subtitleTracks", []))}。\n成品：{destination}'
            (folder/'result-summary.txt').write_text(text)
            original_emit('結果摘要',text,1,job=str(folder),partial=False,autoRepair=True)
        if __import__('fast_mode').enabled(cfg):
            from fast_mode import warning
            original_emit('結果摘要',warning(cfg)+'\n成品：'+str(destination),1,job=str(folder),partial=False)
        original_emit('版本完成',('一般模式成品已保存；局部檢查紀錄及原錄音保留。' if cfg.get('productionMode')=='normal' else '高速模式成品已保存；品質未檢查。' if cfg.get('productionMode')=='fast' else '新版已保存；瑕疵已記入校對報告，舊成品保留。' if quality_defects else '新版已驗證並保存；舊成品保留。'),1,job=str(folder),output=str(destination),artifactRole='published',deliveryKind='complete',partial=False,autoRepair=bool(ai_result or role_result))
    except Exception as error:
        record.update(status='failed',error=str(error));w.atomic_json(state,record);raise
    finally:w.emit=original_emit


def remap_reports(w, folder, spans):
    validation=folder/'validation.json'
    if validation.exists():
        original=json.loads(validation.read_text());w.atomic_json(folder/'validation-source.json',original)
        result=copy.deepcopy(original);rows=[]
        review_path=folder/'review.json'
        cues=json.loads(review_path.read_text()).get('cues',[]) if review_path.exists() else []
        unmapped=[]
        flags=[k for k in original if k.endswith('ReviewIndices')]
        for key in flags:result[key]=[]
        for span in spans:
            if span['blank']:continue
            for row in original.get('rows',[]):
                audible=isinstance(row.get('audibleStart'),(int,float))
                cue_index=row.get('index',0)-1
                cue=cues[cue_index] if 0<=cue_index<len(cues) else {}
                start=row['audibleStart'] if audible else cue.get('start')
                end=row.get('audibleEnd',start+.01) if audible else cue.get('end')
                if start is None or end is None:
                    if row not in unmapped:unmapped.append(row)
                    continue
                a=max(start,span['start']);b=min(end,span['end'])
                if b<=a:continue
                index=len(rows)+1
                mapped=dict(row,index=index,sourceIndex=row['index'])
                prefix='audible' if audible else 'planned'
                mapped[prefix+'Start']=span['outputStart']+a-span['start'];mapped[prefix+'End']=span['outputStart']+b-span['start']
                rows.append(mapped)
                for key in flags:
                    if row['index'] in original[key]:result[key].append(index)
        result.update(rows=rows,unmappedIssues=unmapped,editSpans=spans,contentCheckScope='pre-edit-takes; final media decoded after linked cuts')
        w.atomic_json(validation,result)
    nonverbal=folder/'nonverbal-report.json'
    if nonverbal.exists():
        report=json.loads(nonverbal.read_text())
        for key in ('events','reviewEvents'):
            if key in report:report[key]=map_captions(report[key],spans)
        w.atomic_json(nonverbal,report)
