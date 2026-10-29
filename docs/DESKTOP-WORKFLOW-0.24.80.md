# Desktop workflow 0.24.80 / build 233

## Four changes

1. **Target-language fallback is reachable in normal mode.** The default retain-first policy previously bypassed the generic-reference stage. Healthy fitting first takes remain unchanged. After actor-voice repairs and bounded shortening/tempo fitting are exhausted, `failedVoicePolicy=generic` permits one same-engine attempt using an available bundled target-language reference. Only these candidates receive independent listening; the whole film is not repeatedly audited. Fitting candidates with uncertain checks remain marked for review. Original-source fallback is last, with its actual timing/generation reason retained.
2. **Suspicious source fragments receive bounded contextual re-listening.** Short Latin garbage in Japanese, very small intervals, low-confidence short turns and repeated vowels are hypotheses to check, not text to translate blindly. Up to 64 local windows use an already installed independent ASR for text support and the primary source recognizer for actual word clocks. Each primary window has at most two reserved attempts; the second is a smaller context only when necessary. A stretched word cannot create an early speech start. Healthy adjacent turns and unresolved residual audio remain. Missing ASR deployment produces a saved diagnostic, never an automatic download or a fabricated transcript.
3. **Normal-mode starts are source-locked.** Natural delivery may use a safe following gap; it no longer shifts a line backward or forward by up to half a second. Overlong speech still receives bounded local shortening and gentle tempo fitting. Source speech, preserved performance and scene boundaries constrain the deadline. Existing explicit micro-shift calculations remain available for compatibility outside the normal-mode configuration.
4. **OCR is scene evidence, not the speech clock.** Translation requests contain at most eight requested turns, read-only neighbours, stable caption IDs and nearby caption candidates. Input evidence is partitioned by complete rows instead of truncating JSON. Glossary batches and incomplete results persist. Reports expose suspicious source fragments and captions that span multiple speech turns. Matching IDs and valid JSON are not a semantic-quality pass.

## Saved work and use

- Paused frozen requests retain their existing policy identity and source checkpoint. The new delivery start policy is independent of source-work identity.
- Existing movies, source transcripts, recordings and model weights are not rewritten by installing this update.
- Use **Restart → Reanalyse source** to apply new recognition/segmentation to an old film. **Regenerate voices only** retains that project's source segmentation and translations.
- Caption timing is never supplied by an LLM. OCR and adjacent turns cannot fill a suspicious interval with another person's sentence.
- Bundled generic references currently cover Cantonese and English. An unavailable target-language bank is reported explicitly; there is no invented Mandarin reference or implicit extra model download.
- Mac and Windows share these Python policies. Hardware backends and recognition outputs can differ; physical Windows/GPU inference still requires on-device acceptance.

## Verification and limits

- Isolated real Japanese audio tests recovered two greeting turns and two turns around a corrupted short phrase, with independent text support and original-audio word times. Unconfirmed residuals remained available. No user job was edited.
- Five small-scene translations retained the requested IDs and source clocks; four real Drama 3 takes were audible finite 44.1 kHz WAVs and fit their test slots. Short-clip recognition remains fallible and does not certify accent, every word or performance.
- Regression checks cover fallback reachability and budgets, saved results, good-turn protection, stretched clocks, source-locked starts, row coverage, OCR evidence separation and frozen-request resume.
- This is not a whole-film correctness certificate. Whole-episode 24k-token alignment was not adopted: earlier real experiments exhausted output limits and confused adjacent meanings. Small-scene translation is bounded and still needs listening for names, dishes, songs and ambiguous speech.
