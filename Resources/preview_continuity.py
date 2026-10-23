"""Audible source after bounded repair; never a target-language quality pass.

The finished video and review report retain the defect. Source clocks and the
failed generated take remain intact for later repair.
"""
import array,hashlib,math,wave
from pathlib import Path


def source_audio(cfg,job,cue,run,sr):
    from audio_fallback import healthy
    start=float(cue.get('speechStart',cue['start']));end=float(cue.get('speechEnd',cue['end']))
    # Separated dialogue avoids duplicating the music bed. If separation lost
    # the speech, retain the original mix as the explicitly reported last resort.
    sources=[(Path(cfg.get('dialoguePath','')),0.,'separated-source'),(Path(cfg.get('video','')),float(cfg.get('startOffset',0)),'original-mix')]
    for source,offset,kind in sources:
        if not source.is_file():continue
        key=hashlib.sha256(str([str(source),source.stat().st_mtime_ns,start,end,sr]).encode()).hexdigest()[:24]
        path=Path(job)/'preview-source'/f'{key}.wav';path.parent.mkdir(exist_ok=True)
        if not path.is_file():
            run([cfg['ffmpeg'],'-v','error','-y','-ss',str(start+offset),'-i',source,'-t',str(end-start),'-ar',str(sr),'-ac','1','-c:a','pcm_s16le',path])
        if not healthy(path):continue
        with wave.open(str(path)) as audio:raw=audio.readframes(audio.getnframes())
        pcm=array.array('h');pcm.frombytes(raw)
        if not pcm or max(abs(x) for x in pcm)<40:continue
        # Reject a decode extending outside its immutable source interval.
        if len(pcm)>math.ceil((end-start)*sr)+2:continue
        return path,pcm,round(start*sr),kind
    return None


def fill(cfg,job,cue,row,timeline,run,sr):
    from preview_delivery import allowed
    if not allowed(cfg) or cue.get('editorAudio') or not cue.get('enabled',True):return False
    result=source_audio(cfg,job,cue,run,sr)
    if not result:return False
    path,pcm,offset,kind=result
    from pcm_mix import add
    add(timeline,pcm,offset)
    row.update(previewSourceAudio=str(path),previewSourceKind=kind,originalFallback=True,
               previewAudibleSeconds=len(pcm)/sr,previewRenderedStart=offset/sr,
               qualityCertified=False)
    # Keep skipped/needsReview and failed target audio untouched. Coverage must
    # never count this source speech as a successful translated recording.
    return True
