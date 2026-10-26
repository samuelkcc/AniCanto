# Desktop reliability · 0.24.78 / build 231

Implementation and acceptance are tracked separately. This release keeps existing movies, submitted scripts, recordings and installed models. Remote access is cancelled. No iPad application code or GitHub publication is part of this change.

## OCR

Mac Apple Vision and Windows RapidOCR use bounded per-frame retries and retain frame-level errors instead of aborting all captions on one bad image. Mac persists successful results by image SHA; restarting retries failed frames. The OCR subprocess is stopped after 90 seconds without progress or 30 minutes total, retaining checkpoints. Scan status distinguishes running, failed, partial, empty and complete; partial output is never cached as a successful complete scan. Source speech remains the timing authority.

Resuming failed/partial OCR may refresh caption context at most twice per saved job without rerunning whole-film ASR, changing accepted text, source clocks, references or recordings. Changed/missing dialogue can use recovered context; existing adopted speech is not silently regenerated. Completed old outputs remain unchanged until a user requests a new export. Fresh analysis preserves zero-duration edge subwords and marks abnormally short ASR clocks for bounded local review/source retention.

## Timing and performance

Normal mode keeps its limited meaning-preserving shortening, measured silence trimming and small pitch-preserving tempo bounds. A retained take may not newly overlap a later dialogue. If it still cannot fit after these bounded mechanisms, keep the failed take for audition and use the existing original-source fallback with an explicit review item. Do not truncate words, invent a longer source clock or increase unlimited retry loops.

Untranslated repeated vowels and song-boundary candidates are classified against original and separated audio. Only corroborating acoustic evidence can authorise preserving a nonlexical performance or unrequested song. Meaningful caption evidence prevents treating lexical cries for help as empty vocalisation. Approved/manual dialogue is retained. Shared classification caches avoid rerunning the same original/stem analysis across language/voice tracks. This improves classification, not a claim that every laugh/cry or model pronunciation is perfect.

## Reports and debug download

Review exposes OCR workflow notices independently of line failures, original performance/song counts, uncertain short source clocks, and time-overrun/original-fallback issues. Processing completion is distinct from full dubbed coverage and pronunciation quality.

Debug v2 keeps JSON parseable, declares bounded complete-entry omissions, includes selected-project previous-attempt error context and OCR errors/progress, and includes Windows hardware/runtime receipts, driver/toolkit selection and actual voice CPU/GPU fallback. Overall CUDA status must not imply that every component uses the GPU. System-memory observations are timestamped; native-host-owned descendants include RSS and cumulative CPU time where available. Exporter-process memory is not worker memory, and CPU time is not instantaneous utilisation. Windows optionally includes a bounded NVIDIA whole-GPU memory/utilisation snapshot, explicitly not attributed to a particular model; unavailable readings remain unknown. Deployment records persist analysis acceleration fallback reasons separately from Drama voice fallback. Known secret fields are redacted, but local paths and dialogue remain; no media/model weights are attached. Physical Windows acceptance and whole-film background/sleep field behaviour remain distinct from fixture tests.

## Validation

See private .build/product78 receipts for exact test, packaging and installed-version results. Full-film audio listening and physical Windows GPU tests must not be inferred from unit tests or cross-compilation.
