---
license: other
license_name: fish-audio-community-license
license_link: LICENSE
base_model: fishaudio/drama-3
base_model_relation: quantized
pipeline_tag: text-to-speech
library_name: mlx-audio
tags:
  - mlx
  - mlx-audio
  - text-to-speech
  - multi-speaker
  - voice-cloning
language:
  - zh
  - en
  - ja
  - ko
  - es
  - pt
  - ar
  - ru
  - fr
  - de
  - sv
  - it
  - tr
  - 'no'
  - nl
  - cy
  - eu
  - ca
  - da
  - gl
  - ta
  - hu
  - fi
  - pl
  - et
  - hi
  - la
  - ur
  - th
  - vi
  - jw
  - bn
  - yo
  - sl
  - cs
  - sw
  - nn
  - he
  - ms
  - uk
  - id
  - kk
  - bg
  - lv
  - my
  - tl
  - sk
  - ne
  - fa
  - af
  - el
  - bo
  - hr
  - ro
  - sn
  - mi
  - yi
  - am
  - be
  - km
  - is
  - az
  - sd
  - br
  - sq
  - ps
  - mn
  - ht
  - ml
  - sr
  - sa
  - te
  - ka
  - bs
  - pa
  - lt
  - kn
  - si
  - hy
  - mr
  - as
  - gu
  - fo
---

# Drama 3 MLX 4-bit

**Built with Fish Audio.**

[Fish Audio Drama 3](https://huggingface.co/fishaudio/drama-3) converted for [mlx-audio](https://github.com/Blaizzy/mlx-audio) on Apple Silicon. This is an unofficial community conversion; Fish Audio did not release or endorse it.

- routed experts: 4-bit, dequantized from the block-FP8 release
- dense projections and audio tower: 8-bit
- 22 GB on disk, about 26 GB peak memory while generating

## Usage

Drama 3 support is in review in mlx-audio ([#1018](https://github.com/Blaizzy/mlx-audio/pull/1018)). Until it is merged, install from the PR branch:

```bash
pip install "mlx-audio @ git+https://github.com/stickerdaniel/mlx-audio@fish-drama3"
```

```python
from mlx_audio.tts.utils import load_model

model = load_model("mlx-community/fish-audio-drama-3-4bit")

for result in model.generate(
    text="[sighs] Fine. If we miss it, it's on you.",
    ref_audio="reference.wav",
    ref_text="Transcript of the reference clip.",
    stream=True,
    first_chunk_frames=4,
):
    print(result.audio.shape)  # 44.1 kHz chunks
```

```bash
python -m mlx_audio.tts.generate --model mlx-community/fish-audio-drama-3-4bit \
    --text "[sighs] Fine. If we miss it, it's on you." \
    --ref_audio reference.wav --ref_text "Transcript of the reference clip." \
    --temperature 0.7 --top_p 0.7 --top_k 30
```

Speaker tags (`<|speaker:0|>` to `<|speaker:15|>`), multiple references and streaming are described in the [model docs](https://github.com/stickerdaniel/mlx-audio/blob/fish-drama3/docs/models/tts/fish-drama3.md).

## Quality and speed

On an M3 Max:

- 22 ms per frame (46 ms of audio), about 2x real time
- first streamed audio in 160 to 200 ms once a voice is cached
- teacher-forced against the PyTorch reference: backbone hidden cosine 0.995, semantic top-1 86%

## Conversion

Made with mlx-audio's converter:

```bash
python -m mlx_audio.tts.models.fish_drama3.convert --src drama-3 --dst drama-3-mlx-4bit \
    --expert-bits 4 --dense-bits 8 --tower-bits 8
```

The unquantized weights are at [mlx-community/fish-audio-drama-3-bf16](https://huggingface.co/mlx-community/fish-audio-drama-3-bf16).

`NOTICE` lists every change to the original weights.

## License

The [Fish Audio Community License](LICENSE) applies, including its use restrictions and its terms for commercial use and hosted services.
