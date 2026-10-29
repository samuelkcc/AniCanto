"""Independent Japanese transcription evidence; never replaces audio timing."""
from runtime_installer import ensure_env, pip_command
import json
import os
from pathlib import Path
import sys


def recheck(cfg,job,cues,run,emit):
    """One isolated-audio hypothesis for disputed source turns, cached on resume."""
    import hashlib
    from difflib import SequenceMatcher
    from dubbing import model_job
    from worker import atomic_json
    if not cfg.get('dialoguePath') or not (Path(cfg['storage'])/'asr-ready.json').exists():return
    selected=[i for i,c in enumerate(cues) if c.get('enabled',True) and c.get('asrAgreement',1)<.60 and len(c.get('japanese',c.get('text','')))>3]
    if not selected:return
    audio=Path(cfg['dialoguePath']);signature=hashlib.sha256(audio.read_bytes()).hexdigest()
    key=hashlib.sha256(json.dumps([signature,[(i,cues[i]['start'],cues[i]['end']) for i in selected],'isolated-recheck-1',cfg.get('asrModel')]).encode()).hexdigest()
    cache=job/'source-recheck.json';saved=json.loads(cache.read_text()) if cache.exists() else {}
    if saved.get('key')!=key:
        emit('日語局部重聽',f'{len(selected)} 段兩份聽寫有分歧，改用分離後日語人聲核對一次，唔改動時間。',.31)
        converted=job/'japanese-isolated.wav'
        run([cfg['ffmpeg'],'-v','error','-y','-i',audio,'-ar','16000','-ac','1',converted])
        model_job(cfg,'asr',dict(storage=cfg['storage'],job=str(job),audio=str(converted),cues=[cues[i] for i in selected],output='isolated-asr-result.json'),emit)
        result=json.loads((job/'isolated-asr-result.json').read_text())
        if len(result['rows'])!=len(selected):raise ValueError('日語重聽漏句；未使用不完整結果。')
        saved=dict(key=key,indices=selected,rows=result['rows']);atomic_json(cache,saved)
    clean=lambda t:''.join(c for c in t if c.isalnum())
    for i,row in zip(selected,saved['rows']):
        c=cues[i];c['japaneseRecheck']=row['text']
        agreement=SequenceMatcher(None,clean(c.get('japanese',c.get('text',''))),clean(row['text'])).ratio()
        c['sourceReviewReasons']=[] if row['text'] and agreement>=.75 else ['日語聽寫有分歧；第三份係分離人聲假設，未認證正確原文。']
    atomic_json(job/'source-confidence.json',dict(rows=[dict(index=i+1,japanese=c.get('japanese',c.get('text','')),independent=c.get('japaneseAlt',''),isolated=c.get('japaneseRecheck',''),reasons=c.get('sourceReviewReasons',[])) for i,c in enumerate(cues)],method='original and isolated local ASR; timing unchanged'))


def install(root,variant=None):
    from dubbing_setup import call,download,emit
    from runtime_paths import python_for,packages_ready
    root=Path(root);python=python_for(root,'asr-runtime')
    if not python.exists():ensure_env(root, python.parent.parent, run=lambda args,**kw: call(args))
    if not packages_ready(root,'asr-runtime'):
        call(pip_command(python, root, 'install', '--only-binary', ':all:', '--no-deps', '-r', Path(__file__).with_name('asr-requirements.lock')))
    from model_catalog import install as download,selected
    variant=variant or selected(root,'asr');download(root,variant)
    call([python,Path(__file__),'prepare',root,variant])
    (root/'asr-ready.json').write_text(json.dumps(dict(variant=variant)))


def audio_array(audio):
    if sys.platform=='win32':return audio
    import mlx.core as mx
    return mx.array(audio)


def load_model(root,variant=None):
    if sys.platform=='win32':
        from native_asr import load
        return load(root,variant)
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false')
    from compute_policy import mlx_device
    mlx_device(root,'qwen-asr')
    from mlx_audio.stt import load
    from model_catalog import resolve,selected
    return load(str(resolve(root,variant or selected(root,'asr'))))


def analyze(cfg,job,cues,run,emit):
    from dubbing import model_job
    from worker import atomic_json
    cache=job/'asr-verification.json'
    identity=[(c['start'],c['end'],c.get('enabled',True)) for c in cues]
    saved=json.loads(cache.read_text()) if cache.exists() else {}
    from model_catalog import selected
    variant=cfg.get('asrModel') or selected(cfg['storage'],'asr')
    if saved.get('identity')!=[list(x) for x in identity] or saved.get('model')!=variant:
        model_job(cfg,'asr',dict(storage=cfg['storage'],job=str(job),audio=str(job/'japanese-original.wav'),cues=cues),emit)
        saved=json.loads(cache.read_text())
    for cue,row in zip(cues,saved['rows']):
        cue['japaneseAlt']=row['text']
        cue['asrAgreement']=row['agreement']
        if any(t in cue.get('japanese','') for t in ('ご視','チャンネル登録')) and row['text'] and not any(t in row['text'] for t in ('ご視','チャンネル登録','ありがとう')):
            cue['japaneseOriginal']=cue['japanese']
            cue['japanese']=cue['text']=row['text']
            cue['reviewNote']=(cue.get('reviewNote','')+' 已用獨立聽寫修正疑似片尾套語幻覺；請核對原聲。').strip()
    atomic_json(job/'dual-asr-cues.json',cues)
    return cues


def verify(request):
    import contextlib
    import re
    import unicodedata
    from difflib import SequenceMatcher
    import soundfile as sf
    def emit(message):print(json.dumps(dict(stage='日語核對',message=message),ensure_ascii=False),flush=True)
    emit('載入第二日語辨識模型，逐句核對原聲；保留兩份聽寫供場景分析。')
    with contextlib.redirect_stdout(sys.stderr):model=load_model(request['storage'],request.get('asrModel'))
    audio,sr=sf.read(request['audio'],dtype='float32');assert sr==16000 and audio.ndim==1
    def normalized(text):
        text=unicodedata.normalize('NFKC',text)
        return ''.join(chr(ord(c)-96) if '\u30a1'<=c<='\u30f6' else c for c in text if c.isalnum())
    rows=[]
    for i,c in enumerate(request['cues']):
        clip=audio[round(c['start']*sr):round(c['end']*sr)]
        if not c.get('enabled',True) or len(clip)<sr*.3:text=''
        else:
            with contextlib.redirect_stdout(sys.stderr):
                result=model.generate(audio_array(clip),language='Japanese',max_tokens=min(256,max(32,round(len(clip)/sr*24))),verbose=False)
            text=result.text.strip()
            if len(text)>len(clip)/sr*25+10 or re.search(r'(.{2,8})\1{3,}',text):text=''
        agreement=SequenceMatcher(None,normalized(c.get('japanese',c.get('text',''))),normalized(text)).ratio() if text else 0
        rows.append(dict(text=text,agreement=round(agreement,3)))
        emit(f'已核對第 {i+1}/{len(request["cues"])} 句日語。')
    from model_catalog import selected
    data=dict(identity=[[c['start'],c['end'],c.get('enabled',True)] for c in request['cues']],model=request.get('asrModel') or selected(request['storage'],'asr'),rows=rows)
    filename=request.get('output','asr-verification.json')
    if filename not in ('asr-verification.json','isolated-asr-result.json'):raise ValueError('Invalid ASR output')
    path=Path(request['job'])/filename;tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False));tmp.replace(path)


if __name__=='__main__':
    try:
        if sys.argv[1]=='prepare':load_model(sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)
        else:verify(json.loads(Path(sys.argv[2]).read_text()))
    except Exception as exc:
        print(json.dumps(dict(stage='錯誤',message=str(exc)),ensure_ascii=False),flush=True);raise
