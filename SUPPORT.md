# AniCanto desktop support

[English](SUPPORT.md) · [繁體中文](SUPPORT.zh-HK.md) · [简体中文](SUPPORT.zh-CN.md) · [日本語](SUPPORT.ja.md)

[Home and setup](README.md) · [Current workflow](docs/DESKTOP-WORKFLOW-0.25.0.md)

This repository provides the open-source **macOS and Windows desktop edition** by SCKC. Use its public [issue tracker](https://github.com/samuelkcc/AniCanto/issues) for desktop bugs, setup problems, and feedback.

## Report a desktop problem

[Open a report](https://github.com/samuelkcc/AniCanto/issues/new?title=%5BDesktop%5D%20). Include:

1. AniCanto version/build and operating-system version.
2. CPU, system RAM, graphics card and VRAM. State the selected CPU, Apple Metal/MLX, or NVIDIA CUDA path.
3. Selected translation, recognition, and voice models; source subtitle type; and enabled repair options.
4. Steps to reproduce, expected result, actual error, and the last stage or line count. State how long it remained there.
5. A sanitised diagnostic excerpt or screenshot, if useful.

Check existing issues first and keep replies in the same report. Support does not require a donation.

## Common checks

- **Setup:** Check free storage, memory estimates, runtime readiness, and the affected model download. Hardware detection does not certify every GPU or model.
- **Slow or paused conversion:** Check the latest stage and line count. Use Pause and save before closing; resume the saved job. An unchanged percentage alone does not prove a hang.
- **Subtitle or voice problem:** State whether the source uses embedded text, an external SRT/ASS/SSA/VTT, or burned-in OCR. Add a timestamp. Compare source, separated, and generated speech in the line editor.
- **New workflow test:** Frozen paused jobs keep their saved policy. Reset a test video or create a new conversion to test current defaults.
- **Saved output:** Verify the exported file in the chosen folder before deleting a project or recording.

## Public reports and content

Reports are public. Remove private paths, account details, videos, recordings, scripts, and personal information from diagnostics before posting. Do not upload full private media to report a bug.

Default conversion runs locally after the required models and runtimes are ready. Downloads and updates need internet access. Cloud-folder synchronisation follows the storage service you choose. GitHub hosts this support page and issue tracker under its [privacy statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement). Process only media, subtitles, and voice references you have permission to use.
