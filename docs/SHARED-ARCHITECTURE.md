# Shared architecture — 0.24.1 (build 145)

Status: release candidate, 18 October 2026. Windows GPU execution and a complete
Windows episode conversion have not been performed on the build Mac.

## Ownership

Both desktop packages now launch the same Tauri 2 interface in `studio/web`, with
the same layouts, bilingual copy, themes and interaction handlers. Its asset
manifest is embedded in both native hosts. Mac uses WebKit; Windows uses WebView2,
so native rendering is not a promise of identical pixels on different displays.
The previous Qt desktop is excluded from the portable launcher payload. The
Swift worker remains a headless Mac platform bridge, rather than a second UI.

`Resources/production-contract.json` owns engine ordering and migrations. Rust
`core/` owns deterministic settings projections and hardware/model planning.
`studio/backend.py` owns the common desktop state and actions. Python production
workers own transcription, translation, synthesis, timing and encoding. Native
inference adapters use platform-compatible weights and verified runtime receipts.

Basic and Expert operate on the same settings, project and recordings. Submitted
requests stay immutable: a new global default cannot rewrite a running or paused
conversion. Audition playback uses fitted recordings; playback events do not
perform backend RPC or repeatedly reload the project.

## Production choices

- **Normal** is the default. It follows each source voice, skips visual role
  analysis and the full review pipeline, grounds names in source evidence,
  preserves detected Japanese OP/ED, and performs bounded checks for missing or
  nearly silent recordings and clear Mandarin. Uncertain short or homophonic
  Cantonese is retained. Repairs use the same source reference and selected TTS.
- **High speed** retains the unchecked one-pass workflow. Its warning says that
  quality review and quality-driven retakes are skipped.
- **Full AI review**, audio role grouping and optional visual analysis are
  advanced choices in Expert. They can substantially increase processing time.

Normal checks are cached by recording identity. A targeted retake is journalled
before starting, so resuming cannot repeat an unlimited review/retake loop.
Original and rejected recordings are retained. Unresolved review notes do not
prevent normal/fast encoding. A saved output is not labelled fully certified.
The workflow cannot guarantee perfect dialect, names, emotion or source coverage;
these need listening acceptance with the next real episode.

## Setup and model switching

Welcome offers one primary setup action with visible download progress, bytes,
speed and current file. Extra inventories and deletion controls are disclosed on
demand. Basic uses one selected model per purpose, chosen for the actual memory
budget; 35B is not mandatory. Existing healthy compatible models can be reused.
Drama 3 is preferred, including Drama3-small with the verified Windows CUDA
adapter when the larger model does not fit. Unsupported choices fail planning
before large downloads.

Changing models uses a server-created plan and persistent transaction journal.
Download and verify the replacement first; only then commit model selections.
Basic defaults to retiring the replaced selections, with an opt-out checkbox.
Expert can retain and pin multiple models. Pending submitted jobs, shared weight
files and pinned models are protected. Interrupted or failed setup retains the
previous selections and ready receipt. New setup cannot run alongside the old
Mac application.

The portable Windows EXE contains the common host and application sources, but
not model weights or the complete inference runtime. Its verified application
payload is extracted into a cache; runtime and model packages are downloaded to
the app data folder. Mac likewise keeps downloaded inference packages outside
the app. Cleanup is scoped to app-owned paths and preserves source videos and
exports unless the user explicitly selects export deletion.

## Verification evidence

- Python regression suite, shared UI model checks and Rust policy tests.
- Both languages, ten workspace pages, welcome covers, mode/settings sync,
  compact progress, model-switch confirmation, Basic return navigation and
  playback callback checks: `.build/shared-studio-qa/`.
- EP08 fast-output audio audit: `.build/ep08-fast-audit/`.
- Four nearly silent EP08 takes regenerated using their own source reference:
  `.build/normal-audio-qa/`. All four produced audible audio with original files
  unchanged; dialect was not conclusively confirmed for all short utterances.
- Mac native host verification and ad-hoc signature verification.
- Windows x64 PE, embedded payload hashes, current worker sources and exact
  common frontend manifest: `tests/verify_windows_portable.py`.

Cross-compilation and package integrity do not establish Windows hardware
acceptance. The user's RTX 4090 Laptop / 32 GB RAM test must still verify setup,
preview, native synthesis and a complete export. Intel Mac inference support is
not established by having a universal Rust helper.
