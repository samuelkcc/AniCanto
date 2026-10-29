"""Output caption policy, independent of the evidence used for translation."""


def automatic_modes(languages):
    languages=set(languages or ['yue'])
    return ([m for lang,m in (('yue','yue'),('zh','zh'),('en','english')) if lang in languages]
            + (['dual'] if {'yue','en'}<=languages else []) + ['original'])


def configure(settings, basic=False):
    """Project future submissions only; never mutate an in-flight request."""
    if basic or settings.get('subtitleSelection','automatic')=='automatic':
        settings['subtitleModes']=automatic_modes(settings.get('dubLanguages'))
    if basic:
        settings.update(subtitleSelection='automatic',includeOriginal=True,
                        separateBackground=True,mixOriginal=0,backgroundDucking=True,
                        burnOutputCaptions=False,
                        autoSkipOP=True,translateOPED=False)
        settings.pop('originalSubtitleStreams',None)
    return settings
