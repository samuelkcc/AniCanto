# Desktop 0.24.84: subtitle allocation and responsive import

Source captions and generated dubbing are separate data. A blank target script must not hide an already-read source caption.

## Fixes

- Read performance-review configuration and audio availability once per folder, rather than once per review event. Read-only projection stays stateless, without stale persistent caches. Background polling yields while adding or selecting a video.
- New requests freeze `sourceAllocationRevision=boundary-aware-2`. Existing saved requests retain their original allocation policy. The subtitle content priority remains `subtitle-first-1`.
- Ignore incidental caption display tails when finding candidate speech owners. Keep real short turns contained within a shared caption. Speech times and original ASR remain unchanged.
- Constrain model caption IDs to allowed source records. A wrong ID can only be repaired if its exact quote uniquely matches another allowed source caption. Changed words, dropped clauses and duplicated content still fail validation. A bounded second attempt receives the actual validation error and previous rejected answer.
- If a shared-caption split remains uncertain, preserve each full caption once at its strongest corroborated speech interval. Other fragments retain original audio with an explicit review notice. This preserves authored content; it does not certify the split, speaker, fit or complete target-language dubbing.
- Show missing-dub reasons beside the script. The timeline displays source-only text in dashed clips, distinct from target-language scripts. Per-line review entries make affected positions discoverable.

## Testing saved projects

A voice-only update retains the old script. To test the new source allocation, use **Reset state → select/import Subtitle source → Start**. Earlier output and recordings remain on disk. No saved conversion is reset automatically by installing this patch.

Cloud-file timeouts are a separate I/O issue. The observed Google Drive source read timeout is not proof that subtitle allocation or TTS hung. Keep an offline local source available when testing; this patch does not claim to repair the cloud provider.

## Evidence and limits

Private QA evidence is under `.build/import84/`. The One Piece 820 metadata fixture covers all 259 ASR turns with unchanged original transcripts and speech clocks. This is source/text allocation evidence, not a re-encoded whole-film audio or voice-quality certificate. Windows receives the same Python/UI fixes; physical Windows acceptance remains separate.

## Configurable content priority (latest user instruction)

Arrows mean **content priority**, not media-processing execution order. Factory defaults are **Subtitles > speech** when a usable selected embedded/external text track exists, and **OCR > speech** otherwise. This explicitly supersedes .83's OCR opt-in default for **new** requests. Basic mode uses the two saved Preferences defaults automatically. Expert mode exposes four paths plus Follow preference defaults. Preferences stores separate defaults for text-subtitle and no-text cases. Incompatible manual choices show a clear error; OCR never takes priority over an available selected text track. Explicit ASR-only source choice still excludes captions.

`sourceWorkflowRevision=priority-paths-1` and resolved workflow participate in new-job cache identity. `source-workflow.json` records requested/effective choices, availability and OCR use. Previously frozen requests are not migrated. If A is completely absent, B may supply the line and is marked in the report. If both have content and conflict, A stays authoritative. If neither has content, it is not a successful dub. No changes to original speech timestamps, audio-reference transcripts, sampling defaults or recording ownership.
