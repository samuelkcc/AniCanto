"""Pinned CosyVoice 3 MLX adapter. Download only during setup; inference is offline."""
from runtime_installer import ensure_env, pip_command
from fast_mode import enabled as one_pass

import contextlib
import json
from pathlib import Path
import sys
import time

RESOURCE_DIR = Path(__file__).resolve().parent


def trim_padding(audio, sr=24000):
    """Remove only outer silence; preserve internal pauses and 50 ms at each edge."""
    import numpy as np
    threshold = max(.001, float(np.max(np.abs(audio))) * .003)
    active = np.flatnonzero(np.abs(audio) > threshold)
    if not len(active):
        return audio
    pad = round(sr * .05)
    return audio[max(0, int(active[0])-pad):min(len(audio), int(active[-1])+pad+1)]


def install(root, variant=None):
    from engine_availability import require
    require('cosyvoice3',root)
    from dubbing_setup import call, download, emit
    marker = root / 'cosy-ready.json'
    if variant in (None,'cosy-0.5b-4bit'):marker.unlink(missing_ok=True)
    from runtime_paths import python_for,packages_ready
    python = python_for(root,'cosy-runtime')
    if not python.exists():
        ensure_env(root, python.parent.parent, run=lambda args,**kw: call(args))
    emit('安裝 CosyVoice 3 專用 MLX 環境，唔需要 CUDA。')
    # All transitive packages are frozen after a clean inference test. Avoid
    # mlx-audio-plus optional server/WebRTC extras and overlapping namespaces.
    if not packages_ready(root,'cosy-runtime'):call(pip_command(python, root, 'install', '--only-binary', ':all:', '--no-deps', '-r', RESOURCE_DIR / 'cosy-requirements.lock'))
    manifests = json.loads((RESOURCE_DIR / 'cosy-models.json').read_text())
    from voice_models import install_files,mark_ready
    row,model_path=install_files(root,'cosyvoice3',variant,download,emit)
    for name, manifest in manifests.items():
        if name=='cosy':continue
        for file in manifest['files']:
            emit(f'下載／校驗 CosyVoice 3：{name}/{file["path"]}（模型合共約 2.2 GB）')
            download(f'https://huggingface.co/{manifest["repo"]}/resolve/{manifest["revision"]}/{file["path"]}',
                     root / 'models/cosyvoice3' / name / file['path'], file['sha'])
    call([python, RESOURCE_DIR / 'dubbing_runner.py', 'prepare-cosy', root, row['id']])
    mark_ready(root,row)
    if variant in (None,'cosy-0.5b-4bit') or not marker.exists():marker.write_text(json.dumps({'version':row['repo'],'variant':row['id'],'revision':row['revision'],'adapter':'mlx-audio-plus-0.1.8'}))
    emit('CosyVoice 3 已部署，可以喺角色頁同 GPT-SoVITS 比較試聽。')


def load(root, variant=None):
    from engine_availability import require
    require('cosyvoice3',root)
    if sys.platform=='win32':
        from native_cosy import load as native_load
        return native_load(root,variant)
    from dubbing_runner import offline
    offline()
    import mlx.core as mx
    from mlx_audio.tts.models.cosyvoice3 import Model, ModelConfig
    from mlx_audio.codec.models.s3tokenizer import S3TokenizerV3
    folder = root / 'models/cosyvoice3'
    from voice_models import resolve
    model = Model(ModelConfig(model_path=str(resolve(root,'cosyvoice3',variant))))
    # Upstream defaults to a Hub lookup. Explicit local loading keeps inference
    # independent of network access and the user's global Hugging Face cache.
    tokenizer = S3TokenizerV3()
    tokenizer.load_weights(list(mx.load(str(folder / 's3/model.safetensors')).items()))
    mx.eval(tokenizer.parameters())
    model._s3_tokenizer = tokenizer
    model._ensure_tokenizers_loaded()
    return model


def prepare(root, variant=None):
    from dubbing_runner import emit
    with contextlib.redirect_stdout(sys.stderr):
        load(root,variant)
    emit('部署配音', 'CosyVoice 3、聲音編碼器同文字元件已通過離線載入檢查。')


def synthesize(cfg, emit):
    emit('配音','準備生成音軌。',workID='tts',workCompleted=0,workTotal=len(cfg['items']))
    emit('配音', '載入 CosyVoice 3（Windows · PyTorch），生成角色配音。' if sys.platform=='win32' else '載入 CosyVoice 3（Apple Silicon · MLX），生成角色配音。')
    with contextlib.redirect_stdout(sys.stderr):
        model = load(Path(cfg['storage']),cfg.get('cosyModel'))
    if sys.platform=="win32":
        import numpy as mx
    else:
        import mlx.core as mx
    import numpy as np
    import soundfile as sf
    import librosa
    failures=[]
    for index, item in enumerate(cfg['items']):
        from track_control import check
        check(cfg)
        path = Path(item['output'])
        line = item.get('reviewIndex')
        label = f'校稿第 {line+1} 句' if line is not None else f'第 {index+1} 句'
        if path.exists() and path.stat().st_size > 100:
            emit('配音', f'CosyVoice 3：沿用 {label} 已生成音檔。',workID='tts',workCompleted=index+1,workTotal=len(cfg['items']))
            continue
        attempts=1 if one_pass(cfg) else 2
        for retry in range(attempts):
            try:
                started = time.monotonic()
                voice = item['profile']
                ref, sr = sf.read(voice['reference'], dtype='float32', always_2d=True)
                if not 3 <= len(ref) / sr <= 10.1:
                    raise ValueError('角色參考聲音必須係 3–10 秒。')
                ref = librosa.resample(ref.mean(axis=1), orig_sr=sr, target_sr=24000)
                mx.random.seed(item.get('seed',42)+31*retry)
                instruction = ('You are a helpful assistant. Speak natural, expressive English. Say every word exactly as written.' if cfg.get('targetLanguage')=='en' else 'You are a helpful assistant. 请用地道的香港粤语说话。')
                if cfg.get('targetLanguage')=='en' and item.get('deliveryStyle') in ('brisk','measured','timed'):
                    instruction += f' Deliver the complete line in about {item["targetSeconds"]:.1f} seconds with natural expression and clear words. Do not add, omit or repeat words.'
                if cfg.get('targetLanguage')!='en' and item.get('deliveryStyle') == 'brisk':
                    instruction += '用较快、紧凑利落的语速，减少停顿，不要拖长尾音，完整说出所有台词。'
                if cfg.get('targetLanguage')!='en' and item.get('deliveryStyle') == 'measured':
                    instruction += f'请用从容、有表情的香港粤语，在大约{item["targetSeconds"]:.1f}秒内讲完。字字清晰，适当停顿，不要赶快读完，不添加、重复或省略文字。'
                if cfg.get('targetLanguage')!='en' and item.get('deliveryStyle') == 'timed':
                    instruction += f'请在大约{item["targetSeconds"]:.1f}秒内完整说完这句台词。用自然利落的较快语速，停顿短，不要拉长尾音，不漏字。'
                from voice_expression import settings,instruction as acting_instruction
                expression=settings(item.get('expressionSettings',{}))
                instruction+=acting_instruction(expression['cosyExpression'],cfg.get('targetLanguage','yue'))
                with contextlib.redirect_stdout(sys.stderr):
                    chunks = [np.asarray(result.audio).reshape(-1) for result in model.generate(
                        text=item['text'].strip(), ref_audio=mx.array(ref),
                        instruct_text=instruction, temperature=expression['cosyTemperature'],
                        stt_model=None, verbose=False, stream=False)]
                audio = np.concatenate(chunks) if chunks else np.empty(0)
                from fast_mode import basic_problems
                invalid=basic_problems(audio,24000) if one_pass(cfg) else (len(audio)<2400 or not np.isfinite(audio).all() or np.max(np.abs(audio))<.001)
                if invalid:
                    raise ValueError('CosyVoice 3 輸出無效／靜音，請更換參考聲音。')
                audio = trim_padding(audio)
                path.parent.mkdir(parents=True, exist_ok=True)
                sf.write(path.with_suffix('.raw.wav'),audio,24000,subtype='FLOAT')
                from speech_level import condition
                audio,level=condition(audio,24000)
                tmp = path.with_suffix('.partial.wav')
                sf.write(tmp, audio, 24000, subtype='PCM_16')
                tmp.replace(path)
                path.with_suffix('.level.json').write_text(json.dumps(level))
                emit('配音', f'CosyVoice 3：{voice["name"]} · {label}（{index+1}/{len(cfg["items"])}）',
                     progress=0.55+0.3*(index+1)/len(cfg['items']), workID='tts',workCompleted=index+1,workTotal=len(cfg['items']),cueIndex=item.get('reviewIndex'), seconds=round(time.monotonic()-started, 2))
                break
            except (ValueError,RuntimeError) as error:
                emit('配音重試',f'CosyVoice 3：{label} 嘗試 {retry+1}/2：{error}')
                if retry==attempts-1:
                    failures.append(f'{label}: {error}')
                    emit('配音',f'{label} 已處理，等待修正。',workID='tts',workCompleted=index+1,workTotal=len(cfg['items']))
    if failures:raise ValueError('CosyVoice 3；'+'；'.join(failures)+'；其他片段已保存。')
