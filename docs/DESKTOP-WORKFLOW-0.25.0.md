# Desktop 0.25.0: first-audible workflow

Task: Preserve the first audible take and expose bounded optional repair controls.

## New conversion rules

- Basic and Expert share one fast baseline. Expert exposes additional controls.
- Selected readable authored subtitles supply meaning by default. Speech supplies the source clock. OCR never supplies the speech clock.
- The first translation includes soft length guidance for Cantonese, Mandarin, and English. Preserve complete meaning. Do not add a default editing pass.
- Rate estimates use the language, engine, and exact reference identity when usable samples exist. Otherwise, use a marked uncertain prior. A cue-clock fallback is also marked uncertain.
- Preserve the first audible recording. A transcript warning or duration difference alone cannot replace it.
- Missing, silent, or damaged required audio receives bounded fill. The saved total allows at most three calls per cue: initial clone, one missing retry, and one selected-engine generic fill. Reserve before inference. Resume does not refund attempts.
- Content checks default to zero. Inspection and content repair need separate permission. Existing inspection evidence is reused instead of charging it twice.
- Strict source-duration limiting remains an explicit control. Default output permits overlap and preserves complete recordings at source onsets. Extend the final video frame when a target tail requires it.
- An independent Expert control can repair more than two seconds of confirmed simultaneous target speech. It defaults off. Exclude silence, gaps, and uncertain intervals. Permit one faithful rewrite and same-reference retake. Keep the first take if the candidate fails or does not improve the result.
- Strict-duration repair and optional overlap repair cannot add two timing operations to the same line.
- Keep frozen old requests and spent counts. The new policy applies to newly submitted conversions, not automatically to old paused work.

## Interface and delivery

Production settings use a compact header. AI Repair has its own tab. Global settings apply to waiting global videos; individual snapshots remain independent. Line controls and the mixer use context drawers. The Welcome mark follows the selected theme. The original Shion application icon remains.

Mac and Windows use the same worker and interface sources. Windows uses cargo-xwin cross-compilation. Hardware detection and NVIDIA CUDA choices remain. This release does not change model weights or certify every graphics card.

## Validation and limits

- 206 focused execution-boundary and regression checks pass. Four interface locales pass at two widths. Actual controls save counts 0, 1, and 2 and independent overlap choices.
- Three translation entry paths carry first-request length guidance. Isolated replies replace model inference in these tests.
- Actual FFmpeg export retains both full test takes, overlap, subtitles, and original audio. A three-second source produces a four-second movie. Full decoding and export resume pass. Synthetic PCM replaces TTS and separation only.
- Actual local Silero speech detection has bounded sample evidence. Real optional rewrite plus TTS and whole-film listening remain open.
- The signed Mac candidate passes startup, resource identity, and privacy checks. Windows PE and embedded payload checks pass. This host cannot run the Windows application or certify NVIDIA inference.
- Full legacy discovery reports 49 failure findings across 1,799 tests. All 49 reproduce on installed build 252. Missing test dependencies, old fixture assumptions, and unresolved historical expectations remain. The complete old suite is not certified green.
- Installed Mac and Windows files are version 0.25.0, build 253. 165 user metadata files remain unchanged. Models, recordings, and user media remain.

Reset a test video or submit a new conversion to test the new policy. Compare built-in subtitles, external SRT, and burned-in OCR as separate cases. A valid container or audible signal is not proof of correct meaning, accent, or emotion.

The common authority is [the shared recovery workflow](DESKTOP-IPAD-RECOVERY-WORKFLOW.md). Four-language control help comes from `WORKFLOW-CONTROLS-GUIDE.json`, revision 9. The public source export excludes the private iPad and iPhone application.
