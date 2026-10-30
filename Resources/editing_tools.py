"""Bounded, read-only editing evidence and explicit previews. No model calls."""
import array,copy,hashlib,json,math,subprocess,sys
from pathlib import Path


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def finite(value):
    number=float(value)
    if not math.isfinite(number):raise ValueError('Enter a finite time in seconds.')
    return number


def alignment(captions,params):
    mode=params.get('mode','offset');offset=finite(params.get('offset',0));scale=1.
    if mode=='anchors':
        a,b,c,d=(finite(params.get(k)) for k in ('subtitle1','video1','subtitle2','video2'))
        if c-a<1 or d<=b:raise ValueError('Choose two ordered anchors at least one second apart.')
        scale=(d-b)/(c-a);offset=b-scale*a
        if not .5<=scale<=2:raise ValueError('The anchor timing differs too much. Check the selected video and subtitles.')
    elif mode!='offset':raise ValueError('Unknown subtitle timing mode.')
    result=[]
    for cue in captions:
        start=finite(cue['start'])*scale+offset;end=finite(cue['end'])*scale+offset
        if start<0 or end<=start:raise ValueError('This adjustment creates negative or invalid subtitle times.')
        result.append(dict(cue,start=round(start,3),end=round(end,3),originalStart=cue['start'],originalEnd=cue['end']))
    return dict(scale=scale,offset=offset,cues=result)


def impact(review,draft,params):
    operation=params.get('operation');allowed={'selected','all','append','replace','remix','analysis'}
    if operation not in allowed:raise ValueError('Choose a recording update action.')
    segments=[s for s in draft.get('segments',[]) if s.get('enabled',True)]
    selected=params.get('segment');affected=[s['id'] for s in segments if operation!='selected' or s['id']==selected]
    if operation=='selected' and not affected:raise ValueError('Select a dialogue before generating a new take.')
    cfg=draft.get('settings',{});pairs=cfg.get('_trackPairs') or [[l,e] for l in cfg.get('dubLanguages',['yue']) for e in cfg.get('selectedEngines',[cfg.get('ttsBackend','drama3')])]
    target=[params.get('language','yue'),params.get('engine') or cfg.get('ttsBackend','drama3')]
    tracks=pairs if operation in ('all','analysis','remix') else [target]
    changed=dict(operation=operation,segment=selected,engine=target[1],language=target[0],replaced=params.get('replaced'))
    return dict(token=fingerprint([review,draft,changed]),operation=operation,dialogueIDs=affected if operation!='remix' else [],dialogueCount=len(affected) if operation!='remix' else 0,tracks=tracks,
        retainsSourceAnalysis=operation!='analysis',retainsScripts=operation!='analysis',retainsPreviousRecordings=True,retainsPreviousExports=True,
        retainedTracks=[p for p in pairs if p not in tracks and p!=params.get('replaced')],parameters={k:v for k,v in cfg.items() if k.startswith(('gsv','cosy','drama','voice'))})


def coverage(snapshot):
    review=snapshot.get('review',{});cfg=review.get('config',{});cues=review.get('cues',[])
    pairs=cfg.get('_trackPairs') or [[l,e] for l in cfg.get('dubLanguages',['yue']) for e in cfg.get('selectedEngines',[cfg.get('ttsBackend','drama3')])]
    takes=snapshot.get('takes',[]);issues=snapshot.get('issues',[]);rows=[]
    for language,engine in pairs:
        current=[x for x in snapshot.get('reportRows',[]) if x['engine']==engine and x['language']==language]
        if current:
            required=[x for x in current if x['reportGroup']!='reportPreserved']
            rows.append(dict(language=language,engine=engine,expected=len(required),recordings=sum(bool(x.get('recordingAvailable')) for x in required),missing=[x['index'] for x in required if x['reportGroup']=='reportMissing'],sourcePreserved=len(current)-len(required),checking=sum(x['reportGroup']=='checking' for x in current),presenceOnly=True));continue
        delivered=next((t for t in snapshot.get('deliveryCoverage',{}).get('tracks',[]) if t['engine']==engine and t['language']==language),None)
        if delivered is not None:
            rows.append(dict(language=language,engine=engine,expected=delivered['required'],recordings=delivered['available'],missing=[r['index'] for r in delivered['rows'] if not r['available']],sourcePreserved=delivered.get('sourcePreservedCount',0),presenceOnly=True));continue
        expected=[i+1 for i,c in enumerate(cues) if c.get('enabled',True) and not c.get('preserveOriginalSpeech')]
        existing={x.get('index') for x in takes if x.get('language')==language and x.get('engine')==engine and Path(x.get('audio') or '/nonexistent').is_file()}
        rows.append(dict(language=language,engine=engine,expected=len(expected),recordings=len(set(expected)&existing),missing=[i for i in expected if i not in existing]))
    return dict(tracks=rows,notes=len(issues),stale=len(snapshot.get('staleRecordings',[])),outputPresent=bool(snapshot.get('currentOutput') and Path(snapshot['currentOutput']).is_file()),automaticRepair='missing-or-corrupt-only',qualityCertified=False)


def boundaries(review,analysis):
    proposals=[];cues=review.get('cues',[])
    for index,cue in enumerate(cues):
        start,end=cue['start'],cue['end'];words=[]
        for segment in analysis.get('segments',[]):
            if segment.get('sourceClockUnconfirmed'):continue
            words.extend(w for w in segment.get('words',[]) if all(isinstance(w.get(k),(int,float)) and math.isfinite(w[k]) for k in ('start','end')) and start<=w['start']<w['end']<=end and w.get('probability',0)>=.5)
        words.sort(key=lambda w:w['start'])
        for left,right in zip(words,words[1:]):
            gap=right['start']-left['end'];punctuation=str(left.get('word','')).rstrip().endswith(('。','！','？','!','?'))
            if gap>=.5 or gap>=.2 and punctuation:
                cut=right['start']
                if cut-start<.3 or end-cut<.3:continue
                proposals.append(dict(kind='split',index=index,seconds=cut,evidence='measured-word-gap',gap=round(gap,3),before=left.get('word',''),after=right.get('word','')))
        if index+1<len(cues):
            nxt=cues[index+1];gap=nxt['start']-end
            left=[w for s in analysis.get('segments',[]) if not s.get('sourceClockUnconfirmed') for w in s.get('words',[]) if abs(w.get('end',-99)-end)<.15]
            right=[w for s in analysis.get('segments',[]) if not s.get('sourceClockUnconfirmed') for w in s.get('words',[]) if abs(w.get('start',-99)-nxt['start'])<.15]
            if 0<=gap<.25 and nxt['end']-start<=8 and cue.get('speakerId')==nxt.get('speakerId') and left and right:
                proposals.append(dict(kind='merge',index=index,seconds=end,evidence='adjacent-word-clocks',gap=round(gap,3)))
    return proposals


def waveform(path,start,end,ffmpeg,cache):
    path=Path(path).resolve();start=finite(start);end=finite(end)
    if not path.is_file() or start<0 or not start<end or end-start>180:raise ValueError('Choose an existing audio interval up to three minutes.')
    st=path.stat();key=fingerprint([str(path),st.st_size,st.st_mtime_ns,start,end,'peaks-1'])
    target=Path(cache)/(key+'.json')
    if target.is_file():return json.loads(target.read_text())
    result=subprocess.run([str(ffmpeg),'-v','error','-nostdin','-ss',str(start),'-i',str(path),'-t',str(end-start),'-vn','-ac','1','-ar','2000','-f','f32le','pipe:1'],capture_output=True,timeout=20,check=True)
    samples=array.array('f');samples.frombytes(result.stdout)
    if sys.byteorder!='little':samples.byteswap()
    if not samples:raise ValueError('This interval contains no readable audio samples.')
    end=min(end,start+len(samples)/2000)
    stride=max(1,math.ceil(len(samples)/1000));peaks=[round(max((abs(x) for x in samples[i:i+stride] if math.isfinite(x)),default=0),5) for i in range(0,len(samples),stride)]
    response=dict(path=str(path),start=start,end=end,peaks=peaks,peak=max(peaks,default=0),sampledSeconds=len(samples)/2000)
    from atomic_files import write_json
    write_json(target,response);return response


def boundary_token(review,analysis,draft):return fingerprint([review,analysis,draft])


def apply_boundary(review,analysis,draft,params):
    if params.get('token')!=boundary_token(review,analysis,draft):raise ValueError('The draft or source evidence changed. Refresh the suggestions.')
    proposals=boundaries(review,analysis);index=params.get('proposalIndex')
    if not isinstance(index,int) or not 0<=index<len(proposals):raise ValueError('Choose a current boundary suggestion.')
    proposal=proposals[index];result=copy.deepcopy(draft);segments=result['segments']
    matches=[i for i,s in enumerate(segments) if s.get('sources')==[proposal['index']]]
    if len(matches)!=1:raise ValueError('This source dialogue has already been edited.')
    i=matches[0];segment=segments[i]
    if segment.get('reviewDecisions'):raise ValueError('Remove or review explicit voice overrides before changing this boundary.')
    import uuid
    if proposal['kind']=='split':
        cut=proposal['seconds']
        if not segment['start']<cut<segment['end']:raise ValueError('This boundary is outside the current dialogue.')
        left=copy.deepcopy(segment);right=copy.deepcopy(segment);left['end']=cut;right['start']=cut
        left.update(captionStart=left['start'],captionEnd=cut,trimStart=0,trimEnd=0);right.update(captionStart=cut,captionEnd=right['end'],trimStart=0,trimEnd=0)
        for key in ('original','text','english','mandarin','captionText'):
            if not segment.get(key,'').strip():continue
            parts=params.get('parts',{}).get(key,{})
            if not all(isinstance(parts.get(k),str) and parts[k].strip() for k in ('left','right')):raise ValueError('Provide the text on both sides for every existing script.')
            left[key]=parts['left'].strip();right[key]=parts['right'].strip()
        left['id']='split-'+uuid.uuid4().hex;right['id']='split-'+uuid.uuid4().hex
        segments[i:i+1]=[left,right]
    else:
        if i+1>=len(segments) or segments[i+1].get('sources')!=[proposal['index']+1]:raise ValueError('The next dialogue has already changed.')
        nxt=segments[i+1]
        if bool(segment.get('enabled',True))!=bool(nxt.get('enabled',True)):raise ValueError('These dialogues have different enabled states. Keep them separate.')
        if any(x.get('trimStart',0) or x.get('trimEnd',0) or x.get('rate',1)!=segment.get('rate',1) for x in (segment,nxt)):raise ValueError('These dialogues have manual trims or different rates. Keep them separate.')
        if nxt.get('reviewDecisions'):raise ValueError('Review the next dialogue voice override first.')
        merged=copy.deepcopy(segment);merged.update(id='merge-'+uuid.uuid4().hex,end=nxt['end'],captionEnd=nxt.get('captionEnd',nxt['end']),sources=segment['sources']+nxt['sources'])
        if bool(segment.get('preserveOriginalSpeech'))!=bool(nxt.get('preserveOriginalSpeech')):raise ValueError('These dialogues have different original-voice choices. Keep them separate.')
        for key in ('original','text','english','mandarin','captionText'):merged[key]=' '.join(x[key].strip() for x in (segment,nxt) if x.get(key,'').strip())
        segments[i:i+2]=[merged]
    return result
