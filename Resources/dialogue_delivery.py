"""Explain absent dialogue across tracks; file presence is not content approval."""
from pathlib import Path
from collections import Counter
from audio_fallback import read_json,healthy as _healthy
from functools import lru_cache

@lru_cache(maxsize=2048)
def _cached_health(path,size,modified,changed):return _healthy(path)

def healthy(path):
    try:
        f=Path(path);st=f.stat()
        return _cached_health(str(f),st.st_size,st.st_mtime_ns,st.st_ctime_ns)
    except (OSError,TypeError):return False


def audit(tracks,health=None):
    check_health=health or healthy
    result=[]
    for track in tracks:
        folder=Path(track['folder']);review=track.get('review') or read_json(folder/'review.json',{})
        timing={r['index']:r for r in read_json(folder/'timing.json',[])}
        issues={}
        for row in read_json(folder/'segment-issues.json',[]):issues.setdefault(row.get('index'),[]).append(row)
        report=track.get('report') or read_json(folder/'report.json',{})
        repaired={r['index']:r for r in report.get('audioFallbacks',[]) if r.get('sourceLanguage')==track.get('language','yue') and check_health(r.get('audio',''))}
        from dubbing import is_vocalization
        from workflow_policy import original_allowed
        repair_rows=read_json(folder.parent.parent/'ai-repair-summary.json',{}).get('rows',[])
        generic_indices={r.get('index') for r in read_json(folder/'target-reference-recovery.json',{}).values() if r.get('status') in ('adopted','selected-unverified')}
        from target_delivery import required_clock,trace_issues,source_windows
        malformed=trace_issues(folder,review,timing,generic_indices) if track['engine']=='drama3' else {}
        rows=[];excluded=[]
        for n,cue in enumerate(review.get('cues',[])):
            if not cue.get('enabled',True) or (original_allowed(review.get('config',{}),cue) and not required_clock(cue)) or (is_vocalization(cue) and not required_clock(cue)):
                excluded.append(dict(index=cue.get('reviewIndex',n)+1,editorID=cue.get('editorID'),start=cue['start'],end=cue['end'],reason='caption-owned-by-neighbour' if cue.get('captionCovered') else 'caption-only-no-dialogue' if cue.get('captionOnly') else 'disabled' if not cue.get('enabled',True) else 'deliberate-original' if original_allowed(review.get('config',{}),cue) else 'nonlexical-performance',detail=cue.get('reviewNote') or cue.get('originalSpeechReason') or '',sourceCaption=cue.get('subtitleHint','')))
                continue
            index=cue.get('reviewIndex',n)+1;row=timing.get(index,{})
            path=row.get('renderedAudio') or row.get('audio','')
            donor=repaired.get(index,{})
            matches=lambda r:('text' not in r or r['text']==cue.get('cantonese','')) and ('speakerId' not in r or r['speakerId']==cue.get('speakerId'))
            available=bool(donor and matches(donor)) or (matches(row) and not row.get('skipped') and row.get('renderedSeconds',0)>0 and check_health(path))
            if row.get('originalPreserved') or row.get('originalFallback'):available=False
            errors=list(issues.get(index,[]))
            if index in malformed:
                available=False;errors.append(dict(index=index,**malformed[index]))
            if not errors and not available and report.get('failureReason'):
                import re
                message=report['failureReason'];errors=[dict(kind='reference' if re.search(r'reference|參考|原聲',message,re.I) else 'tts-generation',message=message)]
            if not available and row.get('error') and not errors:errors=[dict(kind=row.get('failureKind','tts-generation'),message=row['error'])]
            kinds={r.get('kind') for r in errors}
            reason='generation-input' if index in malformed else 'source-clock-target-missing' if required_clock(cue) and not available else 'audio-present' if available else 'missing-script' if not cue.get('cantonese','').strip() else 'timing-overrun' if row.get('failureKind') in ('timing-overrun','introduced-dialogue-overlap') and row.get('seconds',0)>row.get('slot',float('inf')) else 'verification-unresolved' if 'normal-unresolved' in kinds else 'reference-blocked' if 'reference' in kinds else 'generation-failed' if 'tts-generation' in kinds else 'missing-audio'
            messages=list(dict.fromkeys(r.get('message','') for r in errors if r.get('message')))
            repair=[r for r in repair_rows if r.get('index')==index and r.get('engine')==track['engine'] and r.get('language','yue')==track.get('language','yue')]
            rows.append(dict(index=index,editorID=cue.get('editorID'),start=cue['start'],end=cue['end'],speakerId=cue.get('speakerId'),script=cue.get('cantonese',''),sourceCaption=cue.get('subtitleHint',''),captionIDs=[r['id'] for r in cue.get('captionRecords',[]) if 'id' in r],available=bool(available),originalFallback=bool(row.get('originalFallback') or row.get('originalPreserved')),reason=reason,retainedAudio=str(path) if path and Path(path).is_file() else None,measuredSeconds=row.get('seconds'),availableSeconds=row.get('slot'),messages=messages,issueKinds=sorted(k for k in kinds if k),repair=repair,fallbackStage=('original-source' if row.get('originalFallback') or row.get('originalPreserved') else 'generic-target-language' if index in generic_indices else 'actor-or-unresolved'),logs=dict(timing=str(folder/'timing.json'),generation=str(folder/'segment-issues.json'),verification=str(folder/'final-speech-check.json'),report=str(folder/'report.json'))))
        counts=Counter(r['reason'] for r in rows)
        preserved=source_windows(review.get('cues',[]),timing)
        result.append(dict(safeAudioEndpoints=report.get('safeAudioEndpoints'),deliveryPolicyRevision=review.get('config',{}).get('deliveryPolicyRevision'),engine=track['engine'],language=track.get('language','yue'),required=len(rows),available=counts['audio-present'],missing=len(rows)-counts['audio-present'],causes=dict(counts),rows=rows,excluded=excluded,sourcePreserved=preserved,sourcePreservedCount=len(preserved),qualityCertified=False))
    return dict(status='missing-dialogue' if any(t['missing'] for t in result) else 'audio-present',tracks=result,method='Enabled spoken dialogue versus delivered timing and same-language repairs; captions and scripts alone do not prove speech generation. Content and voice quality remain separate checks.')


def summary(report):
    languages={'yue':'香港廣東話','en':'英文','zh':'普通話'}
    engines={'drama3':'Drama 3','gpt-sovits-v2':'GPT-SoVITS V2 Pro Plus','gpt-sovits':'GPT-SoVITS','gpt-sovits-v3':'GPT-SoVITS V3','cosyvoice3':'CosyVoice 3','qwen-tts':'Qwen TTS','voxcpm2':'VoxCPM 2','wsyue':'WenetSpeech-Yue'}
    lines=[]
    for t in report['tracks']:
        label=f"對白覆蓋：{languages.get(t['language'],t['language'])} · {engines.get(t['engine'],t['engine'])}"
        if __import__('delivery_policy').repair_first(dict(deliveryPolicyRevision=t.get('deliveryPolicyRevision'))):
            source=sum(not r.get('available') and r.get('fallbackStage')=='original-source' for r in t.get('rows',[]))
            line=f"{label} — 目標配音 {t['available']}/{t['required']}；未交付目標配音 {t['missing']}，當中原聲後備 {source}（時長超出 {t['causes'].get('timing-overrun',0)}、欠稿 {t['causes'].get('missing-script',0)}、參考受阻 {t['causes'].get('reference-blocked',0)}）。未交付目標配音唔等於整段無聲；逐句原因及試聽位置見校對報告。"
        else:
            line=f"{label} — 有錄音 {t['available']}/{t['required']}；缺聲 {t['missing']}（角色參考 {t['causes'].get('reference-blocked',0)}、欠稿 {t['causes'].get('missing-script',0)}、時長超出 {t['causes'].get('timing-overrun',0)}、覆聽待修正 {t['causes'].get('verification-unresolved',0)}、其他 {t['missing']-t['causes'].get('reference-blocked',0)-t['causes'].get('missing-script',0)-t['causes'].get('timing-overrun',0)-t['causes'].get('verification-unresolved',0)}）。"
        endpoint=t.get('safeAudioEndpoints') or {}
        if endpoint.get('tailCandidates'):line+=f" 安全尾音檢查：已裁尾 {endpoint.get('trimmed',0)} 段，未確認 {endpoint.get('unconfirmed',0)} 段；原錄音保留。"
        lines.append(line)
    return '\n'.join(lines)



def incomplete(report):
    """The editor wrapper cannot turn an incomplete child export into complete."""
    ai=report.get('aiAutoFix')
    delivery=report.get('dialogueDelivery',{})
    return bool(report.get('failedEngines') or (ai.get('unresolved') if ai else report.get('segmentIssues')) or delivery.get('status')=='missing-dialogue' or any(t.get('missing',0)>0 for t in delivery.get('tracks',[])) or any(t.get('strongFailures') for t in report.get('encodedSpeechChecks',[])))
