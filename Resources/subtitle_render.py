"""Portable caption images, with timing independent of host player fonts."""
import json,math
from pathlib import Path


def caption_events(cues,duration):
    events=[];cursor=0
    for cue in cues:
        a=max(0,float(cue.get('subtitleStart',cue['start'])));b=min(duration,float(cue.get('subtitleEnd',cue['end'])))
        if not math.isfinite(a+b) or b<=a or a<cursor-1e-5:raise ValueError('字幕時間無效或重疊，未輸出錯位字幕。')
        if a>cursor:events.append(dict(text='',duration=a-cursor))
        events.append(dict(text=cue.get('cantonese',cue.get('text','')),duration=b-a));cursor=b
    if cursor<duration:events.append(dict(text='',duration=duration-cursor))
    # Explicit empty final frame prevents the last caption from sticking.
    events.append(dict(text='',duration=.04))
    return events


def prepare(cfg,job,cues,meta,run):
    video=next(s for s in meta['streams'] if s.get('codec_type')=='video')
    width,height=int(video['width']),int(video['height'])
    folder=Path(job)/'caption-images';folder.mkdir(exist_ok=True)
    events=caption_events(cues,cfg.get('outputDuration',cfg['duration']))
    request=folder/'request.json';request.write_text(json.dumps(dict(folder=str(folder.resolve()),width=width,height=height,captions=events,bottom=cfg.get("captionBottom",.045),fontSize=cfg.get("captionSize",.043)),ensure_ascii=False))
    run([cfg['executable'],'--render-subtitles',request])
    lines=['ffconcat version 1.0']
    for i,event in enumerate(events):
        lines.extend([f"file '{i:05d}.png'",'option framerate 1000',f"duration {event['duration']:.6f}"])
    lines.append(f"file '{len(events)-1:05d}.png'");lines.append('option framerate 1000')
    manifest=folder/'captions.ffconcat';manifest.write_text('\n'.join(lines)+'\n')
    return manifest


def add_overlay(cmd,manifest,extension):
    cmd=list(cmd);index=cmd.count('-i')
    at=min((i for i,x in enumerate(cmd) if x in ('-filter_complex','-map')),default=len(cmd))
    cmd[at:at]=['-f','concat','-safe','0','-i',manifest]
    video='0:v:0';filters=[]
    if extension:
        filters.append(f'[0:v:0]tpad=stop_mode=clone:stop_duration={extension:.6f}[picture]');video='picture'
    filters.append(f'[{video}][{index}:v:0]overlay=eof_action=pass:shortest=0:format=auto[captioned]')
    if '-filter_complex' in cmd:
        i=cmd.index('-filter_complex')+1;cmd[i]+=';'+';'.join(filters)
    else:cmd.extend(['-filter_complex',';'.join(filters)])
    for i in range(len(cmd)-1):
        if cmd[i]=='-map' and cmd[i+1]=='0:v:0':cmd[i+1]='[captioned]'
    return cmd
