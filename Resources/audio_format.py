"""Preserve native GPT bandwidth in delivery; carrier rate is not a quality claim."""
REVISION = 'gpt-native-bandwidth-1'

def delivery_rate(cfg):
    requested = cfg.get('audioSampleRate')
    if requested is not None:
        rate = int(requested)
        if rate not in (24000, 32000, 44100, 48000):
            raise ValueError('Unsupported audio delivery sample rate.')
        return rate
    # V4 generates native 48 kHz; delivery must retain it end to end.
    from gsv_versions import VERSIONS,RATES
    engine=cfg.get('ttsBackend')
    if engine=='voxcpm2':return 48000
    if engine=='drama3':return 44100
    return RATES[VERSIONS[engine]] if engine in VERSIONS else 24000
