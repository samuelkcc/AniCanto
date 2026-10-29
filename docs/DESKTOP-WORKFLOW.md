# AniCanto desktop workflow and automatic repair
> Language standard: English, ASD-STE100 style. See `docs/DOCUMENTATION-STANDARD.md`.

## Current authority

Read `DESKTOP-IPAD-RECOVERY-WORKFLOW.md` before each desktop workflow or AI-control change.
Its active shared rules and alignment register are authoritative. Update them and the JSON mirror in the same task.
Reuse `WORKFLOW-CONTROLS-GUIDE.json` for four-language product explanations. Record desktop Help integration in the desktop handover.
New desktop jobs use one standard flow. The build 240 mode descriptions below are historical.
Do not use them to define current switch permissions. Read the latest handover for installed status and known coupling defects.

## Historical build 240 workflow

Applies to: new jobs in 0.24.87 / build 240. Install state and acceptance follow the latest record in CODEX-HANDOVER.md. Shared requirement: anicanto-recovery-workflow-2. Mac/Windows share the decision code. Hardware, model formats, and system-installed voices can differ. No guarantee of identical waveform or sound.

Balanced is the default. Full AI review is a separate switch, off by default. New settings prefer to keep the first take. A saved generic/original-audio policy is never changed silently. The goal is to save a usable finished product automatically and write questions into the report, without waiting for per-sentence approval.

## Settings UI

From the start screen, basic mode uses balanced when no work mode is selected. Inside a job, the user can pick performance/balanced/quality. "Auto processing" groups the full AI review, intro/outro detection, OP/ED dialogue translation, and the two fallback voices. All of them use side switches. Full AI review stays off by default. Turning this extra analysis off does not disable normal bounded voice fill.

A paused video does not lock the settings of other jobs that have not started. A change affects only newly submitted jobs; a resume still uses its saved settings. During a real conversion, the mode and the AI switches stay locked, so flows never mix mid-job.

## Content source and speaking clock

A > B means content authority, not execution order. Basic mode follows the preference. Expert mode may pick one of four routes per job. With a vendor subtitle and a selected usable built-in/plugin subtitle, use "subtitles > voice". With no text subtitle, use "OCR > voice".

- **Subtitles > voice: translate only the selected subtitles.** Chinese text is rewritten directly into target-language speech. The original audio only sets the speaking time and supplies the character reference. All gaps with no subtitle keep the original audio. Do not add ASR lines there, do not dub, do not repair, and do not count them as missing dubs. This includes segments where voice recognized words but the subtitle has none.
- When the subtitle has text but ASR missed it, keep the subtitle. Use the original subtitle display time as an explicit fallback, and list a timing warning. Never claim the speaking time is confirmed.
- Voice > subtitles, OCR > voice, voice > OCR: A is the primary content and B is the helper. Use B only when A has no content at all, and record the fallback. OCR applies only when no usable text subtitle exists.
- When one subtitle spans several speech segments, assign the meaning by context. Never copy the whole sentence into every segment. Save the native subtitle display time, the voice time, and the real dub time separately.
- Old jobs keep their frozen source rules. Never rewrite the script silently after an app update. A dub-only update keeps the old script. To test a new translation, start a new conversion explicitly.

## Shared steps

1. Freeze the source, clock, work mode, models, and parameters. Check the original video, the selected subtitles, and the deployment environment.
2. Separate background and dialogue. Analyze OP/ED, the original-audio language, and the speaking windows. Pair subtitles/OCR per the source rule.
3. Build names and context, then write the full natural-speech first draft. **Shortening by an estimated character count before generation is forbidden.**
4. Generate against the original voice/character reference. Save each sentence at once: recording, script, parameters, reference identity, and failed candidates.
5. Apply the bounded listening/repair and fallbacks in the table below. The normal flow and model exceptions share one closeout flow.
6. Protect non-voice performance such as laughter and crying, mix the background and the target language, and keep the original subtitle timing.
7. Build the output and verify audio/video, tracks, subtitles, and duration. Save the final deliverable and the problem report. The list continues with the next unfinished video.

## The three work modes

| Per-sentence stage cap | Performance | Balanced [default] | Quality |
|---|---|---|---|
| First generation, stop when one is usable | 1 | 1 | 3 |
| Dub content listening | all fallbacks skipped | yes, under the whole-video budget | yes, under the whole-video budget |
| Same-character measured timing operations | 0 | 0 under the keep-first-take policy, others max 1 | max 2 |
| Generic target-language generation | 1 | 1 | 2 |
| Generic meaning-preserving shorten after measurement | 0 | max 1 | max 1 |
| Another installed AI engine | max 1 engine / 1 pass | same | same |
| Installed system target-language voice | max 2 passes | same | same |
| Whole-video listening + repair budget | 60s | 180s | 600s |

Each stage cap is independent. It is not "1/2 passes total for the whole sentence". Full AI review adds source-meaning and character/visual analysis; dubbing still follows the selected work mode caps. The model deployment page and the recommended combination per work mode are two separate settings.

The first 75% of a time budget goes to AI, and the last 25% is reserved for the system voice. After the deadline, do not start a new inference or chunk. An inference that already started may finish, so real wall-clock time can exceed the number. Never force-kill a shared service. The model itself has a separate no-progress wait limit. Export time is separate.

The budget file repair-time-budget.json stores spentSeconds and activeSince per stage. A normal pause settles the clock. A resume or a mode change does not refund used time. After a hard kill, unsettled time is counted conservatively. A normal model completion saves the audio file of each sentence. Candidates finished mid-way are kept. Never mark an unfinished inference as success.

## Repair and last fallback

Usable first take -> same-engine generic target language -> at most one other installed AI engine that supports the target language -> installed system target-language voice -> original audio last. An explicit "original audio" failure policy may use the original directly.

- Only when the real recording is longer than the available window may the mode shorten with meaning preserved and re-dub in full. A new script keeps names, relationships, negations, quantities, conditions, and grammar. Do not use it before the meaning check approves it. The cache identity changes with the new text.
- Do not cut sentence tails, swallow words, or squeeze the line into the next sentence. Small pitch fixes have their own cap; they are not an unlimited fast-reading solution.
- **Confirmed wrong content** must go into the fallback. A wrong take is never picked back just because the first take has sound. A single language tag, a homophone, a written-language form, or an uncertain recognition is a warning only: never claim a pass, and never trigger an endless re-record loop.
- The system fallback uses only an installed target-language voice; no automatic download. Cantonese must not use a Mandarin voice. It can be turned off before the job starts. The timbre may change, and that does not certify character imitation or accent. Mac uses system voices; Windows uses enabled SAPI voices. The usable voice list can differ between platforms.
- The built-in generic reference bank currently holds Cantonese/English. Mandarin has no equal bank material. You may try a supporting model plus an installed Mandarin system voice, but do not claim equal capability.
- Protect non-voice performance such as laughter, crying, and groaning at its original time. A text-bearing "救命" must not be excluded only because it is loud. Segments with no subtitle under a single-subtitle content route follow the keep-original-audio rule instead.

## Automatic delivery, resume, and reports

A normal AI or system-fallback error writes a warning, then completes with the existing recording/original audio. A missing script, an unconfirmed language, or a final original-audio segment does not block automatic output. When the whole video has 0 target-language segments, output is allowed only when original audio keeps continuity and the mix is valid. State clearly that this is an original-audio delivery, not a completed target dub.

- The report lists missing sound / original-audio fallbacks, times, content evidence, attempts/time used, and the final engine/system voice. The user can later pick a clip to listen, edit the script, or re-record. This is not a required human follow-up before completion.
- Mix + subtitle wrap + verification together get the first pass plus one automatic retry, stored persistently in export-retry.json. Before output, the mix identity and SHA go into final-audio-checkpoint.json. A "last export only" run verifies the identity and the audio, and does not re-translate or re-dub.
- An explicit new conversion / a new dub-refresh round creates a new delivery budget in a new version directory. Keep the parent version, the frozen source, the script, and the takes. A normal resume does not reset. Never move an old budget into the new version.
- User pause/cancel and a manual take/clock choice are protected. A damaged source, a full/unwritable disk, and a persistent encode error still report an honest recoverable failure. No design can guarantee that every hard error still produces a valid video.

## Acceptance limits

The shared spec is a requirement, not a deployment certificate for three platforms. Record the real installed version per platform. Isolated tests must cover three modes x three failure policies, confirmed/uncertain split, subtitle gaps, old-job freeze, exceptions reaching the system fallback, budgets across restarts, suitable neighbor sentences and manual-take protection, and real MP4/subtitles/decodability. Metadata and audible audio are not semantics, accent, or full-episode listening certification. Windows real-machine runs and whole-video results need separate acceptance.
