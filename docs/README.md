# Documentation

The searchable bilingual **Help centre** inside AniCanto is the current user manual. Its source is [`studio/web/help.js`](../studio/web/help.js).

## Current implementation

- [Public distribution and licence review](PUBLIC-DISTRIBUTION-REVIEW.md)

- [Shared architecture](SHARED-ARCHITECTURE.md)
- [Shared desktop interface and packaging](SHARED-STUDIO.md)
- [Windows platform port and acceptance limits](WINDOWS-PORT-2026-10-17.md)
- [Windows interface alignment](WINDOWS-STUDIO-ALIGNMENT.md)
- [Lightweight Mac deployment](MAC-LIGHTWEIGHT-DEPLOYMENT.md)
- [Welcome download management](WELCOME-DOWNLOAD-MANAGEMENT.md)
- [Optional voice models: CosyVoice 3 and WenetSpeech-Yue](VOICE-MODELS.md)
- [Drama3-small and NVIDIA](DRAMA3-SMALL-NVIDIA.md)

## Investigations and historical context

Episode-specific QA reports in this folder record their dated findings. Earlier plans, continuation logs and the old README are kept in [archive/](archive/). They may describe superseded behaviour; current app help and source take precedence.

## Local generated files

`dist/` contains only the current app and EXE. `.build/` is disposable development output except for tools/caches needed for offline builds and explicitly retained test evidence. The cleanup receipt is `.build/maintenance/cleanup-build-report.json`; obsolete release stages and previews were removed, keeping the current stage and one rollback copy. User application data, installed models and completed movies outside the project are not part of project cleanup.
