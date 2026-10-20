"""Cached frame inventory and photographic memory for local visual classification.

The gallery is appearance evidence only. Source audio and speaking evidence remain
mandatory in visual_speakers.fuse; a face on screen does not identify the speaker.
"""
import hashlib,json,subprocess
from pathlib import Path

def prepare_storyboards(cfg,job,cues,selected):
    from PIL import Image,ImageDraw
    from concurrent.futures import ThreadPoolExecutor
    folder=Path(job)/('visual-storyboards-'+cfg['key'][:12]);folder.mkdir(exist_ok=True)
    width=int(cfg.get('visualFrameWidth',256));width=max(256,min(512,width));height=width*9//16
    def extract(i):
        target=folder/(str(i)+'.jpg')
        if not target.exists():
            sheet=Image.new('RGB',(width*4,height+26),(22,22,22));draw=ImageDraw.Draw(sheet)
            draw.text((4,3),f'ROW index={i}: chronological frames',(255,255,255))
            cue=cues[i];span=max(.1,cue['end']-cue['start'])
            for j,fraction in enumerate((.15,.38,.62,.85)):
                frame=folder/(str(i)+'-extract.jpg')
                subprocess.run([cfg['ffmpeg'],'-v','error','-y','-ss',str(cue['start']+cfg.get('offset',0)+span*fraction),'-threads','1','-i',cfg['video'],'-frames:v','1','-vf',f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2','-update','1',str(frame)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                with Image.open(frame) as image:sheet.paste(image.convert('RGB').resize((width,height)),(width*j,24))
            frame.unlink(missing_ok=True)
            temp=target.with_suffix('.tmp');sheet.save(temp,format='JPEG');temp.replace(target)
        return i,target
    result={}
    # Bounded CPU-only extraction; never load two large inference models together.
    with ThreadPoolExecutor(max_workers=max(1,min(4,int(cfg.get('frameWorkers',1))))) as pool:
      for n,(i,target) in enumerate(pool.map(extract,selected)):
        result[i]=target
        if n%8==0 or n+1==len(selected):print(json.dumps(dict(message=f'建立角色畫面：{n+1}/{len(selected)} 段。',workID='character-frame-inventory',workCompleted=n+1,workTotal=len(selected)),ensure_ascii=False),flush=True)
    manifest=folder/'inventory.json';temp=manifest.with_suffix('.tmp')
    temp.write_text(json.dumps(dict(key=cfg['key'],eligibleIndices=list(selected),frames={str(i):str(p) for i,p in result.items()},frameWidth=width,coverage='all eligible dialogue intervals; four samples per interval'),ensure_ascii=False));temp.replace(manifest)
    return result

def photo_atlas(cfg,job,cues,rows,roster):
    from PIL import Image
    from visual_speakers import valid_box
    from character_observations import portrait_observations
    rows=portrait_observations(rows)
    folder=Path(job)/('visual-identity-photos-'+hashlib.sha256(cfg['key'].encode()).hexdigest()[:12]);folder.mkdir(exist_ok=True)
    gallery=[]
    for ident in [r['id'] for r in roster]:
        candidates=[r for r in rows if r.get('visualId')==ident and r.get('headVisible') is True and r.get('continuousShot') is True and r.get('multipleSpeakers') is False and r.get('confidence',0)>=.85 and valid_box(r.get('characterBox')) and isinstance(r.get('index'),int) and 0<=r['index']<len(cues)]
        candidates=sorted(candidates,key=lambda r:(bool(r.get('speaking') and r.get('mouthChanged')),r.get('confidence',0)),reverse=True)
        photos=[];observations=[]
        for row in candidates[:4 if cfg.get('requireVerifiedPhotos') else 2]:
            cue=cues[row['index']];at=cfg.get('offset',0)+cue['start']+(cue['end']-cue['start'])*.62
            dest=folder/(hashlib.sha256(ident.encode()).hexdigest()[:12]+'-'+str(row['index'])+'.jpg')
            if not dest.exists():
                a,b,c,d=row['characterBox'];left,top=round(a*1152)//2*2,round(b*648)//2*2
                width,height=max(2,round((c-a)*1152)//2*2),max(2,round((d-b)*648)//2*2)
                filters=f'scale=1152:648:force_original_aspect_ratio=decrease,pad=1152:648:(ow-iw)/2:(oh-ih)/2,crop={width}:{height}:{left}:{top}'
                try:subprocess.run([cfg['ffmpeg'],'-v','error','-y','-ss',str(at),'-i',cfg['video'],'-frames:v','1','-vf',filters,'-update','1',str(dest)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                except (OSError,subprocess.SubprocessError):continue
            try:
                with Image.open(dest) as image:image.verify()
                photos.append(str(dest))
                local=cue['start']+(cue['end']-cue['start'])*.62
                original=folder/(str(row['index'])+'-frame.jpg')
                if cfg.get('saveAppearanceFrames') and not original.exists():
                    subprocess.run([cfg['ffmpeg'],'-v','error','-y','-ss',str(at),'-i',cfg['video'],'-frames:v','1','-vf','scale=1280:-2','-update','1',str(original)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                observations.append(dict(avatar=str(dest),sourceFrame=str(original) if original.exists() else '',time=local,index=row['index'],visualId=ident))
            except (OSError,ValueError,subprocess.SubprocessError):continue
        if photos:gallery.append(dict(visualId=ident,photos=photos,observations=observations))
    target=Path(job)/('visual-photo-candidates.json' if cfg.get('requireVerifiedPhotos') else 'visual-photo-atlas.json');temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps(dict(key=cfg['key'],gallery=gallery,method='observed appearance; not speaker proof'),ensure_ascii=False,indent=2));temp.replace(target)
    return gallery

def comparison_sheet(gallery,storyboards,batch,target):
    from PIL import Image,ImageDraw
    # Bounded image context; the model still receives the complete textual roster.
    examples=[(entry['visualId'],path) for entry in gallery[-16:] for path in entry['photos']]
    height=((len(examples)+7)//8)*126
    with Image.open(storyboards[batch[0]]) as first:width,row_height=first.size
    sheet=Image.new('RGB',(width,height+row_height*len(batch)),(22,22,22));draw=ImageDraw.Draw(sheet)
    for n,(ident,path) in enumerate(examples):
        x,y=(n%8)*128,(n//8)*126;draw.text((x+3,y+3),'REFERENCE '+ident,(255,255,255))
        with Image.open(path) as image:
            image=image.convert('RGB');image.thumbnail((122,100));sheet.paste(image,(x+(128-image.width)//2,y+22))
    for n,i in enumerate(batch):
        with Image.open(storyboards[i]) as image:sheet.paste(image,(0,height+row_height*n))
    sheet.save(target)

def inference_images(gallery,storyboards,batch,target):
    """Separate images keep grounding coordinates relative to a real frame.

    A montage is useful for human inspection, but a box grounded to its global
    coordinates silently crops unrelated pixels from the original video.
    """
    from PIL import Image
    comparison_sheet(gallery,storyboards,batch,target)
    examples=[path for entry in gallery[-16:] for path in entry['photos']]
    height=((len(examples)+7)//8)*126
    images=[];mapping=[]
    if height:
        memory=Path(target).with_name('visual-reference-memory.jpg')
        with Image.open(target) as sheet:sheet.crop((0,0,sheet.width,height)).save(memory)
        images.append(str(memory));mapping.append('IMAGE 1 contains only labelled REFERENCE photos; it is not a speech frame.')
    for index in batch:
        with Image.open(storyboards[index]) as sheet:
            width=sheet.width//4;frame_height=sheet.height-26
            numbers=[]
            for n in range(4):
                frame=Path(storyboards[index]).with_name(f'{index}-frame-{n}.jpg')
                sheet.crop((n*width,24,(n+1)*width,24+frame_height)).save(frame)
                images.append(str(frame));numbers.append(len(images))
            mapping.append(f'ROW index={index}: chronological individual IMAGE numbers {numbers}; characterBox is relative ONLY to IMAGE {numbers[2]}.')
    return images,' '.join(mapping)+' Each individual image fills its own coordinate system from 0 to 1; never use montage coordinates.'

REFERENCE_PROMPT='The top REFERENCE tiles are actual previously observed character head photographs, each labelled with its existing visual ID. Compare their face/helmet, hair and outfit with the ROW frames; retain that ID across different angles and expressions when appearance agrees. REFERENCE tiles are NOT chronological frames and must NOT be analysed for speech. Do not invent a new ID merely because an expression changes. The requested ROW frames below are chronological. If none of the photographs applies, consult the existing roster and use unknown when unsure. Never infer the speaker from appearance alone. '
