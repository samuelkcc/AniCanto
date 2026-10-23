# Independent listening and retained recordings · 0.24.64

Normal desktop production now defaults to `normalRepairPolicy=missing-only`. Audible first takes are retained. Only missing or damaged WAV recordings receive up to two additional same-engine attempts, persisted across resume. Human-selected recordings and source speech remain protected. Language labels, accent and suspected omissions do not trigger automatic rewrites or retakes. Measured overlong lines still receive up to two local meaning-preserving rewrite/generation passes after safe gaps and silent edges are considered. The candidate must be healthy and fit its available slot before adoption; otherwise the original remains selected and the timing conflict is reported. This exception does not restart language inspection, the recovery director or engine/voice fallback. Full recordings remain available; timing conflicts are flagged, and retained speech may overlap. No unchecked recording is certified as correct.

Detailed automatic checking and repair is an explicit Preferences choice (`verified`). It retains the earlier bounded mechanisms. This mode can take substantially longer and ASR can misclassify audible Cantonese. Fast mode remains separate and skips quality-driven review/retakes.

## Independent checker

Preferences on Apple Silicon offers Auto / Apple MLX / CPU. The optional Apple model is `mlx-community/whisper-large-v3-asr-fp16` at `f4b9d561e7f1a5c0587726ff7ff03da2cc80fcf9`, about 3.1 GB, and uses the existing pinned MLX Audio runtime. Auto uses it only when all files are installed; no implicit model download. Explicit MLX reports an unavailable model rather than pretending CPU is acceleration. Model-card Apache-2.0 terms and original Whisper MIT attribution are retained in `licenses/model-evidence.json` and installed alongside the weights. Windows retains its existing CPU checker in this release.

Each successful recording is atomically checkpointed before emitting its completion event. Cache identity includes recording SHA256, model ID/revision, backend, automatic/explicit language mode and checker policy. It excludes expected dialogue: no script, vocabulary or reference text is supplied as an ASR prompt. Identical recordings share results across repair stages; changed audio or model evidence is checked afresh. Traditional Chinese conversion is a deterministic post-process, not an ASR prompt.

A single item has a 180-second default deadline and a batch a 1200-second deadline. A timed-out item remains unconfirmed; completed results survive. The owned child is terminated and later uncached items may continue with at most two continuation processes. Startup failure does not loop. A later invocation resumes uncached items. Heartbeats report activity separately from measurable completed counts. Recognition failure is never turned into evidence of missing speech.

Output controls are kept in Production & export. The top transport contains the red Pause & save action, which saves and pauses without exporting; there is no adjacent direct-export shortcut.

## Measured comparison

On the author's M2 Max, the same 102 unchanged recordings (331.2 seconds of audio) took 1096.26 seconds with the completed CPU faster-whisper run and 164.76 seconds with MLX, including the MLX model load. Both completed 102 items. Runtime precision and decoding differ; this is a checker-stage timing comparison, not a full-film speed guarantee. Automatic language labels agreed on 94/102 items. There is no human-labelled accuracy score, and the acceleration does not certify Cantonese accent or correctness.

Regression tests cover interrupted checkpoints, unchanged cross-stage reuse, changed-audio/model invalidation, per-item errors, owned-child timeout, token-scoped finish, silent-only repair and preserving audible original bytes. Native Mac and Windows packaging use the same desktop policy. Demo media and private project recordings are not included in source releases.
