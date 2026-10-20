---
license: other
license_name: fish-audio-community-license-v1.0
license_link: LICENSE
base_model: fishaudio/drama-3
base_model_relation: quantized
language:
- ja
- en
pipeline_tag: text-to-speech
tags:
- gguf
- text-to-speech
- voice-cloning
- moe
- pruning
- quantization
- japanese
- audio.cpp
---

# drama3-small: a compressed Fish Audio Drama 3 that should fit in 12 GB of VRAM

**Built with Fish Audio.** This is a compressed derivative of [Fish Audio Drama 3](https://huggingface.co/fishaudio/drama-3). Fish Audio does not sponsor or endorse it.

drama3-small keeps Drama 3's expressive Japanese and English voice cloning: inline tags, English style directions and director's notes. It should fit in 12 GB of VRAM. The 35B-A3B mixture-of-experts backbone was pruned to 45% of its expert slots and quantized to about 3 bits. It was then distilled back towards the original on Japanese and English speech.

| | |
|---|---|
| File | `drama3-small-IQ3_XXS.gguf`, 9.74 GiB |
| VRAM | Should fit in 12 GB. Measured peak 10.26 GiB (streaming, 30 s reference, RTX 4090); not yet tested on an actual 12 GB card |
| Speed (offline, RTX 4090 / 5090) | About 1.6× / 1.8× real time per request, including reference encoding; about 2.6× / 3.2× once generating |
| Languages | Japanese, English (including Japanese with English technical terms) |
| Features | Zero-shot cloning from about 10–30 s of reference audio; `[tags]`, `<spans>`, English style directions, director's notes |
| Runtime | [audio.cpp](https://github.com/JarodMica/audio.cpp) at `9277495a` + `drama3-small-audiocpp.patch` (CUDA) |

## Samples

All samples come from this GGUF in one take, cloned from a 29-second Japanese reference recording of the repo owner's voice (used with consent).

- **Settings:** temperature 0.7, top-p 0.7, top-k 30, pause fix on (`max_pause_frames` 10).
- **Prompt:** the exact text given to the model, including tags.

| Sample | Prompt | Audio |
|---|---|---|
| JA story (4 sentences), seed 8000 | `その日は朝から雨が降っていた。駅前の喫茶店に入ると、窓際の席に古い友人が座っていた。十年ぶりの再会なのに、彼女は昨日も会ったような顔で手を振った。私は少し笑って、向かいの席に腰を下ろした。` | <audio controls src="https://huggingface.co/pentacoxian-dev/drama3-small-GGUF/resolve/main/samples/ja_story.mp3"></audio> |
| JA with English tech terms, seed 8001 | `今回のリリースでは、APIのレスポンスタイムを平均で三十パーセント改善しました。具体的には、Redisのキャッシュを導入して、データベースへのクエリ数を減らしています。次のスプリントでは、Kubernetesのオートスケーリングも見直す予定です。` | <audio controls src="https://huggingface.co/pentacoxian-dev/drama3-small-GGUF/resolve/main/samples/ja_tech_terms.mp3"></audio> |
| JA inline tags, seed 8010 | `[laughs] まさかそんなオチだとは思わなかった。[sighs] でも、ちょっと安心したよ。` | <audio controls src="https://huggingface.co/pentacoxian-dev/drama3-small-GGUF/resolve/main/samples/ja_laughs_sighs.mp3"></audio> |
| JA with English style direction, seed 8009 | `[softly, whispering as if someone might overhear] ここだけの話なんだけど、来月、部長が異動になるらしいよ。` | <audio controls src="https://huggingface.co/pentacoxian-dev/drama3-small-GGUF/resolve/main/samples/ja_whisper.mp3"></audio> |
| EN story (Japanese reference voice), seed 8012 | `The old lighthouse had been dark for nearly forty years. Every evening, though, someone in the village swore they could see a faint glow at the top. Nobody ever went to check. Maybe nobody wanted to know.` | <audio controls src="https://huggingface.co/pentacoxian-dev/drama3-small-GGUF/resolve/main/samples/en_story.mp3"></audio> |
| EN mid-line tag, seed 8125 | `I tried everything. [sighs] Nothing works, and I'm out of ideas.` | <audio controls src="https://huggingface.co/pentacoxian-dev/drama3-small-GGUF/resolve/main/samples/en_sighs.mp3"></audio> |
| EN whisper span, seed 8020 | `If you listen closely, <whisper>you can hear the ocean from here</whisper>.` | <audio controls src="https://huggingface.co/pentacoxian-dev/drama3-small-GGUF/resolve/main/samples/en_whisper_span.mp3"></audio> |

## What changed compared with Drama 3

| Part | Drama 3 | drama3-small |
|---|---|---|
| Routed experts | 256 per layer, FP8 | 256 in layers 0/1/2/36, 100 in the other 36 layers; IQ3_XXS with a speech imatrix (5.20 GiB) |
| Routers / shared experts | n/a | Kept rows; refit layer by layer, then distilled |
| Attention / Gated DeltaNet, embeddings | BF16 | Q8_0 (distilled LoRA merged before quantization) |
| Output head | Full vocabulary | EOS + 4,096 semantic rows (speech only) |
| Audio tower (MTP) | BF16 | Q8_0 |
| Codec | F16 | F16 (unchanged) |

**How expert counts were chosen:**
- Experts were ranked by routing mass on stratified Japanese and English speech: plain, technical code-switching, styled, and tagged.
- Per-layer counts follow measured sensitivity. Pruning layer 0, 1, 2 or 36 costs far more than any other layer, so those four keep all 256. That reallocation alone cut the proxy KL by 26% compared with a uniform 116 experts per layer.

**Recovery:**
- A layerwise refit of routers and shared experts.
- Then 100 steps of knowledge distillation from the exact FP8 model, using KL on the semantic and audio-tower distributions.
- Data: about 282 h of real speech plus 5,501 lines read by the original model (tags, directions, technical Japanese).
- Longer distillation lowered the proxy KL further but made free-running generation worse: dropped content after the first sentence. The released checkpoint was chosen by listening tests.

## Evaluation

**Proxy fidelity.** Teacher-forced KL against the FP8 original, over 4,097 speech candidates, on 152 held-out Japanese and English pairs. Lower is better.

| Model | Size | KL |
|---|---|---|
| Drama 3, all experts at Q4_K | 16.9 GiB | 0.013 |
| Community Q2_K package | 9.8 GiB | 0.094 |
| drama3-small before distillation | 9.74 GiB | 0.0997 |
| **drama3-small (this release)** | **9.74 GiB** | **0.0735** |

**Listening tests.** 58 varied lines, one take each: long-form, numbers, technical terms, every emotion direction and tag, 7 voices. A take counts as a failure if it runs on, drops content, or comes out in the wrong voice (Whisper large-v3-turbo CER/WER and WavLM speaker similarity).

| Model | Failures | Speaker similarity |
|---|---|---|
| Drama 3, FP8 original (PyTorch) | 7 / 58 | 0.911 |
| drama3-small, no pause fix | 10 / 58 | 0.910 |
| **drama3-small + pause fix** | **0 / 58** | **0.947** |

Across 172 takes in five listening sets, the pause fix reduced failures from 30 to 1, and the remaining one is a mispronunciation. Runaways went from 28 to 0, and the longest in-sentence pause from 35 s to 3.5 s. Error rates on clean takes and average durations are unchanged. Most of the remaining failures without the fix are shared with the original model.

## Speed

Measured with `audiocpp_server` and the model already loaded:
- Pause fix on; temperature 0.7, top-p 0.7, top-k 30.
- Each request also encodes the 29 s reference clip.
- 4 lines (JA short, JA long, EN, JA with tags) × 2–3 seeds.

Real time = seconds of audio per second of wall time.

| GPU | Mode | Time to first audio | Overall | Long line (13–14 s of audio) | Steady generation |
|---|---|---|---|---|---|
| RTX 4090 (24 GB) | offline | n/a | 1.6× | 2.0× | about 57 frames/s (2.6×) |
| RTX 5090 (32 GB) | offline | n/a | 1.8× | 2.2× | about 69 frames/s (3.2×) |
| RTX 4090 (24 GB) | streaming | 1.9 s | 1.5× | 1.8× | |
| RTX 5090 (32 GB) | streaming | 1.8 s | 1.7× | 2.1× | |
| ZeroGPU (RTX PRO 6000) | offline, CLI per request | n/a | 9–14 s per request end to end; the 10.5 GB model loads on every request | | |

- Each request has a fixed cost of about 1.5–2 s: encoding the reference plus processing the prompt. That is why very short lines run at about 1× real time.
- Shorter references make that cost smaller.
- Speed on 12 GB cards (for example an RTX 4070) has not been measured yet; expect it to be lower.

## Usage

Build the patched audio.cpp:

```bash
git clone https://github.com/JarodMica/audio.cpp && cd audio.cpp
git checkout 9277495a
git apply /path/to/drama3-small-audiocpp.patch
scripts/build_linux.sh --cuda on --models fish_drama3
```

Clone a voice from the command line (`requests.json` holds `{"requests": [{"id", "text", "voice_ref", "options": {"reference_text": ...}, "seed", "temperature": 0.7, "top_k": 30, "top_p": 0.7, "max_tokens": 645}]}`):

```bash
AUDIOCPP_DRAMA3_MAX_PAUSE_FRAMES=10 AUDIOCPP_DRAMA3_SILENCE_CODES=silence_codes.json \
build/linux-cuda-release/bin/audiocpp_cli --task clon --family fish_drama3 --backend cuda --mode offline \
  --model drama3-small-IQ3_XXS.gguf --request-sequence requests.json --out-dir out \
  --session-option fish_drama3.cpu_expert_layers=0 --session-option fish_drama3.context_length=4096
```

Or run `audiocpp_server` with a model entry `{"id": "drama3-small", "family": "fish_drama3", "task": "clon", "path": "drama3-small-IQ3_XXS.gguf", "voice_presets": {...}}` and call `POST /v1/audio/speech` with `{"model": "drama3-small", "input": "...", "voice": "<preset>", "options": {"max_pause_frames": "10", "silence_codes": "silence_codes.json"}}`.

Recommended sampling: temperature 0.7, top-p 0.7, top-k 30.

### Pause fix (recommended)

Drama 3, and more often its compressed versions, sometimes goes silent at a tag or sentence boundary and never resumes or stops. The patch adds a sampler-side fix, controlled by request options or `AUDIOCPP_DRAMA3_*` environment variables:

- **`max_pause_frames`** (10 is 0.47 s; 21.5 frames is 1 s): after this many consecutive silent frames, the silence codes in **`silence_codes`** (this repo's `silence_codes.json`, 143 codes) are masked out of the next draw. The model must resume speaking or end.
- **Length guard:** the expected length is estimated from the text. A pause after `pause_end_ratio` (2.0) times that length ends the take, and `pause_cap_ratio` (3.0) times stops it regardless. This prevents the model from babbling when it is forced to continue past the end.

## Limitations

- **Requires the patched audio.cpp:** IQ quant types, per-layer expert counts, the speech-only head and the pause fix are not in upstream audio.cpp or llama.cpp.
- **12 GB is an estimate from measurements on 24–32 GB cards, not a test on a 12 GB card.** Offline-mode VRAM also grows with output length: 10.65 GiB for a short line, 13–15 GiB for 30–40 s outputs. On 12 GB cards, use streaming mode, or keep `max_tokens` around 645 (30 s).
- **Weaknesses shared with the original model:**
  - `[gasps]` at the start of a line
  - `<slow>…</slow>` spans
  - phone numbers, e-mail addresses and codes like "UA 837"; write these out as words
  - some English technical terms read in Japanese (for example "Kubernetes")
- **When the model loses its place mid-line,** the pause fix ends the take cleanly, but the rest of that line is skipped.

## License and acceptable use

Licensed under the **Fish Audio Community License v1.0** (see `LICENSE` and `NOTICE`):
- Free for research and non-commercial use. Limited commercial use is allowed below USD 500k annual revenue.
- Offering it as a hosted TTS or voice-cloning service needs a separate license from Fish Audio. Free, non-monetized research demos are allowed.

Do not use this model or its output to:
- imitate the voice of an identifiable person without their consent
- impersonate anyone to deceive, defraud or harass
- produce sexual content involving minors or non-consenting real people
- remove watermarks or provenance signals

If you offer voice cloning built on this model to others, you must bind them to restrictions at least as protective as these.

## Acknowledgements

- [Fish Audio Drama 3](https://huggingface.co/fishaudio/drama-3) and its codec.
- [audio.cpp](https://github.com/JarodMica/audio.cpp) for the runtime.