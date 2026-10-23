# Desktop Mandarin and source timing — 0.24.65

Desktop output codes match iPad: `yue` (Hong Kong Cantonese), `zh` (Mainland Mandarin), `en` (English). Mandarin scripts are independent, use Mainland vocabulary and Simplified Chinese, and produce `zho` audio/subtitle metadata. HK / 普 / EN switches select the matching script and saved per-line recording. WenetSpeech-Yue remains Cantonese-only. Standalone Dubbing studio remains a Cantonese creation tool; this release adds Mandarin to the video workflow.

The red Pause & save control pauses and saves. The extra finish/export shortcut beside it has been removed. New output versions stay in Production/export.

## OCR and source speech

An ASR word could stretch across several separate spoken turns. Source timing now nominates only sparse, stretched-word segments corroborated by separate VAD turns for a local re-listen, using the same already loaded source model. Each window is persisted before inference. At most twelve windows are started, with a 90-second start budget; an individual in-process model call can exceed that budget. Unconfirmed windows retain source speech and review notes; a successful neighbour must never delete them. OCR never sets speech clocks.

The native OCR threshold retains low-confidence outlined captions as evidence. A geometric subtitle selection separates large centred captions from smaller page/scene text; confidence is preserved rather than certifying that OCR is correct. Japanese-only centred subtitles remain eligible. Audio-only translation strips this evidence.

Previously exported movies are unchanged. Incorrect source clocks require a new conversion, not voice-only regeneration. Original text subtitles retain their own timestamps. General mode retains the first audible recording; missing/damaged audio repair and objective overlong-line shortening remain bounded.

## Branding

The default desktop icon is Shion (紫音), derived from the existing original Studio icon. macOS ICNS, Windows ICO and the shared interface use the same source. The earlier orange icon is replaced. The mobile source assets are read-only for this desktop update.

## Start readiness correction — 0.24.66

0.24.65 shipped a stale compiled Swift catalog alongside the updated Rust/Python contract. The native model-plan request failed with a catalog mismatch, and an unhandled asynchronous planning error left Download & prepare visible. Existing models and runtimes were intact.

The Swift catalog is regenerated from the shared contract. Swift staging now rejects stale generated source; final packaging also exercises the compiled Swift-to-Rust boundary in an isolated data folder. Startup distinguishes checking, a failed check, genuinely missing components and ready. Finishing the asynchronous check refreshes the existing Start control without a page or mode switch. A failed check offers Retry setup check and its error details; it does not start a download.

Read-only verification on the affected Mac found all four selected model rows installed and all required runtimes ready. No weights or runtimes were downloaded, removed or reinstalled for this correction.
