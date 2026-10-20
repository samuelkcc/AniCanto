"""Torch CosyVoice provider for the shared generation and diagnostic policy."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace

class NativeCosy:
    def __init__(self,model):self.model=model
    def generate(self,text,ref_audio,instruct_text,temperature=0.8,**unused):
        import numpy as np
        import soundfile as sf
        fd,name=tempfile.mkstemp(suffix='.wav',prefix='anicanto-cosy-');os.close(fd)
        try:
            sf.write(name,np.asarray(ref_audio,dtype=np.float32),24000)
            instruction=instruct_text.rstrip()+'<|endofprompt|>'
            for part in self.model.inference_instruct2(text,instruction,name,stream=False,text_frontend=False):
                yield SimpleNamespace(audio=part['tts_speech'].detach().float().cpu().numpy().reshape(-1))
        finally:Path(name).unlink(missing_ok=True)

def load(root,variant=None):
    if variant not in (None,'cosy-native-0.5b'):raise ValueError('Native CosyVoice model selection is incompatible with MLX.')
    from native_tts import load_model
    model,probe=load_model('cosy',Path(root),dict(device=os.environ.get('CANTOSYNC_NATIVE_DEVICE','auto')))
    return NativeCosy(model)
