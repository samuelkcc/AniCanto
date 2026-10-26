# Desktop subtitle import · 0.24.72 / build 225

The packaged 0.24.71 native host rejected `set-external-subtitle` before Python could inspect the file. Reproduced with the real old binary in isolated application data. The backend and UI already implemented import/removal, but the fixed native RPC allowlist omitted this operation. Python-only import tests did not traverse that boundary.

## Change

- Register `set-external-subtitle` in the shared Mac/Windows native allowlist. Retain active-processing guards and the existing backend lock for running/paused frozen conversions.
- Audit every literal frontend RPC call against the native allowlist. The same omission affected the existing manual `review-triage` action; register it with the same review mutation guard. Internal task-launch/endpoints remain inaccessible through this public RPC entry.
- No subtitle parser, source timing, speech/reference model, acceleration policy, saved recording or conversion job changed.
- Existing usage remains: select the matching video, open Subtitle source, import SRT/ASS/SSA/VTT. The choice belongs only to that video. New submissions copy the original bytes with SHA-256 evidence; removing/replacing the selection does not alter an earlier frozen request.

## Evidence

- Actual user-provided episode 030 SRT: UTF-8, 22,842 bytes, 343 valid nonempty timed cues, first start14.05s / last end1393.81s. Original SHA unchanged. The earlier episode031 file is not substituted for episode030.
- Real packaged native IPC: import actual SRT; reopen/persist; ensure another video's choice stays automatic; freeze worker request and verify exact bytes/SHA; protect paused job; import FFmpeg-converted ASS/SSA/VTT fixtures; reject invalid/empty files; remove to restore automatic detection; earlier frozen bytes remain intact. All passed on candidate and installed dist. No actual user queue edited or source movie converted.
- 39 shared desktop tests and 2 new frontend/native operation-contract tests passed. Updated the old subtitle test to assert frozen copy bytes/receipt rather than the superseded original-path behavior.
- Four browser interface languages clicked import and remove through the real packaged native operation; imported episode030 filename appeared and no JS errors occurred. Deployment/media in that browser harness remain explicit fixtures. Early harness selection/initialisation issues were corrected; not evidence of a movie conversion.
- General legacy native-operations script passed its earlier consent, unknown-operation rejection, queue and model-ownership checks but its final synthetic sine-wave source-language expectation failed. It is not counted as a wholly green test. No unrelated source-language policy was changed to satisfy that historical fixture.
- Mac signature, freshly compiled native worker, installed setup readiness, native startup, exact 163 shared Python files and embedded Mac/Windows interface/payload verified. Privacy scan5,992 files,0 private identifiers. Windows executable cross-built/package-verified only; no PC runtime claim.

Both `dist/AniCanto.app` and `dist/AniCanto.exe` now .72/225. App was closed and exclusive instance lock acquired for replacement; remains closed. Prior .71 pair retained in `.build/subtitle72/rollback`. Hardware acceleration from .71 remains. No GitHub update. Private file paths/audio/fixtures and receipts stay under `.build/subtitle72`; do not publish them.
