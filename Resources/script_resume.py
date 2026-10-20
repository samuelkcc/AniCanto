"""Resume the delivery draft before the older intermediate translation cache.

Reusing text never approves audio quality or rewrites source clocks. Only the same
source/model/policy and unchanged per-cue evidence can reuse a saved scene draft.
"""
import copy,json
from pathlib import Path


def restore(w,cfg,job,cues):
    if any(cfg.get(k) for k in ('forceRetranslate','retranslate','rebuildDialogue')):return False
    try:review=json.loads((Path(job)/'review.json').read_text())
    except (OSError,ValueError):return False
    if not isinstance(review,dict) or not isinstance(review.get('config'),dict):return False
    old=review['config']
    for key,default in [('video',None),('model',None),('translationSource','audio-and-subtitles'),('productionMode','standard')]:
        if old.get(key,default)!=cfg.get(key,default):return False
    rows=review.get('cues')
    if not isinstance(rows,list) or len(rows)!=len(cues):return False
    # Never carry a draft across changed timing, speech recognition or caption evidence.
    fields=('start','end','text','japanese','japaneseAlt','sourceStart','sourceEnd','speechStart','speechEnd','subtitleHint','captionRecords')
    if any(not isinstance(a,dict) or any(a.get(k)!=b.get(k) for k in fields) for a,b in zip(rows,cues)):return False
    from hybrid_script import REVISION
    locked=bool(old.get('scriptLocked') or not old.get('autoApprove',True))
    active=[c for c in rows if c.get('enabled',True) and not c.get('captionPolicyExcluded')]
    if not active or any(not isinstance(c.get('cantonese'),str) or not c['cantonese'].strip() for c in active):return False
    if not locked and any(c.get('hybridRevision')!=REVISION for c in active):return False
    try:w.validate_review(rows,cues,cfg['duration'],require_ready=False)
    except (ValueError,KeyError,TypeError):return False
    cues[:]=copy.deepcopy(rows)
    if old.get('scriptLocked'):cfg['scriptLocked']=True
    w.emit('沿用配音稿',f'已沿用 {len(active)} 段保存嘅配音稿；保留已補稿及已生成錄音，唔重新翻譯整集。',workCached=True)
    return True
