**English** · [繁體中文](README.zh-HK.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

<p align="center"><img src="docs/images/anicanto-cantonese-cover.png" alt="AniCanto — original Cantonese studio assistants" width="1100"></p>

# AniCanto

**Your anime. A whole new voice.**

Turn Japanese anime dialogue into **Hong Kong Cantonese or English dubbing**. Recognition, translation, speech generation and export run locally after models and runtimes are installed.

## Why AniCanto exists

AniCanto began with a simple wish: **to let children enjoy animation in everyday Hong Kong Cantonese while following Chinese subtitles and becoming familiar with Chinese characters.** Familiar stories and characters can make a language feel closer, bringing its rhythm, expressions and humour into everyday life.

Created by SCKC as a personal learning project, AniCanto also welcomes anyone curious about Cantonese. Whether you are sharing the language with your children or comparing Cantonese, English and Japanese to discover new expressions, the hope is to make Hong Kong Cantonese culture a little more accessible through the stories you enjoy.

AniCanto 最初只係一個簡單嘅心願：**希望小朋友睇動畫時，可以聽到日常香港廣東話，同時跟住中文字幕認識漢字。** 熟悉嘅故事、角色同對白，可以令接觸語言變得親切一點，亦讓廣東話嘅節奏、語氣同幽默喺生活入面延續落去。

呢個由 SCKC 以個人興趣同學習心態建立嘅小作品，亦希望將呢份樂趣分享俾更多人。無論係陪小朋友接觸廣東話，定係自己想透過廣東話、英文同日文對照認識新詞句，都可以由熟悉嘅一幕開始，慢慢感受香港廣東話嘅表達同文化。

## With respect to professional voice performers

**AniCanto is for language learning and creative experimentation. It is not intended to replace professional voice actors.** Character interpretation, emotion, timing and dramatic intent are creative skills; AI-generated speech should not be equated with a professional performance. Please continue to appreciate and support the performers behind the voices you love.

AniCanto 以語言學習同創作實驗為本，並非用嚟取代專業配音員。角色演繹、情緒、節奏同戲劇張力都係配音員嘅專業；AI 生成聲音唔等同真人演出，希望大家繼續欣賞同支持背後嘅表演者。

## Download the Beta · 0.24.59

**[Download for Mac](https://github.com/samuelkcc/AniCanto/releases/download/v0.24.59-beta/AniCanto-macOS-0.24.59.zip)** · **[Download for Windows](https://github.com/samuelkcc/AniCanto/releases/download/v0.24.59-beta/AniCanto.exe)** · [Release notes & matching source](https://github.com/samuelkcc/AniCanto/releases/tag/v0.24.59-beta)

## Choose your computer setup

**Preferred voice model: full Drama 3.** Pair it with Qwen 3.5 for translation: 35B is recommended on a 64 GB Mac; 9B is a smaller option for Windows with 32 GB RAM. Drama 3 sounded closer to Hong Kong Cantonese in developer listening tests; results still depend on the source and scene.

| Platform | Recommended system and memory | How Drama 3 runs |
| --- | --- | --- |
| **Mac** | Apple Silicon, macOS 14+; **64 GB+ unified memory recommended** | Full 4-bit MLX on Apple Silicon GPU / unified memory; approximately 28 GB estimated |
| **Windows** | Windows 10 / 11 x64; **32 GB RAM minimum, 64 GB offers more headroom** | Full GGUF Q2 **on the CPU**; approximately 22 GB system RAM estimated |

**On Windows, Drama 3 currently has no NVIDIA, AMD or Intel GPU acceleration.** Even with a dedicated graphics card, Drama 3 uses the CPU and system RAM. Other supported models may use the GPU depending on the card and driver; dedicated VRAM does not replace the RAM Drama 3 needs. This exact Windows package still needs testing on a Windows PC.

A 32 GB Mac can attempt a smaller translation-model combination, but Drama 3 may cause swapping, severe slowdown or loading failure. Memory figures are planning estimates. Allow **100 GB+ free storage** for models, runtimes and working files; long videos need more.

## What the app does

| Feature | How you can use it |
| --- | --- |
| **Cantonese / English dubbing** | Choose either language or both, with separate audio and subtitle tracks in one movie, switchable in a compatible player. |
| **Chinese subtitles as context** | Use embedded text tracks, external subtitles or screen OCR to help check names and meaning. Japanese speech remains the primary source. |
| **Opening and ending preservation** | Automatically detect OP / ED regions and keep their original Japanese songs and audio by default. |
| **Basic and Expert modes** | Start with automatic processing, or use the timeline to edit scripts, adjust timing and work on individual lines. |
| **Audition, retake and review** | Compare original, separated and generated speech; retake a line or choose a saved recording, then export another version while retaining the previous movie. |
| **Local batch processing** | Queue videos, reorder waiting items, pause, save and resume. Processing can run offline after model setup. |

### Experimental: other source languages

Beyond Japanese animation, AniCanto can try converting other detected source languages into Cantonese when the selected engine supports them. **Success is not guaranteed. Only English-to-Cantonese has received limited testing and targeted optimisations so far.** This is an experimental option, not verified support for every language or video.

## Supported formats

| Type | Formats |
| --- | --- |
| **Video input** | MP4 · MKV · MOV · M4V · AVI · WebM · TS |
| **External subtitles** | SRT · ASS · SSA · VTT |
| **Finished output** | MP4 with the selected audio and subtitle tracks. |

An accepted extension still needs readable audio and video codecs. Burned-in captions can be read with OCR, but cannot always be cleanly removed from the picture.

## What’s new in this Beta

- Basic mode now fills the workspace, with a flexible preview above progress and line audition.
- Expert mode has a full-window timeline at the bottom; progress sits directly below the preview.
- Refreshed light-purple screenshots and four-language pages, with English as the default and a bilingual introduction.

## Start in three steps

1. Download and open the app, then prepare the models and runtimes. Initial setup needs internet access.
2. Add videos and choose Cantonese, English or both. For external subtitles, use **Subtitle source → Import subtitle file** above the preview (SRT / ASS / SSA / VTT).
3. Start processing and play the finished movie. Use the review report to compare original, separated and generated speech, retake a line or select an earlier recording, then export another version.

[Subtitle import guide](docs/en/GETTING-STARTED.md)

## Inside the current app

Editing screenshots show **video preview switched off, with the animated assistant visible**, in the light-purple theme. Project and model states are illustrative, not conversion benchmarks.

### Welcome and setup

![Welcome and setup](docs/images/welcome-en.png)

### Basic mode: progress and audition

![Basic mode: progress and audition](docs/images/basic-en.png?v=preview-off)

### Expert mode: timeline and line editing

![Expert mode: timeline and line editing](docs/images/timeline-en.png?v=preview-off)

### Review report: issues and recording comparison

![Review report: issues and recording comparison](docs/images/review-en.png)

[See every interface screenshot](docs/en/SCREENSHOTS.md)

## Before you start

AI can still produce accents, mistranslations, missing words and voice changes. Listen to important scenes. Subtitles help check meaning; Japanese speech remains the primary source. The app supports separate original, Cantonese and English tracks and OP / ED preservation; results vary by scene.

A hobby project by SCKC. Original code uses MIT; third-party components and models retain their own terms. Built with Fish Audio; Drama 3 uses the Fish Audio Community License 1.0. Use only video, subtitles and voices you have permission to process.

[Support the project](https://buymeacoffee.com/samuelchen) · [MIT](LICENSE) · [Licences](docs/LICENSING.md)
