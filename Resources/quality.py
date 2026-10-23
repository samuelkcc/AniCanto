"""Deterministic export acceptance checks, run inside the standalone app."""
import json,math,wave
from pathlib import Path
import numpy as np
from acoustics import activity


def check_voice(job,cues,timing,continue_on_error=False):
    if len(cues)!=len(timing):raise ValueError('配音驗證失敗：台詞同音檔數量唔一致。')
    rows=[]
    with wave.open(str(Path(job)/'cantonese.wav')) as audio:
        sr=audio.getframerate()
        if audio.getnchannels()!=1 or audio.getsampwidth()!=2:raise ValueError('配音驗證失敗：聲道／格式無效。')
        cursor=0
        for cue,row in zip(cues,timing):
            if row.get('skipped'):
                rows.append(dict(index=row['index'],skipped=True,requiresTimingReview=True,speakerId=cue.get('speakerId'),text=cue['cantonese']))
                continue
            a,b=row['renderedStart'],row['renderedEnd']
            if not math.isfinite(a+b) or a<0 or b<=a:raise ValueError('配音驗證失敗：對白時間無效。')
            cursor=b;audio.setpos(min(audio.getnframes(),round(a*sr)))
            raw=audio.readframes(round((b-a)*sr))
            # Inspect each post-tempo take independently; another overlapping
            # character must never make a silent/missing take pass validation.
            if row.get('renderedAudio'):
                try:
                    with wave.open(row['renderedAudio']) as take:
                        if take.getnchannels()!=1 or take.getsampwidth()!=2 or take.getframerate()!=sr:raise ValueError('獨立配音格式無效。')
                        raw=take.readframes(take.getnframes())
                except (OSError,EOFError,wave.Error,ValueError):
                    if not continue_on_error:raise ValueError(f'配音驗證失敗：第 {row["index"]} 句音檔缺失或損壞。')
                    row.update(skipped=True,renderedSeconds=0,failureKind='invalid-take-file')
                    rows.append(dict(index=row['index'],skipped=True,requiresTimingReview=True,failureKind='invalid-take-file',speakerId=cue.get('speakerId'),text=cue['cantonese']))
                    continue
            x=np.frombuffer(raw,dtype=np.int16).astype(np.float32)/32768
            spans=activity(x,sr)
            if not spans:
                if not continue_on_error:raise ValueError(f'配音驗證失敗：第 {row["index"]} 句冇可聽見嘅人聲。')
                row.update(skipped=True,renderedSeconds=0,failureKind='no-audible-voice')
                rows.append(dict(index=row['index'],skipped=True,requiresTimingReview=True,failureKind='no-audible-voice',speakerId=cue.get('speakerId'),text=cue['cantonese']))
                continue
            start=a+spans[0][0];end=a+spans[-1][1]
            source_start=row.get('acousticStart')
            source_end=row.get('acousticEnd')
            rows.append(dict(index=row['index'],audibleStart=start,audibleEnd=end,
                sourceStart=source_start,sourceEnd=source_end,
                startError=None if source_start is None else start-source_start,
                endError=None if source_end is None else end-source_end,
                requiresTimingReview=bool(row.get('requiresTimingReview')) or
                    (source_start is not None and abs(start-source_start)>.12) or
                    (source_end is not None and abs(end-source_end)>.5),
                speakerId=cue.get('speakerId'),text=cue['cantonese']))
    return rows


def inspect_rendered_voice(cfg,job,cues,timing,emit):
    """Check the delivered PCM, including tempo changes and final take selection."""
    from speechcheck import inspect
    from dubbing import is_vocalization
    directory=Path(job)/'final-speech';directory.mkdir(exist_ok=True)
    selected=[];paths=[];indices=[]
    with wave.open(str(Path(job)/'cantonese.wav')) as source:
        sr=source.getframerate()
        for cue,row in zip(cues,timing):
            if is_vocalization(cue) or cue.get('preserveOriginalSpeech') or row.get('skipped'):continue
            source.setpos(round(row['renderedStart']*sr))
            raw=source.readframes(round((row['renderedEnd']-row['renderedStart'])*sr))
            if row.get('renderedAudio'):
                with wave.open(row['renderedAudio']) as take:raw=take.readframes(take.getnframes())
            path=directory/f'{row["index"]}.wav'
            with wave.open(str(path),'wb') as out:
                out.setparams(source.getparams());out.writeframes(raw)
            selected.append(cue);paths.append(path);indices.append(row['index'])
    def final_progress(stage,message,progress=None):
        emit('成品覆聽',message,None if progress is None else .97+max(0,min(1,(progress-.87)/.01))*.02)
    checks=inspect(cfg,job,selected,paths,final_progress)
    result=dict(rows=[dict(check,index=index) for check,index in zip(checks,indices)],stage='final-rendered-PCM')
    (Path(job)/'final-speech-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result


def validate_export(cfg,job,cues,target,run,emit):
    import fast_mode
    if fast_mode.enabled(cfg):return fast_mode.validation(cfg,job,cues,target,run,emit)
    emit('輸出驗證','檢查每句可聽見人聲、音軌、字幕同整條影片解碼；未通過唔標記完成。',.97)
    job=Path(job);timing=json.loads((job/'timing.json').read_text())
    rows=check_voice(job,cues,timing,cfg.get('continueOnError',True))
    from worker import atomic_json
    atomic_json(job/'timing.json',timing)
    for cue,row in zip(cues,rows):
        if row.get('skipped'):
            from project_store import record_issue
            record_issue(cfg,job,cue,row.get('failureKind','missing-voice'),'此段未有可用目標語言配音；其他已生成聲音保留。')
    meta=json.loads(run([cfg['ffprobe'],'-v','error','-show_streams','-show_format','-of','json',target]))
    videos=[s for s in meta['streams'] if s.get('codec_type')=='video']
    audio=[s for s in meta['streams'] if s.get('codec_type')=='audio']
    expected=cfg.get('outputDuration',cfg['duration'])
    duration=float(meta['format']['duration'])
    if not videos or not audio or not math.isfinite(duration) or abs(duration-expected)>.2:
        raise ValueError('輸出驗證失敗：影片或音軌缺失／長度唔一致。')
    if audio[0].get('tags',{}).get('language')!=__import__('output_language').LANGUAGES[cfg.get('targetLanguage','yue')][2] or not audio[0].get('disposition',{}).get('default'):
        raise ValueError('輸出驗證失敗：預設音軌同所選配音語言不符。')
    if cfg.get('separateBackground') and audio[0].get('channels')!=2:raise ValueError('輸出驗證失敗：背景立體聲缺失。')
    if not cfg.get('burnOutputCaptions') and not any(s.get('codec_type')=='subtitle' for s in meta['streams']):
        raise ValueError('輸出驗證失敗：字幕軌缺失。')
    run([cfg['ffmpeg'],'-v','error','-xerror','-i',target,'-map','0:v:0','-map','0:a:0','-f','null','-'])
    can_check=cfg.get('autoValidate',True) and not cfg.get('_userSkipped') and (Path(cfg.get('storage',''))/'asr-ready.json').is_file()
    verification_error=None
    try:content=inspect_rendered_voice(cfg,job,cues,timing,emit) if can_check else None
    except (RuntimeError,ValueError) as error:
        if not cfg.get('continueOnError',True):raise
        verification_error=str(error);content=None
        emit('核對待修正','成品覆聽未完成，保留輸出及已完成錄音：'+str(error))
    content_flags=sorted({r['index'] for r in content['rows'] if r['requiresReview']}) if content else []
    language_flags=sorted({r['index'] for r in content['rows'] if r.get('languageMismatch') or r.get('languageUnverified')}) if content else []
    from script_preflight import issues
    script_flags=[c.get('reviewIndex',i)+1 for i,c in enumerate(cues) if (c.get('englishTimingReview') if cfg.get('targetLanguage')=='en' else issues(cues,i) or c.get('translationWarnings'))]
    voice=json.loads((job/'voice-consistency.json').read_text()) if (job/'voice-consistency.json').exists() else {}
    voice_flags=voice.get('reviewIndices',[])
    from speakers import audit_references
    references=audit_references(cues,cfg.get('voiceProfiles',[]))
    (job/'speaker-confidence.json').write_text(json.dumps(references,ensure_ascii=False,indent=2))
    from source_evidence import audit_allocations
    allocation_review=audit_allocations(cues)
    atomic_json(job/'caption-review.json',dict(rows=allocation_review,method='Saved source evidence only; approved scripts and clocks unchanged; speech checks are separate.'))
    source_flags=sorted(set([c.get('reviewIndex',i)+1 for i,c in enumerate(cues) if c.get('sourceReviewReasons') or c.get('hybridNeedsReview') or c.get('preserveOriginalSpeech')]+[r['index'] for r in allocation_review]))
    nonverbal=json.loads((job/'nonverbal-report.json').read_text()) if (job/'nonverbal-report.json').exists() else {}
    from dialogue import coverage_report
    original=json.loads((job/'review.json').read_text()).get('cues',cues) if (job/'review.json').exists() else cues
    coverage=coverage_report(cfg,job,original)
    performance_pending=len(nonverbal.get('reviewEvents',[]))
    pcm=np.frombuffer(run([cfg['ffmpeg'],'-v','error','-i',target,'-map','0:a:0','-ar','16000','-ac','2','-f','f32le','pipe:1']),dtype=np.float32)
    if not len(pcm) or not np.isfinite(pcm).all():raise ValueError('輸出驗證失敗：混音音訊無效。')
    peak=float(np.max(np.abs(pcm)));clipped=int(np.count_nonzero(np.abs(pcm)>=1))
    mix=dict(peakDb=round(20*math.log10(max(peak,1e-12)),2),clippedSamples=clipped,checkedSampleRate=16000,method='decoded sample peak; not true-peak or broadcast loudness certification')
    level_rows=json.loads((job/'speech-levels.json').read_text()) if (job/'speech-levels.json').exists() else []
    level_flags=[r['index']+1 for r in level_rows if r.get('index') is not None and r.get('warnings')]
    from audio_fallback import read_json
    audibility=read_json(job/'mix-audibility.json',{})
    result=dict(levelReviewIndices=level_flags,speechLevels=level_rows,mixAudibility=audibility,backgroundDucking=bool(cfg.get('backgroundDucking') or audibility.get('automatic')),structuralStatus='passed' ,fullDecode='passed',duration=duration,cues=len(cues),
        timingReviewIndices=[r['index'] for r in rows if r['requiresTimingReview']],
        contentReviewIndices=content_flags,languageReviewIndices=language_flags,contentCheck='local-ASR' if content else 'not-run',rows=rows,
        scriptReviewIndices=script_flags,voiceReviewIndices=voice_flags,
        sourceReviewIndices=source_flags,speakerReviewIndices=references['reviewIndices'],nonverbalReviewCount=performance_pending,mix=mix,
        professionalStatus='not-certified',pronunciationCheck='not-run',pronunciationStatus='audition-required',sourceCoverage=coverage,verificationError=verification_error,originalSpeechIndices=[c.get('reviewIndex',i)+1 for i,c in enumerate(cues) if c.get('preserveOriginalSpeech')],
        qualityStatus='needs-review' if coverage['status']!='checked' or content_flags or level_flags or script_flags or voice_flags or source_flags or references['reviewIndices'] or performance_pending or clipped or any(r['requiresTimingReview'] for r in rows) or content is None else 'automatic-checks-passed',
        limitations='Acoustic timing and ASR are evidence, not certified meaning, character identity, native pronunciation or lip sync.')
    tmp=job/'validation.partial.json';tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2));tmp.replace(job/'validation.json')
    return result
