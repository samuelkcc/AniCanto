---
license: apache-2.0
language: 
- en
- zh
- de
- es
- ru
- ko
- fr
- ja
- pt
- tr
- pl
- ca
- nl
- ar
- sv
- it
- id
- hi
- fi
- vi
- he
- uk
- el
- ms
- cs
- ro
- da
- hu
- ta
- no
- th
- ur
- hr
- bg
- lt
- la
- mi
- ml
- cy
- sk
- te
- fa
- lv
- bn
- sr
- az
- sl
- kn
- et
- mk
- br
- eu
- is
- hy
- ne
- mn
- bs
- kk
- sq
- sw
- gl
- mr
- pa
- si
- km
- sn
- yo
- so
- af
- oc
- ka
- be
- tg
- sd
- gu
- am
- yi
- lo
- uz
- fo
- ht
- ps
- tk
- nn
- mt
- sa
- lb
- my
- bo
- tl
- mg
- as
- tt
- haw
- ln
- ha
- ba
- jw
- su
pipeline_tag: automatic-speech-recognition
library_name: mlx-audio
tags:
- mlx
- speech-to-text
- speech-to-speech
- speech
- speech generation
- stt
- audio
- automatic-speech-recognition
- hf-asr-leaderboar
---


# mlx-community/whisper-large-v3-asr-fp16
This model was converted to MLX format from [`openai/whisper-large-v3`](https://huggingface.co/openai/whisper-large-v3) using mlx-audio version **0.3.0**.
Refer to the [original model card](https://huggingface.co/openai/whisper-large-v3) for more details on the model.

## Use with mlx-audio

```bash
pip install -U mlx-audio
```

### CLI Example:
```bash
    python -m mlx_audio.stt.generate --model mlx-community/whisper-large-v3-asr-fp16 --audio "audio.wav"
```
### Python Example:
```python
    from mlx_audio.stt.utils import load_model
    from mlx_audio.stt.generate import generate_transcription
    model = load_model("mlx-community/whisper-large-v3-asr-fp16")
    transcription = generate_transcription(
        model=model,
        audio_path="path_to_audio.wav",
        output_path="path_to_output.txt",
        format="txt",
        verbose=True,
    )
    print(transcription.text)
```
