"""Qwen3-TTS Base adapter; isolated from CosyVoice's MLX package."""
from runtime_installer import ensure_env, pip_command
import contextlib
import json
import math
import re
from pathlib import Path
import sys


def install(root, variant=None):
    from dubbing_setup import call, download, emit
    from runtime_paths import python_for, packages_ready
    root = Path(root)
    marker = root/'qwen-ready.json'
    if variant in (None,'qwen-0.6b-4bit'):marker.unlink(missing_ok=True)
    python = python_for(root,'qwen-runtime')
    if not python.exists():
        ensure_env(root, python.parent.parent, run=lambda args,**kw: call(args))
    if not packages_ready(root,'qwen-runtime'):
        call(pip_command(python, root, 'install', '--no-deps', '-r', Path(__file__).with_name('qwen-requirements.lock')))
    from voice_models import install_files,mark_ready
    row,path=install_files(root,'qwen-tts',variant,download,emit)
    call([python,Path(__file__),'prepare',root,row['id']])
    mark_ready(root,row)
    if variant in (None,'qwen-0.6b-4bit') or not marker.exists():marker.write_text(json.dumps({'model':row['repo'],'revision':row['revision'],'variant':row['id']}))


def load(root, variant=None):
    from dubbing_runner import offline
    offline()
    from mlx_audio.tts.utils import load_model
    from voice_models import resolve
    return load_model(str(resolve(root,'qwen-tts',variant)))


def attempt_parameters(item,recovery=False):
    # Punctuation only: never silently replace approved words or names.
    normalized=re.sub(r'(?:\.{2,}|…+|⋯+)', '.', item['text'])
    seed=item.get('seed',42)
    extra=dict(text=normalized,seed=seed+62,temperature=.7,repetition_penalty=1.2)
    return [extra] if recovery else [dict(text=item['text'],seed=seed,temperature=.3),dict(text=item['text'],seed=seed+31,temperature=.9),extra]


def synthesize(cfg, emit):
    import mlx.core as mx
    import numpy as np
    import soundfile as sf
    with contextlib.redirect_stdout(sys.stderr):
        model = load(cfg['storage'],cfg.get('qwenModel'))
    failed=[];results=[]
    result_path=Path(cfg.get('job',cfg['storage']))/'qwen-results.json'
    result_path.parent.mkdir(parents=True,exist_ok=True)
    def record(item,attempts,status):
        results.append(dict(output=item['output'],reviewIndex=item.get('reviewIndex'),status=status,attempts=attempts))
        tmp=result_path.with_suffix('.tmp');tmp.write_text(json.dumps(dict(requestId=cfg.get('requestId'),items=results),ensure_ascii=False,indent=2));tmp.replace(result_path)
    result_path.write_text(json.dumps(dict(requestId=cfg.get('requestId'),items=[])))
    for i,item in enumerate(cfg['items']):
        from track_control import check
        check(cfg)
        path = Path(item['output'])
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists() and path.stat().st_size > 100:
            record(item,[],'cached');continue
        voice = item['profile']
        # Chinese selects Mandarin in this Base checkpoint. Automatic language
        # plus target-language ICL is the dialect-safe API available here.
        # Japanese reference text is excluded; it steers generated speech to Japanese.
        target=cfg.get('targetLanguage','yue')
        reference_text=voice.get('promptText') if voice.get('language')==target else None
        language='english' if target=='en' else 'auto'
        if i==0 and target=='yue':
            emit('語言核對','Qwen Base 冇獨立廣東話語言 ID；使用自動語言並獨立覆聽。普通話／錯誤內容會改用合格廣東話補聲，來源會列入摘要。')
        mx.random.seed(item.get('seed',42))
        emit('配音',f'Qwen3-TTS· {voice["name"]} · 第 {i+1}/{len(cfg["items"])} 句',cueIndex=item.get("reviewIndex"))
        from tts_health import problems,duration_limit
        budget=min(2048,math.ceil(duration_limit(item['text'],item.get('targetSeconds'))*12.5)+16)
        failures=[]
        variants=attempt_parameters(item,cfg.get('recoveryAttempt',False))
        for attempt,params in enumerate(variants):
            params=dict(params);mx.random.seed(params.pop('seed'))
            with contextlib.redirect_stdout(sys.stderr):
                generated=list(model.generate(ref_audio=voice['reference'],ref_text=reference_text,lang_code=language,verbose=False,max_tokens=budget,top_p=.9,**params))
            audio=np.concatenate([np.asarray(x.audio).reshape(-1) for x in generated]) if generated else np.array([])
            tokens=sum(getattr(x,'token_count',0) for x in generated)
            errors=problems(audio,model.sample_rate,item['text'],item.get('targetSeconds'),tokens,budget)
            failures.append(dict(attempt=attempt+1,parameters=variants[attempt],problems=errors,seconds=len(audio)/model.sample_rate,tokens=tokens))
            if not errors:break
            emit('配音重錄',f'Qwen3-TTS 第 {i+1} 句音訊異常，保留文字重新生成（{attempt+1}/{len(variants)}）。')
        if failures:path.with_suffix('.health.json').write_text(json.dumps(failures,indent=2))
        if errors:
            if len(audio) and np.isfinite(audio).all():sf.write(path.with_suffix('.rejected.wav'),audio,model.sample_rate,subtype='PCM_16')
            label=f'校稿第 {item["reviewIndex"]+1} 句' if item.get('reviewIndex') is not None else f'第 {i+1} 個生成片段'
            failed.append(f'{label}（{", ".join(errors)}）')
            record(item,failures,'failed')
            emit('配音需修正',f'Qwen3-TTS {label} 重試仍失敗；繼續保存其餘片段。')
            continue
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp = path.with_suffix('.partial.wav')
        sf.write(tmp,audio,model.sample_rate,subtype='PCM_16');tmp.replace(path)
        record(item,failures,'repaired' if len(failures)>1 or cfg.get('recoveryAttempt') else 'generated')

    if failed:raise ValueError('Qwen3-TTS '+ '；'.join(failed) +'；其餘片段已保存，未將缺聲音軌封裝為完成。')

if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        with contextlib.redirect_stdout(sys.stderr): load(sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)
    else:
        from dubbing_runner import emit
        try:synthesize(json.loads(Path(sys.argv[2]).read_text()), emit)
        except Exception as error:
            emit('錯誤',str(error))
            raise
