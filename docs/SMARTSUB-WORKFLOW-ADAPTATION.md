# AniCanto workflow refinement — independent implementation

Updated 2026-10-23. SmartSub public documentation informed product requirements only. No SmartSub source code, UI assets or dependencies were imported. AniCanto keeps its own backend, Tauri host, model adapters and iPad architecture.

## Shared workflow

Import → inspect available subtitles → recognise/translate only missing material → generate immutable per-line recordings → automatic bounded repair → export → focused human review → regenerate only affected lines → export a new version.

Original subtitle timestamps are preserved. Existing speech_timing/natural_schedule timing admission and capped recovery budgets remain authoritative; UI triage never approves a questionable take or relaxes a timing limit.

## Implemented desktop changes

- Review report groups missing voice, wording/language, overlong recordings, reference problems, fallback voices and other notes. Filters preserve the original diagnostic evidence.
- Each issue supports Checked by me, Review later, Reopen review and persistent undo. A decision binds to line + engine + language + current edited words + current evidence. Changed evidence reopens the check automatically. Human acknowledgement is separate from automatic quality status, recording choice and published output.
- Retained take provenance detects changed spoken text, role and reference configuration. Only affected lines are listed for regeneration; old audio and movies remain intact. Unknown historical provenance is not guessed. An in-place externally modified reference without a stored original digest cannot be proved unchanged by this UI check.
- Worker events persist last-event and last-measurable-progress timestamps independently of duplicate log suppression. A quiet worker is labelled as no recent message, never falsely declared stopped or killed. Real errors remain visible.
- Existing per-line generation, role-level configuration, original/separated/generated audition, safe timing, draft saving, undo, targeted repair, output versions, model availability and memory budgets are reused rather than duplicated.

- Subtitle source is a single management drawer opened above the preview; production settings display only the selected filename. SRT/ASS/SSA/VTT import continues to bind to the selected video, with running/paused submission locks preserved.

## iPad parity contract

Apply the same semantics in native iPad views; do not copy desktop pixels or expose desktop-only models. Track identity is immutable cue identity + target language + engine. Persist review state and undo in the project, evidence fingerprints and retained recording provenance. Report counts must distinguish model failures, pending human review, deferred, checked and actual verified repairs. Checked is never a model pass. Modified text/reference/take evidence reopens the note. Refreshing a view must not change playhead, audio choice, repair budget or start tasks.

Preserve the explicit gaps already recorded in IPAD-DESKTOP-WORKFLOW-PARITY.md (source timing, natural placement, evidence director, targeted batch repair). Reuse the same fixture cases before declaring parity; platform-specific ASR output and GPU support are not assumed identical.

## Acceptance

Use isolated fixture storage only. Test persisted choices after reopen, same cue in two languages, evidence invalidation, undo, loading with no progress messages, changed script/reference and retained movies. Automated tests do not certify Cantonese pronunciation, emotion or full-movie quality.

## Queue continuation clarification (803 → 804)

Both interface modes now use the same primary Start/Resume intent: process the unfinished video list in queue order, skip completed outputs, and include videos added while running. Waiting videos may be reordered without interrupting the current episode. Explicit pause stops continuation; a failed episode retains its error and does not loop. Explicit selected-video Retry and new-version operations remain scoped. This corrects the old Expert-mode selected-only default that left episode 804 waiting after 803 completed. Opening the app alone still does not restart user-paused work.

Pause & save uses the same red action style in both Mac and Windows shared interfaces, including hover, focus and disabled variants.

## 0.24.64 stability correction

Normal mode now retains audible first recordings and automatically repairs missing/damaged audio, and locally shortens objectively overlong lines. Language, accent and suspected omissions are review notes rather than automatic retake triggers. Timing candidates must fit before adoption; a maximum of two local passes cannot restart broad language repair. Detailed checking is opt-in. Independent ASR checkpoints each recording, resumes incomplete work and reuses unchanged evidence across stages. Apple Silicon has an optional pinned MLX Whisper model; faster decoding is not a pronunciation certificate. These are independently implemented AniCanto mechanisms, not claims about SmartSub behaviour. See INDEPENDENT-LISTENING.md.
