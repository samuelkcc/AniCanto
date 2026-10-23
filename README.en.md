[繁體中文](README.md) · **English** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

<p align="center"><img src="docs/images/anicanto-cantonese-cover.png" alt="AniCanto — original Cantonese studio assistants" width="1100"></p>

# AniCanto

**Your anime. A whole new voice.**

Turn Japanese anime dialogue into **Hong Kong Cantonese or English dubbing**. Recognition, translation, speech generation and export run locally after models and runtimes are installed.

## Download the Beta · 0.24.58

**[Download for Mac](https://github.com/samuelkcc/AniCanto/releases/download/v0.24.58-beta/AniCanto-macOS-0.24.58.zip)** · **[Download for Windows](https://github.com/samuelkcc/AniCanto/releases/download/v0.24.58-beta/AniCanto.exe)** · [Release notes & matching source](https://github.com/samuelkcc/AniCanto/releases/tag/v0.24.58-beta)

## Choose your computer setup

**Preferred voice model: full Drama 3.** Pair it with Qwen 3.5 for translation: 35B is recommended on a 64 GB Mac; 9B is a smaller option for Windows with 32 GB RAM. Drama 3 sounded closer to Hong Kong Cantonese in developer listening tests; results still depend on the source and scene.

| Platform | Recommended system and memory | How Drama 3 runs |
| --- | --- | --- |
| **Mac** | Apple Silicon, macOS 14+; **64 GB+ unified memory recommended** | Full 4-bit MLX on Apple Silicon GPU / unified memory; approximately 28 GB estimated |
| **Windows** | Windows 10 / 11 x64; **32 GB RAM minimum, 64 GB offers more headroom** | Full GGUF Q2 **on the CPU**; approximately 22 GB system RAM estimated |

**On Windows, Drama 3 currently has no NVIDIA, AMD or Intel GPU acceleration.** Even with a dedicated graphics card, Drama 3 uses the CPU and system RAM. Other supported models may use the GPU depending on the card and driver; dedicated VRAM does not replace the RAM Drama 3 needs. This exact Windows package still needs testing on a Windows PC.

A 32 GB Mac can attempt a smaller translation-model combination, but Drama 3 may cause swapping, severe slowdown or loading failure. Memory figures are planning estimates. Allow **100 GB+ free storage** for models, runtimes and working files; long videos need more.

## This Beta

- Videos continue in queue order; reorder videos that have not started.
- Import subtitles from one Subtitle source panel; mark review notes checked or deferred.
- A compact Basic preview brings progress and audition higher; Pause & save is red on Mac and Windows.

## Start in three steps

1. Download and open the app, then prepare the models and runtimes. Initial setup needs internet access.
2. Add videos and choose Cantonese, English or both. For external subtitles, use **Subtitle source → Import subtitle file** above the preview (SRT / ASS / SSA / VTT).
3. Start processing and play the finished movie. Use the review report to compare original, separated and generated speech, retake a line or select an earlier recording, then export another version.

[Subtitle import guide](docs/en/GETTING-STARTED.md)

## Inside the current app

Real 0.24.58 interface with original demonstration material and illustrative model / project states; these screenshots are not conversion benchmarks.

### Welcome and setup

![Welcome and setup](docs/images/welcome-en.png)

### Basic mode: progress and audition

![Basic mode: progress and audition](docs/images/basic-en.png)

### Expert mode: timeline and line editing

![Expert mode: timeline and line editing](docs/images/timeline-en.png)

### Review report: issues and recording comparison

![Review report: issues and recording comparison](docs/images/review-en.png)

[See every interface screenshot](docs/en/SCREENSHOTS.md)

## Before you start

AI can still produce accents, mistranslations, missing words and voice changes. Listen to important scenes. Subtitles help check meaning; Japanese speech remains the primary source. The app supports separate original, Cantonese and English tracks and OP / ED preservation; results vary by scene.

A hobby project by SCKC. Original code uses MIT; third-party components and models retain their own terms. Built with Fish Audio; Drama 3 uses the Fish Audio Community License 1.0. Use only video, subtitles and voices you have permission to process.

[Support the project](https://buymeacoffee.com/samuelchen) · [MIT](LICENSE) · [Licences](docs/LICENSING.md)
