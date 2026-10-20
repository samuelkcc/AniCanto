"""Keep source bandwidth in role recordings; the 16k speaker embedding is separate."""
def write(path, audio, sample_rate, ranges, short=False):
    import numpy as np
    import soundfile as sf
    clips=[audio[round(a*sample_rate):round(b*sample_rate)] for a,b in ranges]
    if not clips or not any(len(x) for x in clips):raise ValueError('角色原聲範圍無效。')
    reference=np.concatenate(clips)
    if short:reference=np.pad(reference,(0,max(0,round(3.1*sample_rate)-len(reference))))
    sf.write(path,reference,sample_rate,subtype='PCM_16')
