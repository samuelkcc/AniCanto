# Desktop Beta 0.25.20

Task: Show Windows reset progress and keep native CUDA selection consistent.

## Changes

- Show a cleanup window after full reset closes the main studio. Report processed files and freed space. A second launcher waits while removal advances. Stalled progress is bounded. No running process or lock is forcibly removed.
- Correct a native CUDA selection mismatch. Planning used normalized hardware, but the native verification step used an earlier record. A verified PyTorch CUDA13preference could therefore plan13and then test12. Use the same normalized record and selected runtime throughout deployment.
- Add manual CUDA12and CUDA13choices for Drama3, alongside automatic selection and CPU. Refuse incompatible GPU generations. A pinned choice does not silently test the other CUDA major. Model loading and speech validation remain required.
- Retain the final audio validation, Python repair, repeated reset and retained FFmpeg download fixes from0.25.19.
- Remove version history from the five homepage files. Keep synchronized download links for English, Traditional Chinese, Simplified Chinese and Japanese. Changes remain in release notes.

## Evidence and limits

Focused cleanup, launcher, CUDA selection, audio validation and setup tests pass. Four-language UI fixtures retain automatic, CUDA12and CUDA13choices after plan refresh. All3041Windows embedded files verify against the packaged source. Actual Windows clean deployment and GPU speech inference remain user acceptance work. Do not equate a valid package, CUDA enumeration or a CPU fallback with successful GPU speech.

Windows is0.25.20/build273. The current Mac download remains0.25.17/build270. No private iPad or iPhone implementation is included. Existing media, models, recordings and frozen work are not modified by this publication.

## Homepage maintenance

Read docs/DESKTOP-DOWNLOADS.json before each public release. Update the released platform version there, then run scripts/update_desktop_downloads.py. Run it again with --check before publication. It updates all five homepage files from one record. Verify the actual published assets before reporting the download ready. Keep Mac and Windows versions separate when only one platform has a new package. Do not publish local-only builds as released downloads.
