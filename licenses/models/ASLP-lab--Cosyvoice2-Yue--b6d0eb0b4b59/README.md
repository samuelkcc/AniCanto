---
license: apache-2.0
---
<!-- ![WenetSpeech-Yue](https://huggingface.co/datasets/ASLP-lab/WenetSpeech-Yue/resolve/main/wenetspeech_pipe.svg) -->


## 👉🏻 WenetSpeech-Yue 👈🏻  
**WenetSpeech-Yue**: [Demos](https://aslp-lab.github.io/WenetSpeech-Yue/); [Paper](https://arxiv.org/abs/2509.03959); [Github](https://github.com/ASLP-lab/WenetSpeech-Yue); [HuggingFace](https://huggingface.co/datasets/ASLP-lab/WenetSpeech-Yue)

## Highlight🔥

**WenetSpeech-Yue TTS Models** have been released!  
This repository contains two versions of the TTS models:  
1. **ASLP-lab/Cosyvoice2-Yue**: The base model for Cantonese TTS.  
2. **ASLP-lab/Cosyvoice2-Yue-ZoengJyutGaai**: A fine-tuned, higher-quality version for more natural speech generation.

## Roadmap

- [x] 2025/9

    - [x] 25hz WenetSpeech-Yue TTS models released


## Install

**Clone and install**

- Clone the repo
``` sh
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
# If you failed to clone submodule due to network failures, please run following command until success
cd CosyVoice
git submodule update --init --recursive
```

- Install Conda: please see https://docs.conda.io/en/latest/miniconda.html
- Create Conda env:

``` sh
conda create -n cosyvoice python=3.10
conda activate cosyvoice
# pynini is required by WeTextProcessing, use conda to install it as it can be executed on all platform.
conda install -y -c conda-forge pynini==2.1.5
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com

# If you encounter sox compatibility issues
# ubuntu
sudo apt-get install sox libsox-dev
# centos
sudo yum install sox sox-devel
```

**Model download**


1. [Cosyvoice2-Yue](https://huggingface.co/ASLP-lab/Cosyvoice2-Yue)
2. [Cosyvoice2-Yue-ZoengJyutGaai](https://huggingface.co/ASLP-lab/Cosyvoice2-Yue-ZoengJyutGaai)


**Basic Usage**

We strongly recommend using `CosyVoice2-0.5B` for better performance.
Follow code below for detailed usage of each model.

``` python
import sys
sys.path.append('third_party/Matcha-TTS')
from cosyvoice.cli.cosyvoice import CosyVoice, CosyVoice2
from cosyvoice.utils.file_utils import load_wav
import torchaudio
```

**CosyVoice2 Usage**
```python
cosyvoice = CosyVoice2('ASLP-lab/Cosyvoice2-Yue', load_jit=False, load_trt=False, fp16=False)

# NOTE if you want to reproduce the results on https://funaudiollm.github.io/cosyvoice2, please add text_frontend=False during inference
# zero_shot usage
prompt_speech_16k = load_wav('zero_shot_prompt.wav', 16000)

# instruct usage
for i, j in enumerate(cosyvoice.inference_instruct2('收到朋友从远方寄嚟嘅生日礼物，呢份意外嘅惊喜同埋满满嘅祝福令我内心充满咗甜蜜嘅快乐，个笑容就好似花咁咧盛开住。', '用粤语说这句话', prompt_speech_16k, stream=False)):
    torchaudio.save('instruct_{}.wav'.format(i), j['tts_speech'], cosyvoice.sample_rate)
```

## Contact
If you are interested in leaving a message to our research team, feel free to email lhli@mail.nwpu.edu.cn or gzhao@mail.nwpu.edu.cn.