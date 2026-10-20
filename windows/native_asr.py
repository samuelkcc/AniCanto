"""Official Transformers-native Qwen ASR. Expected dialogue is never a prompt."""
import os
from pathlib import Path
from types import SimpleNamespace


class NativeASR:
    def __init__(self,model,processor):self.model,self.processor=model,processor
    def generate(self,audio,language=None,max_tokens=256,verbose=False):
        import numpy as np
        import torch
        audio=np.asarray(audio,dtype=np.float32)
        if audio.ndim!=1 or not len(audio) or not np.isfinite(audio).all():raise ValueError('Invalid ASR waveform.')
        # No transcript, expected text or hotwords are supplied to independent QA.
        kwargs=dict(audio=audio)
        if language:kwargs['language']=language
        inputs=self.processor.apply_transcription_request(**kwargs).to(self.model.device,self.model.dtype)
        with torch.inference_mode():ids=self.model.generate(**inputs,max_new_tokens=max(16,min(512,int(max_tokens))))
        generated=ids[:,inputs['input_ids'].shape[1]:]
        parsed=self.processor.decode(generated,return_format='parsed')[0]
        if not isinstance(parsed,dict):raise ValueError('ASR returned malformed transcription.')
        return SimpleNamespace(text=str(parsed.get('transcription','')),language=str(parsed.get('language','')))


def load(root,variant=None):
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    from model_catalog import resolve,selected
    variant=variant or selected(root,'asr')
    if variant!='asr-native-1.7b':raise ValueError('Select the native Windows ASR model; MLX weights are incompatible.')
    folder=resolve(root,variant)
    import torch
    from transformers import AutoProcessor,AutoModelForMultimodalLM
    device='cuda:0' if torch.cuda.is_available() else 'cpu'
    dtype=torch.bfloat16 if device!='cpu' and torch.cuda.is_bf16_supported() else torch.float16 if device!='cpu' else torch.float32
    model=AutoModelForMultimodalLM.from_pretrained(str(folder),device_map=device,dtype=dtype,local_files_only=True,attn_implementation='sdpa')
    processor=AutoProcessor.from_pretrained(str(folder),local_files_only=True)
    return NativeASR(model,processor)
