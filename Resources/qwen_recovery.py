"""One bounded English-reference recovery for explicitly failed Qwen takes.

Completed takes and approved words are immutable. This is still Qwen synthesis;
CosyVoice supplies only a separately verified reference, with recorded provenance.
"""
import json,uuid
from pathlib import Path


def generate(cfg,job,request,emit,run_model):
    from worker import atomic_json
    from qwen_reference import prepare
    job=Path(job);request=dict(request,requestId=uuid.uuid4().hex)
    try:
        run_model(cfg,'qwen',request,emit)
        return
    except RuntimeError as original:
        from track_control import UserSkipped
        if isinstance(original,UserSkipped):raise
        result_file=job/'qwen-results.json'
        if not result_file.exists():raise
        result=json.loads(result_file.read_text())
        if result.get('requestId')!=request['requestId']:raise
        failed={r['output'] for r in result.get('items',[]) if r.get('status')=='failed'}
        pending=[r for r in request['items'] if r['output'] in failed and not Path(r['output']).exists()]
        if (not pending or cfg.get('targetLanguage')!='en' or cfg.get('qwenReferenceMode','original')=='original'
                or any(r['profile'].get('language')=='en' for r in pending)):
            raise
        audit=dict(requestId=request['requestId'],originalError=str(original),initialResults=result['items'],items=[],status='running')
        audit_file=job/'qwen-recovery.json';atomic_json(audit_file,audit)
        emit('自動修復',f'Qwen 英文 {len(pending)} 段生成異常；只重做失敗片段，先建立／核對英文參考，台詞同已完成音檔保留。')
        items=[]
        try:
            for item in pending:
                profile=prepare(dict(cfg,ttsBackend='qwen-tts'),job,item['profile'],emit,allow_english=True)
                if profile.get('language')!='en':raise ValueError('未取得已驗證英文參考。')
                items.append(dict(item,profile=profile))
                audit['items'].append(dict(output=item['output'],reviewIndex=item.get('reviewIndex'),originalReference=item['profile']['reference'],reference=profile['reference'],provenance=profile.get('referenceProvenance')))
            atomic_json(audit_file,audit)
            run_model(cfg,'qwen',dict(request,items=items,recoveryAttempt=True,requestId=uuid.uuid4().hex),emit)
            audit['status']='audio-generated-needs-content-check'
            emit('自動修復',f'Qwen 英文已補回 {len(items)} 段可聽音訊；下一步覆聽內容同核對時長，未將生成成功當成台詞正確。')
        except Exception as error:
            audit['status']='failed';audit['error']=str(error)
            raise RuntimeError(f'Qwen 英文自動修復未完成：{error}；已保存其他片段，詳見 {audit_file}。') from error
        finally:atomic_json(audit_file,audit)
