"""Pinned offline VoxCPM2 and WenetSpeech-Yue inference in a separate runtime."""
from runtime_installer import ensure_env, pip_command
from fast_mode import enabled as one_pass

import contextlib
import io
import json
import os
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parent
ENGINES = {
    'voxcpm2': dict(key='voxcpmModel', default='voxcpm2-2b-bf16', languages=('yue', 'zh', 'en'), rate=48000, title='VoxCPM2'),
    'wsyue': dict(key='wsyueModel', default='wsyue-cosy2-zjg', languages=('yue',), rate=24000, title='WenetSpeech-Yue'),
    'drama3': dict(key='drama3Model', default='drama3-35b-4bit', languages=('yue','zh','en'), rate=44100, title='Drama 3'),
}
REVISION = 'official-local-tts-2'


def selection(cfg, engine):
    if engine not in ENGINES:
        raise ValueError('Unknown local TTS engine.')
    return cfg.get(ENGINES[engine]['key']) or ENGINES[engine]['default']


def validate(cfg, engine):
    if cfg.get('targetLanguage', 'yue') not in ENGINES[engine]['languages']:
        raise ValueError('WenetSpeech-Yue 只提供廣東話；英文請選擇其他已部署引擎。')
    from voice_models import choice
    return choice(engine, selection(cfg, engine))


def install(root, engine, variant=None):
    if engine=='drama3':
        from drama3 import install as install_drama
        return install_drama(root,variant)
    from dubbing_setup import call, download, emit
    from runtime_paths import python_for, packages_ready
    from voice_models import install_files, mark_ready
    root = Path(root)
    python = python_for(root, 'local-tts-runtime')
    if not python.exists():
        ensure_env(root, root / 'local-tts-runtime', run=lambda args,**kw: call(args))
    if not packages_ready(root,'local-tts-runtime'):
        call(pip_command(python, root, 'install', '--only-binary', ':all:', '--find-links', ROOT / 'wheels', '-r', ROOT / 'local-tts-requirements.lock'))
    row, folder = install_files(root, engine, variant, download, emit)
    call([python, ROOT/'local_tts.py', 'prepare', engine, root, row['id']])
    mark_ready(root, row)
    marker = dict(engine=engine, variant=row['id'], revision=row['revision'], adapter=REVISION)
    (root/'local-tts-ready.json').write_text(json.dumps(marker))
    (root/(engine+'-ready.json')).write_text(json.dumps(marker))
    emit(ENGINES[engine]['title']+' 已通過離線載入檢查。')


def inference_config(path):
    """Use the official inference nodes without constructing training modules."""
    import yaml
    node = yaml.compose(Path(path).read_text())
    wanted = {'sample_rate', 'llm_input_size', 'llm_output_size', 'spk_embed_dim', 'qwen_pretrain_path',
              'token_frame_rate', 'token_mel_ratio', 'chunk_size', 'num_decoding_left_chunks',
              'llm', 'flow', 'hift', 'get_tokenizer', 'allowed_special', 'feat_extractor'}
    if not isinstance(node, yaml.MappingNode):
        raise ValueError('Wenet model configuration is invalid.')
    node.value = [(key, value) for key, value in node.value if key.value in wanted]
    from hyperpyyaml import load_hyperpyyaml
    return load_hyperpyyaml(io.StringIO(yaml.serialize(node)), overrides={'qwen_pretrain_path': str(Path(path).parent/'CosyVoice-BlankEN')})


def load(cfg, engine):
    if engine=='drama3':
        from drama3 import load as load_drama
        return load_drama(cfg)
    validate(cfg, engine)
    from dubbing_runner import offline
    offline()
    cache = Path(cfg['storage'])/'models/cache/local-tts'
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.update(HF_HOME=str(cache), HF_HUB_CACHE=str(cache/'hub'), ORT_DISABLE_TELEMETRY='1')
    from voice_models import resolve
    folder = resolve(cfg['storage'], engine, selection(cfg, engine))
    import torch
    torch.set_num_threads(max(1, min(4, int(cfg.get('localTTSThreads', 2)))))
    if torch.get_num_interop_threads()!=1:torch.set_num_interop_threads(1)
    if engine == 'voxcpm2':
        sys.path.insert(0, str(ROOT/'tts-vendor/voxcpm2'))
        from voxcpm import VoxCPM
        device = cfg.get('voxcpmDevice', 'mps' if torch.backends.mps.is_available() else 'cpu')
        if device not in (('cpu','cuda','cuda:0') if sys.platform=='win32' else ('cpu','mps')):
            raise ValueError('VoxCPM2 運行裝置無效。')
        model = VoxCPM.from_pretrained(str(folder), load_denoiser=False, optimize=False, device=device, local_files_only=True)
        if model.tts_model.sample_rate != 48000:
            raise ValueError('VoxCPM2 原生取樣率不符，未部署。')
        return model
    sys.path.insert(0, str(ROOT/'tts-vendor/wsyue'))
    from cosyvoice.cli.frontend import CosyVoiceFrontEnd
    from cosyvoice.cli.model import CosyVoice2Model
    configs = inference_config(folder/'cosyvoice2.yaml')
    frontend = CosyVoiceFrontEnd(configs['get_tokenizer'], configs['feat_extractor'], str(folder/'campplus.onnx'),
                                str(folder/'speech_tokenizer_v2.onnx'), spk2info='', allowed_special=configs['allowed_special'])
    model = CosyVoice2Model(configs['llm'], configs['flow'], configs['hift'], fp16=False)
    model.load(str(folder/'llm.pt'), str(folder/'flow.pt'), str(folder/'hift.pt'))
    if str(model.device) != 'cpu':
        raise ValueError('WenetSpeech-Yue adapter requires its tested CPU path.')
    return dict(frontend=frontend, model=model, rate=configs['sample_rate'])


def generate(model, engine, item, cfg):
    if engine=='drama3':
        from drama3 import generate as generate_drama
        return generate_drama(model,item,cfg),44100
    import numpy as np
    import torch
    voice = item['profile']
    text = item['text']
    seed = int(item.get('seed', 42))
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if engine == 'voxcpm2':
        from voice_parameters import effective
        parameters=effective(cfg,engine)
        guidance = '用自然香港廣東話，保持參考錄音的音色' if cfg.get('targetLanguage', 'yue') == 'yue' else '请用中国大陆标准普通话，保持参考录音的音色' if cfg.get('targetLanguage')=='zh' else 'Speak natural English, preserving the reference voice'
        return model.generate(text='('+guidance+')'+text, reference_wav_path=voice['reference'], seed=seed,
                              cfg_value=parameters['voxcpmGuidance'], inference_timesteps=parameters['voxcpmSteps'], normalize=False, denoise=False,
                              retry_badcase=False, max_len=min(768, max(96, len(text)*8))), 48000
    from cosyvoice.utils.file_utils import load_wav
    prompt = load_wav(voice['reference'], 16000)
    frontend = model['frontend']
    inputs = frontend.frontend_instruct2(text, '用粤语说这句话', prompt, model['rate'], '')
    from voice_parameters import effective
    parameters=effective(cfg,engine)
    chunks = [result['tts_speech'].detach().cpu().numpy().reshape(-1) for result in model['model'].tts(**inputs, stream=False, speed=parameters['wsyueSpeed'])]
    return (np.concatenate(chunks) if chunks else np.zeros(0)), model['rate']


def synthesize(cfg, emit, engine):
    if engine=='drama3':
        if sys.platform=='win32':
            from native_drama import synthesize as synthesize_drama
            return synthesize_drama(cfg,emit)
        from drama3 import synthesize as synthesize_drama
        return synthesize_drama(cfg,emit)
    validate(cfg, engine)
    from track_control import check
    check(cfg)
    emit('配音', '載入 '+ENGINES[engine]['title']+'；本機離線生成。', workID='tts', workCompleted=0, workTotal=len(cfg['items']))
    with contextlib.redirect_stdout(sys.stderr):
        model = load(cfg, engine)
    import numpy as np
    import soundfile as sf
    from tts_health import problems
    if one_pass(cfg):
        from fast_mode import basic_problems as problems
    from speech_level import condition
    failures = []
    for index, item in enumerate(cfg['items']):
        check(cfg)
        path = Path(item['output'])
        from audio_fallback import healthy
        if path.is_file() and (path.stat().st_size>44 if one_pass(cfg) else healthy(path)):
            emit('配音', '沿用已完成 '+ENGINES[engine]['title']+' 錄音。', workID='tts', workCompleted=index+1, workTotal=len(cfg['items']))
            continue
        started = time.monotonic()
        try:
            with contextlib.redirect_stdout(sys.stderr), torch_inference():
                audio, rate = generate(model, engine, item, cfg)
            audio = np.asarray(audio, dtype=np.float32).reshape(-1)
            path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(path.with_suffix('.raw.wav'),audio,rate,subtype='FLOAT')
            errors = problems(audio, rate, item['text'], item.get('targetSeconds'))
            if errors:
                raise ValueError(', '.join(errors))
            audio, level = condition(audio, rate)
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix('.partial.wav')
            sf.write(temp, audio, rate, subtype='PCM_16'); temp.replace(path)
            path.with_suffix('.level.json').write_text(json.dumps(level))
        except (RuntimeError, ValueError, OSError) as error:
            position=item.get('reviewIndex')
            failures.append(f"第 {position+1 if isinstance(position,int) else index+1} 段：{error}")
            emit('配音需修正', failures[-1])
        emit('配音', ENGINES[engine]['title']+f' · 第 {index+1}/{len(cfg["items"])} 句',
             workID='tts', workCompleted=index+1, workTotal=len(cfg['items']), cueIndex=item.get('reviewIndex'), seconds=round(time.monotonic()-started, 2))
    if failures:
        raise ValueError(ENGINES[engine]['title']+'；'.join(failures)+'；其他完成錄音保留。')


def torch_inference():
    import torch
    return torch.inference_mode()


if __name__ == '__main__':
    try:
        if sys.argv[1] == 'prepare':
            engine, root, variant = sys.argv[2:5]
            cfg = dict(storage=root, targetLanguage='yue', voxcpmDevice='cpu', **{ENGINES[engine]['key']: variant})
            with contextlib.redirect_stdout(sys.stderr):load(cfg, engine)
            print(json.dumps(dict(stage='部署配音', message=ENGINES[engine]['title']+' 離線模型載入通過。'), ensure_ascii=False))
        else:
            from dubbing_runner import emit
            cfg = json.loads(Path(sys.argv[2]).read_text())
            synthesize(cfg, emit, sys.argv[1])
    except Exception as error:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(json.dumps(dict(stage='錯誤', message=str(error)), ensure_ascii=False), flush=True)
        sys.exit(1)
