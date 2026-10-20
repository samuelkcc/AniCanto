"""Bounded local visual inspection before cropped heads enter photo memory.

A source-frame box is only a proposal. Reinspect the actual resulting crop:
recognizable single head, appearance agreement, no hand/hair-only/group crop.
Decisions are cached, with at most eight inspections per appearance identity.
"""
import hashlib,json
from pathlib import Path


def validate(gallery,roster,job,infer,key):
    from PIL import Image,ImageDraw
    job=Path(job);target=job/'visual-portrait-checks.json'
    old=json.loads(target.read_text()) if target.exists() else {}
    decisions=old.get('decisions',{}) if old.get('key')==key else {}
    appearances={r['id']:r['appearance'] for r in roster}
    pending=[];lookups={};counts={}
    for d in decisions.values():counts[d['visualId']]=counts.get(d['visualId'],0)+1
    for entry in gallery:
        ident=entry['visualId'];description=appearances.get(ident,'')
        for photo in entry.get('observations',[]):
            path=Path(photo['avatar']);fingerprint=hashlib.sha256(path.read_bytes()+description.encode()).hexdigest()
            lookups[path.as_posix()]=fingerprint
            if fingerprint in decisions:continue
            if counts.get(ident,0)>=8:continue
            counts[ident]=counts.get(ident,0)+1
            pending.append(dict(photo,appearance=description,fingerprint=fingerprint))
    for offset in range(0,len(pending),4):
        batch=pending[offset:offset+4];sheet=Image.new('RGB',(1024,260*len(batch)),(22,22,22));draw=ImageDraw.Draw(sheet)
        for n,photo in enumerate(batch):
            draw.text((6,n*260+4),f"CROP index={n} / {photo['visualId']}     SOURCE FRAME on right",fill='white')
            with Image.open(photo['avatar']) as im:
                im=im.convert('RGB');im.thumbnail((260,228));sheet.paste(im,((270-im.width)//2,n*260+26))
            if photo.get('sourceFrame'):
                with Image.open(photo['sourceFrame']) as im:
                    im=im.convert('RGB');im.thumbnail((740,228));sheet.paste(im,(280,n*260+26))
        image=job/'visual-portrait-inspection.jpg';sheet.save(image)
        try:reply=infer(image,[dict(index=n,visualId=p['visualId'],appearance=p['appearance']) for n,p in enumerate(batch)])
        except (ValueError,RuntimeError,OSError) as error:reply={};failure=str(error)[:250]
        else:failure=''
        for n,photo in enumerate(batch):
            matches=[r for r in reply.get('crops',[]) if isinstance(r,dict) and r.get('index')==n] if isinstance(reply,dict) else []
            evidence=matches[0] if len(matches)==1 else {}
            accepted=(evidence.get('usableHead') is True and evidence.get('singleHead') is True and evidence.get('matchesAppearance') is True and type(evidence.get('confidence')) in (int,float) and .9<=evidence['confidence']<=1)
            decisions[photo['fingerprint']]=dict(visualId=photo['visualId'],accepted=accepted,photo=photo['avatar'],evidence=evidence,error=failure)
        temp=target.with_suffix('.tmp');temp.write_text(json.dumps(dict(key=key,decisions=decisions,method='local crop inspection; not certified identity'),ensure_ascii=False,indent=2));temp.replace(target)
        print(json.dumps(dict(message=f'頭像品質核對：已檢查 {len(decisions)} 張；只保留獨立、可辨識頭像。'),ensure_ascii=False),flush=True)
    result=[]
    for entry in gallery:
        passed=[p for p in entry.get('observations',[]) if decisions.get(lookups.get(p['avatar'],''),{}).get('accepted')]
        if passed:result.append(dict(entry,observations=passed[:2],photos=[p['avatar'] for p in passed[:2]],portraitEvidence='local crop inspection; not speaker proof'))
    temp=target.with_suffix('.tmp');temp.write_text(json.dumps(dict(key=key,decisions=decisions,method='local crop inspection; not certified identity'),ensure_ascii=False,indent=2));temp.replace(target)
    atlas=job/'visual-photo-atlas.json';temp=atlas.with_suffix('.tmp');temp.write_text(json.dumps(dict(key=key,gallery=result,method='inspected single-head appearance; not speaker proof'),ensure_ascii=False,indent=2));temp.replace(atlas)
    return result
