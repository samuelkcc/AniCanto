"""Deliver an explicitly labelled preview when automatic repair is exhausted."""
import json
from pathlib import Path


def allowed(cfg):return cfg.get('productionMode')=='normal' and not cfg.get('editorRender') and cfg.get('autoPreviewIncomplete',True)


def needed(cfg,coverage,failures,tracks):
    unresolved=False
    for track in tracks:
        try:unresolved |= bool(json.loads((Path(track['folder'])/'normal-checks.json').read_text()).get('unresolved'))
        except (OSError,ValueError):pass
    # A review warning or a failed optional track does not turn a complete
    # spoken-language export into a preview. Preserve the preview label for
    # genuine missing dialogue.
    return allowed(cfg) and coverage.get('status')=='missing-dialogue'


def details(coverage,tracks=()):
    rows=[dict(engine=t['engine'],language=t['language'],index=x['index'],start=x['start'],end=x['end'],reason=x['reason']) for t in coverage.get('tracks',[]) for x in t.get('rows',[]) if not x.get('available')]
    pending={(r['engine'],r['language'],r['index']) for r in rows};checks=[];source_fallbacks=[]
    for track in tracks:
        try:
            timing=json.loads((Path(track['folder'])/'timing.json').read_text())
            source_fallbacks.extend(dict(engine=track['engine'],language=track['language'],index=r['index'],sourceKind=r.get('previewSourceKind')) for r in timing if r.get('originalFallback'))
        except (OSError,ValueError):pass
        try:indices=json.loads((Path(track['folder'])/'normal-checks.json').read_text()).get('unresolved',[])
        except (OSError,ValueError):indices=[]
        try:source=json.loads((Path(track['folder'])/'review.json').read_text()).get('cues',[])
        except (OSError,ValueError):source=[]
        by_index={c.get('reviewIndex',n)+1:c for n,c in enumerate(source)}
        for index in indices:
            key=(track['engine'],track['language'],index);pending.add(key)
            checks.append(dict(engine=track['engine'],language=track['language'],index=index,reason='language-or-content-check',**{k:by_index[index][k] for k in ('start','end') if index in by_index and k in by_index[index]}))
    return dict(kind='incomplete-preview',missingDialogue=len(rows),incompleteDialogue=len(pending),missing=rows,unresolvedChecks=checks,sourceFallbacks=source_fallbacks,qualityCertified=False)
