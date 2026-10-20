"""Retire Qwen TTS for new synthesis; keep historical takes and weights intact."""
from studio_core import catalog
ACTIVE = tuple(row['id'] for row in catalog()['engines'])
REFERENCE_ENGINES = ACTIVE + ('gpt-sovits-v3', 'qwen-tts')

def languages(engine):
    row=next((row for row in catalog()['engines'] if row['id']==engine),None)
    if row:return tuple(row['languages'])
    if engine in ('gpt-sovits-v3','qwen-tts'):return ('yue','en')
    raise ValueError('Unknown voice engine: '+str(engine))

def pairs(engines, selected_languages):
    result=[(language,engine) for language in selected_languages for engine in engines if language in languages(engine)]
    if not result:raise ValueError('所選引擎未支援所選語言；WenetSpeech-Yue 只提供廣東話。')
    return result


def migrate(cfg, emit=None):
    previous = cfg.get('selectedEngines') or [cfg.get('ttsBackend', 'cosyvoice3')]
    retired={'qwen-tts','gpt-sovits-v3'}
    affected = any(e in retired for e in previous) or any(cfg.get(k) in retired for k in ('ttsBackend', 'defaultAudioEngine'))
    if not affected:
        return False
    engines = list(dict.fromkeys(e for e in previous if e not in retired))
    if not engines:
        engines = ['gpt-sovits' if 'gpt-sovits-v3' in previous else 'cosyvoice3']
    cfg['selectedEngines'] = engines
    for key in ('ttsBackend', 'defaultAudioEngine'):
        if cfg.get(key) in retired:
            cfg[key] = engines[0]
    # Config fields for Qwen text, ASR, reference provenance and historic files
    # intentionally survive this migration. No model/take files are deleted.
    cfg.setdefault('engineSelectionRecovery', []).append(dict(previous=list(previous), selected=engines, reason='Retired voice engine selection'))
    if emit:
        emit('引擎設定更新', '舊配音引擎已停用；新配音使用 '+', '.join(engines)+'。舊音軌及已下載模型檔案保留。')
    return True
