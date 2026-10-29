"""Source-matched script length for the collapsed desktop mode.

Rule: measure each line from the Japanese speech start to the Japanese speech
end, then write a Cantonese line with about the same number of spoken units as
the Japanese line. When the two languages are spoken at a similar rate, the
recording ends inside the original speech window, so the dub cannot run over
the next line.

Measured on three finished 2026-10 jobs (One Piece 0822, Ranma half 055, Kung Fu
Muffet Cats): Cantonese characters per Japanese mora = 0.80 to 0.85; finished
takes run at 4.1 to 4.7 Chinese characters per second.

Two rates are kept apart on purpose. The drafting rate below is the rate a
writer should aim at. The measured take rate is what the voice engine really
produces, including its pauses, and it is the rate used to predict whether a
finished recording still fits its window.
"""
REVISION='source-matched-script-245'
KANJI_MORA=1.8                 # One kanji carries one to three morae; 1.8 is the observed mean.
MORA_TO_CHARACTERS=0.8         # Cantonese characters written per Japanese mora.
CHARACTERS_PER_SECOND=4.5      # Drafting rate; it caps the mora target for translation.
TAKE_CHARACTERS_PER_SECOND=3.9 # Real engine output rate: median of 167 Drama 3 takes
                               # in the two 2026-10 standard-mode runs (p25 3.0, p75 4.5).
END_GRACE_SECONDS=0.35         # Small tolerance before a take is called an overrun.
_SMALL=set('ゃゅょぁぃぅぇぉャュョァィゥェォ')


def morae(text):
    """Estimate Japanese morae. Small kana merge; a kanji uses the mean weight."""
    total=0.
    for character in str(text or ''):
        code=ord(character)
        if '\u3041'<=character<='\u309f' or '\u30a0'<=character<='\u30ff':
            if character in _SMALL:continue
            total+=1.
        elif 0x4E00<=code<=0x9FFF or 0x3400<=code<=0x4DBF:
            total+=KANJI_MORA
    return total


def source_text(cue):
    """Only a Japanese transcription can be counted. A Chinese caption cannot."""
    for key in ('japanese','japaneseAlt'):
        value=str(cue.get(key) or '')
        if value and any('\u3041'<=c<='\u30ff' for c in value):return value
    return ''


def speech_seconds(cue):
    start=float(cue.get('speechStart',cue.get('start',0)) or 0)
    end=float(cue.get('speechEnd',cue.get('end',0)) or 0)
    return max(0.,end-start)


def active(cfg):
    """A new collapsed-mode job carries the revision stamp written by work_modes."""
    return bool(cfg) and cfg.get('sourceMatchedScriptRevision')==REVISION and not __import__('speech_duration').enabled(cfg)


def target_characters(cfg,cue):
    """A drafting target in Chinese characters. Never a permission to cut words."""
    mora=morae(source_text(cue))
    if mora<=0:return None
    window_target=int(speech_seconds(cue)*CHARACTERS_PER_SECOND)
    matched=int(round(mora*MORA_TO_CHARACTERS))
    if window_target>0:matched=min(matched,window_target)
    return max(2,matched)


def cap_requested(cfg):
    """Keep the finished take inside the witnessed Japanese speech window."""
    return active(cfg) and bool(cfg.get('sourceSpeechEndCap',True))
