## 0.23.0 studio update

The desktop now follows the Mac studio arrangement: Basic three-column workspace, Expert full-width timeline, four inspector pages, embedded categorized settings, role album/assignment/portrait tools, shared drafts and versioned exports. Per-attempt receipts retain fatal events even when batch conversion exits zero, with full process logs and an actionable banner. Missing runtime/tool files enter bounded setup repair before production. See [layout and acceptance details](../docs/WINDOWS-STUDIO-ALIGNMENT.md).

# AniCanto Windows · 0.22.11 native test build

The deliverable is one `dist/AniCanto.exe` for Windows 11 x64. Copy that file to
your PC and open it. No companion ZIP or user-managed application subfolder is
required. The first launch downloads an isolated desktop runtime; Welcome then
shows a hardware-aware model plan and one-click deployment. Models, runtimes,
projects and logs live in `%LOCALAPPDATA%\CantoSync-Windows`, independently of
the EXE. `CANTOSYNC_WINDOWS_DATA` can override that data location.

The new entry is `desktop.py`, not the historical `app.py` / `studio.py` preview.
Conversions and versioned edits run through `native_worker.py` and the same
`shared/worker.py`, dubbing, repair budgets, immutable recording history and
export logic used by the Mac build. The old `jobs.py` path is not a production
entry. Basic and Expert share one settings owner and queue. Switching modes
cannot rewrite a submitted conversion or restart it.

## First test on the RTX 4090 laptop / 32 GB RAM

1. Open AniCanto.exe and choose English or Hong Kong Traditional Chinese.
2. Review the model plan. Qwen 4B / 9B are the normal baseline. Installed matching
   models are reused when they fit; 35B is not an automatic baseline download.
3. Deploy. Setup verifies real native model loading and a speech sample before
   marking the PC ready. CUDA is probed through an actual calculation.
4. Choose Basic, add a short video, select an engine and subtitles, and start.
   English Welcome defaults to Cantonese + English dubbing/subtitles and keeps
   the original Japanese audio track. Try a short clip before a whole episode.
5. Use Open output folder or Play exported video. Processing time and milestone
   records remain with the project and output. A zero exit without an output is
   never shown as a completed movie.
6. In Expert, inspect scripts/takes, regenerate a line and compare old rejected
   recordings. A short decoder fragment cannot replace a complete line. Export
   edits as a separate version. Original movies remain untouched.
7. Test pause/resume, restart, two-video batches and reuse of installed models.
   Terminal exposes the same local process logs if a stage fails.

## Native engine policy

The order is Drama 3, GPT V2 Pro+, GPT V4, CosyVoice 3, VoxCPM2 and WenetSpeech-Yue.
Drama3-small is the first fallback when the full Drama model is unsuitable.
For a supported NVIDIA GPU with sufficient memory, setup downloads the pinned
CUDA plug-in/runtime and checks the real CUDA device, then generates speech.
Only a successful speech test confirms GPU use. Failed CUDA verification records
its reason and can use the same model on CPU, labelled explicitly. An explicit
CPU selection does not download CUDA. When the model cannot fit system memory,
the GPT fallback remains available. The full native CPU model remains an Expert
option. GPT, Cosy and Vox have native Torch adapters; WenetSpeech-Yue uses CPU.
See [Drama3-small / CUDA details](../docs/WINDOWS-PORT-2026-10-17.md).

Welcome shows installed/reused components, download purposes and sizes, byte
progress, first-load progress and the actual verified voice backend. Expand
Manage models & runtimes to repair, download again or delete a selected package.
Deleting a model/runtime preserves source videos, projects and exports.

Drama3-small's author tuned Japanese/English. Hong Kong Cantonese is experimental;
a successful short inference does not certify pronunciation or a full episode.

## Verification and limits

The portable PE and its embedded manifest are cross-built on Apple Silicon.
The Qt desktop is exercised on the host, including Basic/Expert synchronisation,
Unicode streamed process events, immutable resume, recording history, editor
projection, project cleanup and responsive playback callbacks. These checks
are **not native Windows execution, CUDA inference, voice-quality acceptance or
proof of complete Mac feature parity**. No Windows test PC is connected. Those
acceptance checks remain pending on the user's laptop. Native AMD/Intel paths
are also not hardware-qualified by this build.

Runtime installation requires internet access. Large models are downloaded,
not embedded in the single EXE. SCKC's original code is MIT; dependencies and
weights keep their own notices. This is a local test build, not a public GitHub
binary release or a completed redistribution audit.

Build: `python scripts/build_portable_windows.py`. Internal package archives and
receipts stay under `.build/windows/release/<version>/`; only AniCanto.exe is
placed alongside the Mac app in dist.
