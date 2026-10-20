"""Check pinned packages and imports before trusting a Windows runtime receipt."""
import os,subprocess
from pathlib import Path
PROBES={
 'worker':'import numpy,scipy,soundfile,PIL,av,yaml,httpx,faster_whisper',
 'analysis':'import torch,torchaudio,numpy,soundfile,audio_separator,sklearn,onnxruntime',
 'asr':'import torch,torchaudio,transformers,soundfile',
 'gpt':'import torch,torchaudio,transformers,soundfile,pyopenjtalk,jieba,ToJyutping',
 'cosy':'import torch,torchaudio,transformers,soundfile,hyperpyyaml,onnxruntime',
 'local':'import torch,torchaudio,transformers,soundfile,hyperpyyaml',
}
def state(python):
 from mac_runtime import package_state
 return package_state(python,dict(os.environ,PYTHONNOUSERSITE='1'))
def missing(python,requirements):
 from mac_runtime import requirements as pins
 current=state(python)
 if current.get('python')!=[3,12]:raise ValueError('Windows runtime requires private Python 3.12.')
 return [n for n,v in pins(requirements).items() if current['packages'].get(n)!=v]
def probe(python,name):
 subprocess.run([str(python),'-c',PROBES[name]],check=True,timeout=180,env=dict(os.environ,PYTHONNOUSERSITE='1'))
def damaged(python,requirements,backend=False):
 from mac_runtime import damaged_packages,requirements as pins
 expected=pins(requirements)
 if backend:expected.update(torch='',torchaudio='')
 return damaged_packages(python,dict(os.environ,PYTHONNOUSERSITE='1'),expected)
