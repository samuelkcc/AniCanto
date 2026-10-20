> Historical implementation notes. The current common Tauri interface and
> acceptance limits are documented in [SHARED-ARCHITECTURE.md](SHARED-ARCHITECTURE.md).

# Windows implementation update · Mac 0.22.10 baseline

Updated 17 October 2026. The single-file deliverable is `dist/AniCanto.exe`.
The desktop now launches `windows/desktop.py` and uses `native_worker.py` → the
shared production worker. It no longer launches the old independent jobs.py
conversion policy. Basic/Expert share settings, immutable submissions and queue
state; native projections also cover editor-draft settings before plan freezing.

Native setup and adapters now cover translation/vision, Japanese ASR,
separation, references, GPT V2 Pro+/V4, Cosy, Vox and CPU Wenet/Drama, with pinned
Windows wheel resolution, real startup/speech probes and explicit model formats.
Drama CUDA is not bundled. The authorised GPT fallback is visible. The baseline
uses Qwen 4B/9B rather than automatically downloading 35B.

The Qt desktop includes Welcome, Basic, Expert Edit/Roles/Review/Produce/Queue/
Terminal/Defaults/Models/Preferences/Projects, previews, script edits, retakes,
immutable failed-recording comparisons, accepted complete takes, versioned cuts
and exports, progress milestones and time records. Host Qt and regression tests
are recorded in `.build/windows/shared-workflow/` and `.build/windows/desktop-qa/`.

**Still pending:** actual Windows launch, dependency installation and model
inference on the user's RTX 4090 laptop with 32 GB RAM; automatic short-video
import-to-export, multi-language decode, full episode listening, batch restart,
GPU memory/speed and exhaustive Mac feature-equivalence acceptance. Cross-built
PEs and mocked/host fixtures do not satisfy those hardware acceptance items.

The original source audit below is retained as historical evidence; its
statements about missing integrations describe the earlier prototype, not the
current entry. See windows/README.md for current instructions.

---

# Windows release path after Mac 0.22.7

Source audit: 17 October 2026. This is an implementation and acceptance plan,
not a Windows release announcement. The installed Mac app is unchanged.

## What exists

- `windows/launcher/` can embed the desktop payload inside one Windows x64 EXE.
  It verifies and extracts application code to a cache, separately from models
  and projects. First-use runtime/model downloads still require network access.
- `core/` shares production settings, track selection, memory policy and package
  integrity. It does not run translation, TTS or automatic repair.
- `windows/jobs.py` still has a separate, older conversion implementation. It
  requires translated scripts and role references and stops export on failed
  lines. Invoking the shared settings planner does not make that pipeline equal
  to `Resources/worker.py` and `Resources/dubbing.py`.
- `windows/studio.py` is a previous Qt studio, not the current Mac Basic/Expert
  interface. Engine selections still use older Windows adapter identifiers.
- Current Windows adapters cover GPT V4 and CosyVoice. The older Qwen TTS path
  is retired for new production. Drama 3, GPT V2 Pro Plus, VoxCPM2 and
  WenetSpeech-Yue do not yet have integrated Windows adapters.
- `Resources/drama3.py` explicitly uses pinned MLX inference; a Windows adapter
  must use a compatible native implementation and model format. Merely copying
  the Mac model files or changing a device name is insufficient.
- The Rust first-run planner deliberately reports
  `automatic-platform-adapter-not-integrated` for Windows. That block must only
  be removed when the native runtime/model setup actually works.

## Implementation sequence

1. **One production workflow.** Make Windows submit the same frozen production
   settings and use the shared media worker, caption recovery, reference policy,
   timing, repair ledger and export logic. Preserve Mac behaviour with regression
   tests. Retire the duplicate Windows repair/export policy once its replacement
   is accepted; do not add another independent copy of those rules.
2. **Explicit native adapters.** Separate platform-specific child process launch,
   inference, model formats, paths and cancellation from that workflow. Integrate
   Windows Qwen translation, Japanese speech analysis, separation and TTS with
   pinned dependencies, actual startup probes and installed-model reuse. Qwen
   4B/9B remain the baseline choices; 35B is optional when measured memory fits.
   Prefer Drama 3 when an integrated native model fits and passes inference;
   otherwise use the user-authorized GPT fallback and display the reason.
   Never claim a GPU is supported merely from its name or an encoder probe.
3. **One Windows settings owner.** Implement Welcome and Basic/Expert views using
   the shared job state. Match Mac navigation, tutorials, English/Hong Kong
   Chinese copy, progress, duration records, preview availability and output
   discovery. English Welcome uses Cantonese + English dubbing/subtitles and
   original Japanese audio. Switching modes must not resubmit or change a job.
4. **Windows acceptance, then release.** First prove one short automatic
   import-to-export job on the target PC. Follow with the EP06/EP07 regression
   cases and a full episode, dual-language export, batch jobs, pause/resume,
   restart and model reuse. Only then qualify the portable EXE for that tested
   hardware/backend. Other backends remain explicitly unverified until tested.

The first useful test build must perform an automatic conversion. Another
repackaging of the architecture preview is not that milestone. Full Mac parity
additionally includes all active engines and the full expert editing workflow.

## Release acceptance evidence

- On a clean target Windows PC, launch one EXE without a separate ZIP, installer
  or system Python. Show exactly what will download and reuse compatible verified
  local models. Recover interrupted downloads without deleting user projects.
- Capture Windows version, RAM, GPU/VRAM, driver, runtime, model revisions and
  real inference probes. Test memory fallback using the effective model/backend.
- Use identical settings fixtures in Basic and Expert mode; compare frozen job
  identities, requested engines, emitted audio tracks and switchable subtitles.
- For every enabled dialogue cue, account for translated text, generated take,
  chosen repair/reference and final mixed audio. Verify playable output audio,
  not just the presence of timeline rectangles or recording files. Do not use
  Cantonese ASR disagreement alone to discard an otherwise usable performance.
- Check Japanese speech deadlines, finite/non-silent samples, speech level and
  no spill into the following line. Keep diagnosis and bounded recovery inside
  the shipped application. Do not describe unresolved failures as success.
- Decode the entire final MP4; check selected audio/subtitle tracks, preview,
  elapsed-time sidecars, output discovery, resume and a second queued video.
- Record real Windows execution and model inference separately from build,
  policy tests and synthetic media tests performed on macOS.

## Delivery shape

Public delivery target: `dist/AniCanto.exe`, alongside `dist/AniCanto.app`.
Only one Windows EXE is delivered there; build archives, receipts and intermediate
folders belong under `.build/`. Old Windows packages should be archived there
when the new Windows release replaces them.

"Single EXE" means one file to copy and launch, not one offline file containing
every model. The runtime, verified code cache, models and projects use a writable
Windows data directory. A fully self-contained USB/no-download mode is a separate
requirement and is not currently implemented.

The user's latest target is an RTX 4090 Laptop GPU with 32 GB system RAM; the
earlier desktop 64 GB profile is superseded. The user will execute the Windows
EXE and provide test results. GPU memory must be measured, not inferred from the
4090 name; the laptop commonly has a different memory budget from the desktop. No Windows execution environment is
connected to this Mac task; the exact Windows version remains to be collected.

The user requires the same interface **and** functionality as Mac, not the older
architecture preview. Short-clip and partial adapter builds are internal
milestones, not substitutes for that deliverable. The latest requested toolbar
change (one mode-switch button and one row of consistently styled global action
icons) must also be reflected in the Windows interface.

Drama 3 requires platform-specific investigation. The current
[official Fish Audio installation requirements](https://speech.fish.audio/install/)
list Linux/WSL and at least 48 GB GPU memory for its FP8 implementation. That is
not evidence of a working native Windows/RTX 4090 backend, nor the same model
format as the Mac MLX implementation. Until a compatible lower-memory adapter
is integrated and tested, apply the previously authorized GPT fallback with a
visible reason; do not download an incompatible model or promise Drama 3 inference
from system RAM alone. Full UI/workflow parity does not imply equal model fit
across different accelerators.

## Baseline verification in this audit

- 12 existing Windows policy/cache/retry tests passed on macOS.
- 29 shared production/deployment policy tests passed through the real Rust IPC.
- Six Rust package-integrity tests passed. The initial parallel run exposed a
  test-fixture directory collision caused by wall-clock naming; fixture creation
  now uses an atomic sequence and retries existing names.
- Logs: `.build/windows/port-baseline-tests.log` and
  `.build/windows/shared-core-baseline.log`; shared policy checks are recorded in
  `.build/windows/shared-policy-baseline.log`.
- No Windows model inference, Windows launch or new Windows release is claimed.


## Shared follow-up pending Mac 0.22.8

Keep the shared worker's `script_resume` recovery and persisted journey high-water
mark in the Windows integration. The EP07 audit found saved delivery text was
newer than the intermediate cue cache, causing redundant translation on resume.
The candidate Mac progress card is now compact, with status on the left and
percentage/timing on the right. The Windows UI must consume these same worker
milestones rather than implementing another independent percentage or timer.

Native Drama 3 research found the upstream audio.cpp v0.9.2 release does not
include the Drama implementation. The community `drama-3-native` branch at
`48e7e708259dce828b9ce4e669dbf5629d4fda73` provides a possible GGUF adapter, but
has no prebuilt release. Its Q2 expert/Q8 backbone model alone is about 15.88 GiB;
CPU offload support is not proof of a measured fit or reliable inference on this
laptop. It requires a real native build/probe, not a version relabel. Until that
works, retain the user's authorized GPT fallback and show the actual backend.
This research does not qualify the old Windows desktop as feature complete.


## Native subprocess migration component, 17 October

`windows/shared_backend.py` now provides the platform-specific child launch
boundary while leaving `dubbing.model_job` and its shared runtime recovery and
recording-history wrappers in place. `shared_inference.py` delegates GPT to the
existing shared generation loop instead of `windows/native_tts.synthesize`'s
older policy. It also dispatches shared separation, speaker analysis and
independent-reference work. Windows ready markers and a successful model-load
probe are required, GPT version mismatch is rejected, explicit CPU/GPU selection
is preserved, and a Mac MLX marker is insufficient.

Six new tests cover native runtime/model gating, CPU/GPU selection, dispatch to
the shared GPT loop, real subprocess event/error transport, immutable rejected
audio history and a stalled child. Hardware/model loading is substituted on the
Mac test host; none of these checks claims actual Windows CUDA or speech inference.
The replacement Windows desktop, setup integration, ASR/vision/helpers and full
workflow parity remain outstanding. The old desktop is deliberately not wired
to this partial matrix, and no complete release EXE is placed in `dist`.
Evidence: `.build/windows/shared-workflow/`.
