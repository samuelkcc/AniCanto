# Welcome download management (0.22.12)

Welcome → Manage models & runtimes lists installed, missing and partial model
files, per-component repair / redownload / remove actions and the app storage
folder. Repair checks saved files and only downloads missing or invalid bytes.
An interrupted download resumes its saved prefix. A complete partial is verified
and published locally, without downloading it again. File verification has its
own progress and is not reported as network transfer or model loading.

Windows can return from Basic or Expert to Welcome while setup is running.
The same setup process continues. Video conversion still needs to be paused
before leaving its workspace. The download plan includes the AudioSet classifier:
it distinguishes music, speech and other sounds for OP/ED detection. Model-file
completion is separate from the subsequent real model-load / inference checks.

Two explicit cleanup actions are available:

- **Delete downloaded models:** app-local weights, model sources, interrupted
  model downloads, model cache and readiness receipts. Runtimes remain installed.
- **Delete all downloads & close:** also removes app-local Python runtimes,
  downloaded tools, extracted Windows packages and download caches.

The confirmation shows the scope and approximate file size. Both actions close
the app. The Mac stops its owned model services before removal. Windows writes
a one-shot request bound to the current portable launcher process; the launcher
executes it after the desktop has exited, so loaded runtime DLLs are no longer
in use. A second launcher cannot act on another desktop's cleanup request.
The portable EXE must be kept outside its downloaded data folder.

A shared Rust implementation restricts removal to named app download directories.
It does not traverse symlinks or Windows reparse points, and verifies the file
inventory has not changed since confirmation. Projects, jobs, recordings,
settings, original videos and exported movies / subtitles are preserved. User
media found inside removable folders is also retained. Shared caches outside the
app data root (including an existing global Ollama / Hugging Face installation)
are not removed. Thus these controls are download cleanup, not a full removal of
all personal app data. `last-download-cleanup.json` records the outcome and any
files that could not be removed. Logical sizes may include shared hardlinks.

The next launch checks actual files and reinstalls only required components.
No real user models are deleted as part of release QA; removal tests use temporary
fixtures. Windows native setup, CUDA inference and post-exit file locking still
need validation on the user's PC.

## Export progress and review

A published movie completes the export milestone at 100%, even if speech quality
has review warnings. The review status remains visible separately. Older 94%
records are corrected only in the display when a finished processing run,
measured export stage and existing output prove publication. Interrupted runs
are not relabelled complete; the historical files are not rewritten.

## GPU support boundary

The shipped Drama3-small adapter supports CPU and a verified NVIDIA CUDA path.
There is no implemented Vulkan / Intel GPU Drama backend in this release. Qwen,
ASR, separation and voice generation each select their own supported backend;
a detected GPU is not evidence that every engine can run on it. Vulkan and
DirectML are possible cross-vendor integration choices, requiring per-model
integration and actual hardware tests before they can be advertised as supported.
