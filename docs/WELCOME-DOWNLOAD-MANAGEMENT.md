# Welcome download management (0.24.67)

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

Welcome now has one **Clean up downloads…** entry. Choose the scope inside its
slide-in panel:

- **Models only** (default): remove app-local weights, model sources, interrupted
  model downloads, model cache and readiness receipts. Keep execution environments.
- **Models and execution environments**: additionally remove app-local Python
  runtimes, downloaded tools, extracted Windows packages and download caches.
  The next setup prepares both models and environments again.

Opening the panel, changing the selection or cancelling does not remove anything.
**Review removal** scans the selected scope and shows the approximate size and
file inventory. Only **Confirm removal** starts deletion. Cleanup shows live
progress and refreshes setup readiness afterwards; preparing missing components
can then start without restarting the app. On Windows, when loaded files require
post-exit cleanup, the launcher uses a one-shot request bound to the current
portable process. Another launcher cannot execute that process's request. Keep
the portable EXE outside its downloaded data folder.

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
