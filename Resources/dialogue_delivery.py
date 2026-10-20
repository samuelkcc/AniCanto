"""Explain absent dialogue across tracks; file presence is not content approval."""
from pathlib import Path
from collections import Counter
from audio_fallback import read_json,healthy


def audit(tracks):
    result=[]
    for track in tracks:
        folder=Path(track['folder']);review=read_json(folder/'review.json',{})
        timing={r['index']:r for r in read_json(folder/'timing.json',[])}
        issues={}
        for row in read_json(folder/'segment-issues.json',[]):issues.setdefault(row.get('index'),[]).append(row)
        report=track.get('report') or read_json(folder/'report.json',{})
        repaired={r['index']:r for r in report.get('audioFallbacks',[]) if r.get('sourceLanguage')==track.get('language','yue') and healthy(r.get('audio',''))}
        from dubbing import is_vocalization
        from workflow_policy import original_allowed
        repair_rows=read_json(folder.parent.parent/'ai-repair-summary.json',{}).get('rows',[])
        rows=[];excluded=[]
        for n,cue in enumerate(review.get('cues',[])):
            if not cue.get('enabled',True) or original_allowed(review.get('config',{}),cue) or is_vocalization(cue):
                excluded.append(dict(index=cue.get('reviewIndex',n)+1,editorID=cue.get('editorID'),start=cue['start'],end=cue['end'],reason='disabled' if not cue.get('enabled',True) else 'deliberate-original' if original_allowed(review.get('config',{}),cue) else 'nonlexical-performance',detail=cue.get('reviewNote') or cue.get('originalSpeechReason') or '',sourceCaption=cue.get('subtitleHint','')))
                continue
            index=cue.get('reviewIndex',n)+1;row=timing.get(index,{})
            path=row.get('renderedAudio') or row.get('audio','')
            donor=repaired.get(index,{})
            matches=lambda r:('text' not in r or r['text']==cue.get('cantonese','')) and ('speakerId' not in r or r['speakerId']==cue.get('speakerId'))
            available=bool(donor and matches(donor)) or (matches(row) and not row.get('skipped') and row.get('renderedSeconds',0)>0 and healthy(path))
            errors=issues.get(index,[])
            if not errors and not available and report.get('failureReason'):
                import re
                message=report['failureReason'];errors=[dict(kind='reference' if re.search(r'reference|參考|原聲',message,re.I) else 'tts-generation',message=message)]
            if not available and row.get('error') and not errors:errors=[dict(kind=row.get('failureKind','tts-generation'),message=row['error'])]
            kinds={r.get('kind') for r in errors}
            reason='audio-present' if available else 'missing-script' if not cue.get('cantonese','').strip() else 'timing-overrun' if row.get('failureKind')=='timing-overrun' and row.get('seconds',0)>row.get('slot',float('inf')) else 'verification-unresolved' if 'normal-unresolved' in kinds else 'reference-blocked' if 'reference' in kinds else 'generation-failed' if 'tts-generation' in kinds else 'missing-audio'
            messages=list(dict.fromkeys(r.get('message','') for r in errors if r.get('message')))
            repair=[r for r in repair_rows if r.get('index')==index and r.get('engine')==track['engine'] and r.get('language','yue')==track.get('language','yue')]
            rows.append(dict(index=index,editorID=cue.get('editorID'),start=cue['start'],end=cue['end'],speakerId=cue.get('speakerId'),script=cue.get('cantonese',''),sourceCaption=cue.get('subtitleHint',''),captionIDs=[r['id'] for r in cue.get('captionRecords',[]) if 'id' in r],available=bool(available),reason=reason,retainedAudio=str(path) if path and Path(path).is_file() else None,measuredSeconds=row.get('seconds'),availableSeconds=row.get('slot'),messages=messages,issueKinds=sorted(k for k in kinds if k),repair=repair,logs=dict(timing=str(folder/'timing.json'),generation=str(folder/'segment-issues.json'),verification=str(folder/'final-speech-check.json'),report=str(folder/'report.json'))))
        counts=Counter(r['reason'] for r in rows)
        result.append(dict(engine=track['engine'],language=track.get('language','yue'),required=len(rows),available=counts['audio-present'],missing=len(rows)-counts['audio-present'],causes=dict(counts),rows=rows,excluded=excluded))
    return dict(status='missing-dialogue' if any(t['missing'] for t in result) else 'audio-present',tracks=result,method='Enabled spoken dialogue versus delivered timing and same-language repairs; captions and scripts alone do not prove speech generation. Content and voice quality remain separate checks.')


def summary(report):
    languages={'yue':'香港廣東話','en':'英文'}
    engines={'drama3':'Drama 3','gpt-sovits-v2':'GPT-SoVITS V2 Pro Plus','gpt-sovits':'GPT-SoVITS','gpt-sovits-v3':'GPT-SoVITS V3','cosyvoice3':'CosyVoice 3','qwen-tts':'Qwen TTS','voxcpm2':'VoxCPM 2','wsyue':'WenetSpeech-Yue'}
    return '\n'.join(f"對白覆蓋：{languages.get(t['language'],t['language'])} · {engines.get(t['engine'],t['engine'])} — 有錄音 {t['available']}/{t['required']}；缺聲 {t['missing']}（角色參考 {t['causes'].get('reference-blocked',0)}、欠稿 {t['causes'].get('missing-script',0)}、時長超出 {t['causes'].get('timing-overrun',0)}、覆聽待修正 {t['causes'].get('verification-unresolved',0)}、其他 {t['missing']-t['causes'].get('reference-blocked',0)-t['causes'].get('missing-script',0)-t['causes'].get('timing-overrun',0)-t['causes'].get('verification-unresolved',0)}）。" for t in report['tracks'])


def incomplete(report):
    """The editor wrapper cannot turn an incomplete child export into complete."""
    ai=report.get('aiAutoFix')
    delivery=report.get('dialogueDelivery',{})
    return bool(report.get('failedEngines') or (ai.get('unresolved') if ai else report.get('segmentIssues')) or delivery.get('status')=='missing-dialogue' or any(t.get('missing',0)>0 for t in delivery.get('tracks',[])) or any(t.get('strongFailures') for t in report.get('encodedSpeechChecks',[])))
