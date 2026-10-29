# Documentation
> Language standard: English, ASD-STE100 style. See `docs/DOCUMENTATION-STANDARD.md`.

The searchable bilingual **Help centre** inside AniCanto is the current user manual. Its source is [`studio/web/help.js`](../studio/web/help.js).

## Current implementation

- [Codex co-development handover log (CC Switch routing)](CODEX-HANDOVER.md) — read before starting work; log every finished task there
- [Documentation language and style standard](DOCUMENTATION-STANDARD.md) — every record file in this project is written in English, in ASD-STE100 style
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

## Shared recovery spec

- [Desktop/iPad/iPhone common workflow authority](DESKTOP-IPAD-RECOVERY-WORKFLOW.md): mandatory change protocol, shared control rules, and cross-platform alignment register. All platform owners update this file for every workflow change. WF-16 defines three-language first-draft length; WF-17 defines optional audible-overlap repair. Requirements and installed evidence remain separate.
- [Machine-readable flow contract](RECOVERY-WORKFLOW-CONTRACT.json)
- [Shared four-language workflow-control guide copy](WORKFLOW-CONTROLS-GUIDE.json): both product guides reuse these stable titles and descriptions.
- [Mac/Windows repair parity and remaining platform differences](DESKTOP-RECOVERY-PARITY.md)

- [Source backup and rebuilding](BUILD-AND-RECOVERY.md)

- [Confirmed desktop recovery policy issues pending fixes](DESKTOP-RECOVERY-PENDING.md)

- [iPad handover follow-up register](IPAD-FOLLOWUP-REGISTER.md): current open engineering, real-device, consent, and store-listing items; kept separate from history.
- [iPad line handover, 2026-10-28](IPAD-HANDOVER-2026-10-28.md): resume point for the iPad line. Installed build 189 state, the performance-mode rule set, the evidence, the open items in order, and the device commands.

- [iPad VLC distribution and source check](IPAD-VLCKIT-RELEASE-REVIEW.md): the real registered modules, seven GPL questions, the clean source build, and functional acceptance.
