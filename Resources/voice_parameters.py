"""Bounded, user-facing inference controls for supported voice engines.

These controls change generation, not language verification. Keep defaults in
one place so an untouched Expert panel has the same output as Basic mode.
"""
import math

SPECS = {
    'drama3': {
        'dramaTemperature': (1., .3, 1.2, float),
        'dramaTopP': (.9, .3, 1., float),
        'dramaTopK': (30, 5, 80, int),
    },
    'gpt-sovits': {
        'gptTemperature': (1., .6, 1.2, float),
        'gptTopP': (1., .6, 1., float),
        'gptTopK': (15, 5, 30, int),
        'gptRepetitionPenalty': (1.35, 1., 1.6, float),
        'gsvSampleSteps': (32, 16, 32, int),
    },
    'cosyvoice3': {
        'cosyTemperature': (.7, .3, 1., float),
    },
    'voxcpm2': {
        'voxcpmGuidance': (2., 1., 3., float),
        'voxcpmSteps': (10, 5, 20, int),
    },
    'wsyue': {
        'wsyueSpeed': (1., .8, 1.2, float),
    },
}
GPT = ('gpt-sovits', 'gpt-sovits-v2', 'gpt-sovits-v3')


def family(engine):
    return 'gpt-sovits' if engine in GPT else engine


def keys():
    return {key for group in SPECS.values() for key in group}


def defaults(engine):
    return {key: spec[0] for key, spec in SPECS[family(engine)].items()}


def effective(settings, engine):
    result = {}
    for key, (default, minimum, maximum, kind) in SPECS[family(engine)].items():
        raw = settings.get(key, default)
        if isinstance(raw, bool):
            raise ValueError('Invalid voice parameter: ' + key)
        try:
            value = float(raw)
        except (TypeError, ValueError) as error:
            raise ValueError('Invalid voice parameter: ' + key) from error
        if not math.isfinite(value) or not minimum <= value <= maximum or (kind is int and not value.is_integer()):
            raise ValueError(f'Voice parameter outside supported range: {key} ({minimum:g}–{maximum:g}; default {default:g})')
        result[key] = kind(value)
    if family(engine) == 'gpt-sovits' and result['gsvSampleSteps'] not in (16, 32):
        raise ValueError('GPT-SoVITS steps must be 16 or 32.')
    return result


def validate(settings):
    for engine in SPECS:
        effective(settings, engine)
    from voice_expression import settings as expression_settings
    expression_settings(settings)
    return settings


def overrides(settings, engine):
    if family(engine) not in SPECS:
        return {}  # Retired engines keep their pinned adapter until old jobs finish.
    values = effective(settings, engine)
    return {key: value for key, value in values.items() if value != defaults(engine)[key]}


def drama_sampling(settings):
    values = effective(settings, 'drama3')
    return dict(temperature=values['dramaTemperature'], top_p=values['dramaTopP'], top_k=values['dramaTopK'])
