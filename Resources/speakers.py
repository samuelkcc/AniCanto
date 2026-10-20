"""Local speaker embeddings, clustering and automatic reference selection.

Voice IDs are acoustic groups within one video, not inferred character names.
"""
from whisper_audio import load as whisper_pcm
import hashlib
import json
from pathlib import Path

MODEL_REV = 'f0c48c298fd835726c27956a5d617bad7115627e'
MODEL_SHA = '7bb2f06e9df17cdf1ef14ee8a15ab08ed28e8d0ef5054ee135741560df2ec068'
REVISION = 'wespeaker-recurring-identities-10-native-references'


def audit_references(cues,profiles):
    """Expose uncertain source identity separately from generated-voice similarity."""
    lookup={p['id']:p for p in profiles};rows=[]
    for i,c in enumerate(cues):
        p=lookup.get(c.get('speakerId'));reasons=[]
        if p is None:reasons.append('missing-reference')
        else:
            if p.get('shortReference'):reasons.append('short-source-reference')
            if p.get('mixedReference'):reasons.append('mixed-source-reference')
            if not p.get('promptText','').strip():reasons.append('missing-reference-transcript')
        note=c.get('speakerNote','')
        if any(w in note for w in ('多個聲線','短句','太短','太弱','相近聲線')):reasons.append('uncertain-source-speaker')
        rows.append(dict(index=c.get('reviewIndex',i)+1,speakerId=c.get('speakerId'),reasons=reasons))
    return dict(rows=rows,reviewIndices=[r['index'] for r in rows if r['reasons']],method='source-reference evidence, not certified character identity')


def group_turns(cues, max_seconds=8):
    """Adapt a continuous speaker turn as a whole, retaining every source part."""
    result=[]
    for source in cues:
        cue=dict(source)
        cue['sourceParts']=[dict(start=cue['start'],end=cue['end'],japanese=cue.get('japanese',cue['text']),japaneseAlt=cue.get('japaneseAlt',''))]
        previous=result[-1] if result else None
        same=previous and previous.get('speakerId') and previous.get('speakerId')==cue.get('speakerId')
        if (same and previous.get('enabled',True) and cue.get('enabled',True)
                and 0<=cue['start']-previous['end']<=.25
                and cue['end']-previous['start']<=max_seconds
                and cue.get('previousSpeakerSimilarity',1)>=.5
                and '多個聲線' not in previous.get('speakerNote','')+cue.get('speakerNote','')):
            previous['text']+=' '+cue['text']
            previous['japanese']=previous['text']
            previous['japaneseAlt']=' '.join(x for x in [previous.get('japaneseAlt',''),cue.get('japaneseAlt','')] if x)
            previous['sourceParts']+=cue['sourceParts']
            previous['asrConfidence']=min(previous.get('asrConfidence',1),cue.get('asrConfidence',1))
            for key in ('end','speechEnd','deliveryEnd','sourceEnd'):
                if key in cue: previous[key]=cue[key]
            hints=previous.get('subtitleHint','').split(' ／ ')+cue.get('subtitleHint','').split(' ／ ')
            previous['subtitleHint']=' ／ '.join(dict.fromkeys(h for h in hints if h))
            previous['reviewNote']='同一聲線連續對白，按完整語意同整段時長改寫配音。'
        else: result.append(cue)
    return result


def prepare(root):
    from dubbing_setup import download
    path = Path(root) / 'models/speakers/voxceleb_resnet34_LM.onnx'
    download(f'https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM/resolve/{MODEL_REV}/{path.name}', path, MODEL_SHA)
    from model_licenses import install_auxiliary_notices
    install_auxiliary_notices('Wespeaker/wespeaker-voxceleb-resnet34-LM',path.parent)
    import onnxruntime as ort
    ort.InferenceSession(str(path), providers=['CPUExecutionProvider'])
    (Path(root) / 'speakers-ready.json').write_text(json.dumps({'revision': REVISION, 'sha256': MODEL_SHA}))


def cluster_embeddings(embeddings, threshold=0.60):
    import numpy as np
    from sklearn.cluster import AgglomerativeClustering
    values = np.asarray(embeddings, dtype=np.float32)
    if len(values) == 1:
        return [0]
    labels = AgglomerativeClustering(n_clusters=None, metric='cosine', linkage='complete', distance_threshold=threshold).fit_predict(values)
    # Stable, human-readable ordering follows the first appearance.
    order = {}
    return [order.setdefault(int(label), len(order)) for label in labels]


def stable_assignments(matrix, entries, with_evidence=False):
    """Separate positive novelty from ambiguity; do not invent a new person on a tie.

    IDs remain acoustic hypotheses until corroborated visually. Thresholds are
    similarity heuristics, not calibrated identity probabilities.
    """
    import numpy as np
    if not entries:return ([],[]) if with_evidence else []
    matrix=np.asarray(matrix,dtype=np.float32)
    seeds=[i for i,e in enumerate(entries) if e['end']-e['start']>=2.5 and not e['mixed'] and e.get('quality',{}).get('score',100)>=70]
    if not seeds:
        seeds=[max(range(len(entries)),key=lambda i:entries[i]['end']-entries[i]['start'])]
    groups=cluster_embeddings(matrix[seeds])
    # Complete-linkage protects against unrelated voices but can split one
    # recurring voice when a single emotional delivery differs. Reconcile only
    # strongly matching prototypes, retaining pairwise family and overlap guards.
    initial={g:[i for i,k in zip(seeds,groups) if k==g] for g in set(groups)}
    def compatible(left,right):
        av=matrix[left].mean(axis=0);bv=matrix[right].mean(axis=0)
        cosine=float(av@bv)/(float(np.linalg.norm(av)*np.linalg.norm(bv))+1e-8)
        cross=matrix[left]@matrix[right].T
        overlap=any(entries[a]['start']<entries[b]['end'] and entries[b]['start']<entries[a]['end'] for a in left for b in right)
        return not overlap and cosine>=.75 and float(cross.min())>=.30 and float(np.median(cross))>=.55
    families=[]
    for g in sorted(initial):
        target=next((family for family in families if all(compatible(initial[g],initial[other]) for other in family)),None)
        if target is None:families.append([g])
        else:target.append(g)
    merged={g:n for n,family in enumerate(families) for g in family}
    groups=[merged[g] for g in groups]
    labels=[None]*len(entries)
    for i,g in zip(seeds,groups): labels[i]=g
    anchors={g:[i for i,k in zip(seeds,groups) if k==g] for g in set(groups)}
    evidence=[dict(state='acoustic-anchor',reason='long-source-utterance') if i in seeds else None for i in range(len(entries))]
    # Assign longer remaining evidence first so a unique short character can
    # form a group without borrowing a nearby but acoustically unrelated voice.
    for i in sorted((i for i in range(len(entries)) if i not in seeds),key=lambda i:entries[i]['end']-entries[i]['start'],reverse=True):
        scores=[]
        for g,indices in anchors.items():
            similarity=matrix[indices]@matrix[i]
            scores.append((float(.65*np.max(similarity)+.35*np.mean(similarity)),g,float(np.max(similarity))))
        scores.sort(reverse=True)
        score,group,peak=scores[0]
        margin=score-scores[1][0] if len(scores)>1 else score
        if peak>=.38 and score>=.34:
            labels[i]=group
            evidence[i]=dict(state='acoustic-match' if margin>=.035 and not entries[i]['mixed'] else 'uncertain',reason='compatible-source-voice' if margin>=.035 else 'tied-candidates',score=score,margin=margin)
        elif peak<.30 and entries[i]['end']-entries[i]['start']>=1.2 and not entries[i]['mixed'] and entries[i].get('quality',{}).get('score',100)>=70:
            group=max(anchors)+1;anchors[group]=[i];labels[i]=group
            evidence[i]=dict(state='provisional',reason='distinct-source-voice',score=score,margin=margin)
        else:
            labels[i]=group
            evidence[i]=dict(state='uncertain',reason='insufficient-source-evidence',score=score,margin=margin)
    # Resolve an ambiguous brief reply only when its adjacent acoustic match
    # is practically tied with the best global candidate, never by proximity alone.
    for i in range(1,len(entries)):
        if entries[i]['end']-entries[i]['start']>=1.2: continue
        if not 0<=entries[i]['start']-entries[i-1]['end']<=.35: continue
        similarity=float(matrix[i]@matrix[i-1])
        best=float(np.max(np.delete(matrix@matrix[i],i))) if len(entries)>1 else 1
        if similarity>=.35 and best-similarity<=.04: labels[i]=labels[i-1]
    order={}
    stable=[order.setdefault(int(g),len(order)) for g in labels]
    return (stable,evidence) if with_evidence else stable


def analyze(cfg, emit):
    from dubbing_runner import offline
    offline()
    import numpy as np
    import torch
    import torchaudio
    import onnxruntime as ort
    import soundfile as sf
    torch.set_num_threads(4)
    root, job = Path(cfg['storage']), Path(cfg['job'])
    options = ort.SessionOptions(); options.intra_op_num_threads = 4
    session = ort.InferenceSession(str(root / 'models/speakers/voxceleb_resnet34_LM.onnx'), sess_options=options, providers=['CPUExecutionProvider'])
    audio, sr = sf.read(cfg['audio'], dtype='float32')
    if audio.ndim == 2: audio = audio.mean(axis=1)
    reference_audio=audio;reference_sr=sr
    if sr != 16000:
        audio = torchaudio.functional.resample(torch.from_numpy(audio), sr, 16000).numpy()
    sr = 16000
    background=None
    if cfg.get('backgroundPath') and Path(cfg['backgroundPath']).is_file():
        background,bg_sr=sf.read(cfg['backgroundPath'],dtype='float32')
        if background.ndim==2:background=background.mean(axis=1)
        if bg_sr!=sr:background=torchaudio.functional.resample(torch.from_numpy(background),bg_sr,sr).numpy()
    from reference_quality import measure

    def embedding(clip):
        features = torchaudio.compliance.kaldi.fbank(torch.from_numpy(clip.copy()).unsqueeze(0) * 32768,
            num_mel_bins=80, frame_length=25, frame_shift=10, sample_frequency=16000, window_type='hamming', dither=0)
        features -= features.mean(dim=0, keepdim=True)
        vector = session.run(None, {session.get_inputs()[0].name: features.unsqueeze(0).numpy()})[0].reshape(-1)
        norm = np.linalg.norm(vector)
        if not np.isfinite(vector).all() or norm < 1e-8: raise ValueError('聲紋模型輸出無效')
        return vector / norm

    entries, vectors, skipped = [], [], []
    for index, cue in enumerate(cfg['cues']):
        if not cue.get('enabled', True):
            skipped.append(index); continue
        start, end = cue.get('speechStart', cue['start']), cue.get('speechEnd', cue['end'])
        clip = audio[max(0, round(start*sr)):min(len(audio), round(end*sr))]
        if len(clip) < sr * .25 or np.sqrt(np.mean(clip**2)) < .001:
            skipped.append(index); continue
        # Long captions can cover more than one turn. Compare overlapping windows
        # and flag divergent voices instead of claiming a certain match.
        windows = [clip] if len(clip) <= 3*sr else [clip[p:p+3*sr] for p in range(0, len(clip)-sr, int(1.5*sr))]
        sub = np.stack([embedding(w) for w in windows])
        vector = sub.mean(axis=0); vector /= np.linalg.norm(vector)
        mixed = bool(np.min(sub @ vector) < .65)
        quality=measure(clip,sr,background[max(0,round(start*sr)):min(len(background),round(end*sr))] if background is not None else None)
        entries.append(dict(index=index, start=start, end=end, mixed=mixed, short=len(clip)<sr,quality=quality))
        vectors.append(vector)
        emit('自動配角色', f'分析原聲聲紋：第 {index+1}/{len(cfg["cues"])} 句。', progress=.26+.03*(index+1)/len(cfg['cues']))
    if not vectors: raise ValueError('未有足夠清晰對白分析角色，請檢查分離對白同字幕時間。')
    matrix = np.stack(vectors)
    np.savez(job/'speaker-embeddings.npz', vectors=matrix, indices=[e['index'] for e in entries])
    # Very short replies and OCR fragments cannot establish a reliable new voice.
    labels,identity_evidence = stable_assignments(matrix, entries,with_evidence=True)
    target=job/'speaker-evidence.json';temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps(dict(revision=REVISION,entries=[dict(row,group=int(group),identityEvidence=proof) for row,group,proof in zip(entries,labels,identity_evidence)]),ensure_ascii=False,indent=2));temp.replace(target)
    groups = sorted(set(labels))
    centers = np.stack([matrix[np.array(labels)==g].mean(axis=0) for g in groups])
    centers /= np.linalg.norm(centers, axis=1, keepdims=True)
    profiles, assignments = [], []
    for group in groups:
        members = [i for i, label in enumerate(labels) if label == group]
        role_id = f'auto-{job.name}-{group+1}'
        folder = job / 'auto-voices' / role_id; folder.mkdir(parents=True, exist_ok=True)
        candidates = sorted(members, key=lambda i: (identity_evidence[i]['state']!='uncertain',not entries[i]['mixed'], entries[i]['quality']['score'],min(entries[i]['end']-entries[i]['start'], 8)), reverse=True)
        clean=[i for i in candidates if not entries[i]['mixed'] and identity_evidence[i]['state']!='uncertain']
        if clean:candidates=clean
        clips, ranges, seconds = [], [], 0
        for i in candidates:
            row = entries[i]
            start, end = row['start'], min(row['end'], row['start']+8-seconds)
            if end-start < .25: continue
            clips.append(audio[round(start*sr):round(end*sr)])
            ranges.append([start, end]); seconds += end-start
            if seconds >= 3.2: break
        reference = np.concatenate(clips)
        short_ref = len(reference)<3*sr
        if short_ref: reference = np.pad(reference, (0, max(0, round(3.1*sr)-len(reference))))
        path = folder / 'reference.wav'
        from source_reference import write as write_source_reference
        write_source_reference(path,reference_audio,reference_sr,ranges,short_ref)
        strong=[i for i in members if identity_evidence[i]['state']=='acoustic-anchor']
        identity_status='acoustic' if len(strong)>=2 else 'provisional'
        bg_reference=np.concatenate([background[round(a*sr):round(b*sr)] for a,b in ranges]) if background is not None else None
        profiles.append(dict(id=role_id, name=f'自動角色 {group+1}', reference=str(path), promptText='', language='ja', referenceRanges=ranges, shortReference=short_ref, mixedReference=not bool(clean),referenceCandidates=[],referenceQuality=measure(reference,sr,bg_reference),identityStatus=identity_status))
        # Keep at most two distinct clean same-role originals for bounded retakes.
        for candidate in clean[:4]:
            row=entries[candidate];a,b=row['start'],min(row['end'],row['start']+8)
            if b-a<3:continue
            if len(ranges)==1 and abs(a-ranges[0][0])<.001 and abs(b-ranges[0][1])<.001:continue
            alternate=folder/f"alternate-{candidate}.wav"
            write_source_reference(alternate,reference_audio,reference_sr,[[a,b]])
            profiles[-1]['referenceCandidates'].append(dict(reference=str(alternate),promptText='',language='ja',range=[a,b],quality=row['quality']))
            if len(profiles[-1]['referenceCandidates'])>=2:break
        for i in members:
            row = entries[i]; similarities = matrix[i] @ centers.T
            others = np.delete(similarities, group)
            margin = float(similarities[group] - max(others)) if len(others) else 1.0
            note = ''
            if row['mixed']: note = '同一句可能包含多個聲線；已按主要聲紋自動配對。'
            elif row['short'] or margin < .08 or identity_evidence[i]['state'] in ('uncertain','provisional'): note = '短句／相近聲線，暫按最接近參考配對；身份未確定。'
            if short_ref: note += ' 呢個角色參考對白較短，聲線相似度可能較低。'
            previous=next((j for j,e in enumerate(entries) if e['index']==row['index']-1),None)
            similarity=float(matrix[i]@matrix[previous]) if previous is not None else 0
            assignments.append(dict(index=row['index'], speakerId=role_id, speakerNote=note.strip(),mixedVoices=row['mixed'],previousSpeakerSimilarity=similarity,identityEvidence=identity_evidence[i]))
    # Silent/too-short OCR rows receive the nearest temporal voice, clearly labelled.
    for index in skipped:
        cue = cfg['cues'][index]
        nearest = min(range(len(entries)), key=lambda i: abs((entries[i]['start']+entries[i]['end'])/2-(cue['start']+cue['end'])/2))
        assignments.append(dict(index=index, speakerId=f'auto-{job.name}-{labels[nearest]+1}', speakerNote='呢句聲音太短或太弱，暫按鄰近角色自動配對。',previousSpeakerSimilarity=0,identityEvidence=dict(state='uncertain',reason='no-usable-source-voice')))
    result = dict(profiles=profiles, assignments=assignments, revision=REVISION)
    target = job / 'speaker-analysis.json'
    temp = target.with_suffix('.tmp'); temp.write_text(json.dumps(result, ensure_ascii=False, indent=2)); temp.replace(target)
    emit('自動配角色', f'已按原聲分出 {len(profiles)} 個聲線，自動抽取角色參考。', progress=.29)


def transcribe_profiles(cfg,job,profiles,speech_path,emit):
    from faster_whisper import WhisperModel
    model = None
    analysis = job/'japanese-analysis.json'
    source_words = [w for s in json.loads(analysis.read_text()).get('segments',[]) for w in s.get('words',[])] if analysis.exists() else []
    for i, profile in enumerate(profiles):
        profile['language']=cfg.get('sourceLanguage','ja')
        if cfg.get('independentVoiceMapping') and not profile.get('reference'):continue
        if source_words:
            parts=[]
            for start,end in profile.get('referenceRanges',[]):
                parts.append(''.join(w['word'] for w in source_words if start <= (w['start']+w['end'])/2 < end))
            profile['promptText']=''.join(parts).strip()
            if profile['promptText']:
                profile['transcriptSource']='original-japanese-words'
                continue
        if model is None: model = WhisperModel(str(speech_path), device='cpu', compute_type='int8', local_files_only=True)
        emit('角色參考', f'自動辨識 {profile["name"]} 嘅日語參考原文。', .29)
        segments, _ = model.transcribe(whisper_pcm(profile['reference']), language=cfg.get('sourceLanguage','ja'), vad_filter=True, condition_on_previous_text=False)
        profile['promptText'] = ''.join(s.text for s in segments).strip()
        if not profile['promptText']:
            segments, _ = model.transcribe(whisper_pcm(profile['reference']), language=cfg.get('sourceLanguage','ja'), vad_filter=False, condition_on_previous_text=False)
            profile['promptText'] = ''.join(s.text for s in segments).strip()
        if not profile['promptText']:
            message=f'{profile["name"]} 參考原聲辨識失敗；請檢查呢段片嘅對白品質。'
            if cfg.get('independentVoiceMapping') and cfg.get('continueOnError',True):
                profile['referenceIssue']=message;emit('逐句參考待覆核',message,.29)
            else:raise ValueError(message)
    for profile in profiles:
        for candidate in profile.get('referenceCandidates',[]):
            ranges=candidate.get('ranges') or ([candidate['range']] if candidate.get('range') else [])
            candidate['promptText']=''.join(w['word'] for w in source_words for a,b in ranges if a<=(w['start']+w['end'])/2<b).strip()
            if not candidate['promptText']:
                if model is None:model=WhisperModel(str(speech_path),device='cpu',compute_type='int8',local_files_only=True)
                segments,_=model.transcribe(whisper_pcm(candidate['reference']),language=cfg.get('sourceLanguage','ja'),vad_filter=False,condition_on_previous_text=False)
                candidate['promptText']=''.join(s.text for s in segments).strip()


def assign(cfg, job, cues, run, emit):
    if cfg.get('roleAnalysisMode')=='independent':
        from independent_voices import assign as independent_assign
        return independent_assign(cfg,job,cues,emit)
    from dubbing import model_job
    root = Path(cfg['storage'])
    if not (root/'speakers-ready.json').exists(): raise ValueError('請先部署「自動角色配對」模型。')
    from model_catalog import folder,choice,selected
    speech_path=folder(root,choice(cfg.get('referenceSpeechModel') or selected(root,'referenceSpeech')))
    if not (speech_path/'model.bin').exists(): raise ValueError('自動角色參考需要先部署日語語音辨識。')
    key = hashlib.sha256(json.dumps([REVISION, cfg.get('referenceSpeechModel'), cfg['dialoguePath'], [(c['start'], c['end'], c.get('speechStart'), c.get('speechEnd'), c.get('enabled', True)) for c in cues]]).encode()).hexdigest()
    cache = job/'auto-speakers.json'
    if cache.exists():
        saved = json.loads(cache.read_text())
        if saved.get('key') == key and all(Path(p['reference']).exists() for p in saved['profiles']):
            result = saved
        else: result = None
    else: result = None
    if result is None:
        model_job(cfg, 'speakers', dict(storage=str(root), job=str(job), audio=cfg['dialoguePath'],backgroundPath=cfg.get('backgroundPath'), cues=cues), emit)
        result = json.loads((job/'speaker-analysis.json').read_text())
        result['key'] = key
        temp = cache.with_suffix('.tmp'); temp.write_text(json.dumps(result, ensure_ascii=False, indent=2)); temp.replace(cache)
    for row in result['assignments']:
        cues[row['index']].update(speakerId=row['speakerId'], speakerNote=row['speakerNote'],mixedVoices=row.get('mixedVoices',False),previousSpeakerSimilarity=row.get('previousSpeakerSimilarity',0),identityEvidence=row.get('identityEvidence',{}))
    profiles=json.loads(json.dumps(result['profiles']))
    if cfg.get('roleAnalysisMode')=='audiovisual':
        from visual_speakers import refine
        cues,profiles=refine(cfg,job,cues,profiles,emit)
    # Final references are transcribed only after audiovisual identity fusion.
    transcribe_profiles(cfg,job,profiles,speech_path,emit)
    plan=dict(revision=REVISION,status='ready-for-dubbing',acousticGroups=len(result['profiles']),finalVoiceGroups=len(profiles),visuallySupported=sum(p.get('identityStatus')=='audiovisual' for p in profiles),provisionalGroups=sum(p.get('identityStatus')=='provisional' for p in profiles),uncertainSegments=[i+1 for i,c in enumerate(cues) if c.get('identityEvidence',{}).get('state') in ('uncertain','provisional')],identities=[dict(id=p['id'],status=p.get('identityStatus','acoustic'),reference=p['reference'],visualId=p.get('visualId'),cueIndices=[i+1 for i,c in enumerate(cues) if c.get('speakerId')==p['id']]) for p in profiles],policy='Fixed per-identity reference before translation and TTS; voice groups are not certified people.')
    target=job/'character-plan.json';temp=target.with_suffix('.tmp');temp.write_text(json.dumps(plan,ensure_ascii=False,indent=2));temp.replace(target)
    emit('角色歸類',f"已整理 {len(profiles)} 組配音參考；畫面支持 {plan['visuallySupported']} 組，待確認 {plan['provisionalGroups']} 組。",.29)
    cfg['voiceProfiles'] = profiles; cfg['defaultSpeaker'] = ''
    return cues
