"""Versioned subtitle translation from saved evidence; no ASR, OCR or TTS."""
import copy
import hashlib
import json
from pathlib import Path


def prepare(w, cfg, folder, cues):
    languages = cfg.get('scriptLanguages') or ['yue']
    if not languages or any(x not in ('yue', 'en') for x in languages):
        raise ValueError('請選擇廣東話或英文字幕。')
    mode = cfg.get('scriptRevisionMode', 'missing')
    if mode not in ('missing', 'all'):
        raise ValueError('字幕重新製作模式無效。')
    result = copy.deepcopy(cues)
    before = {c['editorID']: copy.deepcopy(c) for c in cues}
    identity = hashlib.sha256(json.dumps([cfg.get('model'), 'hong-kong-cantonese-1', mode, languages, cues], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]
    cache = Path(folder) / ('script-work-' + identity + '.json')
    saved = json.loads(cache.read_text()) if cache.exists() else {}
    for language in languages:
        field = 'cantonese' if language == 'yue' else 'english'
        for cue in result:
            if not cue.get('enabled', True):
                continue
            key = language + ':' + cue['editorID']
            pending = mode == 'all' or not str(cue.get(field) or '').strip()
            if pending:
                cue[field] = saved.get(key, '')
                if field == 'english':
                    cue.pop('englishGenerationFailed', None)
                    cue.pop('englishCaptionText', None)
        pending = [c for c in result if c.get('enabled', True) and not str(c.get(field) or '').strip()]
        if language == 'en':
            from dub_languages import english_script
            english_script(w, dict(cfg, continueOnError=True), folder, result)
        else:
            for offset in range(0, len(pending), 8):
                batch = pending[offset:offset+8]
                w.emit('重新翻譯字幕', f'廣東話：第 {offset+1}–{min(offset+8,len(pending))}/{len(pending)} 段。')
                def checkpoint():
                    for item in result:
                        if item.get('cantonese', '').strip():
                            saved['yue:' + item['editorID']] = item['cantonese']
                    w.atomic_json(cache, saved)
                w.translate_batch(cfg, batch, [], checkpoint)
                checkpoint()
        for cue in result:
            old = before[cue['editorID']]
            if not old.get('enabled',True):
                if field in old:cue[field]=old[field]
                else:cue.pop(field,None)
                continue
            # A translation request can never move source/editor clocks or roles.
            for key in ('start', 'end', 'subtitleStart', 'subtitleEnd', 'speechStart', 'speechEnd', 'speakerId', 'editorSources'):
                if key in old:
                    cue[key] = copy.deepcopy(old[key])
            if cue.get(field, '').strip():
                saved[language + ':' + cue['editorID']] = cue[field]
            if language == 'yue' and (mode == 'all' or not old.get('cantonese', '').strip()):
                cue['captionText'] = cue.get('cantonese', '')
        w.atomic_json(cache, saved)
    missing = [dict(id=c['editorID'], language=lang) for lang in languages for c in result
               if c.get('enabled', True) and not str(c.get('english' if lang == 'en' else 'cantonese') or '').strip()]
    return result, missing


def save(w, cfg, folder, draft, cues):
    generated, missing = prepare(w, cfg, folder, cues)
    proposal = copy.deepcopy(draft)
    by_id = {c['editorID']: c for c in generated}
    for row in proposal['segments']:
        cue = by_id[row['id']]
        for lang in cfg.get('scriptLanguages', ['yue']):
            if lang == 'yue':
                row['text'] = cue.get('cantonese', '')
                row['captionText'] = cue.get('captionText', row['text'])
            else:
                row['english'] = cue.get('english', '')
    w.atomic_json(Path(folder)/'subtitle-draft.json', proposal)
    w.atomic_json(Path(folder)/'cues.json', generated)
    subtitles = {}
    for lang in cfg.get('scriptLanguages', ['yue']):
        path = Path(folder)/('cantonese.srt' if lang == 'yue' else 'english.srt')
        field = 'cantonese' if lang == 'yue' else 'english'
        rows = [dict(start=c.get('subtitleStart', c['start']), end=c.get('subtitleEnd', c['end']), text=c.get('captionText') or c.get(field, ''))
                if lang == 'yue' else dict(start=c.get('subtitleStart', c['start']), end=c.get('subtitleEnd', c['end']), text=c.get(field, ''))
                for c in generated if c.get('enabled', True) and c.get(field, '').strip()]
        w.save_srt(path, rows)
        subtitles[lang] = str(path)
    return generated, missing, subtitles
