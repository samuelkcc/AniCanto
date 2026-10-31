"""Deterministic subtitle track preference for automatic source selection.

Rule from Samuel, 2026-10-31: with text subtitles present, prefer a Chinese
subtitle as the translation basis. Traditional Chinese first, then Simplified
Chinese. With no Chinese track, use another readable language as translation
help. With no text subtitle at all, the caller keeps speech as primary and OCR
as auxiliary. An explicit user choice always outranks this order.
"""

REVISION = 'subtitle-track-preference-1'

SUBTITLE_CODECS = ('subrip', 'ass', 'ssa', 'mov_text', 'webvtt', 'text')
SUBTITLE_SUFFIXES = ('.srt', '.ass', '.ssa', '.vtt')

# Written Cantonese subtitles are already the target register, so they lead.
CANTONESE = ('yue', 'yue-hant', 'cant', 'cantonese', 'gz', 'sgh')
TRADITIONAL = ('zh-hant', 'zh-hk', 'zh-mo', 'zh-tw', 'zh-cht', 'cht', 'tch', 'trad', 'tc',
               'hk', 'mo', 'tw')
SIMPLIFIED = ('zh-hans', 'zh-cn', 'zh-sg', 'zh-chs', 'chs', 'simp', 'sc', 'cn', 'sg')
CHINESE = ('zh', 'zho', 'chi', 'chn', 'zh-hu', 'chinese', 'hua')
# Other readable tracks only assist translation when no Chinese track exists.
OTHER_LANGUAGE = ('en', 'eng', 'ja', 'jpn', 'ko', 'kor', 'fr', 'fra', 'de', 'deu',
                  'es', 'spa', 'it', 'ita', 'th', 'tha', 'vi', 'vie', 'id', 'ind')

SCRIPT_RANK = {'cantonese': 0, 'traditional': 1, 'simplified': 2, 'chinese': 3,
               'other-language': 4, 'unlabeled': 5}

# Titles and file-name markers that state the script in plain words.
SCRIPT_WORDS = {
    'traditional': ('traditional', '繁體', '正體', '繁', 'big5'),
    'simplified': ('simplified', '簡體', '简体', '簡', 'gbk', 'gb2312'),
}


def canonical(value):
    """Normalise a stream tag, a UI label or a file-name marker to lower case."""
    value = (value or '').strip().lower()
    if value in ('und', '', 'unknown', '未標示語言', 'undefined'):
        return ''
    return value


def script_of(token):
    """Return the Chinese script family for one tag, or '' when it is not Chinese."""
    token = canonical(token)
    if not token:
        return ''
    if token in CANTONESE:
        return 'cantonese'
    for family in ('traditional', 'simplified'):
        if token in (TRADITIONAL if family == 'traditional' else SIMPLIFIED):
            return family
    for family, words in SCRIPT_WORDS.items():
        if any(word in token for word in words):
            return family
    if token in CHINESE or token.startswith('zh-'):
        return 'chinese'
    return ''


def family(stream):
    """Classify one ffprobe subtitle stream or sidecar candidate."""
    tag = canonical((stream.get('tags') or {}).get('language') if 'tags' in stream else stream.get('language'))
    title = canonical((stream.get('tags') or {}).get('title') if 'tags' in stream else stream.get('title'))
    marker = canonical(stream.get('marker'))
    tag_script = script_of(tag)
    if tag_script and tag_script != 'chinese':
        return tag_script
    # A plain zh tag does not state the script, so the title or file name decides.
    for other in (script_of(title), script_of(marker)):
        if other:
            return other
    if tag_script:
        return 'chinese'
    if tag:
        return 'other-language'
    return 'unlabeled'


def rank(stream):
    return SCRIPT_RANK[family(stream)]


def is_text_stream(stream):
    return stream.get('codec_type') == 'subtitle' and stream.get('codec_name') in SUBTITLE_CODECS


def sort_key(stream, language=None, title=None):
    """Lower sorts first. Explicit choice beats the automatic order."""
    wanted = canonical(language)
    tags = stream.get('tags') or {}
    stream_language = canonical(tags.get('language'))
    stream_title = canonical(tags.get('title'))
    language_match = 0 if wanted and (stream_language == wanted or script_of(stream_language)
                                      and script_of(language) == script_of(stream_language)) else 1
    title_match = 0 if title and stream_title and canonical(title) == stream_title else 1
    return (language_match, title_match, rank(stream),
            0 if (stream.get('disposition') or {}).get('default') else 1,
            int(stream.get('index', 0)))


def pick(streams, language=None, title=None):
    streams = [s for s in streams if is_text_stream(s)] or list(streams)
    return min(streams, key=lambda s: sort_key(s, language, title)) if streams else None


def reason(stream):
    return family(stream).replace('-', ' ')


def sidecar_key(path):
    """Rank a sidecar file by the language marker in its name."""
    marker = path.get('marker')
    return (rank({'marker': marker}), 0 if not marker else 1, str(path.get('name')))
