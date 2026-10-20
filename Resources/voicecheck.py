"""Reject automatic replacement takes that substantially change speaker embedding."""
import hashlib,json,os,subprocess,sys
from pathlib import Path


def embeddings(cfg,job,paths):
    from runtime_paths import python_for
    request=Path(job)/'voice-batch-request.json';result=Path(job)/'voice-batch-result.json'
    request.write_text(json.dumps(dict(mode='embeddings',storage=cfg['storage'],ffmpeg=cfg['ffmpeg'],paths=[str(p) for p in paths],cache=str(Path(job)/'voice-check-cache.json'),result=str(result))))
    with (Path(job)/'voice-check.log').open('a') as log:
        p=subprocess.run([str(python_for(Path(cfg['storage']),'separator-runtime')),str(Path(__file__).resolve()),str(request)],stdout=log,stderr=log,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',ORT_DISABLE_TELEMETRY='1'))
    if p.returncode:raise RuntimeError('批量聲線核對未完成；詳見 voice-check.log。')
    return json.loads(result.read_text())['vectors']


def inconsistent_takes(cues,vectors):
    """Only flag an outlier against a corroborated same-role generated anchor."""
    import numpy as np
    groups={}
    for i,(c,v) in enumerate(zip(cues,vectors)):
        if v is not None and c.get('speakerId'):groups.setdefault(c['speakerId'],[]).append(i)
    result=[]
    for speaker,ids in groups.items():
        if len(ids)<3:continue
        values=np.asarray([vectors[i] for i in ids]);similarity=values@values.T
        medoid=int(np.argmax(np.median(similarity,axis=1)))
        # At least two other takes must independently corroborate this anchor.
        if sum(similarity[medoid,j]>=.7 for j in range(len(ids)) if j!=medoid)<2:continue
        for j,i in enumerate(ids):
            if similarity[medoid,j]<.5:result.append(dict(index=i,anchor=ids[medoid],similarity=float(similarity[medoid,j]),speakerId=speaker))
    return result


def preserves(cfg,job,original,candidate,reference):
    if not (Path(cfg.get('storage',''))/'speakers-ready.json').is_file():return False
    from runtime_paths import python_for
    request=Path(job)/'voice-check-request.json';result=Path(job)/'voice-check-result.json'
    request.write_text(json.dumps(dict(storage=cfg['storage'],ffmpeg=cfg['ffmpeg'],paths=[str(original),str(candidate),str(reference)],cache=str(Path(job)/'voice-check-cache.json'),result=str(result))))
    with (Path(job)/'voice-check.log').open('a') as log:
        p=subprocess.run([str(python_for(Path(cfg['storage']),'separator-runtime')),str(Path(__file__).resolve()),str(request)],stdout=log,stderr=log,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',ORT_DISABLE_TELEMETRY='1'))
    if p.returncode:raise RuntimeError('聲線核對程序失敗，原音檔已保留；詳見 voice-check.log。')
    row=json.loads(result.read_text())
    history=Path(job)/'voice-check.json';rows=json.loads(history.read_text()) if history.exists() else []
    rows.append(dict(row,original=str(original),candidate=str(candidate),reference=str(reference)))
    history.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    return row['accepted']


def compare_scores(similarity,before,after):
    stable=similarity>=.65 and after>=before-.08
    improved=after>=.5 and after>=before+.05
    return dict(accepted=stable or improved,takeSimilarity=similarity,originalReferenceSimilarity=before,
                candidateReferenceSimilarity=after,referenceImproved=improved,
                reason='closer-to-original-role-reference' if improved else 'stable-generated-role' if stable else 'insufficient-role-similarity',
                method='relative-speaker-embedding; not acting or identity certification')


def verify(cfg):
    import numpy as np
    import torch,torchaudio,onnxruntime as ort
    torch.set_num_threads(2)
    file=Path(cfg['cache']);cache=json.loads(file.read_text()) if file.exists() else {}
    session=None;vectors=[]
    for path in cfg['paths']:
        key=hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if key not in cache:
            raw=subprocess.check_output([cfg['ffmpeg'],'-v','error','-i',path,'-ar','16000','-ac','1','-f','f32le','pipe:1'])
            x=np.frombuffer(raw,dtype=np.float32).copy()
            if len(x)<12000:cache[key]=None
            else:
                if session is None:
                    options=ort.SessionOptions();options.intra_op_num_threads=2
                    session=ort.InferenceSession(str(Path(cfg['storage'])/'models/speakers/voxceleb_resnet34_LM.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
                features=torchaudio.compliance.kaldi.fbank(torch.from_numpy(x[:160000]).unsqueeze(0)*32768,num_mel_bins=80,frame_length=25,frame_shift=10,sample_frequency=16000,window_type='hamming',dither=0)
                features-=features.mean(dim=0,keepdim=True)
                vector=session.run(None,{session.get_inputs()[0].name:features.unsqueeze(0).numpy()})[0].reshape(-1)
                norm=np.linalg.norm(vector)
                cache[key]=(vector/norm).tolist() if np.isfinite(vector).all() and norm>1e-8 else None
        vectors.append(cache[key])
    temp=file.with_suffix('.tmp');temp.write_text(json.dumps(cache));temp.replace(file)
    if cfg.get('mode')=='embeddings':
        Path(cfg['result']).write_text(json.dumps(dict(vectors=vectors)));return
    result=dict(accepted=False,reason='insufficient-speaker-evidence')
    if all(v is not None for v in vectors):
        old,new,ref=np.array(vectors)
        similarity=float(old@new);before=float(old@ref);after=float(new@ref)
        result=compare_scores(similarity,before,after)
    Path(cfg['result']).write_text(json.dumps(result))


if __name__=='__main__':verify(json.loads(Path(sys.argv[1]).read_text()))
