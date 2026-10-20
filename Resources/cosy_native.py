"""Official FunAudioLLM CosyVoice 3 inference, isolated to its own Mac runtime."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace


class NativeCosy:
    def __init__(self, model):
        self.model = model

    def generate(self, text, ref_audio, instruct_text, temperature=0.8, **unused):
        import numpy as np
        import soundfile as sf
        fd, name = tempfile.mkstemp(suffix='.wav', prefix='anicanto-cosy-')
        os.close(fd)
        try:
            sf.write(name, np.asarray(ref_audio, dtype=np.float32), 24000)
            instruction = instruct_text.rstrip() + '<|endofprompt|>'
            import torch
            with torch.inference_mode():
                for part in self.model.inference_instruct2(text, instruction, name,
                                                           stream=False, text_frontend=False):
                    yield SimpleNamespace(audio=part['tts_speech'].detach().float().cpu().numpy().reshape(-1))
        finally:
            Path(name).unlink(missing_ok=True)


def load(root, variant=None):
    if variant not in (None, 'cosy-native-0.5b'):
        raise ValueError('CosyVoice 3 requires the official PyTorch model.')
    import torch
    import torchaudio
    import soundfile as sf
    import onnxruntime as ort

    # Upstream expects torchaudio.load's earlier PCM API. The app already
    # uses soundfile for decoding; keep reference audio local and deterministic.
    def load_audio(path, frame_offset=0, num_frames=-1, normalize=True,
                   channels_first=True, **kwargs):
        audio, rate = sf.read(str(path), start=frame_offset, frames=num_frames,
                              dtype='float32' if normalize else 'int16', always_2d=True)
        return torch.from_numpy(audio.T.copy() if channels_first else audio.copy()), rate
    torchaudio.load = load_audio
    torch.set_num_threads(max(1, min(8, (os.cpu_count() or 4) // 2)))
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', ORT_DISABLE_TELEMETRY='1')
    source = Path(root) / 'sources/cosy'
    if not (source / '.source-complete').is_file() or not (source / 'third_party/Matcha-TTS/.source-complete').is_file():
        raise ValueError('CosyVoice 3 source code is incomplete; repair the download.')
    sys.path[:0] = [str(source), str(source / 'third_party/Matcha-TTS')]
    original_session = ort.InferenceSession
    def cpu_session(*args, **kwargs):
        kwargs['providers'] = ['CPUExecutionProvider']
        return original_session(*args, **kwargs)
    ort.InferenceSession = cpu_session
    from cosyvoice.cli.cosyvoice import CosyVoice3
    model = CosyVoice3(str(Path(root) / 'models/cosy'), fp16=False,
                       load_trt=False, load_vllm=False)
    return NativeCosy(model)
