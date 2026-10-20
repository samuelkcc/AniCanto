"""Recover removed frozen models using compatible, complete local weights."""
import json,subprocess,sys
from pathlib import Path

def recover(cfg,emit):
    if sys.platform=='win32':
        from native_models import recover as native_recover
        return native_recover(cfg,emit)
    import model_catalog
    if not cfg.get('storage'):return
    root=Path(cfg['storage'])
    try:selected=json.loads((root/'model-selections.json').read_text())
    except (OSError,ValueError):selected={}
    budget=cfg.get('modelMemoryBudgetGB')
    if budget is None:
        try:budget=int(subprocess.check_output(['/usr/sbin/sysctl','-n','hw.memsize'],text=True,stderr=subprocess.DEVNULL))/1073741824*.75
        except (OSError,ValueError,subprocess.CalledProcessError):budget=0
    engines=cfg.get('selectedEngines') or [cfg.get('ttsBackend','cosyvoice3')]
    for role,key,default in [('cosyvoice3','cosyModel','cosy-native-0.5b'),('qwen-tts','qwenModel','qwen-0.6b-4bit'),('voxcpm2','voxcpmModel','voxcpm2-2b-bf16'),('wsyue','wsyueModel','wsyue-cosy2-zjg'),('drama3','drama3Model','drama3-35b-4bit')]:
        if role not in engines and not (role=='cosyvoice3' and (cfg.get('gsvReferenceMode')=='target-bridge' or cfg.get('qwenReferenceMode')=='cantonese-bridge')):continue
        old=cfg.get(key,default)
        try:model_catalog.resolve(root,old);continue
        except (ValueError,OSError):pass
        candidate=selected.get(role)
        if candidate and candidate!=old:
            try:
                row=model_catalog.choice(candidate)
                if row.get('retired') or row['category']!='voice' or row['engine']!=role or (budget and row['estimatedMemoryGB']>budget):raise ValueError('引擎不相符或記憶體不足')
                model_catalog.resolve(root,candidate)
            except (ValueError,OSError):candidate=None
        if not candidate or candidate==old:
            old_row=next((r for r in model_catalog.catalog() if r['id']==old),{})
            options=[r for r in model_catalog.catalog() if not r.get('retired') and r['category']=='voice' and r['engine']==role and r['id']!=old and budget and r['estimatedMemoryGB']<=budget]
            options.sort(key=lambda r:(r.get('precision')!=old_row.get('precision'),abs(r['parameterB']-old_row.get('parameterB',r['parameterB'])),-r['bytes']))
            candidate=None
            for row in options:
                try:model_catalog.resolve(root,row['id']);candidate=row['id'];break
                except (ValueError,OSError):continue
        if not candidate:
            emit('模型需修正',f'{role}：專案所選 {old} 未下載完整；未有目前選用的可用版本。請到模型中心下載或選用。')
            continue
        cfg[key]=candidate
        cfg.setdefault('modelRecovery',[]).append(dict(engine=role,previous=old,selected=candidate,reason='frozen model removed; explicit current choice' if candidate==selected.get(role) else 'frozen model removed; compatible downloaded model'))
        source='你目前選用的版本' if candidate==selected.get(role) else '同引擎已下載且記憶體可承受的版本'
        emit('模型自動修復',f'{role}：專案版本 {old} 已移除，改用 {candidate}（{source}）；未下載任何新模型。')
