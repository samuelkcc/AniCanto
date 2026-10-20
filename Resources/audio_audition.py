"""One native-rate audition, with no timeline allocation or movie encoding."""
import hashlib
from pathlib import Path


class AuditionRejected(ValueError):
    def __init__(self,message,audio):
        super().__init__(message);self.audio=Path(audio)


def generate(w,cfg,folder,cue):
    import dubbing,speechcheck
    from reference_quality import read
    cue=dict(cue)
    for key in ('editorAudio','editorAudioBackend','editorAudioLanguage'):
        cue.pop(key,None)
    paths=dubbing.gsv_audio(cfg,folder,[cue],w.run,w.emit)
    path=paths[0]
    if not path.is_file() or path.name.startswith(('skipped-','failed-')):
        raise ValueError('這句配音未成功生成，請檢查生成紀錄。')
    samples,rate=read(path)
    seconds=len(samples)/rate
    check=speechcheck.inspect(cfg,folder,[cue],[path],w.emit)[0]
    profile=dubbing.profile_for(cue,cfg)
    w.atomic_json(Path(folder)/'voice-reference-manifest.json',{profile['id']:hashlib.sha256(Path(profile['reference']).read_bytes()).hexdigest()})
    row=dict(start=cue['start'],end=cue['end'],audio=str(path),renderedAudio=str(path),seconds=seconds,renderedSeconds=seconds,rate=1,sampleRate=rate,speechCheck=check)
    w.atomic_json(Path(folder)/'timing.json',[row])
    w.atomic_json(Path(folder)/'report.json',dict(preview=True,duration=seconds,speechCheck=check,pronunciationStatus='requires-audition'))
    from cantonese_review import needs_repair
    import numpy as np
    audible=bool(len(samples) and np.isfinite(samples).all() and np.max(np.abs(samples))>.001)
    advisory=cfg.get('targetLanguage','yue')=='yue' and not needs_repair(cue,check,'yue')
    if not audible or (not advisory and not check.get('heard','').strip()):
        row['skipped']=True;row['reason']='generated-speech-unrecognized'
        w.atomic_json(Path(folder)/'timing.json',[row])
        raise AuditionRejected('未能辨認有效對白；請試聽後重生或更換同角色參考。',path)
    if not advisory and (check.get('languageMismatch') or check.get('criticalDifferences')):
        row['skipped']=True;row['reason']='critical-speech-review'
        w.atomic_json(Path(folder)/'timing.json',[row])
        raise AuditionRejected('語言或關鍵字核對未通過；請試聽後調整或重生。',path)
    profile=dubbing.profile_for(cue,cfg)
    w.atomic_json(Path(folder)/'voice-reference-manifest.json',{profile['id']:hashlib.sha256(Path(profile['reference']).read_bytes()).hexdigest()})
    return path,seconds
