# Desktop recovery parity — 0.24.68

Mac and Windows execute the same shared worker. Platform adapters load and run compatible models; they must not implement another recovery director.

| Stage | Shared behaviour | Remaining platform-dependent evidence |
| --- | --- | --- |
| Normal delivery | Retain the first audible take; language/accent doubts stay in the report. Repair missing/damaged audio only. | MLX and GGUF/PyTorch generators can return different recordings. |
| Overlong dialogue | Measure duration and safe gaps, preserve complete words, locally shorten only measured overlong lines within existing bounded budgets. | A different take/script can have a different measured duration. |
| Detailed listening | Same evidence interpretation, per-recording cache, timeout ownership and resume; no expected-text prompt. | Qwen ASR uses MLX on Mac and PyTorch on Windows. Optional Whisper checking can use installed Apple MLX on Mac or CPU; Windows uses CPU. |
| Background separation | Same pinned Mel-Band RoFormer checkpoint, segmentation and stereo level handling. | Device kernels and supported acceleration differ. |
| Nonverbal preservation | Normal and Fast both retain confident isolated performance; exclude original lexical speech, duck only overlapping new dialogue, never restore the whole vocal stem. | Mac uses Apple SoundAnalysis, Windows uses the pinned AudioSet AST. Equal probability thresholds do not certify equal accuracy. |
| Performance timing | Retain model-specific validated context: Mac 1 s / 0.5 s hop, Windows AST 5 s / 2.5 s hop. OP/ED remains separate. | The two classifiers remain different models; changing windows is not proof of acoustic improvement. |
| Checkpoint reuse | Versioned audio-hash/backend/window-keyed classification shared across language and engine tracks; old unkeyed five-second caches cannot be reused as new evidence. | Cache identity includes the classifier backend. |
| Final mix | Same gain/overlap/fade policy; performance restoration and preserved vocalizations retain engine delivery rates (Drama 3 44.1 kHz, GPT V4 48 kHz). | A sample rate is not an acoustic-quality certificate. |
| Failure handling | Completed takes/history remain; missing-only does not restart broad language retakes. | Native model load, device and process errors differ and stay visible. |

## What was corrected

Fast previously disabled the extra nonverbal-restoration pass. A direct Windows one-second trial was rejected: the public laughter sample's maximum laughter score fell from .4525 to .0707 and classification took about 3.37 s instead of 1.07 s. Windows retains five-second context; this platform difference is explicitly unresolved rather than relabelled parity. Windows taxonomy now includes Baby cry/infant cry, Chuckle/chortle and Pant/wheeze. Whole-original restoration still requires positive non-speech evidence and lexical exclusion. Classifier scores remain uncertain evidence, particularly for laughter mixed with spoken words.

Performance restoration and per-cue original vocalization extraction previously forced 24 kHz, although the shared dialogue renderer already honoured the engine's native delivery rate. Both now use `audio_format.delivery_rate`; preserved-clip cache identities include the rate so old lower-bandwidth clips are not silently reused.

## Scope and validation

The shared policy and mixing rules are aligned. MLX versus GGUF quantization, translation-model selection, Apple versus AST classification, OCR implementations, and hardware runtimes are not identical. This update does not replace these models or claim bit-identical speech. There is no new recognition-driven retry loop. A three-clip exploratory comparison is not an accuracy benchmark; unchanged evidence is reused across tracks.

Tests cover window clocks, adjacent-word exclusion, cache reuse/invalidation, common mode policy, and actual FFmpeg preservation of a 14 kHz signal at the Drama/GPT delivery rates. Synthetic signals and substituted classifier outputs do not establish real-world laughter recall. Actual Windows execution and matched human listening remain separate acceptance checks. No user project, model weight or existing output is modified during release QA.

## Exploratory classifier evidence

The exact pinned [AudioSet AST](https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593) weights were hash-verified, then run on Mac CPU through the Windows adapter for three public [ESC-50 labelled samples](https://github.com/karoldvl/ESC-50/blob/master/meta/esc50.csv). This is not physical Windows acceptance. Mac SoundAnalysis was also run on the same files. The one-second AST experiment is retained as a rejected candidate, not a release feature.

Raw scores, source URLs/checksums and elapsed times remain in the private `.build/recovery68/classifier-check/` evaluation folder. Samples and classifier weights are not bundled. A low `event_ranges` count alone is not proof that a sound disappeared: `original_sound_ranges` may separately retain the original mix in positively non-speech windows. The user's specific missing-laughter example has not been located, and these samples do not establish application recall or false-positive rates.
