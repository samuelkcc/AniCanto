**English** · [繁體中文](README.zh-HK.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

<p align="center"><img src="docs/images/anicanto-cantonese-cover.png" alt="AniCanto — original Cantonese studio assistants" width="1100"></p>

# AniCanto

**macOS / Windows · Open-source desktop edition**

**Your anime. A whole new voice.**

Turn Japanese anime dialogue into **Hong Kong Cantonese, Mandarin or English dubbing**. Recognition, translation, speech generation and export run locally after models and runtimes are installed.

[Download](#download-the-beta--0259) · [Features](#what-the-app-does) · [Workflow](#from-video-to-a-new-voice) · [Screenshots](#inside-the-current-app) · [Technical support](SUPPORT.md) · [Support the project](#help-more-people-discover-cantonese) · [Demo](#try-the-original-demo-and-compare-the-voices)

## Why AniCanto exists

AniCanto began with a simple wish: **to let children enjoy animation in everyday Hong Kong Cantonese while following Chinese subtitles and becoming familiar with Chinese characters.** Familiar stories and characters can make a language feel closer, bringing its rhythm, expressions and humour into everyday life.

Created by SCKC as a personal learning project, AniCanto also welcomes anyone curious about Cantonese. Whether you are sharing the language with your children or comparing Cantonese, English and Japanese to discover new expressions, the hope is to make Hong Kong Cantonese culture a little more accessible through the stories you enjoy.

AniCanto 最初只係一個簡單嘅心願：**希望小朋友睇動畫時，可以聽到日常香港廣東話，同時跟住中文字幕認識漢字。** 熟悉嘅故事、角色同對白，可以令接觸語言變得親切一點，亦讓廣東話嘅節奏、語氣同幽默喺生活入面延續落去。

呢個由 SCKC 以個人興趣同學習心態建立嘅小作品，亦希望將呢份樂趣分享俾更多人。無論係陪小朋友接觸廣東話，定係自己想透過廣東話、英文同日文對照認識新詞句，都可以由熟悉嘅一幕開始，慢慢感受香港廣東話嘅表達同文化。

## With respect to professional voice performers

**AniCanto is for language learning and creative experimentation. It is not intended to replace professional voice actors.** Character interpretation, emotion, timing and dramatic intent are creative skills; AI-generated speech should not be equated with a professional performance. Please continue to appreciate and support the performers behind the voices you love.

AniCanto 以語言學習同創作實驗為本，並非用嚟取代專業配音員。角色演繹、情緒、節奏同戲劇張力都係配音員嘅專業；AI 生成聲音唔等同真人演出，希望大家繼續欣賞同支持背後嘅表演者。

## Download the Beta · 0.25.14

**[Download for Mac](https://github.com/samuelkcc/AniCanto/releases/download/v0.25.14-beta/AniCanto-macOS-0.25.14.zip)** · **[Download for Windows](https://github.com/samuelkcc/AniCanto/releases/download/v0.25.14-beta/AniCanto.exe)** · [Release notes & matching source](https://github.com/samuelkcc/AniCanto/releases/tag/v0.25.14-beta)

[Download matching source materials](https://github.com/samuelkcc/AniCanto/releases/download/v0.25.14-beta/available-source-materials.tar.gz) · [Source backup & rebuild guide](docs/BUILD-AND-RECOVERY.md)

## What’s new in this Beta

**0.25.14 patch:** Keep downloaded models on switches and separate requested NVIDIA from verified CPU/CUDA processing. Reset production parameters from the settings header. Fix a Mac optional-analysis stall by reusing validated local source audio instead of reading the cloud movie again.

- **Cloud video import:** wait for large Google Drive, OneDrive or iCloud files to become readable before media checks. Show preparation progress and allow cancellation.
- **Clearer errors and assistants:** bright red errors with white text in both appearances, plus gentle breathing and hair movement in the nine distinct resting scenes.
- **Subtitle and repair controls:** retain caption-only text when no dialogue is confirmed, keep covered subtitle continuations from being dubbed twice, and separate optional repair permissions.

**Known limitation:** bounded source-clock recovery is included, but uncertain OCR windows can still collect repeated or long subtitle text. A complete cloud download and Windows GPU conversion depend on the provider and target device.

[0.25.14 release details](docs/DESKTOP-RELEASE-0.25.14.md)

## Try the original demo and compare the voices

[![A frame from the downloadable output demo](docs/images/demo-output-sample.jpg?v=desktop-body4)](https://github.com/samuelkcc/AniCanto/releases/download/demo-v19/AniCanto-demo-output.mp4)

Click the image to open the output video, then choose an audio and subtitle track in your player.

One 3-minute 8-second Japanese input and one desktop reference output, shared across all interface languages.

- **[Japanese input · try converting](https://github.com/samuelkcc/AniCanto/releases/download/demo-v19/AniCanto-demo-input.mp4)**
- **[Desktop output · listen and compare](https://github.com/samuelkcc/AniCanto/releases/download/demo-v19/AniCanto-demo-output.mp4)**

The output contains **Cantonese, Mandarin, English and Japanese audio**. Both movies include **Traditional Chinese, Simplified Chinese, English and Japanese subtitles**; choose tracks in a compatible player.

The reference was authored with the desktop version using Fish Audio Drama3. Qwen3.6-35B-A3B 4-bit MLX reviewed the base script. It is an edited comparison demo, not an unedited one-click conversion. Built with Fish Audio.

[Demo details](docs/en/DEMO.md)

## Choose your computer setup

**Preferred voice model: full Drama 3.** Pair it with Qwen 3.5 for translation: 35B is recommended on a 64 GB Mac; 9B is a smaller option for Windows with 32 GB RAM. Drama 3 sounded closer to Hong Kong Cantonese in developer listening tests; results still depend on the source and scene.

| Platform | Recommended system and memory | How Drama 3 runs |
| --- | --- | --- |
| **Mac** | Apple Silicon, macOS 14+; **64 GB+ unified memory recommended** | Full 4-bit MLX on Apple Silicon GPU / unified memory; approximately 28 GB estimated |
| **Windows** | Windows 10 / 11 x64; **32 GB RAM minimum, 64 GB offers more headroom** | Full GGUF Q2: **NVIDIA CUDA when supported**, or CPU for AMD / Intel / integrated graphics. System RAM is still required. |

**Windows now offers NVIDIA CUDA acceleration for full Drama 3 Q2.** In model setup, choose **Drama 3 processing → Automatic** or **NVIDIA · CUDA**. Automatic uses CUDA when the device, memory and deployment checks support it; choose CPU for AMD, Intel or integrated graphics. The app shows system RAM and VRAM separately and downloads the matching acceleration program and libraries. It reuses the same Q2 weights instead of downloading a second model. A compatible NVIDIA driver is required.

The author’s preliminary Windows tests report substantially faster Drama 3 generation with CUDA. This is not a fixed speed multiplier or proof of compatibility with every card. **Recognition and checking use supported acceleration where available and fall back to CPU when required. CUDA does not accelerate every module.**

A 32 GB Mac can attempt a smaller translation-model combination, but Drama 3 may cause swapping, severe slowdown or loading failure. Memory figures are planning estimates. Allow **100 GB+ free storage** for models, runtimes and working files; long videos need more.

Other voice options include **GPT-SoVITS V2 Pro Plus, GPT-SoVITS V4 and CosyVoice 3**, subject to platform and runtime compatibility. They are alternatives to explore, not extra models you must download. Accents, expression and voice similarity can differ between engines.

### What the author hears in repeated tests

In the author’s repeated scene-by-scene listening tests, **full Drama 3 has given the most convincing Hong Kong Cantonese accent among the models tried in AniCanto**. Other TTS engines can preserve a Japanese character’s voice and expression, but sometimes carry Japanese-influenced pronunciation or intonation into Cantonese. This is a personal listening assessment, not an independent benchmark or a guarantee for every voice. Drama 3 can still mispronounce words, lose expression or need a retake.

### Tested computers and realistic expectations

The author’s test machines are a **MacBook Pro with M2 Max and 64 GB unified memory**, and a **Windows laptop with an NVIDIA graphics card with 16 GB VRAM and 32 GB system RAM**. The release-validation standard is to complete an end-to-end conversion on both machines. Check each release’s notes for outstanding platform checks; the latest Windows NVIDIA CUDA update has passed the author’s preliminary desktop test with a clear speed improvement; this remains limited to the tested configuration and workload. Testing these two configurations does not establish compatibility with every computer.

**Author-reported timing with full Drama 3 on the M2 Max: approximately 1:2 video-to-processing time** — a 30-minute video takes about 60 minutes to convert, including automatic AI repair for roughly 8–10% of dialogue lines in those tests. This is an example from the author’s workload, not a promised speed or a Windows estimate. Scene complexity, model settings, repairs, storage and memory pressure can change the total substantially.

The timing example above used an earlier repair policy. Version0.25.0 leaves optional checks off by default.

If your configuration behaves differently, please [report the problem](https://github.com/samuelkcc/AniCanto/issues) with the app version, operating system, CPU, RAM, graphics card/VRAM, selected models and the stage that stopped or slowed down. Include a sanitised diagnostic log where possible; private videos or recordings are not needed.

## What the app does

| Feature | How you can use it |
| --- | --- |
| **Cantonese / Mandarin / English dubbing** | Choose one language or a combination, with separate audio and subtitle tracks in one movie, switchable in a compatible player. |
| **Chinese subtitles as context** | Selected readable text subtitles provide meaning by default; source speech provides timing. Without text tracks, compare OCR and recognised speech. |
| **Opening and ending preservation** | Automatically detect OP / ED regions and keep their original Japanese songs and audio by default. |
| **Basic and Expert modes** | Start with automatic processing, or use the timeline to edit scripts, adjust timing and work on individual lines. |
| **Audition, retake and review** | Compare original, separated and generated speech; retake a line or choose a saved recording, then export another version while retaining the previous movie. |
| **Local batch processing** | Queue videos, reorder waiting items, pause, save and resume. Processing can run offline after model setup. |
| **Model & download management** | See installed models, missing downloads and estimated memory needs; check or repair files before switching. |
| **Saved projects & versions** | Keep scripts, recordings and review notes together. Make another export without overwriting the previous movie. |
| **Standalone Dubbing studio** | Turn typed text or a recording into editable Cantonese speech, then save versions, learn with both texts and export a WAV. |

### New: Mandarin video dubbing

In **Production settings → Dubbing languages**, choose **Mainland Mandarin** alone or combine it with Hong Kong Cantonese and English, including all three. Mandarin has its own script and recording, with Mainland wording and Simplified Chinese subtitles. Keep the original audio too if selected, then switch tracks in a compatible player.

Available in Basic and Expert video workflows. Changing the interface language does not add dubbing tracks. **Standalone Dubbing studio currently outputs Cantonese**, and the downloadable comparison demo remains Cantonese / Mandarin / English / Japanese.

### Dubbing studio: from text or your recording to a saved clip

Available in **Basic and Expert modes**, without importing a video. Type Japanese or English text, or record/import your speech. Recording detects the source language automatically, subject to the installed model’s coverage.

1. **Check & translate** — Correct the recognised source text, choose a local translation model and edit the Cantonese script.
2. **Generate & listen** — Choose an installed voice engine, a preset reference or your recorded voice where supported, and adjust speech speed and supported generation parameters. Voice imitation needs a clear, complete 3–10 second reference.
3. **Save & compare** — Keep immutable takes in the separate **Dubbing studio** player folder. Compare original and generated audio with both texts, change playback speed, loop a part, rename/export a WAV or delete one version. The category name follows the interface language.

Independent listening checks flag uncertain words and language problems. Optional repair makes at most two additional attempts per confirmed faulty part; uncertain spelling alone does not replace a take. Flagged recordings can be saved after explicit listening acceptance. Earlier versions remain available.

### AI automatic repair

The standard flow keeps the first audible take. Extra checks default to zero.

1. **Translate once** with soft source-time guidance in Cantonese, Mandarin or English. Preserve meaning.
2. **Fill missing audio** with a saved allowance of at most three calls per line in total, including the initial clone and one selected-engine generic fill. Audible takes do not use this retry allowance.
3. **Optional Expert controls** independently enable content checks, content repair, strict duration or repair of more than two seconds of confirmed audible overlap. Silence does not count as overlap. Failed optional retakes keep the first take.

Default output permits overlapping dialogue and retains complete takes at source onsets, extending the final frame if needed. Old paused jobs retain their saved policy.

Apple Silicon offers optional **MLX Whisper** checking (about 3.1 GB). Each completed check is saved and reused; timeouts retain completed work. On the same 102-recording test, CPU took 18m16s and MLX 2m45s. This measures only the checking stage; recognition results can differ.

[Checking and repair details](docs/INDEPENDENT-LISTENING.md)

### Experimental: other source languages

Beyond Japanese animation, AniCanto can try converting other detected source languages into Cantonese when the selected engine supports them. **Success is not guaranteed. Only English-to-Cantonese has received limited testing and targeted optimisations so far.** This is an experimental option, not verified support for every language or video.

## Your subtitles, your language tracks

By default, **selected readable embedded or external subtitles provide the meaning** and recognised speech supplies the start/end times. Chinese subtitles are adapted into spoken Cantonese, Mandarin or English. Without usable text subtitles, OCR and speech are compared under the selected policy. Expert mode can change source priority; OCR does not set the speech clock.

| Source or output | What happens |
| --- | --- |
| **External subtitle file** | Use **Subtitle source → Import subtitle file** to attach SRT, ASS, SSA or VTT to the selected video. |
| **Embedded text subtitles** | Read available text tracks inside containers such as MKV and MP4. |
| **Burned-in Chinese captions** | Try OCR when readable text tracks are unavailable. Picture quality and layout affect recognition. |
| **Original, Cantonese, Mandarin and English tracks** | Keep the original audio if selected, add your selected dubbing languages, and choose independent or bilingual learning subtitles. Switch tracks in a compatible player. |

Automatic subtitle selection checks a matching external file, then embedded text, then screen OCR. **Original subtitle timestamps are preserved separately from dubbing timing.** Changing the interface language does not change the languages of the finished movie.

## Supported formats

| Type | Formats |
| --- | --- |
| **Video input** | MP4 · MKV · MOV · M4V · AVI · WebM · TS |
| **External subtitles** | SRT · ASS · SSA · VTT |
| **Finished output** | MP4 with the selected audio and subtitle tracks. |
| **Dubbing studio audio** | WAV · MP3 · M4A · FLAC · WebM · OGG input; WAV export. |

An accepted extension still needs readable audio and video codecs. Burned-in captions can be read with OCR, but cannot always be cleanly removed from the picture.

## From video to a new voice

1. **Import & prepare** — Add videos, inspect audio/subtitles and download any missing models.
2. **Listen & translate** — Recognise the source dialogue, prepare separated speech references and write Cantonese, Mandarin and/or English scripts with available subtitle context.
3. **Generate & check** — Create speech, preserve detected OP/ED audio and try bounded local repairs where needed.
4. **Export & review** — Save a new MP4 with the chosen tracks. Use the review report to inspect remaining notes when you want to improve a line.

### Improve a scene without starting again

| What you want to change | Where to work |
| --- | --- |
| Hear the difference | Compare the original mix, separated dialogue and saved generated recordings in **Review report**. |
| Fix one line | Edit its script or settings in **Expert mode**, generate a new take and listen before exporting. |
| Use an earlier recording | Choose a retained take in **Review report**, then apply your choices to a new export. |
| Change production or language tracks | Use **Production defaults / Produce** for a new version; reuse saved project material where it remains valid. |
| Leave a note for later | Mark a review item checked or deferred. The report keeps the evidence available. |

Recordings and previous exports are retained. New languages, models or changed scripts may still need translation or speech generation; reusing a project does not make every change instant.

## Start in three steps

1. Download and open the app, then prepare the models and runtimes. Initial setup needs internet access.
2. Add videos and choose Cantonese, Mandarin, English or a combination. For external subtitles, use **Subtitle source → Import subtitle file** above the preview (SRT / ASS / SSA / VTT).
3. Start processing and play the finished movie. Use the review report to compare original, separated and generated speech, retake a line or select an earlier recording, then export another version.

[Subtitle import guide](docs/en/GETTING-STARTED.md)

## Inside the current app

Editing screenshots show **video preview switched off, with the animated assistant visible**, in the light-purple theme. Project and model states are illustrative, not conversion benchmarks.

### Welcome and setup

![Welcome and setup](docs/images/welcome-en.png?v=0.25.14)

Choose the interface language, prepare local models, and enter Basic or Expert mode.

### Basic mode: progress and audition

![Basic mode: progress and audition](docs/images/basic-en.png?v=0.25.14)

Add a queue, choose dubbing languages and an output folder, then follow processing and audition individual lines. Preview can stay off while the assistant keeps you company.

### Expert mode: timeline and line editing

![Expert mode: timeline and line editing](docs/images/timeline-en.png?v=0.25.14)

![AI Repair](docs/images/ai-repair-en.png?v=0.25.14)

Use the full-width timeline to compare source dialogue and dubbing scripts, adjust timing and generate another take for a selected line.

### Restart or add a voice track

Use the circular arrow on a video to restart conversion, regenerate only its voices, or add a language / engine track without re-importing the file.

![ Restart or add a voice track ](docs/images/restart-en.png?v=0.25.14)

### Review report: issues and recording comparison

![Review report: issues and recording comparison](docs/images/review-en.png?v=0.25.14)

See what was flagged and what was tried. Compare retained recordings, make a choice and export another version while keeping the previous movie.

### Dubbing studio and saved clips

![Dubbing studio](docs/images/speech-studio-en.png?v=0.25.14)

Create a Cantonese clip, check the text and keep independent takes. The saved player compares source speech, generated audio and both texts.

![Saved clips](docs/images/speech-player-en.png?v=0.25.14)

### Windows: NVIDIA CUDA setup

![NVIDIA CUDA setup](docs/images/nvidia-cuda-en.png?v=0.25.14)

Choose automatic detection, NVIDIA CUDA or CPU. Setup separates system RAM, VRAM and the extra CUDA download; the screenshot illustrates the setup controls, not a speed benchmark.

[See every interface screenshot](docs/en/SCREENSHOTS.md)

## A work in progress, shaped by listening

AniCanto has grown through listening to failed conversions, comparing individual recordings and improving how difficult scenes are handled. Animation is demanding: whispers, shouting, overlapping voices, music and dramatic changes in delivery all affect recognition and voice references. A fix for one scene still needs checking against others.

Normal mode uses source references per line; **it does not guarantee one identical voice for a character throughout an episode**. Full AI review offers character analysis and reference organisation, but speaker identity can still be misclassified. Automated checks can help find problems; they cannot judge a performance the way a listener can.

<details>
<summary><strong>Do review notes mean the finished movie is unusable?</strong></summary>

A saved movie can still be played while notes remain. The report tells you which lines may need attention and lets you compare them. A fallback may use another voice or original speech according to your settings; an exported file is not proof that every line has been dubbed correctly.

</details>

<details>
<summary><strong>Why can a conversion take a long time?</strong></summary>

Dialogue density, model loading, memory pressure, separation and repeated speech generation all affect the time. NVIDIA CUDA can speed up Drama 3 on supported Windows systems; the CPU option is slower, and some recognition/checking steps remain on the CPU. More unused RAM alone does not make inference faster. There is no fixed conversion-time promise.

</details>

<details>
<summary><strong>Does my video need to go to a cloud service?</strong></summary>

No cloud translation or dubbing service is required for this workflow. Once models and runtimes are installed, recognition, translation, speech generation and export run locally. Initial downloads, repairs and app updates need internet access.

</details>

## Before you start

AI can still produce accents, mistranslations, missing words and voice changes. Listen to important scenes. Selected readable authored subtitles are primary by default; source speech supplies timing. Without usable text subtitles, OCR and recognised speech supply evidence under the selected source policy. Separate original, Cantonese, Mandarin and English tracks and protected OP/ED are supported; results vary by scene.

A hobby project by SCKC. Original code uses MIT; third-party components and models retain their own terms. Built with Fish Audio; Drama 3 uses the Fish Audio Community License 1.0. Use only video, subtitles and voices you have permission to process.

## Help more people discover Cantonese

If AniCanto helps you share Cantonese with your children, learn a new expression or enjoy a familiar scene in another voice, you are welcome to support this independent project. A coffee is a voluntary way to encourage more testing and development. Thoughtful bug reports and feedback are just as welcome.

<a href="https://buymeacoffee.com/samuelchen"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy me a coffee — support AniCanto" width="217" height="60"></a>

Made by **SCKC** — for the joy of hearing a familiar story in Cantonese.

[MIT](LICENSE) · [Licences](docs/en/LICENSING.md)

