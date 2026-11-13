"""Share name requests and source-only exclusion rules with mobile production."""
import re

REVISION = 'names-and-sustained-source-441'


def configure(cfg, basic=False):
    cfg['dialoguePolicyRevision'] = REVISION
    cfg['keepOriginalNamePronunciation'] = False if basic else bool(cfg.get('keepOriginalNamePronunciation', False))


def instruction(cfg):
    if cfg.get('dialoguePolicyRevision') != REVISION:
        return ''
    names = ('Represent the original name pronunciation in a speakable target-language script. This name rule overrides glossary spelling. '
             if cfg.get('keepOriginalNamePronunciation') else
             'Use source-supported translated names or their literal target-language reading. ')
    return (' NAME POLICY: ' + names + 'Translate and dub name-only calls and complete dialogue. '
            'Never omit a name, return untranslated kana, or change the speaker reference. ')


def source_unconfirmed(cue):
    from primary_source import authored, content
    if authored(cue) and content(cue).strip():
        return False
    if any(str(cue.get(k, '') or '').strip() for k in ('cantonese', 'english', 'mandarin')):
        return False
    return bool(cue.get('sourcePolicyBlocked') or cue.get('originalSpeechReason') in
                ('uncertain-source-clock', 'source-recognition-unconfirmed', 'source-content-unavailable'))


def excluded_card(cue):
    return bool(cue.get('noSpeech') or cue.get('opEdKind') or
                str(cue.get('japanese') or cue.get('text') or '').strip() == '[NO_SPEECH]')


def prepare(cfg, cues):
    if cfg.get('dialoguePolicyRevision') != REVISION:
        return
    from primary_source import authored
    for cue in cues:
        # Authored content and existing takes override this narrow source pattern.
        if authored(cue) or cue.get('editorAudio') or cue.get('sourcePolicyBlocked'):
            continue
        if any(str(cue.get(k, '') or '').strip() for k in ('cantonese', 'english', 'mandarin')):
            continue
        source = str(cue.get('japanese') or cue.get('text') or '')
        compact = re.sub(r'[\s。、，,.!！?？…ー〜～―—-]', '', source)
        if re.fullmatch(r'([あア啊])\1{3,}', compact):
            cue.update(preserveOriginalSpeech=True, originalSpeechReason='sustained-source-vocalization')
