"""Offline model-load probes; never describe these as speech-quality acceptance."""
import json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;SHARED=HERE/'shared' if (HERE/'shared').is_dir() else HERE.parent/'Resources';sys.path.insert(0,str(SHARED))
def main(kind,root,backend=None):
 root=Path(root)
 if kind=='analysis':
  from native_tts import audio_compatibility
  audio_compatibility()
  from dubbing_runner import prepare_separator
  prepare_separator(root)
  from speakers import prepare
  prepare(root)
  from model_catalog import resolve,selected
  from faster_whisper import WhisperModel
  WhisperModel(str(resolve(root,selected(root,'speech'))),device='cpu',compute_type='int8',local_files_only=True)
  from native_tools import classifier
  classifier(root)
 elif kind=='asr':
  from native_asr import load
  load(root)
 elif kind=='drama3':
  from native_drama import probe
  probe(root,backend=backend,emit=lambda stage,message,**extra:print(json.dumps(dict(stage=stage,message=message,**extra)),flush=True))
 else:
  import torch
  if kind=='wsyue':torch.cuda.is_available=lambda:False
  from local_tts import load
  from native_tts import audio_compatibility
  audio_compatibility()
  selected=json.loads((root/'model-selections.json').read_text())
  cfg=dict(storage=str(root),voxcpmDevice='cuda' if torch.cuda.is_available() else 'cpu')
  cfg['voxcpmModel' if kind=='voxcpm2' else 'wsyueModel']=selected.get(kind) or selected.get('voice')
  load(cfg,kind)
 print(json.dumps(dict(stage='Windows setup',message=kind+' offline model loading passed. Speech quality is not yet tested.')),flush=True)
if __name__=='__main__':main(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)
