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
- [Desktop Mandarin output, OCR timing and startup readiness](DESKTOP-MANDARIN-OCR.md)
- [Optional voice models: CosyVoice 3 and WenetSpeech-Yue](VOICE-MODELS.md)
- [Drama3-small and NVIDIA](WINDOWS-PORT-2026-10-17.md)

## Investigations and historical context


## Local generated files

`dist/` contains only the current app and EXE. `.build/` is disposable development output except for tools/caches needed for offline builds and explicitly retained test evidence. The cleanup receipt is `.build/maintenance/cleanup-build-report.json`; obsolete release stages and previews were removed, keeping the current stage and one rollback copy. User application data, installed models and completed movies outside the project are not part of project cleanup.

## Shared recovery and source delivery

- [Desktop / iPad recovery workflow and acceptance checklist](DESKTOP-IPAD-RECOVERY-WORKFLOW.md)
- [Machine-readable recovery contract](RECOVERY-WORKFLOW-CONTRACT.json)
- [Desktop platform differences and evidence](DESKTOP-RECOVERY-PARITY.md)
- [Source backup and rebuilding](BUILD-AND-RECOVERY.md)

## Desktop 0.24.75 update

- [Startup appearance](DESKTOP-APPEARANCE-0.24.75.md)
- [Playback and translated subtitle synchronisation](DESKTOP-PLAYBACK-0.24.74.md)
- [Audio/subtitle playback choices](DESKTOP-PLAYER-0.24.73.md)
- [Native subtitle import fix](DESKTOP-SUBTITLE-IMPORT-0.24.72.md)
- [Hardware acceleration and CPU exceptions](DESKTOP-ACCELERATION-0.24.71.md)
- [General dialogue and source-vocal workflow](DESKTOP-WORKFLOW-0.24.70.md)
- [Drama 3 sampling controls](DESKTOP-PARAMETERS-0.24.69.md)

## Desktop 0.24.79 update

- [Per-video restart and voice updates](DESKTOP-RESTART-0.24.79.md)
- [OCR, timing and diagnostic reliability](DESKTOP-RELIABILITY-0.24.78.md)
- [Editing, queue tools and hardware setup](DESKTOP-IMPROVEMENTS-0.24.77.md)
- [Queue wake and continuation](DESKTOP-QUEUE-WAKE-0.24.76.md)
