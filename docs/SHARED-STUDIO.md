# Shared desktop migration — 0.24.0 candidate

The shared desktop uses Tauri 2 with one HTML/CSS/JavaScript view bundle. macOS
and Windows compile the same files, including fonts, ten welcome illustrations,
assistant sprite sheets, icons, bilingual copy and theme palette. Platform
adapters handle the file picker, model runtime, hardware and process lifecycle.
Conversion policy remains in the existing Rust core and Python worker.

## Scope

The common view includes Welcome/setup, Basic and Expert, the video shelf,
video/caption preview, source and translated scripts, a selectable timeline,
individual auditions and retakes, role references, review/history, versioned
exports, queue, terminal, defaults, models, preferences, project removal, guide
and About. Mode selection is one button showing the current mode and the other
mode in its tooltip. All controls use the same stroke icon system.

Playback callbacks only read an in-memory cue/take projection. State and project
reads run outside the native UI thread, at most one snapshot request at a time.
Background events update the progress region without replacing the video node.
A new running job cannot show the preceding job's recordings as current work.
Elapsed times use `processing-time.json`; pauses are excluded by the worker's
existing accounting. An estimate is only shown after measured work advances.

## Workflow preservation

The new host owns `studio/desktop-state.json` inside the existing app library.
Existing reviews and in-flight requests are imported read-only. Draft edits use
`editor-draft-studio.json`; submitted conversions and each retake/render get
separate immutable snapshots. Previous outputs cannot count as a new attempt's
successful export. Stale drafts are archived once rather than on every poll.

New Basic jobs use audio reference grouping. Per-line source voice imitation is
available in Expert; Fast mode continues to use its existing per-line source
reference path and bypasses quality review. Visual role analysis is an explicit,
default-off Expert option. Resuming an old request preserves its submitted
analysis policy. Deployment repair does not erase an explicit visual opt-in.

The EP07 observation of female voices becoming male remains a listening issue
to investigate against the Fast-mode output. This migration does not certify a
gender/voice-identity fix, or promise literal 1:1 cross-language voice cloning.
The synthesis and rejection algorithms have not been loosened to hide failures.

## Native ownership and setup

On Mac, `AniCanto-worker` is the existing Swift engine with a headless entry.
It preserves managed process groups, model selection, runtime repair, Metal
deployment planning and Apple media helpers. A parent watchdog and termination
handlers shut down its owned model descendants. Its self-launch path uses the
actual helper executable, not the bundle's Tauri main executable.

On Windows, the portable launcher extracts and verifies its payload, then opens
`AniCanto-Studio.exe` before Python exists. First-run bootstrap installs private
Python without the former Qt interface dependency. The same Welcome remains
available throughout model setup. Native worker setup still requires real
device/model probes before GPU inference is marked available. A Windows Job
Object owns each task and its descendants; pause closes that job immediately.

Download cleanup uses the existing Rust ownership/token checks. Windows runtime
and payload removal is deferred to the portable launcher after the desktop
exits, so loaded EXE/DLL files are not deleted underneath it. Source videos,
projects, retained recordings and exports remain protected.

## Build and validation

1. `python3 scripts/prepare_shared_studio.py` creates the common assets and their
   SHA-256 manifest. Both native hosts compile that exact manifest.
2. Build the Swift adapter with `scripts/stage_release.py` for a fresh stage.
3. Build the host with `python3 scripts/build_shared_host.py` and the Windows host with `--target x86_64-pc-windows-msvc`. Release builds remap private compiler paths and exclude checkout-directory fallbacks. Windows
   uses `+crt-static`; Tauri's additional mixed-UCRT mode is disabled to avoid
   conflicting linker selections under cargo-xwin.
4. `scripts/package_shared_studio.py` stages a separate signed Mac candidate.
   The installed/running app is not replaced. `scripts/build_portable_windows.py`
   embeds the Windows Tauri host in the single distributable EXE.

The UI acceptance fixture exercises real state/draft RPC and a real six-second
video. It deliberately simulates deployment/progress: it is not an inference
test. Both languages cover all ten workspace pages, Basic return navigation,
mode/settings sync, guide, About and draft saving. Native package verification,
Mac launch checks and Windows hardware acceptance are separate evidence.

The Mac candidate is Apple Silicon, as is its current MLX adapter. Sharing the
view does not itself create a working Intel Mac inference adapter. Windows GPU
inference and end-to-end output still require testing on a Windows PC.
