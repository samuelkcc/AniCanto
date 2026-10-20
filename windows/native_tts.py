"""Native PC voice adapters. A child process owns each model and releases it on exit."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
SHARED = HERE / 'shared' if (HERE / 'shared').is_dir() else HERE.parent / 'Resources'
sys.path.insert(0, str(SHARED))
os.environ.update(ORT_DISABLE_TELEMETRY='1', HF_HUB_DISABLE_TELEMETRY='1')
from gpu import torch_probe


def emit(message, **extra):
    print(json.dumps(dict(stage='Voice', message=message, **extra), ensure_ascii=False), flush=True)


def audio_compatibility():
    # Torchaudio 2.9 delegates load to TorchCodec; these upstream engines expect
    # the earlier soundfile API. Use PCM decoding without an extra CUDA codec.
    import torch
    import torchaudio
    import soundfile as sf
    def load(path, frame_offset=0, num_frames=-1, normalize=True, channels_first=True, **kwargs):
        audio, sr = sf.read(str(path), start=frame_offset,
                            frames=num_frames, dtype='float32' if normalize else 'int16', always_2d=True)
        return torch.from_numpy(audio.T.copy() if channels_first else audio.copy()), sr
    torchaudio.load = load


def gpt_text_compatibility():
    # jieba_fast has no standard Windows wheel. The reference Jieba package
    # provides the same segmentation/posseg API without a local C compiler.
    import jieba
    import jieba.posseg
    sys.modules['jieba_fast'] = jieba
    sys.modules['jieba_fast.posseg'] = jieba.posseg


def load_model(engine, root, cfg):
    import torch
    audio_compatibility()
    torch.set_num_threads(max(1, min(8, (os.cpu_count() or 4)//2)))
    requested = cfg.get('device', 'auto')
    if requested == 'cpu':
        # CosyVoice internally chooses cuda from is_available(). This child
        # owns that policy; no monkey-patch leaks into another task.
        torch.cuda.is_available = lambda: False
    probe = torch_probe(engine, requested, int(cfg.get('gpuIndex', 0)))
    if engine=='cosy':
        from engine_availability import require
        require('cosyvoice3',root,sys.platform,probe['backend'])
    emit('Selected inference device', hardware=probe)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    if engine == 'qwen':
        from qwen_tts import Qwen3TTSModel
        model = Qwen3TTSModel.from_pretrained(str(root / 'models' / cfg.get('qwenModel', 'qwen-small')),
                    device_map=probe['device'], dtype=getattr(torch, probe['dtype']), attn_implementation='sdpa')
    elif engine == 'cosy':
        source = root / 'sources/cosy'
        sys.path[:0] = [str(source), str(source / 'third_party/Matcha-TTS')]
        # Tokenizer/voice embedding ONNX nodes use CPU on this first PC beta.
        # The large LLM/flow/vocoder still run on CUDA or ROCm. Upstream asks
        # for CUDA ORT on HIP too; choosing CPU here avoids a false capability.
        import onnxruntime as ort
        original_session = ort.InferenceSession
        def session(*args, **kwargs):
            kwargs['providers'] = ['CPUExecutionProvider']
            return original_session(*args, **kwargs)
        ort.InferenceSession = session
        from cosyvoice.cli.cosyvoice import CosyVoice3
        model = CosyVoice3(str(root / 'models/cosy'), fp16=probe['device'].startswith('cuda'),
                           load_trt=False, load_vllm=False)
    else:
        gpt_text_compatibility()
        import dubbing_runner
        from gsv_versions import version as model_version
        version=model_version(cfg)
        dubbing_runner.gsv_import(root,version)
        from TTS_infer_pack.TTS import TTS, TTS_Config
        settings = dict(TTS_Config.default_configs[version])
        settings.update(device=probe['device'], is_half=probe['device'].startswith('cuda'))
        config = TTS_Config({'custom': settings})
        folder = Path(cfg.get('job', root / 'checks'))
        folder.mkdir(parents=True, exist_ok=True)
        config.configs_path = str(folder / 'gpt-infer-config.yaml')
        model = TTS(config)
    return model, probe


def take(model, engine, item, language, seed):
    import torch
    import numpy as np
    reference = item['profile']['reference']
    text = item['text']
    torch.manual_seed(seed)
    if engine == 'cosy':
        instruction = 'You are a helpful assistant.' + (' 请用广东话表达。' if language == 'yue' else ' Speak English.') + '<|endofprompt|>'
        chunks = [chunk['tts_speech'].detach().float().cpu().numpy().reshape(-1)
                  for chunk in model.inference_instruct2(text, instruction, reference,
                           stream=False, text_frontend=False)]
        return np.concatenate(chunks) if chunks else np.array([]), model.sample_rate
    if engine == 'qwen':
        # Cantonese is not a named Qwen language. Auto is experimental and
        # must not be relabelled as verified Cantonese or Mandarin forced.
        audio, sr = model.generate_voice_clone(text=text,
                      language='English' if language == 'en' else 'Auto', ref_audio=reference,
                      x_vector_only_mode=True, max_new_tokens=1024, temperature=.3,
                      repetition_penalty=1.15)
        return np.asarray(audio[0]).reshape(-1), sr
    if int(item.get('sampleSteps',32)) not in (16,32):raise ValueError('Invalid V4 rendering quality.')
    from dubbing_runner import gsv_take
    voice = item['profile']
    request = dict(text=text, text_lang='en' if language == 'en' else 'all_yue',
                   ref_audio_path=reference, prompt_text=voice.get('promptText', ''),
                   prompt_lang={'ja': 'all_ja', 'yue': 'all_yue', 'en': 'en'}[voice.get('language', 'ja')],
                   text_split_method='cut0', batch_size=1, speed_factor=1., seed=seed,
                   parallel_infer=False, streaming_mode=False, fragment_interval=0., repetition_penalty=1.35,sample_steps=int(item.get('sampleSteps',32)),super_sampling=False)
    # Our outer loop supplies the two persistent attempts. Keep this helper's
    # internal retry budget to one, preserving actual signal diagnostics.
    remaining = [True]
    def reserve():
        return remaining.pop() if remaining else False
    sr, audio, attempts = gsv_take(model, lambda: model, request, item.get('targetSeconds'),
                                   device='cuda', reserve_attempt=reserve)
    if attempts[-1]['problems']:
        raise RuntimeError(', '.join(attempts[-1]['problems']))
    if sr!=48000:raise RuntimeError('GPT-SoVITS V4 did not generate native 48 kHz audio.')
    return audio, sr


def synthesize(cfg):
    import numpy as np
    import soundfile as sf
    from tts_health import problems
    from speech_level import condition, REVISION
    engine, root = cfg['engine'], Path(cfg['storage'])
    with contextlib.redirect_stdout(sys.stderr):
        model, probe = load_model(engine, root, cfg)
    emit('Inference runtime ready', hardware=probe)
    failures = []
    for index, item in enumerate(cfg['items']):
        path = Path(item['output'])
        path.parent.mkdir(parents=True, exist_ok=True)
        health = path.with_suffix('.health.json')
        from downloads import sha256
        evidence = json.loads(health.read_text()) if health.is_file() else {}
        if path.is_file() and evidence.get('passed') and evidence.get('audioSHA256') == sha256(path):
            emit('Reusing completed recording', progress=(index+1)/len(cfg['items']))
            continue
        if path.is_file():
            path.replace(path.with_suffix(f'.invalid-{time.time_ns()}.wav'))
        attempts = json.loads(health.read_text()).get('attempts', []) if health.is_file() else []
        while len(attempts) < 2:
            seed = 42 + 31*len(attempts)
            started = time.monotonic()
            # Record the reserved attempt before inference: an interrupted or
            # killed child cannot loop forever through the same bad sentence.
            attempts.append(dict(seed=seed, error='interrupted-before-completion'))
            health.write_text(json.dumps(dict(passed=False, attempts=attempts), indent=2), encoding='utf-8')
            try:
                with contextlib.redirect_stdout(sys.stderr):
                    audio, sr = take(model, engine, item, cfg.get('language', 'yue'), seed)
                audio = np.asarray(audio, dtype=np.float32).reshape(-1)
                errors = problems(audio, sr, item['text'], item.get('targetSeconds'))
                raw = path.with_suffix(f'.seed{seed}.raw.wav')
                if len(audio) and np.isfinite(audio).all():
                    sf.write(raw, audio, sr, subtype='FLOAT')
                leveled, level = condition(audio, sr)
                errors += [e for e in problems(leveled, sr, item['text'], item.get('targetSeconds')) if e not in errors]
                attempts[-1] = dict(seed=seed, errors=errors, seconds=round(time.monotonic()-started, 3),
                                   duration=len(audio)/sr, level=level, raw=str(raw))
                if not errors:
                    temporary = path.with_suffix('.partial.wav')
                    sf.write(temporary, leveled, sr, subtype='PCM_16')
                    temporary.replace(path)
                    health.write_text(json.dumps(dict(passed=True, attempts=attempts, hardware=probe,
                                   audioSHA256=sha256(path), levelRevision=REVISION,
                                   contentVerified=False, speakerVerified=False), indent=2), encoding='utf-8')
                    break
            except Exception as error:
                attempts[-1] = dict(seed=seed, error=str(error), seconds=round(time.monotonic()-started, 3))
            health.write_text(json.dumps(dict(passed=False, attempts=attempts, hardware=probe), indent=2), encoding='utf-8')
        if not path.is_file():
            failures.append(index+1)
        emit(f'{engine}: line {index+1}/{len(cfg["items"])}', progress=(index+1)/len(cfg['items']))
    if failures:
        raise RuntimeError(f'Failed lines {failures}. Recordings and diagnostics retained; no completed movie exported. Edit the line/reference to create a new take.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config', nargs='?')
    parser.add_argument('--prepare-gpt')
    parser.add_argument('--load-check', choices=['qwen', 'cosy', 'gpt'])
    parser.add_argument('--root')
    parser.add_argument('--qwen-model', default='qwen-large')
    parser.add_argument('--gsv-version',choices=['v2ProPlus','v4'],default='v4')
    args = parser.parse_args()
    try:
        if args.prepare_gpt:
            audio_compatibility()
            gpt_text_compatibility()
            from dubbing_runner import prepare_gsv
            prepare_gsv(Path(args.prepare_gpt),args.gsv_version)
        elif args.load_check:
            with contextlib.redirect_stdout(sys.stderr):
                load_model(args.load_check, Path(args.root), dict(qwenModel=args.qwen_model,ttsBackend='gpt-sovits-v2' if args.gsv_version=='v2ProPlus' else 'gpt-sovits'))
            emit('Model load passed; speech inference not yet tested.')
        else:
            synthesize(json.loads(Path(args.config).read_text(encoding='utf-8')))
    except Exception as error:
        import traceback
        traceback.print_exc(file=sys.stderr)
        emit('Failed: ' + str(error))
        sys.exit(1)
