"""Finite whole-gallery comparison before acoustic/visual identity fusion.

Pixel descriptors retrieve candidates only. The local vision model compares
actual photographs; co-visible heads veto merging and compatible source voice
is still required by visual_speakers.fuse. No text-name-only identity merging.
"""
import hashlib,json
from pathlib import Path


def candidate_pairs(gallery):
    import numpy as np
    from PIL import Image
    vectors={}
    for entry in gallery:
        features=[]
        for path in entry['photos']:
            with Image.open(path) as im:
                im=im.convert('RGB').resize((12,12));pixels=np.asarray(im,dtype=np.float32)/255
                # Spatial and channel information retrieves similarly dressed
                # heads; it MUST NOT be interpreted as person identity.
                feature=pixels.flatten();feature/=max(1e-8,float(np.linalg.norm(feature)));features.append(feature)
        if features:vectors[entry['visualId']]=features
    pairs=set()
    for a,features in vectors.items():
        ranked=sorted(((max(float(x@y) for x in features for y in other),b) for b,other in vectors.items() if b!=a),reverse=True)
        for score,b in ranked[:2]:
            if score>=.65:pairs.add(tuple(sorted((a,b))))
    return sorted(pairs)


def conflicting_pairs(rows):
    result=set()
    for row in rows:
        ids=list(dict.fromkeys(p['visualId'] for p in row.get('characters',[]) if p.get('visualId','').startswith('v')))
        for n,a in enumerate(ids):
            for b in ids[n+1:]:result.add(tuple(sorted((a,b))))
    return result


def consolidate(cfg,job,cues,rows,roster,gallery,compare):
    from PIL import Image,ImageDraw
    job=Path(job);target=job/'visual-appearance-links.json'
    by_id={p['visualId']:p for p in gallery};pairs=candidate_pairs(gallery);conflicts=conflicting_pairs(rows)
    # Exclude known co-visible identities before inference, not just afterwards.
    pairs=[p for p in pairs if p not in conflicts]
    fingerprint=hashlib.sha256(json.dumps([cfg['key'],pairs,[(p,hashlib.sha256(Path(p).read_bytes()).hexdigest()) for entry in gallery for p in entry['photos']]]).encode()).hexdigest()
    old=json.loads(target.read_text()) if target.exists() else {}
    decisions=old.get('decisions',[]) if old.get('key')==fingerprint else []
    done={tuple(d['pair']) for d in decisions};pending=[p for p in pairs if p not in done]
    for offset in range(0,len(pending),4):
        batch=pending[offset:offset+4];sheet=Image.new('RGB',(1024,270*len(batch)),(22,22,22));draw=ImageDraw.Draw(sheet)
        for n,(a,b) in enumerate(batch):
            for side,ident in enumerate((a,b)):
                draw.text((side*512+4,n*270+4),'PAIR '+a+' '+b+' / '+ident,(255,255,255))
                for k,path in enumerate(by_id[ident]['photos'][:2]):
                    with Image.open(path) as im:
                        im=im.convert('RGB');im.thumbnail((246,235));sheet.paste(im,(side*512+k*256,n*270+28))
        image=job/'visual-appearance-comparison.jpg';sheet.save(image)
        try:reply=compare(image,batch)
        except (ValueError,RuntimeError) as error:reply={};failure=str(error)[:250]
        else:failure=''
        for a,b in batch:
            found=[r for r in reply.get('pairs',[]) if isinstance(r,dict) and r.get('left')==a and r.get('right')==b] if isinstance(reply,dict) else []
            d=found[0] if len(found)==1 else {}
            accepted=(d.get('sameAppearance') is True and d.get('distinctiveAgreement') is True and
                      type(d.get('confidence')) in (int,float) and .98<=d['confidence']<=1)
            decisions.append(dict(pair=[a,b],accepted=accepted,evidence=d,error=failure))
        temp=target.with_suffix('.tmp');temp.write_text(json.dumps(dict(key=fingerprint,status='partial',decisions=decisions),ensure_ascii=False));temp.replace(target)
        print(json.dumps(dict(message=f'全片角色相片比對：{len(decisions)}/{len(pairs)} 組；結果已保存。',workID='character-photo-comparison',workCompleted=len(decisions),workTotal=len(pairs)),ensure_ascii=False),flush=True)
    parent={ident:ident for ident in by_id}
    def family(ident):return [x for x in parent if parent[x]==parent[ident]]
    # Require complete pair support; A~B and B~C cannot blindly merge A and C.
    accepted={tuple(d['pair']) for d in decisions if d['accepted']}
    for a,b in sorted(accepted):
        fa,fb=family(a),family(b)
        if parent[a]==parent[b]:continue
        if all(tuple(sorted((x,y))) in accepted and tuple(sorted((x,y))) not in conflicts for x in fa for y in fb):
            keeper=parent[a]
            for ident in fb:parent[ident]=keeper
    for row in rows:
        ident=row.get('visualId');selected=parent.get(ident,ident)
        if selected!=ident:row.update(sourceVisualId=ident,visualId=selected)
        for person in row.get('characters',[]):
            ident=person['visualId'];selected=parent.get(ident,ident)
            if selected!=ident:person.update(sourceVisualId=ident,visualId=selected)
        for field in ('visibleCharacterIds','activeCharacterIds'):
            if field in row:row[field]=[parent.get(i,i) for i in row[field]]
    temp=target.with_suffix('.tmp');temp.write_text(json.dumps(dict(key=fingerprint,status='complete',decisions=decisions,aliases=parent,coVisibleConflicts=[list(p) for p in sorted(conflicts)],method='local-photo-comparison; acoustic speaker fusion still required; confidence uncalibrated'),ensure_ascii=False,indent=2));temp.replace(target)
    return rows
