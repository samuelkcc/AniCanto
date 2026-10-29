# Desktop subtitle-first source workflow · 0.24.83 / build 236

New submissions use a versioned source policy. Existing paused requests retain their original policy and recordings.

| Source | Dialogue content | Speech timing |
|---|---|---|
| Selected embedded or external text subtitles | Authored subtitle text is primary; Chinese is adapted directly into spoken Cantonese | Original speech recognition and witnessed audio bounds |
| No usable subtitles | Original-language recognized speech | Original audio |
| Explicit Expert OCR | Compare time-matched OCR and recognized speech; neither blindly overwrites the other | Original audio |

Use **Subtitle source** above the preview to choose the conversion source. This selection is separate from the player subtitle selector, which changes playback only. Automatic detection prefers an imported/same-name external file, then supported embedded text subtitles; absent those, it uses speech recognition. It does not automatically enable OCR. Image subtitle tracks require the explicit OCR path.

External bytes are frozen per submission. Embedded normalized text retains an extracted-source hash; a source-video size/mtime snapshot protects the selected source identity during resume. Subtitle display clocks remain separate from speech clocks. Authored content spanning several speech turns is assigned with exact quotes before translation: no lost or duplicated source characters, no reversed order, and lexical turns cannot silently receive empty text. Unconfirmed allocations keep their original audio and appear in the review report; unmatched subtitle intervals are reported rather than given invented speech times.

The chosen primary text is used for the initial draft, names, English/Mandarin output, shortening and missing-script recovery. The original audio transcript remains separate for voice-reference conditioning. OCR remains a compared source, not a professional authored subtitle. Old takes, media and models remain.

## Testing the new workflow

- New video: add/import the intended subtitles, choose the conversion source, then Start.
- Existing paused/finished video: use Restart / update dubbing → Reset state, confirm the filename, select/import its subtitles, and Start. Reset detaches prior job links while retaining the previous files on disk. Merely resuming an old request does not change its source policy.
- Regenerating voices alone retains that project's frozen source/translation policy. Reanalyse as a new version to change source analysis.

The small real-model text test kept the existing 16 source clocks and Japanese transcripts and retained the previously lost date/right-hand content. This is not a full-film pronunciation, voice identity or synchronization certificate. Review ambiguous captions, OCR conflicts and missing speech clocks. Hardware inference still needs user acceptance on each platform.
