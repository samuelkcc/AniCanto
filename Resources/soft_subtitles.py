"""Selectable original subtitle streams, extracted on the source-video timeline."""
import json
from pathlib import Path


def original_tracks(w,cfg,job):
    indices=cfg.get('originalSubtitleStreams')
    explicit=indices is not None
    indices=indices if explicit else []
    if not isinstance(indices,list) or any(type(i) is not int or i<0 for i in indices):raise ValueError('原片字幕選擇無效。')
    if explicit and not indices:return []
    if not explicit and cfg.get('subtitle') and Path(cfg['subtitle']).is_file():
        from worker import window_subtitles
        path=Path(job)/'original-external.srt'
        w.run([cfg['ffmpeg'],'-v','error','-y','-i',cfg['subtitle'],path])
        cues=window_subtitles(w.parse_srt(path.read_text(encoding='utf-8-sig')),cfg.get('startOffset',0),cfg['duration'])
        if not cues:return []
        w.save_srt(path,cues)
        return [dict(path=path,cues=cues,mode='original',sourceLanguage=cfg.get('sourceCaptionLanguage') or 'und',sourceTitle=Path(cfg['subtitle']).stem)]
    meta=json.loads(w.run([cfg['ffprobe'],'-v','error','-show_streams','-of','json',cfg['video']]))
    available={s['index']:s for s in meta.get('streams',[]) if s.get('codec_type')=='subtitle' and s.get('codec_name') in ('subrip','ass','ssa','webvtt','mov_text','text')}
    if not explicit:
        # Preserve the selected source track, otherwise one preferred original.
        # Do not manufacture a soft original from burnt-in text or Japanese ASR.
        selected=cfg.get('subtitleStream')
        if selected in available:indices=[selected]
        elif available:
            from worker import select_batch_subtitle
            stream=select_batch_subtitle(list(available.values()),'zho')
            indices=[stream['index']] if stream else []
    result=[]
    seen=set()
    for index in dict.fromkeys(indices):
        if index not in available:raise ValueError('所選原片文字字幕軌不存在；配音已保留，可以重新選擇字幕再匯出。')
        stream=available[index];tags=stream.get('tags',{});path=Path(job)/f'original-stream-{index}.srt'
        w.run([cfg['ffmpeg'],'-v','error','-y','-ss',str(cfg.get('startOffset',0)),'-i',cfg['video'],'-map',f'0:{index}','-t',str(cfg['duration']),'-c:s','srt',path])
        cues=w.parse_srt(path.read_text());cues=[dict(c,cantonese=c['text']) for c in cues]
        language=tags.get('language','und');language={'zh':'zho','chi':'zho','ja':'jpn','en':'eng'}.get(language,language)
        signature=(language,tuple((round(c['start'],3),round(c['end'],3),c['text'].strip()) for c in cues))
        if not cues or signature in seen:continue
        seen.add(signature)
        result.append(dict(path=path,cues=cues,mode='original',sourceLanguage=language,sourceTitle=tags.get('title') or language,sourceStream=index))
    return result
