"""Normalize a source-witnessed name suffix without another model call."""
import re

REVISION = 'bounded-target-response-392'


def names(text, source, source_language, target_language):
    if not isinstance(text, str) or source_language != 'ja' or target_language not in ('yue', 'zh'):
        return text
    for match in re.finditer(r'([\u3400-\u9fff]{1,4})くん', source):
        text = text.replace(match.group(0), match.group(1))
    return text


def normalize(cfg, cue, text, language):
    if cfg.get('draftOutputGuardRevision') != REVISION:
        return text
    from primary_source import content, authored
    # Chinese captions remain the primary text. Do not reinterpret them as Japanese.
    source_language = 'zh' if authored(cue) else cfg.get('sourceLanguage', 'ja')
    return names(text, content(cue), source_language, language)
