# Desktop hardware acceleration · 0.24.71 / build 224

Scope: Samuel requests available Mac acceleration enabled, and Windows decisions based on actual supported NVIDIA/AMD/Intel runtime, VRAM and system RAM. Desktop only. No Git/GitHub publication. Preserve source media, recordings, saved conversion progress and installed model versions. Rollback retains dist 0.24.70.

## Delivered policy

- Source speech processing defaults to automatic; CPU compatibility remains available in Preferences → Checking and repair. Fully installed MLX large-v3 is shared by Apple Silicon source recognition, language sampling, reference transcription and optional independent listening. The pinned MLX model is an additional ~3.1 GB in Mac large-v3 one-click setup. Other explicitly chosen Whisper variants are preserved.
- Primary Whisper runs in an owned dedicated model process. Real word/segment clocks are validated; invalid/non-finite/out-of-range clocks cause one CPU fallback. No timing is invented. Pause propagates without a CPU retry. A parent-death watcher prevents an orphan model process; the owned model and input arrays are released. Old saved project clocks are retained; new conversions use the new backend.
- MLX decoding in this pinned implementation is greedy; it does not implement beam search. The former CPU path uses beam search. Model/backend/decoding identity is saved with analysis. This is a speed option, not an accuracy certificate. Captions and independent language evidence remain necessary.
- Windows source/independent Whisper attempts CUDA only for the configured supported NVIDIA runtime. Torch DLL directory and current VRAM are checked; CUDA load or inference failure switches to CPU once. Independent per-recording checkpoints, bounded batch/item timeouts, incomplete evidence semantics and no-expected-text prompting remain intact; actual backends are saved separately from requested backend.
- Existing Mac Drama 3 / Qwen text, vision and ASR MLX paths explicitly select available Metal and cap MLX allocator/cache below the reported recommended working set. Supported GPT and separator paths explicitly select MPS or a supported CUDA/ROCm runtime. Windows Qwen ASR and audio classification use supported Torch acceleration; classification has a bounded CPU fallback.
- System planning reserves max(8 GB, 15% RAM). Dedicated-GPU budget considers 80% of physical VRAM and reported current free VRAM minus display headroom; integrated shared memory is never counted twice. Stage-local Torch checks can select CPU when insufficient free memory. Existing tested native Drama expert-layer deployment profiles remain intact; this patch does not invent a new quantisation/offload profile or guarantee free RAM throughout a conversion.
- Preferences includes Hardware acceleration decisions: latest saved stage configuration, successful inference / CPU fallback and memory estimates. This is not a live utilisation meter. A configured provider does not establish whole-model GPU placement.

## Actual support and explicit CPU exceptions

| Module | Apple Silicon | Windows |
|---|---|---|
| Source/reference Whisper large-v3 | Installed MLX automatic; CPU compatibility | NVIDIA CT2 CUDA candidate, one CPU fallback; AMD/Intel CT2 CPU |
| Independent Whisper | Shared MLX if installed; explicit CPU possible | Supported NVIDIA CUDA candidate; checkpointed CPU fallback |
| Drama 3 | Existing MLX Metal | Existing tested NVIDIA native CUDA / CPU-expert split, or CPU; no AMD/Intel CUDA |
| Qwen translation / vision | Existing MLX Metal | Existing supported Ollama adapter; unsupported hardware uses CPU |
| Qwen ASR | Existing MLX Metal | Supported Torch CUDA/ROCm only; free-memory check / CPU |
| GPT | Supported MPS path; FP32 policy retained | Supported installed Torch CUDA/ROCm path; free-memory check |
| Background separation | MPS verified on real selected audio | Supported Torch GPU, otherwise CPU |
| Audio classification | Native Apple framework, placement system managed | Torch CUDA/ROCm when supported; CPU fallback |
| WeSpeaker embeddings | **CPU retained** for pinned model + ORT 1.30.0 | Available GPU ONNX EP only if installed and first result matches CPU; current CPU ORT runtime stays CPU |
| CosyVoice / WenetSpeech | Current official adapters remain CPU | Cosy supported installed NVIDIA runtime; WenetSpeech current CPU adapter |
| OCR / VAD | Apple Vision system managed / current VAD CPU | Current RapidOCR ONNX CPU / VAD CPU |
| Video encoding | Existing native encoder selection | Existing tested NVENC / AMF / QSV probes, CPU fallback |

There is no claim that all modules now run on GPU, nor that installing an AMD/iGPU alone enables every model. No unverified Cosy MPS, WenetSpeech accelerator, GPU ONNX package replacement or OCR CUDA dependency is shipped.

## Model installed for this Mac

Whisper `mlx-community/whisper-large-v3-asr-fp16`, pinned revision `f4b9d561e7f1a5c0587726ff7ff03da2cc80fcf9`: 13 verified files, 3,087,748,437 bytes, existing model catalog ownership/ready markers and notices. Installation completed in 59.93 seconds. Previous CPU model and all user projects remain intact. No model weights enter dist.

## Measurements and limits

Isolated One Piece 817 fixtures; selected Japanese stream. No live job edited or full film rerun.

- Same 90-second original-audio excerpt: MLX cold elapsed **6.582 s**, Faster-Whisper CPU int8 beam 5 **140.82 s**. Single-run stage ratio ~21.4; not a whole-film benchmark. Normalised transcript similarity 97.18%, with proper-name disagreements, so **not equal accuracy** or a claim of improved Cantonese pronunciation.
- Real 5-second separation + source analysis completed in 21.706 s: MPS separation, MLX source recognition, original source-offset mapping, finite real word clocks and 2 dialogue cues. Completed inference itself 2.212 s. Separation decision records MPS configuration; no GPU-counter occupancy claim.
- Real independent two-recording batch: 5.804 s; repeat from checkpoint 0.004 s. Both actual MLX transcripts saved; no expected words in model request.
- Real missing-source-word reference fallback after final fix: correct Japanese transcript from PCM, MLX inference 0.566 s, overall 2.301 s. This also catches the formerly dangling `WhisperModel` name on that backup path.
- WeSpeaker CoreML failed numerical validation: output vectors contained NaN with MLComputeUnits ALL and CPUAndGPU. A first-run ONNX profile showed CoreML node dispatch, which **did not prove valid embeddings**. Exact pinned SHA `7bb2f06e9df17cdf1ef14ee8a15ab08ed28e8d0ef5054ee135741560df2ec068` + ORT 1.30.0 is hard-gated to CPU before production inference. No further blind attempts. Alternative provider versions require fresh validation.
- 131 affected Python tests passed, including device policy, current free VRAM, fallback-on-lazy-CUDA-error, cancellation, original word clocks, reference PCM, timing, language workflow, native Windows deployment, checkpoints and MLX text mocks. Four browser languages passed auto/CPU selection, persistence and hardware drawer layout without JS errors. Native/package/signature/embedded-frontend checks have separate receipts.
- Broader discovery was also attempted: wrong system Python lacked runtime dependencies; correct base Python ran 1,409 tests but was **not all green** (8 failures/30 errors before final reference/test-fixture fix). Remaining cases include split-runtime-only dependencies (Torch/MLX/sklearn/ToJyutping), old model/memory expectations, old subtitle-path expectations, outdated performance taxonomy and unrelated cleanup/icon fixtures. Do not present this as a full green suite. Changed-path NameError was fixed and its real inference plus regression passed; MLX text mock tests now mock device setup explicitly. No unrelated production behavior was rewritten merely to silence historical tests.
- Windows is cross-built with cargo-xwin and package-verified on Mac; current Windows GPU inference needs Samuel's PC test. Existing user-validated native Drama CUDA implementation remains preserved.

## Files and evidence

Primary changes: Resources/whisper_accel.py, compute_policy.py, onnx_accel.py; dialogue.py, speakers.py, source_language.py, secondary_speech.py, dubbing_runner.py, voicecheck.py, asr_verify.py, drama3.py, mlx_text.py, visual_speakers.py, worker.py; Windows GPU/setup/memory/ASR/classification adapters; Sources/StudioCore.swift and ModelDeployment.swift; desktop RPC allowlist, backend/preferences/locales/help; tests/test_acceleration71.py and related reference/MLX mocks, tests/shared_acceleration71_ui.cjs. No mobile source changed.

Detailed private measurements and staging/install receipts: `.build/acceleration71/`. These contain private fixture paths and audio and must not be published. This document contains no source media, generated speech or model weights.

## Final installation

`dist/AniCanto.app` and `dist/AniCanto.exe` are now 0.24.71/build224. Mac signature and actual native startup verified after replacement; 163 shared Python files match Mac and Windows payloads. Native IPC includes compute-status. Actual installed setup reports ready and zero missing download bytes. Privacy scan: 5,992 files, zero private build/account identifiers. Previous .70 pair retained under the private rollback directory. No GitHub publication and no user conversion launched. Detailed final receipt: `.build/acceleration71/final-receipt.json`.
