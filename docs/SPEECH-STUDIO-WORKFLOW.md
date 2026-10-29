# Dubbing studio — shared iPad / macOS / Windows workflow

User-approved feature scope, 2026-10-23. Desktop work is in progress; this is a shared UX/data contract, not a claim of completed device validation.

## User refinement — 2026-10-23 (latest instruction)

**Basic and Expert may both use the Dubbing studio.** The user briefly reverted to Expert-only, then explicitly chose both again. Do not reintroduce an Expert paywall. On iPad, place the standalone entry in the video-list shelf immediately above the player / projects-and-outputs entry; remove it from the Expert function bar. Follow the desktop's independent route, independent of a selected video.

The central activity is **typed text + a separately recorded voice reference → editable Cantonese → generated clip**. Recording a voice reference must not erase typed text or the translated draft. Keep dictation as an optional input mode, separate from the short voice reference.

Offer four distinct voice choices: random synthetic reference, a named synthetic template, imitate the user's voice reference, or use a template voice with a reference-driven intonation effect. Do not call the last mode exact voice conversion or guaranteed anonymity. iPad currently analyses a normalized, smoothed relative F0 contour and applies bounded pitch modulation to template-generated audio; it never supplies that personal audio/embedding to the TTS conditioner in this mode. It does not copy timing, phrasing or lexical tone exactly. Label it experimental until listening validation. Exact isolation of identity and prosody is not established.

Expose actual working controls: speech speed, bounded pitch shift, supported CosyVoice style instruction (natural/happy/gentle/serious), intonation-effect strength, and regenerate with a fresh seed. No decorative temperature/identity-similarity sliders where the engine does not expose them. Every take freezes chosen template, reference hash/transcript, style, speed, pitch, contour amount, engine and seeds. Voice imitation is reference-conditioned synthesis; never promise an exact match.

Voice references use complete 3–10 second recordings. Allow import, recording, preview, automatic recognition and transcript editing. Keep original typed text and reference transcript separate. Save clips in the stable speech-studio player category with their required own audio; deleting a video import must not remove them. Audio preview must explicitly activate a playback audio session after microphone use.

Desktop handover: apply this UX/data contract using actual desktop engine capabilities; keep its existing workflow and adapters, do not copy iPad MLX implementation or claim untested prosody parity. Do not advertise the now-free Dubbing studio as an Expert purchase benefit. See latest CODEX-HANDOVER entry for concrete implementation / validation state.

## Entry and language

Add a left-menu entry independent of video conversion. Labels: English **Dubbing studio**, Hong Kong Traditional Chinese **配音器**, Simplified Chinese **配音器**, Japanese **吹き替えスタジオ**. Basic and Expert users can reach it without importing a video.

## Same four steps on every platform

1. **Input** — Text (Japanese, English, or automatic source language) or a recording. Recording uses automatic language detection, without a Japanese/English source-language whitelist; actual recognition depends on the installed ASR model. Ask OS microphone permission when the user starts recording; also allow importing audio.
2. **Translate** — The selected local text model produces an editable spoken Hong Kong Cantonese script. Show the recognised source alongside it. Do not silently substitute a demonstration transcript or fake successful translation.
3. **Generate and listen** — Choose an available local TTS engine, its supported parameters and a bounded speech-speed setting. Offer a preset reference voice or the user's recorded voice where the engine supports it. Keep source audio and transcript together; voice imitation needs a clear complete reference, not an arbitrary mid-word cut. Permit listening before publishing.
4. **Save to player** — Save immutable generated clips, with title, source/target text, engine/settings and creation time. Keep earlier takes. A failed, silent or partial attempt must not appear as a successfully saved recording.

## Separate player folder

Use a stable category identifier **speech-studio**. The player displays its name using the current interface language (the four labels above); changing language immediately changes the displayed folder name while retaining recordings and links. This is a dedicated category, never an extra video-conversion queue item. Stable storage IDs avoid destructive filesystem renames and duplicate folders across language changes.

## Presentation

- Text / Recording tabs; source and editable Cantonese script side by side.
- Voice controls grouped together, with less common sampling settings in an expandable section.
- Visible task status, generation stop control and inline audio preview.
- Saved clips in the named player category; no A/B popup or transient-only audio.
- Persist text drafts and recorded input. Do not change the user's video-production settings to test a clip.
- A video conversion and speech generation must not launch overlapping model jobs.

## Platform responsibility and validation

Desktop uses the common web UI and Python/native adapters; iPad uses its native models and recorder. Match behaviour and saved metadata rather than claiming identical engines or quality. Check microphone permission denial, empty/unsupported recording, automatic source-language detection, translation failure, TTS failure, saved clips surviving restart, localized folder switching, and independence from existing video projects.

## Desktop 0.24.63 acceptance boundary (2026-10-23)

The current desktop update adds two-phase editable recording recognition, per-document installed text-model selection, immutable version snapshots, saved-version selection/edit/rename/delete/export, source and target playback, dual-text learning, generated-part seeking, playback memory, and independent review with a persistent two-additional-attempt cap per confirmed failure. Saved files are checked against their recorded SHA before prior review or export can be used. Flagged usable recordings require explicit acceptance to save; acceptance is never quality certification.

Recording dictation and preset/recorded-reference generation are supported by this desktop candidate. The newer iPad four-mode random/preset/clone/experimental-prosody refinement above is a separate parity increment: do not describe it as already implemented or validated on desktop. The desktop candidate has no new Japanese-curve experiment button.

Actual short Mac acceptance: bundled English reference -> native Whisper recognition -> local MLX translation -> Drama3 generation -> independent Qwen ASR -> saved/reopened WAV. UI and storage tests use clearly labelled synthetic completions; they do not certify microphone capture or GPU inference on Windows. The user's existing Windows 0.24.62 CUDA executable is retained while being tested; 0.24.63 Windows is staged separately. No public GitHub update is authorised until the CUDA result is confirmed.

## iPad 115 refinements (2026-10-23)

The compact iPad text editors adapt to window height and scroll internally. Separate dice buttons immediately select a different supported template (switching to template mode) or a different supported expression for the next generation; neither button synthesizes automatically or changes existing takes, scripts or reference files. The existing random-each-time mode remains distinct. These two controls are CosyVoice-only, since system reading voices do not implement these template/expression controls.

Both own-voice and intonation generation validate an actual 3–10 second audible reference before loading generation models. Reference actions consistently resolve an explicit reference or a legacy input recording; arbitrary typed source text is never assumed to be the reference transcript. Clone mode can recognize the actual recording or accept its manually entered transcript. Intonation uses pitch and does not require ASR. Quiet valid input is normalized for F0; silence and invalid duration report a reference-specific error while preserving text, translations and existing recordings. Recorder completion is matched by unique filename after file closure, rejecting late callbacks and short/silent captures rather than accepting an empty replacement. Physical microphone capture remains to be confirmed by the user; synthetic-reference inference has separate device evidence.

These refinements are implemented on iPad only. Desktop can use this as the next parity specification; its previous acceptance boundary above is unchanged.
