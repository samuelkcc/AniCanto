# First-run guide

[← AniCanto](../README.md)

This guide describes the current development workflow. Public downloads are not available in this repository yet.

## Interface language

AniCanto is designed primarily in Hong Kong Traditional Chinese. An English interface is included to help English speakers interested in Cantonese use the app and compare languages. Choose either interface language on the Welcome screen or in Preferences; this is separate from the dubbing and subtitle languages.

## Video, dialogue and subtitle sources

Accepted video containers: **MP4, MKV, MOV, M4V, AVI, WebM and TS**. Codec compatibility and a readable, undamaged source file are still required.

The main workflow recognises **Japanese audio** and can use **embedded Chinese text subtitle tracks**, **Chinese captions burned into the picture through screen OCR**, or matching external **SRT / ASS / VTT** files as supporting evidence. Embedded text and screen OCR are different sources. Automatic selection checks matching external subtitles, then embedded text, then burned-in captions; Expert mode can explicitly use Japanese audio only or Japanese audio + screen OCR. Unreadable or absent OCR captions do not by themselves mean the spoken line should be ignored.

Choose **Cantonese**, **English**, or **both for bilingual dubbing**. Selecting both creates separate dubbed audio tracks in the same exported video, not simultaneous overlapping speech. Keep the original Japanese track for comparison if selected. You can also choose separate subtitles or a combined Cantonese-and-English learning subtitle track in a compatible media player.

## 1 · Prepare the recommended Mac

Use an Apple Silicon Mac with 64 GB or more unified memory and macOS 14 or later. Reserve around 100 GB or more free space before model setup, plus additional working space for your videos.

## 2 · Choose your models

For the closest Hong Kong Cantonese accent heard in current developer tests, choose **Drama 3 + Qwen 3.5 35B**. Qwen is the translator and repair planner; Drama 3 generates speech. GPT-SoVITS and CosyVoice may retain Japanese intonation when using Japanese voice references. CosyVoice 3 is not offered on Mac.

Read the model terms, then use **Download & prepare**. First setup needs the internet. The app keeps model downloads separate from projects and lets you inspect expected sources and SHA-256 checksums in About. These catalogue hashes are not a fresh verification of installed files; repair performs that separately.

![English model setup](images/models-setup-en.png)

## 3 · Try one short original clip

Choose Basic mode, add a Japanese-language animation clip you are permitted to use, select Cantonese, English or both, and check the output folder. A short test lets you hear the selected model before processing an episode.

Original videos remain in their existing location. Queue order controls determine the order of waiting videos; pause and save before changing a running production.

## 4 · Let Normal mode check and repair

The app recognises dialogue, references subtitles, separates audio, translates, generates voices and attempts targeted quality repairs. OP/ED songs retain Japanese audio by default. Repair can take longer than initial generation.

High-speed mode deliberately omits quality review and quality-driven retakes. Choose Normal mode when you want those automatic checks.

## 5 · Check the report and export

The review report distinguishes unfinished work from verified results. When available, compare the original mix, separated speech and generated take. Expert mode lets you edit the script, inspect the timeline, audition or retake a line, and export a new version while retaining earlier recordings and exports.

A labelled incomplete preview can contain original Japanese speech for unresolved lines. Do not mistake it for a fully verified Cantonese export. Hardware or model failures can still prevent an export.

## 6 · Learn by comparing

English speakers can keep the English interface and compare the original Japanese, Cantonese and English text/audio. Check unfamiliar names and expressions: the app can mistranslate, and generated speech is not an authoritative pronunciation model.

## Voice consistency

Normal mode uses a source-voice reference for each line. The result is an imitation of that clip, not a guaranteed persistent voice identity. Even with Drama 3, accent, timbre and expression can change between takes. Optional role analysis may split one character or merge similar voices, especially when the original performer uses a wide emotional range.

AniCanto is a hobby project for learning and creative exploration. It does not replace professional dubbing. Please respect and support professional voice performers and use only voices and media you are permitted to process.
