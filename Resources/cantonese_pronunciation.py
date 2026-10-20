"""Explicit Jyutping overrides for V4's Cantonese target frontend only.

Displayed text, reference transcripts and other engines are never rewritten.
An override controls phoneme input; it does not certify the generated tones.
"""
import contextlib
import functools
import re


def rules(value):
    result = {}
    for line in (value or '').splitlines():
        if not line.strip():
            continue
        if '=' not in line:
            raise ValueError('粵拼修正請每行輸入「台詞字詞 = 粵拼」，例如「銀行 = ngan4 hong4」。')
        source, reading = (x.strip() for x in line.split('=', 1))
        tokens = reading.lower().split()
        if not re.fullmatch(r'[\u4e00-\u9fa5]{1,80}', source) or len(tokens) != len(source):
            raise ValueError('粵拼修正只接受中文字詞，每個字需要一個粵拼音節。')
        if any(not re.fullmatch(r'[a-z]+[1-6]', token) for token in tokens):
            raise ValueError('每個粵拼音節需要聲調 1–6，例如 ngan4 hong4；音節之間用空格。')
        if source in result and result[source] != tokens:
            raise ValueError('同一字詞有多個粵拼修正；請保留一個讀法。')
        result[source] = tokens
    if len(result) > 200:
        raise ValueError('每個專案最多保存 200 個粵拼修正。')
    return result


def matching(value, text):
    entries = rules(value)
    return {source: tokens for source, tokens in entries.items() if source in text}


def normalized(entries, frontend):
    # Upstream V4 uses the extended symbol inventory, shared with post-v1
    # frontends. The filename is not the selected acoustic model version.
    from text.symbols2 import symbols
    allowed = set(symbols)
    result = {}
    for source, tokens in entries.items():
        source = frontend.text_normalize(source)
        if len(source) != len(tokens):
            raise ValueError('字詞正規化後長度改變，未套用粵拼修正。')
        phones, word2ph = frontend.jyuping_to_initials_finals_tones(tokens)
        if len(word2ph) != len(tokens) or any(phone not in allowed for phone in phones):
            raise ValueError('粵拼讀法未能轉換成 V4 支援嘅音素，請檢查拼寫。')
        if source in result and result[source] != tokens:
            raise ValueError('繁簡轉換後有衝突嘅粵拼修正。')
        result[source] = tokens
    return result


def replace(text, syllables, entries):
    if not entries:
        return syllables
    pattern = '|'.join(re.escape(x) for x in sorted(entries, key=len, reverse=True))
    matches = list(re.finditer(pattern, text))
    if not matches:
        return syllables
    tokens = [token for syllable in syllables for token in syllable.split()]
    if len(tokens) != len(text):
        raise ValueError('文字同粵拼音節未能逐字對應；未套用不確定嘅讀音修正。')
    for match in matches:
        tokens[match.start():match.end()] = entries[match.group()]
    return tokens


@contextlib.contextmanager
def override(frontend, entries):
    original = frontend.get_jyutping
    frontend.get_jyutping = lambda text: replace(text, original(text), entries)
    try:
        yield
    finally:
        frontend.get_jyutping = original


def install(model):
    """Scope the hook to target preprocessing, outside reference preprocessing."""
    from text import cantonese
    preprocessor = model.text_preprocessor
    original = preprocessor.preprocess
    @functools.wraps(original)
    def preprocess(*args, **kwargs):
        with override(cantonese, getattr(model, '_canto_readings', {})):
            return original(*args, **kwargs)
    preprocessor.preprocess = preprocess


def select(model, entries):
    from text import cantonese
    model._canto_readings = normalized(entries, cantonese)
