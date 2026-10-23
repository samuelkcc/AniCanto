# AniCanto Support

[繁體中文](SUPPORT.zh-HK.md) · [简体中文](SUPPORT.zh-CN.md) · [English](SUPPORT.md) · [日本語](SUPPORT.ja.md)

[AniCanto home](README.md) · [iPad privacy policy](docs/IPAD-PRIVACY-POLICY.md)

## English

AniCanto is an independent project by **SCKC**. This page covers help, bug reports and feedback for iPad, Mac and Windows. The iPad edition is currently in development; these instructions also apply to development testers. Availability and supported features follow the release announcements for your platform.

### Contact SCKC

- [Report an iPad issue](https://github.com/samuelkcc/AniCanto/issues/new?title=%5BiPad%5D%20).
- [Report a Mac or Windows issue](https://github.com/samuelkcc/AniCanto/issues/new?title=%5BDesktop%5D%20).
- [Read existing reports or send general feedback](https://github.com/samuelkcc/AniCanto/issues).

GitHub Issues is the current contact channel. Reading this page does not require an account; posting an issue requires a GitHub account. Reports are **public**. Do not post private videos, voice recordings, scripts, account details, purchase receipts or unedited diagnostic logs. For a general privacy question, describe the concern without including personal data.

Please include:

1. Platform, device model, operating-system version, and AniCanto version/build.
2. What you were trying to do and the steps that reproduce the problem.
3. What you expected and what actually happened, including the exact error text.
4. Selected translation/voice models and the stage where processing stopped, if relevant.
5. An optional screenshot or short diagnostic excerpt with personal information removed.

Support and bug reporting do not require a donation. Please keep replies about the same problem in the same issue.

### iPad help

| Question | What to check |
| --- | --- |
| Can my iPad enter the studio? | The current development edition requires an M1 or newer M-series iPad with at least 8 GB RAM and supported GPU capabilities. Check **About & Licenses → iPad compatibility** in the app. Meeting the requirements does not mean every model or workload has been tested on that device. |
| Why does initial setup need the internet? | AI models and Apple-managed speech resources may need downloading. Download size and storage needs depend on your selection; check the model manager before starting. Recognition, translation and dubbing run on the iPad after the required resources are ready. |
| A download or model check failed. | Check the connection and available storage, then retry or repair the affected model in model management. Report the model name and error if it keeps failing. Avoid deleting the app to troubleshoot: this can remove local projects and recordings. |
| Processing paused or is taking a long time. | Keep the app in the foreground. Use its pause/save and resume controls; backgrounding can interrupt or pause work. Processing time depends on the video, selected models, memory and temperature. Include the last visible stage in a report. |
| Recording is unavailable or silent. | Check AniCanto's microphone permission in iPad Settings and the connected microphone/audio accessory. Permission is needed for recording, not for typing text or importing an existing file. Report your device, audio route and error if the problem persists. |
| Where are my finished files? | Open the saved-output player and use **Save video to Files…**, **Save subtitles to Files…** or the audio export/share action. Verify the saved copy in Files or your chosen cloud provider before removing the app or deleting a project. |
| How do I restore Expert? | When App Store purchasing is available for your build, open the Expert introduction and choose **Restore purchases**, using the Apple Account that made the purchase. A development-test entitlement is separate from a real App Store purchase. Never post a receipt or account information in a public issue. |
| The translation or voice sounds wrong. | Listen to the output and check the text. AI can mistranslate, omit words or change pronunciation and voice character. Where available, use Expert review and retained takes to revise a line. Automated checks do not certify translation or performance quality. |

### Mac and Windows help

See the [desktop setup, model requirements and workflow](README.md). Desktop and iPad requirements are different; desktop installation instructions, downloadable runtimes and model recommendations do not apply automatically to iPad. For a desktop report, also include CPU, system RAM, graphics card/VRAM and whether you selected CPU, MLX or NVIDIA CUDA processing.

### Privacy and content

Read the [iPad privacy policy](docs/IPAD-PRIVACY-POLICY.md) for local processing, model connections, sharing, backups and deletion. That policy describes the iPad app. This support page and its public issue tracker are hosted by GitHub, whose [privacy statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement) applies when you visit or post there. Only use video, subtitles and voice references you have permission to process.

## 繁體中文

[繁體中文技術支援](SUPPORT.zh-HK.md)

### 聯絡 SCKC

[前往繁體中文聯絡及問題回報說明](SUPPORT.zh-HK.md#聯絡-sckc)。
