# Desktop/iPad/iPhone shared: dubbing, repair, and original-audio performance protection spec
> Language standard: English, ASD-STE100 style. See `docs/DOCUMENTATION-STANDARD.md`.

## Shared authority and mandatory change protocol

This file is the common workflow authority for macOS, Windows, iPad, and iPhone development.
Samuel set this rule on 2026-10-28. All development lines must maintain this same file.
Do not create a second platform-specific definition of the common workflow.
`RECOVERY-WORKFLOW-CONTRACT.json` is the machine-readable mirror. Platform guides describe implementation and exceptions only.
The current shared rules below take precedence over dated historical sections in this file.
A requirement is not proof that either installed app implements it.

Before each workflow change:

1. Read this authority, the JSON contract, and the newest three handover entries.
2. Check the source and latest acceptance receipt for each affected platform. Use narrow, bounded reads.
3. Identify the affected rule IDs below. Check initialization, translation budgeting, generation, recovery, resume, and final export.
   Recheck WF-01, WF-02, WF-03, WF-15, WF-16, and WF-17 against the effective frozen request.
4. State the intended behaviour and any platform difference before changing code.
5. Preserve saved-job rules. Do not migrate budgets, sources, scripts, or chosen takes silently.

Before closing the change:

1. Update the affected shared rule here and its JSON summary in the same task.
2. Update the platform mapping and alignment register below, including every affected counterpart.
3. Record implemented, tested, installed, and whole-film accepted states separately for desktop, iPad, and iPhone. Name the evidence and remaining work.
4. Test effects at execution boundaries. A settings projection or interface screenshot is not execution evidence.
5. Update affected guides and write the handover entry. Leave a clear task for the other development line.

An unimplemented counterpart is an open alignment item. It is not an approved platform difference.
Use `pending`, `defect`, `intentional difference`, or `verified` explicitly. Samuel approves intentional behaviour differences.
Do not block unrelated work or start another conversation, device test, or conversion to enforce this protocol.
The common rule does not require identical models, hardware, interface layouts, or build numbers.

### Automatic source selection, confirmed 2026-10-29: `basic-source-defaults-231`

Basic has no manual source menu. Detect readable selected embedded or imported external text subtitles before source selection.
With readable text subtitles, select subtitles > speech. Without them, select speech > OCR.
Burned-in picture text is OCR evidence, not an embedded text subtitle track.
Expert offers five choices: Automatic detection and the four existing manual source flows.
Automatic detection uses the same fixed rule as Basic. Old preference overrides do not change this detection rule.
Retain the existing missing-text fallback for an explicit speech/subtitle selection. Report the effective flow and reason.
A determines meaning. B assists only. Subtitle-led gaps do not create new ASR dialogue.
Apply this decision only at new source initialization. Keep saved effective flows and spent budgets unchanged.
Freeze the requested selection mode, effective flow, and selection-rule revision separately.
This decision supersedes the earlier no-subtitle OCR > speech default. Four manual Expert flows remain available.
Use guide12 item `sourceWorkflowDefaults`. Mobile source is prepared; runtime boundary tests and package delivery are pending.
Desktop and phone owners must record separate implementation, execution, installation, and whole-film acceptance.

### Original-audio report visibility, confirmed 2026-10-29: `original-delivery-report-233`

A preserved original is not proof of delivered target-language speech.
Show known non-OP/ED dialogue in the alignment report even when keepOriginal is true.
Show the source-audio label and saved processing issue. Do not call every preserved original a user choice.
Keep automatic source fallback visible as unconfirmed delivery. An uncertain ASR score is not confirmed wrong speech.
A report notice cannot start generation, replace a take, grant repair permission, or renew spent allowances.
No generation gate or saved preservation reason changes in this presentation correction.
Normal phone233 is installed. The native finalizer/report fixture and direct controls pass. Whole-film acceptance remains open.
Shared iPad presentation source has the same change. Its native package and installation remain pending.
Desktop255 owns its separate coverage correction. Do not infer phone output acceptance from the desktop audit.
Use shared guide13 item `originalDelivery`. Earlier source-selection guide12 text remains exact within guide13.

### Basic preferences and fallback access, confirmed 2026-10-29: `basic-controls-235`

Basic and Expert expose the existing final voice-fallback choice. The factory choice remains first audible take.
Production controls set the stored choice for new jobs. General Preferences must not duplicate this control.
Freeze that choice only when a new job starts. Normal240 is installed on M4. Its separate receipt confirms launch and unchanged saved jobs.
Do not replace a saved job policy on resume. Do not grant optional AI repair or cross-engine permission.
Mandatory missing-audio fill, the three-call total, duration rules, first-draft guidance and overlap permissions stay unchanged.
Check WF-01/02/03/15/16/17 against frozen requests. Their generation and export algorithms do not change here.
Use guide14 item `failedVoiceFallback`; all four languages use one shared definition.
The iPad settings page places assistant preview first. It offers the existing idle and work animations.
A capability-limited Reading introduction explains the reason, then Reading functions, then entry steps.
Its final action says Enter Reading mode. It does not introduce Basic or Expert as available destinations.
A capable device's voluntary introduction must not claim insufficient memory.
Normal M4235 is installed and launched. Four native cases pass; all three saved jobs remain byte-identical.
Normal phone236 installs the narrow fallback controls and guide14. Its separate native and direct checks pass.
Compact phone assistant placement and desktop help consumption remain separate. No complete-film output acceptance is claimed.

### Shared Reading introduction information: `reading-intro-overview-237`

This information-only follow-up supersedes the235Reading page copy. It changes no workflow or purchase gate.
First explain the actual hardware limit and the lighter Reading option.
Then show short Basic and Expert feature summaries with their corresponding screenshots.
State that studio features need supported hardware. Basic is free; Expert needs the existing one-time upgrade.
The final action explicitly enters Reading mode. It cannot open an unsupported studio or start a purchase.
iPad and iPhone consume the same ReadingIntroContent keys and four locale values.
Retain separate native layouts and capability reasons. Source parity is not installed acceptance.
Normal M4237 is installed. One native case captures13layouts and all three saved jobs remain exact.
Phone236 is installed according to its owner. The signed normal package matches all31shared keys in four locales.
Its native Reading layouts pass. Broader phone purchase-navigation and final-preservation checks retain their separate receipt.

### Phone upgrade presentation236

The first lower-left action is Back. It dismisses the introduction. Later pages show Previous.
The lower-right action is Next. It is disabled on the last page.
The existing priced purchase action fills the content width. Restore purchases is upper-right, purple, and underlined.
Normal236 installs this phone layout. Native captures and direct navigation checks pass.
The shared lifetime product, tablet layout, entitlement rules and transaction handlers remain unchanged.
No purchase or restore transaction runs during validation.

### Mobile purchase access, confirmed 2026-10-29

Only Expert mode requires the existing non-consumable purchase. Keep its product identifier.
Basic, Reading, Learning, playback, export, save, and share remain free. Learning has no dialogue limit.
Unpaid Expert entry shows a lock and opens the common upgrade introduction.
A stored Expert selection cannot bypass the entry check. Simulated unpaid state takes precedence in DEBUG builds.
The iPad DEBUG test menu is in About and licences. Production builds omit this menu.
This rule supersedes the earlier export-only and Expert-plus-export policies.
No conversion source, frozen request, first take, model, or spent recovery budget changes.
Normal M4229 is installed. Two native access/menu tests pass. Its package contains exact guide11.
Normal phone227 is installed. Native access fixtures and both actual unpaid Expert entries pass.
Real purchase/restore remains open. Desktop purchase behaviour does not change.

### iPhone scope, 2026-10-28

Samuel first authorized a Standard-only iPhone 17 Pro prototype and an original three-minute sample.
He later expanded the interface to Standard, Expert, Speech, Viewer, Learning, and the existing reading workspace.
Build 202 implements portrait phone navigation with a drawer and the shared native workspaces.
Welcome uses swipe themes. Models and app-icon selection are in Settings. About and licences use a trailing icon.
An eligible AI entry opens the existing default-model consent flow when required files are missing.
No download starts before approval. Existing files, purchase identity, and saved requests remain unchanged.
The shared control guide stays `WORKFLOW-CONTROLS-GUIDE.json`. Phone navigation does not define another conversion policy.
WF-02, WF-03, WF-07, and WF-08 retain their missing-audio, first-take, budget, and engine requirements.
The foreground queue uses the common completion and cleanup gates. Cold Welcome does not start a conversion.
Earlier normal build 202 was installed on iPhone 17 Pro. Its focused layout, consent, and queue checks pass.
See `docs/IPHONE-PORTRAIT-202.md` and its private receipt for evidence and exact limits.
The source-reference defect and rejected voice consistency remain open. The interface port does not certify speech quality.
Full-film, real queue conversion, fresh model deployment, and production purchase acceptance remain pending.
No iPad installation or whole-film acceptance is implied by phone evidence.
Phone welcome revision 204 adds small theme page dots and reuses the iPad DEBUG purchase/memory simulator.
Welcome has no workspace header or menu. Unsupported capability exposes Reading only, regardless of simulated purchase.
Earlier normal build 204 was installed on iPhone 17 Pro. Four focused cases pass, with a corrected layout-capture rerun.
The 24 native fixtures and normal Welcome/Settings captures pass visual inspection. Human acceptance remains pending.
The package includes completed iPad build 203 source policy and guide revision 6. No fresh source-model run occurred.
See `docs/IPHONE-WELCOME-204.md`. Earlier conversion and queue evidence retains its own build and limits.
Phone UI build 208 supersedes the interim selection-and-Enter design.
Eligible Welcome has direct Basic/Expert glass buttons. Reading is in the drawer.
Unknown or unsupported devices show Reading only, with a reason.
Introduction and Settings reuse iPad functions. Expert Preview/timeline and compact Speech have portrait adapters.
The package is installed on iPhone 17 Pro. Native and Simulator-native layout evidence is in `docs/IPHONE-PORTRAIT-208.md`.
Duo identification retains memory/GPU gates. Physical folding and real Duo neural acceptance remain pending.
The private phone core is still completed 203 with guide revision 6.
Completed iPad 205 workflow fixes require separate phone adoption and acceptance. Do not infer that alignment from UI evidence.

Phone UI revision 211 adds a compact Basic workspace.
Target language is below Preview. New jobs retain the existing Cantonese default and explicit saved preferences.
Existing jobs keep their saved language. The new row cannot change active or resumed jobs.
The top-right Basic options button opens the existing production controls in a sheet.
Progress is collapsed initially. Existing conversion requests and frozen job settings remain unchanged.
Welcome uses larger purple angled buttons, corrected mode icons, smaller art, and a theme-colored information icon.
This is a presentation change. Desktop and iPad control semantics and the shared AI-control guide remain unchanged.
Compilation and installation evidence are recorded separately in the phone receipt.

Phone UI revision 212 completes the later navigation request.
The workspace header uses the former information-button position for Basic or Expert options.
About and licences are in the left drawer. Welcome retains its themed information icon.
Phone Learning opens the playlist without selecting or playing a video automatically.
iPad entry and playback behavior remain unchanged. New phone selections use the existing study and playback handlers.
Revision 211 was an interim installed package. Its early captures were not accepted as final visual evidence.
Revision 212 evidence records the final package and settled captures.
Normal build212 is installed on iPhone 17 Pro. Six settled captures pass visual inspection.
See `mobile/Validation/iphone-compact-interface-build212-2026-10-28.json`. Human acceptance remains open.

Phone UI revision213 raises Welcome page dots and removes side arrows.
Phone theme changes request a 420ms crossfade; Reduce Motion disables it.
The native Duo Welcome harness is deployed. Two layout states have Simulator-native render evidence.
The initial Simulator.app check was incomplete. Later assessment confirms DeviceHub provides the Duo GUI.
Preview214 uses live window geometry. Full workspace folding and AI Simulator acceptance remain open.
These presentation changes do not alter common workflow rules or saved conversion requests.
See `mobile/Validation/iphone-welcome-duo-build213-2026-10-28.json`.

### Phone multiple-video interface, revision222

The phone entry selects multiple Files documents and imports them sequentially in picker order.
A failed file does not remove completed imports. Import cancellation stops the remaining files.
The introduction stays pinned. New videos precede older user videos. The first successful import becomes selected.
The preview shelf scrolls vertically. Existing bottom actions stay outside the scroll region.
Import does not start conversion. Conversion remains blocked during import and deletion.
Existing foreground full-video continuation gates stay unchanged. Pause, failure, and background stop continuation.
No cold launch starts. Frozen requests, first takes, and spent recovery allowances stay unchanged.
Shared iPad entry remains single-file until its owner adopts the optional API. Desktop entry stays unchanged.
Source implementation, device checks, installation, and human acceptance need separate evidence.
See `docs/IPHONE-MULTI-VIDEO-222.md`. No WF-16/WF-17 or MLX adoption is implied.

### Phone workflow and interface224

Normal224 consumes completed205 target/reference rules, completed223 workflow, and bounded215 MLX.
Phone import, portrait layout, and newer capability profiles remain. Explicit v4 and Cosy preferences remain.
The picker represents stored v4. M4223 has its own matching engine-selection evidence.
The phone bundles exact guide9. Eighteen native cases pass, followed by three final boundary cases.
Actual E4B first requests, Whisper/Cosy, six MLX calls, cancellation, memory bounds, and native exports have bounded evidence.
Default full-take overlap and held tails pass export checks. Optional overlap execution uses injected speech spans in these tests.
Production overlap uses installed Apple attributed lexical timing. Actual overlap recognition plus retake remains open.

Normal224 passes deep strict signing, installs, and launches on iPhone17Pro. No test plug-in is present.
All three original checkpoints remain byte-identical after installation. No spent allowance resets.
Long-press source editing adds jiggle, minus actions, and Done. Saved outputs use the existing archive-before-delete service.
Final native320/402 Basic/Expert editing layouts show complete controls within the viewport.
Welcome mode buttons follow all nine themes. Drawer symbols share a24point column.
Normal Welcome and drawer captures pass visual inspection. The normal editing capture is rejected as stale.
The phone locks before that capture can be repeated. Human touch acceptance remains open.

The older23minute job still fails bounded Whisper recovery at its first3.75second part.
The failure is not proof of silence or wrong speech. The original job and counters remain unchanged.
Whole-film, speaker consistency, emotion, real neural batch, clean-user deployment, and full Duo adaptation remain open.
See `docs/IPHONE-WORKFLOW-224.md` and `mobile/Validation/iphone-workflow-build224-2026-10-28.json`.

### Phone interface225

Normal225 adds a phone export banner and the shared Reading restriction introduction.
It removes duplicate drawer entries, adds the source reset icon, and fixes motion after Done.
Five native cases and one final portrait case pass. Normal225 is installed and visually inspected.
This is presentation evidence. Completed224 workflow execution keeps its own scope and open limits.
Samuel confirms manual removal of the old sample. The remaining One Piece checkpoint stays byte-identical.
The new full-screen portrait introduction request replaces225's interim border/backdrop target. Phone227 work follows.
See `mobile/Validation/iphone-interface-build225-2026-10-29.json`.

### Phone introduction227 and initial model preparation

Phone227 uses a real portrait introduction movie with original audio and subtitle clocks.
Its unpaid Expert card opens the shared purchase introduction. The separate Welcome banner is removed.
Current default, confirmed 2026-10-29: prepare Gemma 4 E4B and CosyVoice, plus required Whisper and HTDemucs.
Qwen, GPT-SoVITS and other alternative models require a separate manual action in Models.
This decision supersedes the five-group default from227. It does not remove existing models or change selected engines.
The user approves one combined plan before connection. Preparation runs sequentially.
The default pass does not request Apple recognition resources. Recognition remains Whisper-first.
Normal phone245 and iPad245 now install this source and exact guide8.
Three phone native cases pass. Existing-file one-click preparation and direct zh-HK setup instructions pass on phone245.
The iPad owner records its separate compilation, installation and preservation evidence. Native scope execution on M4 remains unverified.
Clean-device full download acceptance remains open. The phone lower chapter-row remote hit behavior needs separate review.
Pause cancels the active transfer and prevents the next group from starting.
Reuse verified files and partial downloads. Keep selected engines, saved requests, and spent counts.
GPT packages remain installed/imported resources until a verified public artifact exists.
The iPad owner checks provenance and notices. The dedicated model release remains an unpublished draft.
Phone227 is installed. Consent, exact approval reuse, queue order, and cancellation fixtures pass.
Normal M4229 does not include the setup change. Clean-user whole-download acceptance remains open.
No desktop deployment change or clean-user whole-download acceptance is claimed.
See `docs/IPHONE-PORTRAIT-INTRO-227.md`. WF-01/02/03/15/16/17 remain unchanged.

## GPT MLX deployment decision, 2026-10-28

Samuel selected MLX for GPT-SoVITS deployment. Speed is the first deployment priority.
The target order is iPad first, then iPhone after iPad acceptance.
The short Mac candidate has listening acceptance. This does not establish iPad performance or complete model support.
Use one MLX runtime with existing CosyVoice. Do not load a second conflicting MLX implementation.
Keep the current verified Cantonese frontend until its replacement has equivalent evidence.
CPU input preparation does not make the neural generation backend a CPU engine.
The required audible-output check remains active. This backend change does not enable optional AI repair.
Preserve valid first takes, target scripts, source priority, frozen jobs, and spent recovery allowances.
Do not call a backend installed until its actual app package and device execution pass.
Measure equal-boundary generation, model loading, memory, cancellation, and repeated recordings on each device.
Record desktop, iPad, and iPhone evidence separately. No speed factor transfers between devices.
No new workflow control is added. Use the shared control guide. Record each installed consumer revision separately.

## Manual Learning line actions, confirmed 2026-10-29

Translate only the source line selected by the user. Preserve other line translations for the same target language.
A target-language change clears stale translations. Cancellation cannot publish a late response.
Record only the selected translated line with the explicitly selected supported engine and parameters.
Store it as an independent candidate. Do not overwrite the original dub, project, output, or automatic repair budget.
A hash-verified short cue can use the existing short-reference adapter. It adds only silence for encoder context.
Never repeat words, borrow another speaker, or switch engines solely because a reference is shorter than three seconds.
This manual action does not change WF-01/02/03/15/16/17 or frozen automatic requests.
Use guide10 item `learningLineActions` for product help. Normal iPad228 is installed. Five native cases pass, including two actual engines and live assistant frames.
Normal phone227 consumes completed228 Learning and guide11. Five native Learning cases pass, including two actual engines.
Human listening and desktop line-action review remain pending.



### Native target delivery, iPad234

New iPad projects freeze `caption-clock-target-234`. Required selected content cannot be suppressed by automatic source uncertainty.
Keep original clocks, transcripts and spent counts. Old frozen jobs and explicit user originals are not migrated.
Source waveform identity cannot certify generated audio. Source retention, requested delivery and actual audio stay separate in coverage.
Unknown old preservation flags are not assumed user choices. Fifteen unique M4 fixture cases pass. Normal234 is installed and launched; three real checkpoint files remain byte-identical.
Optional generic readback requires content-check permission in every stored mode label. Strict timing does not grant content permission.
Bundled CC0 profile reuse is CPU-only and bounded to six entries/eightMiB. Private references do not enter it.
One same-input cold/warm pair produces identical recordings in49.99/3.75seconds. This is not whole-film performance acceptance.
Completed phone233 report and serial setup sources are consumed. Normal phone241 now consumes the234 core, cache and coverage rules with its own device evidence.
See `docs/IPAD-TARGET-DELIVERY-234.md`. Guide13 retains the shared report and source-control definitions.

### iPhone target delivery241

Normal phone241 is installed and launched on Samuel's iPhone 17 Pro after the completed234 core is adopted in the private phone source.
Fifteen unique native cases pass in one invocation with zero failures in80.152seconds on that device.
New phone projects freeze `caption-clock-target-234`. Both saved jobs keep every file byte-identical, including the saved One Piece checkpoint and its spent Whisper source-window attempts.
The saved One Piece job has no `standardFlowRevision` and receives none. All47 preference keys match except the StoreKit polling timestamp.
The bundled reference cache keeps the same six-entry and eightMiB bounds. One warm reuse returns a byte-identical recording and lowers reference open time from1.228to0.654seconds.
The Cosy model was already loaded in that process. This is profile encode reuse only, not cold preparation and not whole-film performance acceptance.
Operation guide4 and control guide15 stay exact in the package. No product copy and no locale string changes occur.
The phone keeps its inline voice fallback selector and the239 duplicate-entry fix. Purchase gating and layouts stay separate from this core change.
Whole-film target coverage, audio presence, subtitle coverage and human listening acceptance remain unaccepted on the phone.
See mobile/Validation/iphone-target-delivery-241-2026-10-29.json.

### Target speech preflight and source retention, desktop255

This clarification maps WF-02, WF-03, WF-09, WF-10, WF-13, and WF-14.
Desktop new submissions freeze `targetDeliveryRevision=caption-clock-target-255`.
Existing frozen requests and spent recovery counts remain unchanged.

- Every TTS synthesis chunk must contain the approved spoken target text. Delivery instructions
  cannot form an independent generation chunk. Verify the actual pinned engine splitter before
  inference. Keep the vendor source unchanged. Do not cut a fixed waveform prefix as a repair.
- A valid owned subtitle script remains required target dialogue when only source word timing is
  uncertain. Keep the saved clock and its uncertainty label. Do not mark it as a confirmed word
  clock. Do not use that uncertainty alone to set deliberate original preservation.
- Try the selected engine with a usable reference. Missing or invalid clone conditioning can
  reach the existing bounded selected-engine generic fill. Do not enable a second engine or
  a system voice implicitly. Keep the first audible take and the same presence budget.
- A shared-caption continuation does not automatically need a duplicate translation. Keep its
  owner evidence. Report source retention and unconfirmed meaning coverage separately.
  Genuine subtitle gaps, OP/ED, nonverbal performance, and explicit user choices retain their rules.
- Report generated target audio, absent target delivery, source preservation, known generation
  input defects, and unchecked language quality separately. A physical source recording does
  not count as a delivered target recording. An ASR label alone does not prove wrong language.
- A read-only report can reveal an older deterministic input defect. It must not overwrite an old
  recording, renew an automatic budget, or launch inference. Explicit user repair creates a new
  version and retains the earlier movie and evidence.

Mac255 has the implementation and focused execution evidence. One real Drama3 MLX candidate
uses the same822reference, target words, seed, and sampling. It has one spoken chunk and lasts
7.105seconds. The previous take has an instruction-only chunk and lasts13.514seconds. Independent
readback no longer returns the Japanese prefix. This is not whole-film or accent acceptance.
Windows uses the same source guard and report code. Its native GGUF splitter is not certified by
the MLX test. Native Windows execution remains open. Mac0.25.2/build255 and the Windows package are now installed in dist. The app stays closed.
The210-case focused regression, separate14/4/18recovery-related cases, four report locales,
and24navigation viewport cases pass. Native Windows inference and whole-film acceptance remain
open. See `docs/DESKTOP-TARGET-DELIVERY-0.25.2.md`.

iPad and iPhone owners were notified on Samuel's explicit request. Their installed versions
and later corrections require their own receipts. The M4 subtitle-first
path already retains a labelled subtitle clock instead of silently skipping authored dialogue.
The mobile legacy source-preservation gate and export-coverage classification still need review.
The mobile GPT/Cosy adapters do not use the desktop Drama3 instruction path. Do not infer the same
300-byte defect or completed platform alignment. Each owner must record native execution,
packaging, installation, and user acceptance separately.

## Shared operation manual, desktop256

`docs/APPLICATION-USER-GUIDE.json` is the single operation-manual source for desktop, iPad and iPhone.
Its source revision is `application-user-guide-3`. Its SHA-256 is `8cef8e01fb22ec8ca3571cbf3e67718624df0a9f3980ab23b3f16bd0aa24a244`.
Installed Mac256 retains operation guide revision2 at SHA35e4e9f42ed92f0363fe4c28a68194dc855072f1e9bcdbc5f50fa1430a4214b6.
Revision3changes only mobile Reading prerequisites and seated rest/dozing help. Desktop chapter content is unchanged.
A later desktop package must consume the new source; do not relabel the installed256copy.
Revision1 is superseded before desktop installation. Its source remains in the private manual256 evidence.
Filter both chapters and sections by platform. Four locales share stable IDs and chapter aliases.
Resolve `controlRefs` from `docs/WORKFLOW-CONTROLS-GUIDE.json`; do not copy and alter a control definition.
Guide14 remains exact at `d8c6a0da78914b5ed68fd81ed3615814c8ebb6700e0c1ba43284102e508d1aaa`.
`docs/USER-GUIDE-MAINTENANCE.md` defines the change procedure. AGENTS requires this check for every visible feature change.
Desktop owns the initial common source. The mobile owner supplies ten reviewed mobile-only chapters.
The file contains30chapters. Desktop displays20; Reading, Learning, mobile purchases and mobile navigation are filtered out.
Desktop Help consumes the canonical source and shared control IDs. The old duplicate chapter definitions are removed.
Mac0.25.3/build256 is installed after user closure. Isolated installed startup and strict signing pass.
All194user metadata files remain exact during installation. Windows remains255.
Mobile consumers must record their own copied hashes, native tests, package and install states.
This documentation change does not change WF-01/02/03/15/16/17, a frozen request, a recording, or a spent allowance.
The actual822/823requests retain first-audible253, target-delivery255, zero content checks, no optional repair, no duration limit and allowed overlap.
Do not infer mobile core parity, complete-film language quality, or new hardware support from a manual copy.

## Confirmed silent captions and contextual Cantonese260

Target: Keep screen-text subtitles visible without target speech only when positive evidence proves no dialogue.
New desktop requests save skipNonDialogueCaptions, default true, and caption-only-no-dialogue-260.
Require completed original and vocal-stem VAD with matching waveform hashes and offsets.
Require no lexical recognition in the padded caption window, no VAD activity and a complete near-digital-silent vocal-stem window.
Absent recognition, failed TTS, uncertain speech or offscreen speech is not proof of silence. Keep target dubbing when evidence is incomplete.
Keep source text, translated captions and display clocks. Exclude a confirmed caption-only row from missing-target fill only with this evidence.
Do not restamp old frozen jobs, refund spent limits, change tempo or add inference calls.

For new Cantonese drafts, use contextual Hong Kong examples from Resources/hk-spoken-style.json.
Freeze hong-kong-contextual-260. Preserve nouns such as 小說 and uncertainty meanings such as 搞不好.
Do not apply global character substitutions, rewrite saved scripts or add repair permission.

Mac260is installed after guarded replacement. All239related cases, including34focused cases, pass. Four locale Basic and Expert UI checks pass. Installed startup and signing pass;204saved metadata files stay exact.
Mobile implementation and whole-film acceptance of these new controls remain pending. The user accepts the prior823output; that is a separate listening result. See .build/timing260/verification.json.
Guide13/control19 are source copy. Installed iPad248 retains exact guide11/control17. Phone248 packages exact12/18.
Evidence: .build/timing260/shared-rule-contribution.json and .build/timing260/canonical-copy.json.

## Phone model-start controls248

Phone Basic and Production defaults hide incomplete local models. Models retains the download entries.
Name missing engines from a frozen saved request. Default preparation does not silently change a saved GPT engine.
An explicit new-conversion action returns to current defaults and retains old job files and spent limits.
Normal phone248 is installed and launch-verified. Four isolated native cases and direct zh-HK model menus/notice pass.
Five saved project files and two latest job files remain byte-identical. Whole-film acceptance is not claimed.
iPad248 does not adopt this named resume notice or the phone partial-GPT component-size gate.
Guide12/control18 define the shared four-language copy. Mobile caption-only and contextual wording adoption remain pending.
WF-01/02/03/15/16/17 generation and repair permissions stay unchanged.

## Automatic queue source selection248

For new automatic full-video queue work, save the selected source-language policy and a configured fallback, Japanese by default.
Use a valid consensus probe result without another language dialog. If no consensus exists, use the configured fallback.
Record detectedSourceLanguage as absent and sourceLanguageConfirmed as false when the fallback is used.
A configured language is not proof of speech or recognition accuracy. Keep original transcripts and source/caption evidence.
The source-content priority under WF-10 stays exact. Resume retains the saved revision, language and spent budgets.
Legacy saved requests without this revision retain their prior confirmation path. Do not migrate them from current preferences.

The automatic queue reads excluded video IDs before each next handoff. Skip excluded, introduction and completed videos.
Deselecting never deletes media or stops active work. It never creates a launch-time queue replay.
Production defaults disable incomplete local models, using installed files rather than a loaded-runtime flag.
Do not clear existing preferences, trigger downloads or mutate a running/frozen selection.
UI and supported OS service choices are distinct from AI control permissions.

Normal iPad248 is installed. Eight isolated native cases pass, including two cooperative-pause cases. Four locale queue screens pass visual checks.
Complete-film queue and loaded-model pause latency remain unverified. iPhone and desktop have not adopted this queue revision.
Gemma, Qwen and Cosy use file-completeness gates. GPT still uses a deployment marker; partial GPT files remain an open gap.
Counterpart queue behavior review remains open; matching common Help does not prove adoption.
Control items queueSelection, queueSourceLanguage and downloadedPresetModels carry the canonical four-language definitions.
WF-01/02/03/15/16/17 remain unchanged; no generation or repair permission is added.

## Mobile error navigation247

Samuel removes the process-log entry from iPad and iPhone. Preserve internal English diagnostics and saved work.
Errors stay on the active work screen. The review report keeps missing-audio and advisory results.
Normalize a saved terminal page to preview. Desktop Terminal is unchanged.
Guide10-mobile-errors keeps the phone pause-response paragraph scoped to iphone. It does not claim iPad pause uptake.
The iPad UI-only247candidate uses frozen246conversion core. Shared mobile source can separately contain later phone pause changes.
Record each installed package and exact source separately. No workflow permission or recovery budget changes here.

## Report classification, confirmed2026-10-29: `report-classification-246`

The primary report group is Needs dubbing. It contains required target lines whose currently selected delivery is missing, silent or damaged.
An unplanned source fallback for required target dialogue is missing target delivery, even when the original track has sound.
OP/ED, deliberately protected performances and explicit user source choices do not enter this group.
Processing, optional verification, human choice and export application are separate axes. A pending human export choice is not missing audio.

Usable first audible takes, selected-engine generic fills and healthy repaired takes belong in Audio available.
Missing or inconclusive optional verification is not a confirmed failure and cannot move healthy audio into Needs dubbing.
Current wording, language, source or duration evidence can enter Review suggested. A file-span overrun is advisory, not confirmed simultaneous speech.
Keep uncertain results visible as badges or details. Do not certify content, accent or emotion from file presence.
Resolve historical missing-audio labels from the current selected cue/language/engine and recording identity. Preserve real current findings and history.
During local file checks, show checking state separately. Perform PCM reads off the interface thread and reuse per-recording evidence.
This read-only classification grants no generation, repair, extra inspection, resume refund or audio replacement.
WF-01/02/03/15/16/17 and frozen requests remain unchanged. Control item reportClassification is the canonical four-language copy.

Implementation: Normal iPad246 is installed and launch-verified. Six native cases pass. Saved822has0missing,24advisory and210available rows after physical PCM checks. Four locale category views render. Phone247 is installed and launch-verified. Five native classification cases pass; one M4-only case skips. Four locale category views render. Direct phone route/filter checks pass. No phone saved-film acceptance is claimed. Mac259was installed with separate source and fixture evidence. Mac260now retains that classifier and adds the later caption-only control; installed startup and signing pass. Windows remains255. See docs/DESKTOP-REPORT-CLASSIFICATION-259.md.
The phone review identifies absent-audit pending inflation. Desktop review identifies advisory default-list inflation and stale resolved failures.
Phone247 and Mac259 provide separate classification evidence. These checks do not prove full workflow or whole-film alignment.

## Cooperative pause and saved progress247

A manual pause first saves the current safe checkpoint, then requests cancellation of the running operation.
An active timing transaction keeps its existing reserved checkpoint until its safe cancellation path completes.
Cancellation is cooperative. A synchronous model kernel can finish before its runtime observes the request.
Do not start another cue, inference, automatic recovery or queued video after a pause request.
Keep the interface busy until text, separator, recognition and voice cleanup finish. Then save the paused state.
Preserve scripts, selected recordings, frozen source/engine/control policy and all spent attempts. Resume never refunds work.
A pause event records its request time and interrupted phase. A missing historical event cannot prove pause latency.
This change does not authorize a retake, content repair, timing repair, new ASR review or different voice engine.

Private phone247 and later shared source implement this rule. Normal phone247 is installed and launch-verified.
Two isolated native launcher cases pass. Five saved projects and two latest files remain byte-identical.
Frozen iPad246 and UI-only iPad247 retain the prior Pipeline. Do not infer pause uptake from their UI delivery.
Desktop pause implementation is not audited in this bounded phone task. Counterpart source review remains open.
Actual runtime cancellation latency during each loaded model remains a separate device acceptance check.
See mobile/Validation/iphone-pause-menu-247-2026-10-29.json. WF-01/02/03/15/16/17 permissions and budgets stay unchanged.

## Active shared baseline: `shared-workflow-controls-4-language-budget-overlap`

| Rule ID | Shared requirement |
| --- | --- |
| WF-01 | New Basic jobs use the fast standard flow. Expert adds optional controls to that same flow. Extra AI controls default off or zero. |
| WF-02 | Missing, silent, or damaged required dubbing always receives bounded fill attempts. Allow at most two retries after first generation. |
| WF-03 | The default flow keeps the first audible TTS take. AI/ASR findings alone cannot replace it. Mandatory fill handles missing, silent, or damaged audio; optional mutation needs its own explicit permission. |
| WF-04 | Preserve each requested control through all initializers and resume. One control must not silently switch another on or off. |
| WF-05 | Inspection and mutation are distinct permissions. Review alone reports findings; a separate enabled repair control authorizes recording changes. |
| WF-06 | Content repair does not enable timing repair. Timing repair does not enable global content or visual review. |
| WF-07 | Freeze finite per-stage counts and whole-job time limits. Reserve before inference. Resume never refunds spent budgets. |
| WF-08 | Use the selected TTS engine by default. Cross-engine and system-voice fallback need separate explicit permission. |
| WF-09 | Attempt final output with saved valid work and report genuine missing target dubs. Storage, source, or encode failure stays an explicit error. |
| WF-10 | A determines meaning and B supplies auxiliary evidence. Basic and Expert Automatic use subtitles > speech with readable text subtitles, otherwise speech > OCR. |
| WF-11 | Preserve OP/ED and nonverbal performances. A subtitle gap does not authorize new translated dialogue or prove silence. |
| WF-12 | Cantonese uses spoken Hong Kong grammar and Traditional Chinese. Preserve source meaning and keep source captions separately selectable. |
| WF-13 | Keep source, subtitle display, and delivered audio clocks distinct. Do not drop captions because audio or caption intervals overlap. |
| WF-14 | Each platform proves output decoding, audio/caption coverage, timing, and listening separately. Metadata alone is not acceptance. |
| WF-15 | Freeze the duration choice. Off keeps full first takes at source onset, with overlap and a held final frame if needed. On permits one measured timing rewrite. Source clocks, captions, and internal pauses stay unchanged. |
| WF-16 | Budget the first translation against original speech time in Cantonese, Mandarin, and English. Use language-aware soft limits; preserve complete meaning. This is first-draft work, not an extra review or retake. |
| WF-17 | Excessive audible-overlap repair is an independent Expert option, default off. Only more than two seconds of confirmed simultaneous target speech permits one faithful rewrite and retake per affected line. Silence and empty gaps do not trigger it. |

WF-05 is the target for independent controls. It is not a claim about installed iPad build 190 or desktop build 245.
If a combined control intentionally inspects and repairs, its label and saved permissions must state both actions.
Do not call a combined control inspection-only. Record that mapping as a difference until the shared interface is agreed.
Required missing-audio fill under WF-02 is independent of optional content inspection and repair.
An audio presence check is not transcript, language, or pronunciation certification.


### First-draft length and optional audible-overlap repair, confirmed 2026-10-28

This section is the active common target. It is not an installed-feature claim.
It applies to Hong Kong Cantonese (`yue`), Mandarin (`zh`), and English (`en`).
No separate platform definition may override it without a recorded user decision.

**Basic and Expert share the same baseline.** New untouched Basic jobs use one first generation per required line.
First-generation translation and its length guidance are part of the baseline, even with zero optional AI checks.
Keep the first audible recording. Do not retry it because an ASR result is uncertain, a score is low, or its duration differs.
Only missing, silent, or damaged required audio enters mandatory bounded presence recovery under WF-02.
A missing clone reference uses the selected-engine fallback within that same allowance.
Do not silently treat Japanese source continuity as completed Cantonese, Mandarin, or English dubbing.
Expert exposes additional controls. Zero content checks means no added content inspection or content-driven retake.
A check count does not itself authorize replacement. Full visual review remains separate and default off.
Changing the interface mode alone does not grant permissions, rewrite a saved job, or renew its allowances.

**Write a short first draft in the selected language.** Use the original speech onset and end as the timing target.
Use selected readable authored captions as the primary wording by default; speech supplies timing and reference evidence.
For other source choices, follow WF-10. OCR is not a speech clock.
Do not derive the speech budget from a long subtitle display interval.
Retain original captions, source text, and clocks. Record an explicit fallback when a speech clock is unavailable.

Send the own-turn meaning, target language, source seconds, context, protected names, and a soft spoken-length range in the first translation request.
Preserve action, negation, conditions, relationships, numbers, names, emotion, and intended repetition.
Prefer a direct spoken clause. Do not expand short English reactions into explanations or add stage directions.
Do not merge neighbouring dialogue or duplicate a shared caption in several turns.
If the full meaning exceeds the estimate, keep the complete meaning. Do not delete words to pass a numeric limit.
This first-draft guidance does not add a second translation pass or a second TTS call.

Estimate spoken duration in language-appropriate units:

| Target | Draft-length evidence |
| --- | --- |
| Hong Kong Cantonese | Estimate spoken syllables. Chinese character count is only a proxy. Expand numbers, abbreviations, and foreign names as they will be spoken. |
| Mandarin | Estimate Mandarin spoken syllables with its own rate profile. Do not reuse a Cantonese rate as an exact Mandarin rate. |
| English | Use spoken word and syllable estimates, including number, abbreviation, and proper-name readings. Chinese character limits do not apply. |

Use a versioned rate estimate for the target language, engine, and reference voice when valid prior samples exist.
Reuse existing measured recordings. Do not synthesize calibration samples for each new line.
Measure complete takes after safe edge-silence handling; retain meaningful internal pauses and quiet endings.
Without usable history, use a documented conservative language prior and label the estimate uncertain.
Record the estimator revision, rate source, source seconds, planned range, and actual generated duration.
One universal characters-per-second number is not a cross-language rule or a timing guarantee.

Aim first at the original speech interval. Do not enlarge the requested script because overlap is allowed.
A free following gap can absorb a modest natural tail. It is tolerance, not permission to expand the dialogue.
Default export keeps fixed source onsets and full first takes, including allowed target-to-target overlap.
Preserve source, subtitle-display, and delivered-audio clocks separately.
Retain separated background music and effects under target tails. Apply WF-11 and the existing protected OP/ED policy.

**Optional Expert control:** Repair excessive audible overlap. Default off. The initial threshold is two seconds.
This is separate from strict original-duration limiting, content checks, content repair, and full visual review.
Selecting it authorizes only its targeted timing rewrite. It does not enable those other controls.
With it off, do not shorten or retake a voiced recording solely because it overlaps another generated line.

Measure placed target recordings on the same target-language track after safe edge-silence handling.
Compare the current take with subsequent target takes. Do not compare the original and target language tracks as if they were one mix.
Count the union of confirmed simultaneous audible-speech intervals. Do not count one instant twice when three takes overlap.
Exactly two seconds does not trigger repair. More than two seconds can trigger the optional operation.
A duration overrun of two seconds is not automatically two seconds of audible overlap.
Exclude confirmed silence and empty timeline gaps. Preserve quiet words, uncertain low-level tails, and intentional pauses.
PCM energy alone cannot prove that an interval is speech. Uncertain classification produces a report, not forced shortening.
If no later target speech is audible, this option does not trigger, even when the current take is long.

For a confirmed trigger, request one meaning-preserving shorter target script and one same-voice retake.
Keep the source clock, language, speaker reference, original script, and first recording.
Do not use tempo acceleration or cut word endings to pass the threshold.
Reserve the optional operation before inference. Freeze one operation per line and the whole-job time allowance.
The optional operation has a separate counter from mandatory missing-audio fill and content checks.
If the retake is invalid, silent, or does not improve the overlap without losing meaning, retain the first audible take and report it.
Do not repeat the overlap repair until it passes. Resume does not grant another operation.
Strict original-duration limiting remains a separate explicit choice. If it already owns the line's timing rewrite, do not add another overlap rewrite.
A final take beyond the movie end still follows WF-15; it is not evidence of overlap with a later line.

Examples for a three-second source line, with timing-limit controls otherwise off:

| Measured output | Default result | Optional overlap repair result |
| --- | --- | --- |
| Take lasts five seconds; the next take starts at six seconds | Keep it. There is no target overlap. | No rewrite. |
| The same five-second take; the next audible take starts at four seconds | Keep it. Audible overlap is at most one second. | No rewrite. |
| Confirmed simultaneous target speech totals 2.4 seconds | Keep the first audible take. | One bounded rewrite/retake is permitted. |
| File intervals overlap for three seconds, but confirmed simultaneous speech totals 0.6 seconds | Keep the first audible take. | No rewrite. |
| Required recording is missing, damaged, or silent | Mandatory bounded fill, regardless of optional count 0. | Same presence rule; the overlap option is irrelevant. |

**Desktop status, 2026-10-29:** Mac and Windows0.25.0/build253 are installed in dist. Focused execution, source identity, and actual FFmpeg export checks pass. Windows native inference, real optional overlap ASR/TTS, and whole-film listening remain open. See `DESKTOP-WORKFLOW-0.25.0.md`.
iPad223 implements the local-AI first-request budget and independent overlap option. Fourteen focused native cases pass.
Normal223 is installed and launched. Actual E4B requests and synthetic native export have separate evidence.
Real optional overlap recognition plus TTS and whole-film acceptance remain open.
Apple system translation cannot receive the numeric prompt. Its duration-guidance mapping remains pending.
Normal phone224 is installed. Its separate receipt records18 native cases and three final boundary cases.
Phone optional overlap recognition plus retake and whole-film acceptance remain open.
See `mobile/Validation/ipad-workflow-build223-2026-10-28.json` and `docs/IPAD-WORKFLOW-223.md`.

Acceptance must cover all three target languages, silence gaps, quiet tails, exact two-second boundaries, overlapping subtitles,
multiple target tracks, failed retakes, count zero, independent permissions, save/resume, and unchanged spent allowances.
Use real bounded media and model tests after deterministic cases. Metadata alone is not full-film or pronunciation acceptance.

### Own-turn caption ownership gate, prepared 2026-10-29: `own-turn-caption-ownership-242`

This section states the shared target and the iPad source change. It is not an installed or accepted feature claim.
It serves the existing rule "Do not merge neighbouring dialogue or duplicate a shared caption in several turns."

**Shared target.** Before text-to-speech uses a translated script, each required line must own its content.
One deterministic check compares the target script with the saved source captions of the same context window.
A contiguous alphanumeric span of four or more characters that appears in exactly one neighbouring caption,
and not in this cue's own source, is an own-turn finding. The check uses no model and scores no quality.

**Preserve rules.** A span present in this cue's source is never a finding. A span present in more than one
source in the window is never a finding. That keeps rolling captions, shared lines, songs, intentional
repetition, and separate speakers valid. The check never deletes text globally and never rewrites saved takes.

**Bounded correction.** When the finding crosses an authored-caption boundary, the platform may run one
re-translation per cue on a first draft only. The retry names the forbidden clause and keeps the first draft.
When the retry is invalid, still crossing, or already used, keep the first draft and report the finding.
The retry uses a saved per-cue counter. It is not the optional overlap repair, not a content check, and not a
recording retake. First-take audio, source clocks, selected references, and spent budgets stay unchanged.

**iPad source mapping, 2026-10-29.** `StandardProject.subtitleLeakageIssues` and its attempt key implement the
check. `StandardPipeline.translateCue` runs it after the first draft and before TTS. `GemmaRuntime.translateStandard`
accepts `forbiddenClauses` for the one retry. Two deterministic native cases cover the frozen cue413/414
repetition and the shared/repeated negative fixtures. Compile, targeted test result, package, installation, and
listening acceptance are recorded separately below and in the execution receipt.

**iPad execution state, 2026-10-29.** Normal build 242 is compiled, signed, and installed on Samuel's M4 iPad
`00008132-000478D23C69001C`. The launch check passes. Two deterministic native cases pass with zero failures. The
saved job pointers for One Piece, Ranma, and Ninja stay byte-identical across the install. No control-guide copy
changes. Desktop and iPhone do not adopt this gate. Real-request proof and human listening acceptance are still
open, because no fresh user-video conversion ran. Receipt:
`mobile/Validation/ipad-own-turn-gate-242-2026-10-29.json`. Working evidence: `.build/ownturn242/`.

**Desktop and iPhone mapping remains open.** Desktop keeps its separate `script_fit.copied_neighbour_content`
guard. Neither platform has adopted this gate. Do not claim shared execution from this section.

**Execution follow-up244, 2026-10-29.** Normal244 is installed and launch verified on M4.
The correction now accepts priority caption-primary origins. One saved reservation is enforced without resetting old spent values.
A fingerprinted first draft and resolution survive cancellation/resume. Immutable owner counts prevent false uniqueness and missing-index failure.
Ten injected execution cases and one actual Gemma correction pass. The real-model case injects a frozen bad draft;
it does not reproduce a complete new film request. Five stale fixture/guide expectations now pass; two older timing cases remain open.
The242full regression receipt is still failed and its zero-test baseline is inconclusive. Do not claim a clean full suite.
Exact canonical manual6/control15 is installed. First-take audio, source clocks, optional permissions and spent recovery budgets do not change.
See mobile/Validation/ipad-own-turn-followup-244-2026-10-29.json. Pacing, alternate budget mapping and full-film listening remain open.

**Desktop source follow-up258, 2026-10-29.** New submissions freeze ownTurnGateRevision. Resources/own_turn.py checks authored embedded or external primary captions, with NFKC and native Hans-to-Hant normalization. It excludes speech-primary policy, saved script fields, disabled cues and deliberate source preservation. A unique4–12character neighbour span can request one correction. The persistent per-cue/language reservation is written before inference. The first draft and selected resolution remain available after cancellation or replay, including when a new model reply differs. The correction prompt excludes full neighbour captions. An invalid, failed or spent correction retains the saved first draft and reports a hint in all three output languages. Fast, Normal, alternate-language and full-review first-draft paths are connected. This does not change the first audible take, source clocks, optional checks or spent voice budgets.25focused cases and116related regression cases pass. Package, installation and whole-film listening are recorded separately. Pacing calibration is still an open review; no automatic tempo or new retake is added.

### Required caption target delivery, build 205

New jobs freeze `subtitle-target-presence-205`. Old jobs retain their existing policy and spent allowances.
A valid target-language draft survives advisory name and meaning findings. Record the findings without removing speech.
New priority-source prompts do not use the legacy fixed franchise name table.
A Chinese primary caption can supply Traditional Chinese wording if bounded translation produces no usable target script.
Mark that retained wording for colloquial review. Do not invent a translation from unrelated audio or context.

Keep the first audible take. Missing audio permits at most three generation calls in total per line.
A missing clone reference permits one generic fill in the selected engine within that total.
This mandatory presence exception cannot replace an audible take or enable another engine or a system voice.
Preserve original clocks, source captions, immutable recordings, and reserved counts.
An output with target gaps must report those gaps. A saved file is not complete target-language acceptance.

New subtitle local clocks use Whisper once per exact cached window, not hidden Apple speech recognition.
A failed local clock retains authored display times as an explicit fallback. It cannot erase the authored caption.
A truncated speaker reference requires a transcript of that exact audio clip before cloned generation.
Generation requests natural pace and expression from that reference. This is not verified prosody matching.

When an allowed target tail enters an uncaptioned source interval, use its separated music bed during the overlap.
Outside that overlap, retain the source. Protected OP/ED stays unchanged.
Separation can retain vocal residue. Missing or failed separation remains an explicit limitation.

New required Whisper source windows freeze `bounded-eight-short-windows-205`.
Round one decodes the full window. Round two uses eight fixed parts, at most 3.75 seconds each.
No recursive split, third round, or resume refund is allowed. Legacy half and quarter policies remain frozen.
The actual late Ninja Cat window is 1357.62–1387.62 seconds, separate from the earlier 216-second defect.

Implementation and test state: normal iPad 205 is installed on M4. Nine distinct focused cases pass.
The actual late Ninja Cat window and One Piece caption-to-Cosy generation pass with isolated copies.
Evidence: `docs/IPAD-REQUIRED-TARGET-205.md` and the private build 205 receipt.
Phone224 consumes completed205 rules and passes one actual exact-reference Whisper/Gemma/Cosy case.
Its older failed source window remains a recorded failure. Desktop adoption and whole-film acceptance remain separate.
Whole-film coverage, listening, meaning, pace, and OCR acceptance remain pending on every platform.

### Long displayed caption review, 2026-10-29

Samuel reports a desktop Ninja subtitle at about187seconds that combines multiple Pizza Cat order and greeting lines.
He reports broadly meaningful dubbing with roughly matching timing. Do not infer a bad take from a long caption alone.
The desktop owner must compare saved source units, frame/OCR identities, translation groups and final subtitle clocks.
Distinguish dialogue grouping from caption export merging. Keep accepted audio while this cause remains undecided.
Any display-only split needs witnessed source/caption boundaries. Do not assign timestamps from character count.
iPad and phone counterpart risk is reported, not verified from the screenshot. Separate source and output evidence is required.
Screenshot: <home>/Desktop/Screenshot 2026-10-29 at 22.55.18.png.

### Unconfirmed source handoff251

Complete the remaining reserved round for short windows in the quarter-first policy. Two timed halves are sufficient below eight seconds.
Use at most two reserved rounds and the existing eight-call ceiling. Do not renew an exhausted allowance.
After an eligible bounded timestamp, repetition or decoder-time failure, retain the exact input interval as unconfirmed.
Cache the empty timed result with its source/model/audio identity, explicit reason and unconfirmed-source-window-251 strategy.
Do not label it no-speech, claim witnessed timestamps or use text-only repetition as source dialogue.
Continue the existing selected-content workflow. A usable selected subtitle or OCR text can supply missing primary content.
A selected speech/OCR or OCR/speech workflow activates picture-caption OCR independently of optional Expert picture assistance.
Caption OCR detects its language independently of the soundtrack. Keep name-only requests on their prior explicit language.
Only that positive content can release the automatic original-preservation gate. Missing evidence stays unconfirmed in Review.
Protected OP/ED, user choices and first audible takes remain exact. Cancellation, file changes, storage and unsupported errors still stop.
Legacy half/quarter/eighth requests do not adopt this handoff. A quarter-first draft can use its unused reserved round and valid cached chunks.

Actual isolated evidence: The5.548-second Ninja window fails its second timed half. Untimed decoding emits unbounded repeated 好きよ text.
Neither result is a usable complete transcript. Local Mac sound classification does not prove singing; do not extend ED from this evidence.
The source fix and native fixtures are in progress. Installed M4 remains250 until a separate251receipt exists.
Phone and desktop implementation and whole-film acceptance remain pending.

### Quarter-first bounded source recovery250

New iPad requests freeze bounded-quarter-first-eight-call-250. Keep old requests and identities unchanged.
Round one decodes the full source window. Round two first tries four fixed quarters.
Split only a failed quarter into two equal parts, once, for the existing repetition, timestamp-limit or decoder-timeout errors.
Keep successful quarters. Stop after at most eight decoder calls in the complete second round.
Reserve each round before work. Resume retains both reservations and never grants a third round.
Do not recursively shrink, switch recognizers, change translation priority or treat an undecided result as silence.

The new Ninja job9095DA9F fails at216.3–246.3seconds with the legacy frozen eighth policy.
An isolated exact audio copy produces11timed units with four quarters. Eight eighths fail on their first part.
The complete diagnostic takes93.185seconds. Timing output is not transcript accuracy or listening acceptance.
Six native bound, cancellation and legacy-policy fixtures pass with zero failures in0.032seconds.
Normal M4250 is installed and launch-verified. Exact guide16/control19 are packaged. Whole-film acceptance remains pending.
See mobile/Validation/ipad-ninja-quarter-first-250-2026-10-29.json.
Phone and desktop mapping remain pending. Their source or installation cannot be inferred from this paragraph.

### Missing text-subtitle selection and source recognition, 2026-10-28

An explicit speech/subtitle workflow can find no readable selected text subtitle.
In that case, select speech > OCR and show the effective workflow notice.
Burned-in captions are picture content. They are not selectable text-subtitle tracks.
Keep the automatic defaults: subtitles > speech with text subtitles, OCR > speech without them.
A missing track and a corrupt explicitly selected file are different errors. Do not hide file-read errors as absence.

A failed source-selection initialization may have no frozen workflow yet.
Only that incomplete pre-script, pre-recording state can finish selection from the current user choice.
Do not rewrite an initialized workflow, translation, or take. Preserve all recognition and repair allowances.
Record the missing-text fallback reason and effective workflow in the new checkpoint.

New iPad jobs freeze `bounded-four-quarter-windows-203` for required Whisper source recognition.
The first round uses one full window. The second round uses four fixed quarter-windows, at most 7.5 seconds each.
Both rounds reserve before decoding. There is no recursive shrinking or automatic third round.
Legacy jobs keep two half-windows. New code does not renew a legacy exhausted reservation.
Bind cached source chunks to the frozen recovery policy. Preserve legacy cache identity when the policy is absent.
An error must identify the failed source window and distinguish decoding failure from an exhausted saved allowance.
The diagnostic record retains the underlying technical error. User notices use the selected interface language.

The observed Ninja Cat job first failed source selection, then exhausted Whisper at 216.3–246.3 seconds.
That old checkpoint has no finalized source workflow. A dropdown change alone cannot restore spent recognition attempts.
Build 203 passes five M4 tests. The isolated failed 30-second window succeeds in four quarter decodes.
The actual model test takes 87.092 seconds. Normal build 203 is installed on M4.
The old checkpoint and attempt ledger remain byte-identical. Desktop counterpart inspection remains pending.
This required source-recognition path is separate from optional AI repair under WF-01 and WF-07.

### iPad foreground video queue, 2026-10-28

Build 201 adds sequential handoff after a full-video automatic conversion finishes.
This implements the missing iPad batch scheduling path under WF-04, WF-07, and WF-09.
Use the visible video-list order after the current item. Do not wrap to earlier items.
Skip the bundled introduction and completed jobs. Do not regenerate completed output.
Release the current models and save its checkpoint before starting the next item.
Resume an unfinished saved job with its existing controls, model choices, and spent allowances.
New jobs inherit the completed job's dubbing settings. Resolve their source workflow from their own subtitle type and saved defaults.
Short-range tests, single-line retakes, and manual exports do not authorize another video.
Pause, errors, background entry, and missing resources stop automatic handoff.
Do not run two video jobs together. Do not repeat a completion event or retry a failed handoff automatically.
Cold launch still opens Welcome and never resumes this queue without user action.
Phone build 202 uses the same cleanup and completion gates in its active conversion workspace.
Three native phone queue cases and the route gate pass. Real multi-video phone acceptance remains pending.

The iPad implementation passes three isolated M4 tests, including the real pipeline cleanup and handoff.
Normal build 201 is installed on M4. Ranma checkpoint bytes remain unchanged. Full-film batch acceptance remains pending.
Desktop scheduling is separate. This task does not certify desktop queue parity or change its implementation.

### Shared compact control presentation, 2026-10-28

The product interface uses written Traditional Chinese (Hong Kong), not spoken Cantonese grammar.
Cantonese translation and generated dialogue retain spoken Hong Kong grammar under WF-12.
`WORKFLOW-CONTROLS-GUIDE.json` revision `workflow-controls-guide-6-source-fallback` retains the revision 5 common panel title and short warning.
Use the production-slider and repair-wand icons in the panel header.
The repair section is named "Additional AI repair". It contains optional settings, not mandatory conversion repair.
Show one short warning above the controls. Keep labels, switches, and values on the control rows.
Do not place explanatory paragraphs under individual controls. Put detailed behaviour in the existing guide.
Keep each platform's supported controls and permissions. Presentation does not enable or disable any setting.
The workspace assistant has no caption and no duplicate overall progress bar.
Only the screen saver shows the assistant's overall progress bar. Settings can preview that screen saver.
Embedded work-step progress remains inside the artwork. The separate conversion status card remains unchanged.

The iPad compact interface is delivered in normal build 201 on M4. Compile, locale, guide, and browser checks pass.
Native compact-panel visual acceptance remains pending.
Desktop Mac build 252 implements and installs the compact header. Four-locale browser checks pass at two widths.
Windows packaging and native visual acceptance remain pending.
Selected-line editing and mixing use context drawers. Caption-only edits preserve the selected recording.
The source-fallback text added in guide revision 6 does not prove desktop source-fallback implementation.
That counterpart remains pending. Desktop Help states this limitation.
No workflow permission, saved request, or spent budget changes in this presentation task.

### Standard first-take clarification, 2026-10-28, build 196

Samuel reaffirmed one Standard rule for desktop, iPad, and iPhone during the phone test.
Keep the first TTS recording when it has audible audio. Do not use Cantonese AI/ASR ratings as selection gates.
Mandatory missing/silent checks remain active when optional AI/ASR review is off.
Standard review is optional and report-only. It defaults off. Explicit Expert repair permissions remain separate.

The default accepts overlap. A timing conflict must not silently change an audible Standard take to original speech.
Play the whole take from its fixed source onset. Preserve original sound in retained intervals as part of the mix.
This does not label an unrecognized interval silent and does not authorize translating a subtitle gap.
When a take ends after the selected range, hold its last video frame until the take ends.
Keep the source range frozen. Record source duration and output duration separately. Never accelerate or truncate the take.
This clarification supersedes the older off-state hard-boundary wording below. Strict duration control retains its separate limits.

Three report bands mean no obvious issue, listen suggested, and listen first. They are listening priorities, not quality certification.
Unchecked, inconclusive, and stale evidence have a separate state. Do not classify them as poor speech.
Each band retains the selected first recording. Samuel decides acceptability by listening.
Use the shared four-language guide, revision `workflow-controls-guide-4-first-audible`, for these labels and explanations.
Saved jobs retain their review settings and spent budgets. A setting change does not renew or silently enable a saved review.

Native build 196 source implements this mapping for the shared iPad/iPhone code.
Phone build 196 is installed. Its real saved-take remix delivers all 27 first recordings with zero source fallbacks.
Full video/audio decoding and increasing frame timestamps pass. All source recordings and spent budgets remain unchanged.
The sample keeps optional review off. Human listening and real optional scoring remain pending.
Evidence: `mobile/Validation/iphone-standard-build196-2026-10-28.json`.
The existing 17-dub/10-original phone output fails this rule and remains preserved as failure evidence.
Desktop source `repair-fallback-permissions-249` still checks fit and rejection during first-take choice; counterpart integration is pending.
No desktop or iPad installation or acceptance is implied by the phone test or this document.

The iPad build 197 source applies the regular frame clock when export adds a held final frame.
The focused M4 test decodes the full fixture and requires strictly increasing presentation timestamps through the tail.
It also checks the complete audio duration, unchanged first recording, and zero source fallback.
This is isolated export evidence. M4 whole-episode acceptance remains pending.

### Phone listening defect, 2026-10-28, build 196

Samuel rejected voice consistency and emotion in the phone sample. Export checks still pass.
The saved job has two original-reference takes and 25 `yue-bright` generic takes.
Failed local-clock calls erase existing Whisper hints. The Cosy reference guard then rejects the unconfirmed transcript.
This is a native source-reference defect. It is separate from optional Cantonese output quality review.
The target keeps uncertain timing separate from usable source-reference evidence. A failed clock must not prove silence.
The build 170 decision already uses Whisper for source text and native sentence clocks in new jobs.
Bounded subtitle timing and source-reference checks must follow that source provider, with no hidden Apple dependency.
The current local-clock Apple call remains an implementation defect. Reading and optional output review are separate scopes.
No implementation changed in this diagnosis. Native correction and short listening acceptance remain pending.
The shared iPad source needs the same correction review. Desktop needs separate inspection.
Evidence: `mobile/Validation/iphone-voice-reference-build196-2026-10-28.json`.

### Review and repair combinations

| Content inspection | Content repair permission | Required behaviour |
| --- | --- | --- |
| Off | Off | Keep the first audible take. Fill genuinely missing or silent audio. No optional content retakes. |
| On | Off | Inspect within saved limits. Report findings and retain the take. No automatic replacement for a review finding. |
| Off | On | Preserve the repair request. Use existing confirmed evidence or bounded targeted checks for suspect cues. Do not enable whole-film review. |
| On | On | Inspect, then perform only authorized bounded repairs for confirmed defects. Keep unconfirmed takes and all history. |

Repeat this matrix with timing repair off and on. Also test translation review, endpoint checks, and gap analysis independently.
Count review stages, raw model calls, format retries, and generated candidates separately. A pass count is not a model-call count.
Report an exhausted allowance honestly. Do not reopen a stage through an alternate initializer or final export.

## Final fallback permission contract, 2026-10-28

This target refines WF-03 through WF-09. New desktop requests freeze `repair-fallback-permissions-249`.
Saved requests keep their original revision and consumed limits. Do not restamp a resumed job.

1. Always attempt required missing or silent audio fill, at most twice after initial generation.
2. Review alone reports findings. Optional actor repair needs AI repair permission.
3. Duration control remains independent. Strict mode permits one measured shortening pass. It still applies during final choice.
4. The final selector does not enable optional content review or actor repair.
5. `first-take` retains a usable first recording. It never authorizes generic or native generation.
6. `source` uses source speech only after unresolved permitted repair. It never authorizes generic or native generation.
7. `generic` explicitly permits one final selected-engine bank-voice trial, even when AI repair is off.
8. Alternate engines require AI repair and their separate enabled choice. Generic alternate trials also require `generic`.
9. Installed native voices require AI repair, `generic`, and their separate enabled choice. Never download a voice implicitly.
10. Reuse hash-bound recordings and persisted counters. No stage may replenish its allowance during resume or export.
11. An unusable strict first take cannot bypass its boundary. Preserve source continuity and report the missing target dub.
12. Empty recognition results do not prove silence. Keep audible unrecognized takes as advisory findings.
13. A failure on old audio bytes cannot reject a different current recording. Keep the old evidence for inspection.

The shared product copy is `failedVoiceFallback` in `WORKFLOW-CONTROLS-GUIDE.json`, revision `workflow-controls-guide-4-first-audible`.
Desktop source implements these gates. Synthetic acceptance and installation are recorded separately in the desktop handover.
iPad must inspect its corresponding finalizer and candidate paths. This remains pending until it records execution evidence.
Do not treat this desktop patch or an outbound message as verified cross-platform alignment.

### Japanese character names: separate content and audio controls

The app focuses on Japanese animation. Use evidence from the current movie, not an external or fixed franchise character list.
Keep authored subtitle spellings first. Match Japanese names, readings, Chinese variants, and English aliases within that work.
A known name is not proof of speaker identity or a word-level audio boundary.
Desktop `name_evidence.py` now accepts stored primary-language aliases when it protects names during rewrite.
The iPad build 195 alias correction has separate device evidence. Neither correction implements name-audio splicing.

The proposed `Keep Japanese name audio` control defaults off. Off means complete target-language TTS, including names.
On may splice only source name spans with reliable acoustic and lexical boundaries.
Keep the complete TTS if boundaries, speaker, source isolation, or target insertion cannot be verified.
Never cut by character ratio. Never remove a target word before a complete replacement is ready.
Do not preserve a whole Japanese sentence to retain one name. Do not infer sound timing from a name dictionary.
This audio option is pending short-clip and listening validation on both platforms. Do not expose a working claim yet.

Samuel cancelled the external/prebuilt index proposal on 2026-10-28. Do not integrate AniList or package a fixed franchise table.
Use the existing bounded AI glossary step. Quote names from the selected primary cue, with same-row evidence.
For Chinese primary text, preserve its name spelling after Traditional Chinese conversion.
Do not pair a source name with an unrelated row's Chinese spelling. Do not infer names from filenames or model plot memory.
Cache the result by current source text, model, and policy. Store cue evidence indices and keep identity uncertified.
An empty or failed glossary must not block complete translation or remove speech.
Desktop implements `primary-name-evidence-249` inside the existing AI call. iPad integration remains pending.
Tests use injected model responses. Real-model name extraction and listening still need separate acceptance.

### Desktop 249 scope after the mobile first-take clarification

The new mobile WF-03/WF-15 clarification arrived while desktop 249 was in packaging.
Desktop 249 still checks first-take fit against retained source/OPED boundaries and the selected movie end.
It does not extend video through a held final frame. This is an open counterpart defect, not verified alignment.
Do not claim that the desktop implements unrestricted full-take delivery across these boundaries.
The desktop Help records this limit. It omits mobile-only report controls until their desktop execution mapping exists.
The exact shared source copy remains intact. Shared source requirements do not certify installed behaviour.
Resolve this in a separately bounded desktop scheduling/mixing/export patch with actual media and pause/resume tests.
Keep the original source range and recordings. Test final-frame extension, protected original audio, multiple tracks, captions, and final-only export.

### Desktop assistant activity presentation

Desktop preserves nine original characters with visible faces and eyes. Do not replace them with iPad silhouettes.
Use four activities: computer work, listening and notes, translation, and dubbing.
The preview-off surface and Settings preview use the same scene and animation component.
Mac 0.24.98/build 251 uses animation-only assistant scenes at Samuel's direct request.
Remove visible activity captions, step circles, percentages, and duplicate assistant progress bars.
Keep the separate main conversion progress card. Do not change saved conversion state to animate the assistant.
Pause, hidden documents, and reduced-motion preferences suppress activity motion.
Idle keeps the original desktop character animation.

The built-in generator corrected Shion's listening hands. A scene-specific image override preserves her other three original cells.
All nine characters use fixed hand regions and subtle head and breathing motion. No fast finger distortion is used.
WebGL and Canvas2D use the same image selection and hand policy.
Checks and source paths are in `docs/DESKTOP-ASSISTANT-HANDS-251.md`.
Artwork and movement do not certify model execution or output quality.

The current iPad proposal retains embedded step progress. Desktop removes it under the direct user request.
Do not claim exact assistant presentation parity. Desktop build 252 separately implements the compact AI-control header.
This patch does not change conversion, first-take selection, overlap, repair, or export rules.

### iPhone239 presentation and common manual uptake

Normal239 is installed and launched after Samuel explicitly resumes phone work.
The package contains exact operation guide4 and control guide15. Six native invocations across four cases pass.
Eight final four-language manual captures and18final canvas captures pass.
The final shared renderer removes the tested native atlas-edge strip. The source bitmap has no isolated strip.
Normal app search for Whisper opens First setup and models. The moon opens seated rest without progress.
General Preferences removes duplicate fallback. Basic and Expert production controls remain unchanged.
Reading background preparation checks hardware and model readiness at both boundaries. System narration remains available.
The saved One Piece checkpoint remains byte-identical. All app preferences match the fresh baseline after restoring Standard.
Only the StoreKit polling timestamp advances. No conversion, repair, export, saved request or spent budget changes.
At that installation the phone core remained233/231 with236controls, and no234core/cache uptake was claimed. Normal241 later adopts that core; see the iPhone target delivery241 section. Whole-film acceptance remains open.
The desktop257 character-style audit remains separate and open. This delivery does not close its five corrections.
See mobile/Validation/iphone-assistant-manual-239-2026-10-29.json.

### Phone playlist drawer243

Phone243 removes the duplicate Import videos drawer entry. Edit and preview retains source import and management.
The renamed Playlist entry first shows saved outputs, then opens the selected player.
Only phone navigation and initial selection change. Conversion and frozen permissions stay exact to the recovered242baseline.
Operation guide6 supplies four-language phone navigation and one separately scoped iPad draft-ownership section.
Control guide15 stays unchanged. The phone excludes the iPad-only section.
Normal243 is installed and launched. Direct drawer, playlist/player and zh-HK manual navigation/search checks pass.
Five saved project files and two latest pointers remain exact. Configuration settings are unchanged.
Only StoreKit polling time and one sub-millisecond normalized playback position differ.
See mobile/Validation/iphone-playlist-drawer-243-2026-10-29.json. Other platform installations retain their own records.

## Cross-platform alignment register

Snapshot: 2026-10-28. This register separates the shared target from recorded implementation evidence.
Update the affected rows every time either line changes a workflow.

| Item | Desktop evidence or mapping | iPad evidence or mapping | Alignment and next action |
| --- | --- | --- | --- |
| 822 pacing and repeated-clause audit | Owner receives source-review request. No fix or acceptance claim. | Frozen complete job has long takes and a verified adjacent partial-clause repetition. See CROSS-PLATFORM-822-PACING-REPETITION-REVIEW.md. | Phone owner reviews its actual core separately. Keep original takes, source clocks, optional-off permissions and spent budgets. |
| Own-turn caption ownership gate242/244 | Mac258 is installed and tested; new requests only.26focused cases and116related regressions pass. Full-film listening remains pending. | Normal244 is installed. Ten injected execution cases and one actual Gemma correction pass. Priority origin, one saved retry and resume defects are fixed. Saved jobs remain exact. | Phone243 has not adopted244. The real-model fixture injects its initial bad draft. Full fresh-film requests and listening stay open. |
| Required target/source separation234 | Desktop255 implements its adapter, clock and disclosure corrections with separate evidence. | Fifteen unique M4 cases pass, including actual generic inference and decoded translated-caption export. Normal234 is installed; three real checkpoint files remain byte-identical. | Normal phone241 is installed with the adopted234 core, bounded cache and coverage two. Fifteen unique native cases pass with zero failures; two saved job folders and47preference keys stay unchanged. Whole-film coverage and human listening acceptance remain open. |
| Original delivery report233 | Desktop255 owns separate coverage correction; acceptance pending. | Shared report presentation source prepared. Native package/install pending. | Normal phone233 installed. Native finalizer/report fixture and direct controls pass. No generation gate change. |
| Automatic source selection231 | Owner notified; implementation and acceptance pending. | Source prepared. Basic and Expert Automatic share fixed text-subtitle detection. Tests and install pending. | Normal phone233 consumes231. Native import/capture/resolve and manual controls pass. Full neural prepare and whole-film acceptance remain pending. |
| Mobile Expert-only purchase229 | Desktop open-source access is unchanged. | Normal229 installed. Two native access/menu tests pass; guide11 is exact. | Normal phone227 is installed. Sixteen capability/access combinations and both actual unpaid entry checks pass. Guide11 is common copy. Real transactions remain open. |
| Initial model preparation227/245 | Desktop setup is unchanged. | Normal iPad245 is built, strictly signed, installed and launch-verified. Gemma, CosyVoice, required Whisper and HTDemucs are default; Qwen/GPT remain manual. Three latest job files stay exact. M4 scope execution and clean-device download remain untested. See mobile/Validation/ipad-default-models-245-2026-10-29.json. | Normal phone245 is installed. Three focused native cases and existing-file one-click completion pass. Guide8 renders current setup text. Five jobs, two pointers and all configuration values remain exact. Only StoreKit polling time advances. Full clean-device download and lower chapter-row remote hit review remain open. See mobile/Validation/iphone-default-models-245-2026-10-29.json. |
| Cooperative pause247 | Not audited in this phone task. Counterpart mapping remains open. | Later shared source requests safe cancellation and preserves checkpoint/budgets. Frozen normal246 retains its previous Pipeline; no M4 pause acceptance is claimed. | Normal phone247 is installed. Two native launcher cases pass with preserved checkpoints and spent counts. No loaded-model latency or new user-film acceptance is claimed. See mobile/Validation/iphone-pause-menu-247-2026-10-29.json. |
| Phone model-start248 | Desktop setup is unchanged. | Installed248 does not adopt the named resume notice or partial-GPT file gate. | Normal248 is installed. Four native cases and direct Basic menu/missing-GPT notice pass. Saved jobs remain exact. Whole-film acceptance is open. See mobile/Validation/iphone-model-start-248-2026-10-29.json. |
| Manual Learning line actions228 | Pending review of desktop line actions and short-reference handling. | Normal228 is installed. Five native cases cover one-line translation/recording and valid short-reference silence padding. | Normal phone227 is installed. Five native cases and two actual engines pass. Preserve original outputs and automatic budgets. Human acceptance remains open. |
| Basic fallback and assistant controls235 | Existing desktop fallback execution remains. Guide14 consumption is pending. | Normal235 is installed. Basic exposes the existing fallback menu and passes its selected choice for new work. Assistant preview is first in Preferences. Four native cases pass; whole-film acceptance stays open. | Normal236 installs Basic fallback controls and guide14. Native recovery fixtures and direct settings checks pass. Compact assistant placement remains separate. |
| Fallback placement240 | No desktop control behavior change. Canonical manual4/control15 location copy is complete; desktop installed consumer remains separate. | Duplicate general Preferences entry removed in source. Basic operation and Expert production controls remain. Normal240 is installed with exact manual4/control15. Launch and saved-job preservation checks pass. | Normal phone239 is installed with exact manual4/control15. Direct search/navigation, launch and saved-job/preference checks pass. No policy or budget changes. |
| WF-16 three-language first-draft length |253 is installed on desktop. Real submission snapshots and first-request payload tests pass for three languages. Model replies are isolated fixtures; whole-film acceptance remains open. | Normal223 is installed. Three real E4B first requests contain language-aware soft guidance. Clock fallback and original data retention pass. | Default local-AI mapping is tested on M4 and installed phone224. Three actual phone E4B requests pass. Apple system-translation guidance and whole-film acceptance remain pending. |
| WF-17 optional audible overlap over two seconds |253 is installed. Local Silero sample detection and bounded one-operation coordinator fixtures pass. Real optional neural retake and Windows inference remain open. | Normal223 has a default-off independent switch. Native coordinator fixtures cover thresholds, gaps, uncertainty, strict interaction, failed takes, and resume. | M4 and installed phone224 use conservative attributed lexical ranges. Native permission/resume fixtures pass. Real recognition plus retake acceptance and full-film tests remain open. |
| GPT MLX deployment | Mac short comparison accepted; desktop app backend unchanged. | Normal223 retains tested215 MLX and the character App icon. Explicit engine preferences and the legacy picker are preserved. | Normal phone224 is installed. Six fresh MLX calls, memory/cancel subchecks, and retained-take export have bounded evidence. Whole-film acceptance remains open. This is not a v4 MLX port. |
| Phone multiple-video entry222 | Desktop entry stays unchanged. | Shared optional picker/library APIs exist. iPad entry stays single-file. Phone adds sequential import and a scrollable shelf. | Phone224 retains installed222 import/saver features. Source removal, output preservation, four editing layouts, and nine themes pass native cases. Real multi-film neural and iPad import-entry adoption remain open. |
| Phone Basic control placement 211 | Existing desktop controls remain. | iPad control placement remains. Phone shows target language below Preview and moves options into a sheet. | Presentation mapping remains. Saved language is unchanged. Separate phone224 execution evidence certifies bounded205/223 adoption, not whole-film acceptance. |
| Required subtitle target delivery 205 | Counterpart review is pending on Mac 252. | Installed M4 build 205 retains drafts, adds Chinese wording fallback, and checks exact references. | Nine M4 cases pass. Installed phone224 passes one real exact-reference Whisper/Gemma/Cosy case. Its older source window still fails. Whole-film and desktop acceptance remain pending. |
| Default flow and controls | Mac and Windows253 use one baseline with content checks0, optional repair, strict duration, and excessive-overlap controls. Source and payload identity pass. Native execution evidence remains separate. | Build 191 implements `independent-duration-controls-191` with independent permissions. | Core control mapping tested separately. Inspection capabilities and whole-film acceptance remain platform-specific. |
| Review and content repair | Mac build 246 has review-only guards and initializer fixes, with synthetic execution evidence. | Build 191 has separate `autoRepair`; report-only findings keep evidence and the audible take. Eight injected execution combinations pass. | Core permissions tested on each platform. Real-model behaviour and full fallback coverage remain open. |
| Timing repair | Mac build 246 implements `speech-duration-246`, with overlap by default and one measured rewrite in strict mode. | Build 191 maps the explicit switch through planning, measurement, rewrite limits, and final export. Actual PCM and protected-boundary tests pass. | WF-15 control mapping implemented and tested with fixtures. iPad real-model shortening and whole-film acceptance remain open. |
| Missing audio | Desktop policy states two silent-only retries. Initializer and finalization paths still need their own regression evidence. | The required presence check and two silent-only retries remain enabled in build 190. | Same requirement. Whole-film coverage and exception paths need separate acceptance. |
| Other-engine and native fallback | New Mac requests use `repair-fallback-permissions-249`. First-take/source cannot enter generic/native generation. Generic selected-engine delivery is explicit. Alternate/native need AI repair and their choice. Full real-model acceptance remains open. | Build 191 requires `autoRepair` plus each explicit fallback choice. Native use retains preflight consent. Permission/resume tests pass. | Permission mapping tested. Real inference and unavailable-model/native-consent paths still need platform acceptance. |
| Hong Kong register | Desktop has Hong Kong prompts and delivery cues. | Build 190 adds a 29-entry local style bank. | Same language target; different implementation. No claim of equal register or sound quality. Real-model listening remains required. |
| Caption overlap | No corresponding desktop defect or fix was verified in this task. | Build 190 splits active caption intervals. Two actual MP4 tests pass. | Desktop must check overlap preservation in its own muxer. iPad whole-film re-export remains pending. |
| Saved jobs and budgets | Frozen revisions and persistent budgets are required. | Frozen revisions and persistent counters are required. | Regress resume and final-only export on each platform. Do not migrate an old job to align it. |

### Required acceptance evidence for an alignment item

Record the rule IDs, source revision, installed build, and test names.
Test submission through the real initializer chain, not only a configuration helper.
Test all four inspection/repair combinations and confirm the mutation and generation counts.
Inject missing audio, confirmed defects, and unconfirmed recognition separately.
Test pause/resume, model failure, multi-track work, and final-only export without a budget refill.
Keep manual choices and original recordings unchanged. Use isolated fixtures.
Record whole-film results separately for embedded text subtitles, external SRT, and screen OCR.
An older test failure or missing receipt stays open. Do not mark the other platform verified from one platform's tests.

## 2026-10-28 iPad: independent controls and measured duration, build 191

New iPad requests freeze `independent-duration-controls-191`. Saved build 190 jobs keep their original controls and semantics.
Content review and automatic content repair now have separate permissions. Review alone preserves audible takes and reports confirmed findings.
The evidence can remain `failed-confirmed` without authorizing replacement. Do not relabel it as passed or delete its recording.
AI auto repair can use existing confirmed evidence or bounded checks of suspect recordings without global review.
Other-engine and system-voice fallback have separate switches. Both also require AI auto repair. Native use requires preflight consent.
All new optional controls default off or zero. Missing and silent audio fill remains active.

The duration switch is independent of content review and repair. With it off, keep each source onset and permit generated dialogue overlap.
Retained source intervals, OP/ED, and the video end remain boundaries. Neighbouring starts do not move.
With it on, limit the take to its original speech interval. Measure actual PCM, removing only exact digital edge silence.
Keep 80 ms of padding, quiet samples, stereo channels, and internal pauses. Keep the original recording unchanged.
A real overrun permits one meaning-preserving rewrite and same-reference retake under the persistent budget.
Suspected noisy tails remain uncertain under the existing independent endpoint gate. Do not treat noise as confirmed silence.
Never accelerate a take to satisfy this policy. Source subtitles remain unchanged; only an accepted target script/caption can change.
Final export still reports unresolved delivery and preserves the previous output.

`StandardNaturalSchedule`, `StandardNaturalDelivery`, and capacity checks share the same frozen duration flag.
Content findings reach automatic fallback only with repair permission. Report-only findings do not enter the rejected-audio ledger.
Old optional fields remain decodable. Resume retains the original policy, counters, and time already spent.
This maps WF-04, WF-05, WF-06, WF-07, WF-08, and WF-15 to iPad. Check the private receipt for actual installation status.
Synthetic execution tests do not certify real-model shortening, whole-film timing, or voice quality.

### One source for product guide copy

Use `docs/WORKFLOW-CONTROLS-GUIDE.json`, revision `workflow-controls-guide-4-first-audible`, for both product guides and setting explanations.
It contains stable item IDs with `title` and `body` in `zh-HK`, `zh-CN`, `en`, and `ja`.
The `repairCostWarning` item states that extra review/repair may take 2–3 times as long or longer, without guaranteed improvement.
This is a conditional user advisory, not a measured benchmark or maximum runtime promise.
iPad build 192 separates Production settings and AI Repair tabs, with the advisory above the repair controls.
Build 193 uses plain icon selectors for these pages. This is an iPad presentation choice, not a workflow difference.
The same separation applies to iPad production defaults. Presentation changes do not alter any frozen repair or budget policy.
The iPad app bundles this file directly. The desktop line must reuse the same text instead of drafting another definition.
The copy explains independent review/repair, both duration states, missing-audio checks, fallbacks, endpoint/gap checks, translation review, and resume.
Keep platform-specific inspection capabilities separate. iPad content readback does not claim desktop audiovisual role analysis.
When a rule changes, update this copy and its consumers in the same task. Record any consumer that is not yet updated.

## Historical iPad build 190 controls

Build 190 is the historical implementation below. Build 191 adds the independent permissions and duration mapping described above.

New iPad UI requests use `standard-optional-repair-190`. The stored mode remains `performance` for compatibility.
Basic uses the former high-speed flow. Expert exposes independent controls. All controls default to zero or off:

- Content check passes per recording: 0 to 2. Each pass reserves a persisted counter before model use.
- Same-actor timing repair operations per line: 0 to 2.
- Safe endpoint checks.
- Analysis of source gaps that can supply extra time.
- A second translation review pass.

Missing-audio checks remain active. The first generation has up to two silent-only retries in the selected engine.
Keep the first audible take. Do not use native speech automatically. Always attempt export and report genuine missing dubs.
Optional content checks do not enable timing changes. Optional timing repair uses normal capacity planning before final assembly.
Final assembly retains the always-export rule. It does not certify unresolved timing or semantic quality.
Embedded caption packaging splits overlapping intervals and includes all active lines. A contained short caption must not disappear.
The existing independent time caps and persisted counters still apply. Resume does not refill them.
Saved jobs keep their revision and controls. An explicit new dubbing request can freeze new controls.

Hong Kong translation uses `hk-spoken-memory-190`. It retrieves at most four original examples from a local 29-entry style bank.
The bank guides grammar and register. It is not an automatic word replacement table or a semantic embedding database.
The translation must keep names, relationships, numbers, negation, and source meaning. It must not import example facts.
No external corpus data is bundled in this change. Real-model register and listening acceptance remain required.

Production, Expert, Study, retakes, and internal playback are free. Study has no ten-line cap.
The existing non-consumable entitlement now gates external video, subtitle, and recording export and sharing only.
Keep its product identifier. Update the store display name before submission. Each platform records acceptance separately.


## 2026-10-28 Desktop: compact Global control (build 248)

The Global control shows its name and switch on one row in all four interface languages. Its state does not change the panel height. Move the scope explanation to the shared user guide item `globalScope`. The item is explicitly marked as desktop help because equivalent iPad scope behaviour remains unverified. The required AI cost warning remains visible. No settings scope, submitted request, conversion rule, or budget changes in this presentation update. Mac 0.24.95 / build 248 is installed locally. All four language cases measure the same 57-pixel scope row in both states. The iPad installed guide remains its own recorded build; the new scope section is explicitly desktop-labelled. Platform evidence is in the handover.

## 2026-10-28 Desktop: production settings scope and AI Repair tab (build 247)

Desktop production settings use global defaults unless a video explicitly selects individual settings. Turning Global off captures a private snapshot for that video. Later global changes do not replace it. Turning Global on removes that override for future work. Appearance, deployment, and hardware preferences remain global. The real per-video submission selects the effective settings before it freezes the request. Running requests cannot change scope. Resume preserves the existing request and spent budgets. A fresh reset returns to global defaults without deleting old recordings or outputs.

Both desktop interface modes separate Production and AI Repair tabs. The scope switch applies to both tabs. Inspection, repair, duration, OP/ED, and fallback controls move together into AI Repair. No generation policy, retry count, or time budget changes in this presentation task. The cost warning stays visible at the top. It states that review and repair may take 2–3 times as long or longer, without guaranteed improvement over optimized defaults. This is an advisory, not a benchmark or a duration promise.

Local Mac 0.24.94 / build 247 is installed. Thirteen scope/guide tests, 174 related tests, two operation-contract tests, and four language browser cases pass. No model inference ran.

The desktop Help centre and setting explanations consume `docs/WORKFLOW-CONTROLS-GUIDE.json`. Build preparation copies the exact JSON bytes and generates its JavaScript consumer with the source SHA. The iPad build 192 AI Repair tab and guide are recorded separately. Desktop scope behaviour and iPad scope behaviour are not yet verified as equivalent. Real-model and whole-film acceptance remain separate from these settings and interface tests.

## 2026-10-28 Desktop: independent measured duration control (build 246)

Samuel selected intentional dialogue overlap when the duration limit is off. New desktop jobs freeze `speechDurationRevision=speech-duration-246`. Older jobs keep their saved timing and repair rules. This change does not alter the iPad implementation.

The `limitSpeechDuration` switch is off by default. Each target recording starts at its original speech time. The full recording can cross later generated dialogue. Do not call this authorized overlap a failed recording. Keep protected opening and ending ranges, retained source intervals, and the video end as boundaries. Do not move neighbouring starts or accelerate speech.

When the switch is on, use the original speech interval as the limit. Measure the real generated recording first. Remove only exact digital silence at the edges. Keep 80 milliseconds of padding, quiet phonemes, and every internal pause. Retain the original file. Noise is not confirmed silence. Existing independent endpoint evidence remains necessary for an uncertain noisy tail. Never subtract a sentence pause merely to claim a fit.

A real overrun can authorize one meaning-preserving AI rewrite and one retake with the same reference. Use the existing persistent attempt and time budgets. Resume cannot refill them. Do not shorten from a mora count, a caption length, or a predicted duration before synthesis. Preserve names, facts, negatives, quantities, and emotion. Keep authored embedded, external, and OCR subtitle evidence unchanged. Only the target dubbing script and its target caption can change. Never alter a locked user script. If the candidate still fails, retain it for comparison, report the unresolved delivery, and continue the existing final fallback/export policy.

The duration switch is independent of both AI switches. Full review can inspect content and voice consistency without retakes when AI auto repair is off. AI auto repair must survive fast-path initialization and can run without full frame analysis. Physical missing-audio recovery stays active with all three switches off.

Source implementation: `speech_duration.py`, `speech_timing.py`, `natural_finish.py`, `natural_delivery.py`, `recovery_coordinator.py`, `work_modes.py`, `fast_mode.py`, `delivery.py`, and the desktop setting/UI boundary. Mac 0.24.93 / build 246 is installed in local dist. Twenty targeted tests and 154 related tests pass. Real-film acceptance remains pending. Windows packaging remains deferred.

## 2026-10-28 Desktop: one standard pipeline, the first audible take, and a source-timed script

Deployment on 2026-10-28: local Mac dist is 0.24.92 / build 245. Windows dist stays at 0.24.91 / build 244. Samuel deferred the Windows package. The three new Mac test jobs have not run. Do not treat source parity as Windows delivery.

The desktop source line for 0.24.92 / build 245 removes the three mode choices (fast, balanced, quality) from new desktop jobs. One pipeline serves every new job. That pipeline is the former fast pipeline. `work_modes.REVISION='desktop-work-modes-2'` carries only `MODES=('performance',)`. The stored value stays `performance` so the frozen performance gates in other modules keep their names. Older jobs and iPad jobs keep their own revision and rules, and the older mode view still reads them. `tests/test_work_modes85.py` and `tests/test_ai_repair_migration245.py` check this.

The old mode list is now two separate switches. Both default to off:

| Switch | Job key | Default | Effect when on |
| --- | --- | --- | --- |
| AI repair | `aiAutoFix` | off | The app listens again and re-records a take it judges wrong. Alternate-voice and system-voice substitution become available again. |
| Full AI review | `fullAIReview` | off | The new job uses the standard pipeline instead of the fast pipeline, adds audio-visual role analysis, and allows one timing rewrite pass. |

In the collapsed mode `maximumTimingRewritePasses` is 0 and `automaticDurationRewrite` is false while Full AI review is off. `maximumMissingRepairAttempts` stays 2 with the switch off, because a required segment with no sound must always get a fill attempt. A silent take is a defect, not a choice. `Resources/multitrack.py` calls `fill_missing_audio` whether or not AI repair is on.

Why the re-record loop went wrong: the recogniser often tags correct Cantonese speech as Japanese or Mandarin, and each new take lost emotion. The rule keeps the **first take that has sound** (`preferFirstAudibleTake` is true, `failoverStrategy` stays `first-take`). Re-record runs only when a take has no audible audio.

Time budget from the source language: the script writer uses the Japanese cue start and end plus the mora count of the Japanese line (`source_mora.REVISION='source-matched-script-245'`). The writer keeps the Cantonese character count close to the Japanese character count. When the speaking rate is the same, the take fits the source window, so overlap handling is not needed. Measured take rate in job `45a87d47cfa4851b`: median 3.88 characters per second, p25 3.08, p75 4.46, from 84 audit rows. `target_characters` uses that measured rate, not an assumed rate.

Script fit pass before recording (`script_fit.REVISION='script-fit-245c'`): the app rewrites each line that cannot fit its real window before the engine records. The window comes from the renderer, through `speech_timing.natural_window`, which applies the mora end cap, `END_GRACE_SECONDS` = 0.35, the next spoken barrier, and protected opening and ending ranges. Before this change the writer used `window_seconds` only, so a line looked safe and the renderer refused it later. `needs_fit`, `target_characters`, `request`, the `over_window` check, and the audit row now carry `allowedSeconds`. Test: `tests/test_script_fit245.py::test_next_line_shortens_the_time_a_take_may_use`.

Caption window floor (set 2, job `74a9760cd57bce58`): four required segments stayed silent because a take passed the end of the Japanese speech it can hear but was still inside its own subtitle. The cap rule alone refused those takes, so the original Japanese played under a Chinese subtitle. `natural_window` now takes the later of the mora cap and the caption end of the same line, and still stops at the next spoken barrier. A take may use the silent tail of its own subtitle; it may never cross into the next line. Tests: `tests/test_natural_delivery.py::test_caption_tail_absorbs_an_overrun_without_crossing_the_next_line` and `tests/test_standard_mode245.py::test_the_take_deadline_stops_at_its_own_caption_end_not_past_the_next_line`. `source_mora.active` also returns false when no configuration is present, which removed a crash in the same area.

Hard character ceiling (set 1, job `5a6de8963d59f56b`): the first ceiling was only advice. The pass kept a clean candidate that was still longer than the window, so 13 of 20 rewritten lines stayed over and 8 required segments fell back to the original Japanese. The pass now checks `len(normalize(candidate)) <= targetCharacters`. When the first candidate passes every guard but is over the ceiling, the pass makes one more call with the ceiling written as a hard rule ("上限 {n} 字係硬性要求"). It adopts a candidate inside the ceiling first, otherwise the shortest valid candidate. The audit row records `attempts`. The prompt text is now part of the cache key, so a prompt change cannot reuse a stale answer. Test: `test_candidate_over_the_character_ceiling_gets_one_harder_attempt`.

Copied neighbour content (`script_fit.copied_neighbour_content`): the translation sometimes folds the caption before or after into one line. Job `5a6de8963d59f56b` cue 7 shows it: the Japanese of that cue is "这里果然正义的伙伴秘密忍者队", and the Cantonese line also carried cue 6 and cue 8. Such a line cannot fit, and the take is refused. The app now flags it when a neighbour within 3 seconds has its whole Cantonese line inside this line, and this cue's own speech or caption does not carry the neighbour's source. Repeated lines, a chorus, and split sentences stay safe: on that job 1 of 66 lines is flagged, and it is the real case. The flagged text goes to the model as `removeDuplicated`, the audit row records `copiedNeighbourContent`, and the line enters the fit pass even when the draft looks short. Test: `test_short_line_that_copied_the_next_line_is_still_rewritten`.

Defect rule: when a Chinese subtitle has no Cantonese audio, or when a take passes its allowed window and the original audio plays instead, that is a defect. Report it. Do not record it as normal behaviour. Acceptance target for a standard desktop run: `missing = 0` and 0 overlap rows.

Flat delivery: the engine cue for Cantonese now uses `cantonese-strict` instead of a bare language tag. The bare tag produced a reading voice. Job `45a87d47cfa4851b` shows 84 of 84 generation traces with `deliveryStyle: normal`. Prosody evidence for the same run: take pitch standard deviation 6.59 semitones against reference 6.84, median ratio 0.92, and 14 of 80 takes flatter than 60 percent of the reference. `prosody_check.py` measures this. The delivery style is part of the take cache key, so a style change re-records takes; do not treat that as lost work.

Recovery keeps the delivery cue (`drama3.recovery_styles`): when a take hits a decoder cap, the app retries in the same loaded model. For Cantonese work the retry styles are `cantonese-strict`, then `cantonese-strict-clauses`. The plain styles drop the Hong Kong delivery instruction, which is why a recovered take read flat. The bound stays three attempts per line. `tests/test_drama3.py` and `tests/test_fast_mode.py::test_recovery_styles_keep_the_hong_kong_delivery_instruction` pin this.

The strict cue also asks for the reference pitch movement and tempo: "跟住參考錄音嘅音高起伏、速度同情緒講，唔好平讀". `drama3.language_hint` holds the text, and `tests/test_drama3.py::test_reference_resampling_and_language_hint_preserve_approved_words` pins it. Set 1 evidence for why this is needed: take contour step standard deviation 1.38 semitones against reference 2.23, ratio 0.62, while take pitch standard deviation ratio was 1.00. The line-level movement is the flat part.

Interface note: the right panel is "Production settings" (製作設定). The default tab is "Production" (製作), not "Dialogue".

## 2026-10-27 iPad only: single-take and forced-dubbing pilot (desktop followed in performance mode on 2026-10-28)

iPad build 189 froze two rules for **new performance jobs** to help Samuel investigate missing dubs: `single-take-dubbing-189` (performance and balanced modes record one take per sentence; re-record only when the take has no sound at all) and `forced-tts-dubbing-always-export-189` (in performance mode every dialogue segment with a subtitle must be dubbed by the selected TTS engine; a system voice or the source-language audio does not count as dubbing; the first voiced take is used directly; the dub start time uses the real onset of the source language). The delivery rule changed to **always write an output file**: segments with truly no usable target-language take keep the original audio, and the segment numbers go into the job prompt and into `export-coverage.json` / `<output>.coverage.json`. Export is no longer aborted. The incomplete-export gates for balanced and quality modes stay as they were. The shared requirements in this file do not change. `safe-capacity-delivery-4` and the v3 delivery order did not change on macOS/Windows, and "always export" was not pushed into desktop at that time. For receipts and limits, see `mobile/Validation/forced-tts-dubbing-build189-2026-10-27.json` and `ipadOnlyExperiments` in `docs/RECOVERY-WORKFLOW-CONTRACT.json`.

Desktop adoption on 2026-10-28: 0.24.91/build244 replaced the local Mac/Windows dist (**new performance jobs only**). macOS/Windows now follow the iPad performance rules under `forced-tts-dubbing-desktop-244`: re-record only takes with no sound at all, max 2 attempts per sentence; alternate-voice and system-voice substitution is hard-disabled in performance jobs, even if the job file has those switches on; the first voiced take is kept directly, and performance mode never had a duration rewrite. Desktop already exported in all cases (`unresolvedAction=continue-to-delivery-policy-and-export`), so the delivery gate did not change. Balanced jobs, quality jobs, and older frozen jobs keep their original policies. Old jobs carry their old revision number and do not switch to the new rules by themselves. Receipts: `tests/test_forced_desktop91.py` and `desktopExperiments` in `docs/RECOVERY-WORKFLOW-CONTRACT.json`.

## 2026-10-27 Report and manual re-repair: separate normal checkpoints, hints, and real missing dubs

Desktop 0.24.90/build243 replaced the local Mac/Windows dist (2026-10-27): a resume checkpoint that saves the voiced take of each sentence is not a defect by itself. Rounding error must not create an over-length warning. A subtitle-free gap, or a short fragment where the subtitle continues, keeps the original audio and is not counted as a missing TTS dub. Keep the hint when the real sentence split or source assignment is not confirmed yet. The report must separate these groups: no target dub delivered / a clear defect, versus optional listening / subtitle pairing / old candidate records. Do not claim "everything converted wrong" from the total hint count. A single ASR language tag, or a homophone or name-spelling difference, cannot authorize a re-record and cannot certify success.

The pending sentences offered by the "Repair again" action contain only items explicitly marked `repairEligible`, plus unprotected rewrite/reference changes. Advisory items are not pulled into generation by themselves. Explicit per-sentence re-record and "refresh all dubs" still work. This fix does not re-dub existing finished work by itself, and it does not change the repair budget or the models of unchanged updates and older frozen jobs. The full diagnosis stays in the job file and in the debug download. Do not show internal keys to the user as the explanation. Record the real deployment and acceptance for each platform separately.

## 2026-10-27 v4 desktop: safe audio measure -> borrow evidence-backed gaps -> shorten only on true overrun

New desktop jobs adopt `safe-capacity-delivery-4`. 0.24.89/build242 replaced the local dist (Mac/Windows). 400 targeted tests and 22 isolated synthetic cases pass. Windows real-machine runs and full-episode semantics/accent still await acceptance; see the handover for details. The matching iPad implementation is recorded separately and does not use the desktop version number. Normal Resume keeps the original v3/v2 flow and the budget already spent. Only a reset new job adopts the new rules. Source-first, the three first-recording/generic/original-audio options, the three modes, and repair-first stay as in v3 below.

Add a separate endpoint check only for recordings that measured over length and are suspected of long tail noise. Continuous energy only nominates a candidate. A full Whisper transcript with no script prompt, the last-word time, and matching sensitive Silero voice evidence must agree before the app stores an additional-rate/channel/PCM-accuracy candidate. The candidate keeps the final sound / weak activity / 240ms after the VAD endpoint, and keeps the original file. If either side is unsure, do not trim and do not certify a complete read. Never hide a missed read with a cut. If the comparison sounds like different words, do not automatically confirm a real missed read; keep the bounded fallback of the full script. See SAFE-AUDIO-ENDPOINT-WORKFLOW.md for details.

| Endpoint check | Performance | Balanced | Quality |
|---|---|---|---|
| Extra word-level recognition budget (shared per track for the whole video) | none new | 60s | 180s |
| Max questions per batch | 0 | 32 sentences | 96 sentences |
| Attempts per sentence/engine/target language | 0 | 1 | max 2 |

This time does not consume the required AI/system voice quota. Nested stages save and pause the parent clock; pause/restart does not refund used time. Valid evidence with the same SHA can be reused. A missing model or a timeout is recorded as unconfirmed; no automatic download. The strict text-match gate can reject a recording that was correct. This is a conservative safety limit, not a pronunciation or accent certification.

Keep the original start time, and first use the safe gap before the next voice. Auto-released subtitle gaps may be borrowed only when the original separated-voice SHA and the exact window prove near-digital silence with no ASR words. The noSpeech flag, the absence of a subtitle, or the keep-original flag is not enough by itself. Keep the background mix once. Unknown content, weak voice, laughter/crying/breathing, OP/ED, and manual keeps are still blockers. This evidence gate is deliberately conservative and does not guarantee that every music-only gap can be identified. After borrowing gaps, if it still truly overruns, do the v3 count-limited meaning-preserving shorten and full re-read: performance does not shorten, balanced one time with the same voice, quality two times. Do not feed an unconfirmed tail directly into a shorten.

## 2026-10-27 Acceptance addendum: protect the generic fallback quota; Cantonese output subtitles in Traditional Chinese

Repair-first alone is not enough: a same-voice rewrite/timing sub-stage must not exhaust all remaining AI quota for the selected engine's generic dubbing later. Each platform must have a persistent sub-stage limit. Keep the existing whole-video cap and the per-sentence counts. Inference that already started may finish; a new sub-stage must not act as a refund. The generic path may first use the full reviewed script; do not pre-shorten the generic script because a character recording is long. A selected AI generic dub must not silently pass off a system voice as the AI voice. Record model/memory problems honestly, then use the explicit last system fallback. Record the ratios, deployment, and real-video acceptance per platform; never count one platform's test as delivered for the other.

The Cantonese target subtitle must be Traditional Chinese, independent of the interface language. A source native subtitle keeps its original glyph form and stays separately selectable. The player auto-selects the full subtitle track of the target dub. The menu index must belong to the filtered list. Never use the unfiltered AVKit forced-only index, or the player can pick the native Simplified Chinese track by mistake. Acceptance must open the player with a real file that contains both Traditional and Simplified subtitles, not only check translated script strings. Also keep an explicit way to select the native Simplified track.

## 2026-10-27 v3: required delivery first, independent listening clock (Samuel authorized)

Requirement id **anicanto-recovery-workflow-3**; the machine-readable summary is in `RECOVERY-WORKFLOW-CONTRACT.json`. Desktop 0.24.88/build241 replaced the local dist (Mac/Windows); targeted regression and synthetic tests pass. Windows real-machine runs and the next full-episode test await Samuel's acceptance; see the handover. The iPad implementation, deployment, private device validation, and unfinished items are recorded in the handover; this shared document does not replace platform acceptance. The v2/v1 history below is historical only. Jobs created during the v3 period use v3. Current new desktop jobs follow the v4 section above. Normal Resume keeps its frozen flow and its spent counts; do not migrate silently.

| Per-sentence / whole-video rule | Performance | Balanced [default] | Quality |
|---|---|---|---|
| First generation, stop when one is usable | 1 | 1 | max 3 |
| Measured over length, same-voice meaning-preserving re-dub | 0 | max 1, includes the keep-first-take policy | max 2 |
| Same-engine generic target-language generation | 1 | 1 | max 2 |
| Generic voice measured shorten | 0 | max 1 | max 1 |
| Extra content listening | not done | max 24 question/change sentences | broader |
| Required repair base budget / cap | 60s / 5 min | 180s / 15 min | 600s / 30 min |
| Independent extra listening budget | 0 | 60s | 180s |

Required order: physical silence/damage check -> fix measured over length -> same-engine generic target language -> at most one other installed AI -> installed system target-language voice -> extra listening -> confirmed content error uses only the remaining repair budget / per-sentence counts -> original audio last -> export. An explicit "keep original audio on failure" policy may keep the original audio directly. Full AI video analysis stays a separate switch, is off by default, and cannot cancel the mode caps.

Freeze the budget when repair starts, from the not-yet-delivered sentence count and the first-round measured generation seconds: `min(mode cap, max(mode base seconds, sentences to repair x estimated repair seconds per sentence))`. The per-sentence estimate is `clamp(2 x median first-take generation seconds + 8, 8, 90)`; when there is no usable generation event, use 24s. This is a time-allocation heuristic, not a success-rate or best-performance guarantee; measure it with the next real video. Reserve 25% of the required repair time only when the system-voice fallback is on; when it is off, give all of it to AI. Do not change user consent by itself. Listening is separate and must not consume the required voice quota. The budget is shared across the video tracks; pause/restart/mode change does not refund it. An operation that already started may finish and go slightly over; when the budget expires, do not start the next item. Export time is separate. In quality mode, the extra silent-take fills inside the first max-3 generations also count against repair time.

Shorten only after the audio measured over length. Never delete words up front by character count. Never delete negations, names, relationships, or facts, and never cut the tail. Save the shorten candidate, review that the meaning is preserved, re-generate in full, and measure again; if it is not suitable, keep the old recording. Persist per-sentence and per-character counts and the generic counts. Do not refund quota by rewriting the script to change the cache key. Bind extra-listening evidence to the audio SHA; a new recording must not reuse an old wrong judgement. Do not mark an item passed when it was not checked or ASR did not confirm it. A new error does not restart the whole review round; use only the remaining voice budget and counts.

Keep v2 for source, native subtitle timing, non-dialogue performance protection, and human take protection: subtitles > voice uses only the chosen professional subtitle as translation content, and the audio as clock/voice reference. A subtitle-free gap keeps the original audio and is not a missing dub. When the script is missing, or a fallback could not generate the target language, still try to output for continuity; the report lists the real original-audio ranges and the incomplete target language. Do not write only "repair succeeded." Report source damage, low storage, and persistent encode errors honestly; no design guarantees output under every failure. Export retries automatically at most once; final-only reuses the saved mix and does not re-dub the whole video.

v3 acceptance additions: after a simulated full-episode listening consumes the whole independent budget, the required voice fill still has its own balance; a balanced first-take that measured over length may re-dub once with the same voice; the SHA type plus the generic measured-shorten chain; "出現喺" must not become "出而家"; per-sentence counts/time survive Resume, old v2 freeze, and unchanged suitable neighbor sentences; real FFmpeg subtitles / multi-audio / source-only are readable, which still is not accent or whole-video semantics certification.

---

### 2026-10-27 Addendum: measure the audio safely first, then borrow voice-free gaps, shorten last

The detailed solution pending validation, with shared positive/negative cases, is in [SAFE-AUDIO-ENDPOINT-WORKFLOW.md](SAFE-AUDIO-ENDPOINT-WORKFLOW.md). Desktop v4 implements word-level endpoints and the conservative safe-trim candidate. Read the latest handover for the real install/acceptance status and limits. Old jobs are not migrated backwards.

Samuel confirmed again: when nothing is spoken after a line, a longer dub may extend into the free space. Do not shorten it or fall back to the original audio only because it passes the original subtitle display end. Work in this order:

1. Check that the recording content is complete, and rule out fake length caused by tail noise. Trim head and tail silence safely. Do not cut weak sounds with a single-sample noise peak or a fixed high threshold. The known 030 counter-example has an 8.04s file whose real main energy is about 3.14s. Energy values are diagnostics only, not a production trim threshold.
2. Use the real voice clock of the original audio and keep the original start position. First allow extension into the free space before the next original voice / dub starts. Music and normal sound effects keep playing; they are not a hard blocker, and the same background must not be layered twice because of the extension. Subtitle end does not mean the audio must be cut. No subtitle does not mean no voice.
3. You must protect the next sentence (including source-language dialogue with no subtitle that is kept), original laughter/crying/breathing that must be kept, OP/ED, and explicit protection boundaries. When it is unknown whether the space has sound, do not treat the noSpeech/keepOriginal flag as "borrowable". Also do not treat every original-audio-kept range as forbidden.
4. Only when a safe measure and gap borrowing still cannot fit, do the mode-based AI Cantonese meaning-preserving shorten and full re-dub: performance does not shorten, balanced max one time with the same voice, quality max two times; the fixed generic stage caps are separate. Keep the original script and all takes. Keep negations, names, numbers, relationships, and intent. Measure again after the re-dub. Do not fake a fix with a cut tail or an arbitrary speed-up.

Implementation status must be reported separately: iPad 186 has a general gap-borrowing scheduler, but preserveOriginal turns the whole gap into a barrier and does not split even pure background space. This is an open gap; do not claim this addendum is deployed. The source-only subtitle rule does not change: the audio still supplies only time/voice and the safe-gap judgement; no subtitle does not create a new translation script.

---

## v2 historical spec (new jobs follow v3 above)

Current requirement version **anicanto-recovery-workflow-2**; the machine summary is in the JSON above. Samuel authorized desktop sync. Each platform must fill in delivery and acceptance separately. Never count a candidate, or a pass on another platform, as deployed on this platform. Platform implementation and private device validation are recorded in the handover. This shared spec does not contain private device validation data, and it does not mean any platform is deployed.

| New-job rule / per-sentence cap | Performance | Balanced [default] | Quality |
|---|---|---|---|
| First generation, stop when one exists | 1 | 1 | 3 |
| Content listening (under the whole-video time budget) | skipped, including all fallbacks | yes | yes |
| Same-character measured timing operations | 0 | 0 for the keep-first-take policy, others max 1 | max 2 |
| Selected engine generic voice | 1 | 1 | 2 |
| Another installed AI engine | max 1 engine / 1 pass | same | same |
| Installed system target-language voice | max 2 passes | same | same |
| Whole-video listening / repair time budget | 60s | 180s | 600s |

Each stage has its own budget. Do not say the whole per-sentence flow is only 1/2 passes. The table counts whole-sentence operations at the application layer; bounded chunking inside the GPT engine needs its own cache and deadline handling, and chunking must not allow endless re-reads. An explicit new conversion or a new dub-refresh round may create a new delivery budget; a normal resume cannot. A new delivery does not migrate frozen source rules and does not change the parent version. Give the last 25% of the time to the native voice. When AI time is exhausted, do not start new inference; when native time is also exhausted, finish with the recordings/original audio you have. A single inference that already started may finish; do not force-kill a shared service. GPT chunk generation must also check the deadline between chunks. Export time is not in these budgets. The budget persists with the draft; pause/restart/mode change does not refund it. A hard kill keeps the active clock anchor and conservatively counts time that was not checkpointed; do not reset from the kill.

**Source:** In "subtitles > voice", the only translation content is the built-in/plugin subtitle set the user selected. The audio supplies only the speaking clock and the original character voice reference, never a second translation text. All gaps with no subtitle keep the original audio. Do not send them to translation/dubbing/repair, and do not count them as missing dubs. This rule has priority over the old "gap at A -> fill at B" description. When the subtitle has content but ASR is empty, do not delete the script; show the fallback with the original subtitle display clock. The other three routes stay: A primary / B helper. Save the native subtitle timing, the translated subtitles, and the real dub clock separately.

**Script:** For new jobs, no character-count guessing and no shorten before generation. Only when real generated audio measures over the available window may you shorten with meaning preserved, in a bounded way, with a full re-dub. Performance does not shorten. Balanced/quality allow at most one measured shorten for the generic fallback, plus the per-table same-character timing operations. Never delete negations, relationships, names, or facts. Do not fake a fix with keyword strings that are not sentences, a cut tail, or arbitrary fast reading. Keep the original script and every candidate. A script change must change the cache identity and does not refund spent budget.

**Delivery:** first usable recording -> same-engine generic -> at most one other installed AI engine that supports the target language -> installed system target-language voice -> original audio last. List the usable banks/models/voices per platform honestly; no automatic download. Get system-use consent before the job starts; do not block an unsupervised job hours later. An explicit Original-audio policy may keep the original directly. A confirmed wrong content must go into the bounded fallback; do not pick the wrong first take back just because it has sound. Uncertain ASR / homophone / spelling evidence is a warning only; never mark it `passed` falsely.

One coordinator serves the normal flow, model errors, and the final closeout. Write missing scripts, unconfirmed items, and final original-audio segments into the report; do not block automatic output. When the whole video has only original audio, state clearly that the target-language dubbing is not complete. Never claim the AI dubbing is finished. A failed main mix / subtitle wrap may auto-retry once using the existing data; a restart does not refund, and a final-only draft does not rerun the episode. Output must have playable audio/video and the selected subtitles. Source damage, low storage, and persistent encode failure must still report a recoverable error honestly; do not promise an impossible success. Manual takes and pause/cancel stay protected.

**Regression acceptance:** three modes x three failure policies; confirmed vs uncertain split; subtitle-free gaps; no migration of old jobs; exceptions still reach native; no loop without progress; alternate/native and export budgets survive restart; three policies on real source-only MP4 + translated subtitles + decodable; quality does not re-pick a take confirmed wrong; suitable neighbor sentences and old recordings do not change. Short-clip tests do not replace full-episode semantics/listening acceptance or one-hour performance certification.

The v1 history below stays. Where it conflicts with the newer requirement above, the newer requirement wins. Read the handover again for real evidence and install state.

---

Spec id: `anicanto-recovery-workflow-1`. This file is the handover entry point where Mac, Windows, and iPad builds align the flow and acceptance. The machine-readable summary is in [RECOVERY-WORKFLOW-CONTRACT.json](RECOVERY-WORKFLOW-CONTRACT.json).

**Status at that time: desktop 0.24.68 / build 221 finished Mac/Windows packaging and replaced the dist; 71 related tests, the Mac signature / isolated launch, and package content checks on both platforms passed. Windows real-machine runs and the iPad flow were not verified in that round.** "The spec requires it" does not mean all three platforms are complete. Record platform implementation, test evidence, and remaining differences separately. Desktop platform differences are in [DESKTOP-RECOVERY-PARITY.md](DESKTOP-RECOVERY-PARITY.md).

## 1. Shared processing order

1. Read the selected source audio track. Keep the original video and the native subtitles, and record the time offset.
2. Separate background and voice. Check the usable audio, channels, and length. Never treat file existence as completion.
3. Recognize and split sentences from the original voice. Subtitles/OCR supply meaning and name reference only; they never replace the dialogue clock of the original voice.
4. Prepare per-sentence/per-character references and translate to the user's selected target language. Save the original script, the subtitles, and each translation separately.
5. Generate sentence by sentence. When a sentence finishes, save at once the recording, script, engine, language, references, and parameter identity.
6. Apply the repair rules for the mode below. Reuse completed items on resume; never re-record from scratch.
7. Protect native non-language performance. Mix at the original time with the selected dub/background.
8. Write the new version and verify the audio tracks, subtitles, decodability, and length. Keep "done" separate from "waiting for human proofreading."

## 2. Modes and re-record conditions

| Rule | Normal mode (default) | Performance mode | Detailed check (explicit selection) |
| --- | --- | --- | --- |
| Keep the first voiced recording | yes | yes | original recordings still keep their history |
| Language/accent/homophone questions | keep in the report; a tag alone never discards the recording | no quality listening | limited repair on extra evidence |
| Silence / damage | max two extra voice-fill attempts at the application layer, with a persistent budget | no quality re-record; a required usable-audio fix needs its own explicit budget | limited budget; never re-enter the full batch check |
| Measured over length | keep the measurement, the legal gap, and a bounded meaning-preserving shorten; adopt the full re-read first when the measure fits | follow the duration policy already stated for performance mode; never start detailed rewrite/listening silently | the same bounded duration policy |
| Protect original laughter/crying/breathing | keep | keep, same rule, not a quality check | keep |
| Automatic repair fails | keep the finished files; show the specific problem and the available actions | same | same |

Keep the application-layer voice-fill budget, the engine's internal partial-decode recovery, and the shorten budget in separate records. Never reset an allowance by switching stage or reopening the app. The desktop normal-mode over-length flow uses at most two rounds of local shortening. Multiple candidate scripts with meaning checks are also under their own bounded budgets. Never decide a recording is broken from text length alone.

**An accent, a recognizer tag of Japanese/Mandarin, or a wrong character is not by itself a real wrong utterance or a missing word.** Normal mode keeps the first voiced take for human listening; these tags must not cause repeated re-records. Mark unconfirmed evidence `unconfirmed`; never disguise it as `passed`. Human script edits, chosen recordings, kept original audio, and protected segments must never be overwritten automatically.

**Desktop note (2026-10-28).** New desktop jobs use one pipeline, not a fast/balanced/quality choice. Read "2026-10-28 Desktop: one standard pipeline, the first audible take, and a source-timed script" at the top of this file. In that pipeline the "Measured over length" row does not run automatic shortening or re-listening; the time budget is set before recording, in the script. The AI repair column behaviour sits behind the `aiAutoFix` switch, which is off by default.

## 3. Non-dialogue original performance: laughter and crying first

### Content you must protect

Keep the original recording first for non-language performances that need no translation: big laughter, crying/sobbing, screaming, gasping, sighing. Do not require TTS to re-perform them. Handle original music, normal sound effects, and OP/ED original audio with the existing keep settings.

### Shared decision order

1. The separated voice track also contains laughter/crying. Never drop the whole voice track and assume the background is complete.
2. Get sound-event evidence with a source and a time window. Empty ASR text only means "not recognized". It does not authorize mixing the original back by itself.
3. Exclude Japanese/other source dialogue using word times that the original voice confirms, including protection boundaries. When only a loose whole-sentence time is available, keep the uncertainty hint; do not guess where the laughter is.
4. Add an independent non-language sound back at its original time. When a new dub delay crosses into it, duck only the overlapping part of the performance sound; never delete all of it.
5. When the same moment is already restored through a kept original range or an individual cue, do not layer it again.
6. When source dialogue overlaps laughter or crying, never bring the full Japanese back to save the laughter. When you cannot extract it safely, list it clearly for human proofreading.
7. Save the kept events, the events not safely kept, the times, the reasons, the classifier/version, and the window. Provide an original/separated/output comparison and a manual keep entry point.

### Analysis windows and performance

The target final time granularity for performance events is a one-second window with a half-second step. **This is not a requirement to cut every classifier input into one second without validation.** Classifiers may need different context, padding, and probability distributions. Measure with one shared set of positive/negative cases first. The confirmed difference today: Windows classifies in five-second windows and Mac in one-second windows. In 0.24.68 we compared the real classifier on three public samples: cutting one second directly on Windows lowers laughter/crying confidence and adds time, so we rejected it. We keep the five-second context of the current classifier for now. Improve this with a time-localizing classifier or a validated context-splitting scheme. Do not change only the number and claim both sides match. Handle OP/ED song classification separately; do not change its window or protection time because of this work.

Reuse event results across languages/engines when the source audio, model version, and analysis settings are the same. Never disguise an old-window result as the new time granularity. Invalidate results when the audio or model changes; never use an identical file name instead of content verification. Short windows add work; state the time cost and avoid duplicate inference across tracks.

## 4. Audio quality and timing

- Keep original generation rate, analysis rate, and final delivery rate clearly separate. A 16 kHz analysis file may be used only for recognition/measurement, never for final playback or dubbing.
- When you mix back laughter, keep original cues, change times, and do the final mix, do not drop Drama 3 44.1 kHz / GPT V4 48 kHz to 24 kHz without a reason. Follow the delivery rule per engine. Upsampling does not return detail to a low-rate recording.
- Keep the timing of original performances, and use short fades at segment joins. Keep the real words; never pass off a cut tail as a duration fix.
- Keep the left/right channel information of the background and effects. State the dub channel layout; never confuse the analysis mono with the finished stereo.
- Save native subtitle timing separately. Changing dub times must not move the native subtitles.

## 5. Saving, timeouts, pause, and reports

- Save each finished line atomically. Cache identity includes the audio content, model/version, related settings, and comparison target.
- Never mark an unfinished inference as success. A timeout stops only the job that owns it, never another process or the model service.
- A restart processes only unfinished items. A stage change must not make the same recording listen or re-record again.
- "Pause and save" only pauses and saves. It never exports silently. Never overwrite an exported version. Keep export state separate from review state.
- The completion report must state the video/language/engine and the sentence or time range, the problem, the steps tried, the final recording used, and the available actions (listen / re-record / keep original).

## 6. Three-platform acceptance table (the iPad build should fill in real results line by line)

| Acceptance case | Must confirm |
| --- | --- |
| First round has sound but ASR text differs | Normal mode does not auto-discard or auto-re-record; list it uncertain |
| Silence or damage | Limited extra voice fill; the budget does not reset after a restart |
| Measured long but voiced | Meaning-preserving shorten still allowed; adopt a full new recording that fits the window first |
| Independent laughter/crying/breathing | Normal and performance both keep the original time; never leave a hole |
| Laugh then speak Japanese / speak then cry | Do not delete the performance with it, and do not mix the full source back |
| Source dialogue and laughter overlap at once | Do not claim safe separation; leave a clear human proofreading item |
| New dub extends into laughter | Duck the overlap in a bounded way; do not delete the whole laugh |
| One video with many languages and engines | Share source event evidence; no duplicate layering / repeated inference |
| Sample rate and bandwidth | Confirm with the real FFmpeg / AVAudioEngine path; a 14 kHz signal test does not replace human-ear quality acceptance |
| Pause / timeout / restart | Finished recordings and per-sentence results survive; the whole batch does not restart |
| Manual script edit / chosen recording | Automatic repair does not overwrite; the exported new version is traceable |

Record on each side: app version, hardware, models, mode, input clip hash, processing time, real output, and test limits. Models may differ by platform. The shared repair decisions and budgets must never fork silently. Leave unfinished items `pending`; never mark them passed because another platform passed.

## 7. Sync rules

When you change this flow, update at the same time: this file, the machine-readable summary, the four-language user instructions, and the matching tests, and list done/todo in `CODEX-HANDOVER.md`. Desktop and iPad keep their own implementation and real-device acceptance records. Without user authorization, never overwrite a converter, model, or project that is running. This file itself does not authorize interrupting other work.

### Real iPad build pickup steps

1. Read this spec and the JSON summary first. Then map each item in section 6 to the real iPad code location. Never move only the desktop UI or reuse the same feature name.
2. Record for each item: "current behaviour -> required behaviour -> files changed -> test input/output -> result." Check saving, retry budgets, over-length shortening, and non-dialogue protection.
3. Run the same test clip in normal and performance mode, and test resume after pause. Compare the chosen recording, timing, mix, and report. Note model differences separately. Never use an ASR text difference instead of human-ear acceptance.
4. Fill in the app/spec version and the acceptance evidence in the handover record; use pending when unfinished. If a shared decision must change, revise this spec and the summary first, then implement and verify on each platform.

Record every future change to detection, translation, dubbing, repair, original-audio protection, or output behaviour with the same handover method. Pure appearance changes may follow the UI docs only.

## 8. Confirmed desktop safety gaps with no fix yet (2026-10-24)

An independent pure-policy review confirmed SP1 (a short voiced Japanese word wrongly treated as performance), SP2 (a missing classification field wrongly read as zero), and NS1 (a segment with dubbing disabled but original audio kept not treated as a barrier). The corresponding source in the Mac/Windows 0.24.68 packages is identical. **That round only recorded the findings; no production change, no re-release.** See [desktop pending counter-examples and acceptance requirements](DESKTOP-RECOVERY-PENDING.md). An iPad private-stage fix must never be counted as synced on all three platforms; validate each platform later and keep the original-audio clock.


## 2026-10-28 Desktop: context editors and compact header (build 252)

Task: Consolidate editing controls without changing conversion policy.

Mac 0.24.99/build252 is installed in dist. Two icons select Production or Additional AI repair.
The dialogue edit button opens Listen, Retake, and Adjust. Player controls own subtitle language and size.
Adjust owns the per-line display caption. A display-only caption edit preserves the selected take and review choice.
A script, source transcript, or role change clears that selection. Recording history remains available.
A paused explicit line selection stays stable during audition and editing.

The timeline mixer owns export background gain and manual ducking.
Both display and save use the active Global or individual-video scope.
Absent values use worker defaults: gain 80%, ducking off. Gain is limited to 150%.
Saving the mixer writes the visible values. The original-track choice remains in Production only.
Preview volume does not set export gain. Per-line retake submits native audio, without preview movie encoding.

Four-locale browser checks pass at two widths. Backend persistence, scope, audition playback, and retake-request checks pass.
Three AAC exports use the real mixing filter and decode successfully. No actual new TTS inference ran.
The wider backend checks pass 79 of 81. Two failures also occur against installed build 251.
They concern a short wordless take and an old production-mode lock assertion.
The underlying execution files are byte-identical to build 251. These failures remain open.
No model, media, existing recording, saved progress, source workflow, repair budget, or worker export rule changed.

The compact guide consumer matches revision 6. Its new source-fallback behaviour remains pending on desktop.
The first-take duration/fallback defect and held-tail work remain separate. Whole-film listening is not certified.
Windows remains build 244. See `docs/DESKTOP-INSPECTOR-CONSOLIDATION.md` for evidence and limits.


## Desktop preview257 and shared guide15

See docs/DESKTOP-PREVIEW-ASSISTANTS-257.md for the presentation and source-reader change. It does not change WF-01, WF-02, WF-03, WF-15, WF-16 or WF-17. Existing requests and spent allowances remain unchanged. Mac257 is installed after process and instance-lock checks. Installed startup passes. Windows remains255.

The latest common operation source is application-user-guide-4. The control source is workflow-controls-guide-15-fallback-location. Only the fallback location clause changes: Production settings and mobile Basic operation options. No repair, retry or final-fallback permission changes. Exact hashes and separate consumer install states are in RECOVERY-WORKFLOW-CONTRACT.json. Mobile owners must copy the same files and validate their own packages.

### Desktop operation guide7, 2026-10-29

Guide7 corrects legacy desktop CN/JA chapter-index mismatches and documents bounded first-draft correction in a desktop-only section. It preserves guide6 mobile-only chapters. Control guide15 is unchanged. Mac258 installs guide7 with hash eb6531da6e955f09ebc2c25fa8667775f448b11f98eb18f3d24477d725d02aa9. The installed mobile guide6 hashes remain separate in the JSON consumer map. Mobile-visible filtered content is exact. Windows255 remains unchanged.

**Desktop258 delivery.** Mac0.25.5/build258 is signed, installed and passes isolated native-host startup.194queue/job metadata hashes remain unchanged. Package parity covers161web files and247Python files. Receipt: .build/desktop258/verification.json. No real film conversion, new model download, Windows binary change or GitHub publication occurs.

## Phone workspace presentation249

Installed-model validation stays in the selected Welcome button until entry is ready.
Missing or invalid required resources retain the deployment route. The bar counts verified default model groups.
The phone can hide its default-visible preview assistant independently of video preview.
Expert Review retains the filename header and hides the lower timeline.
The drawer Edit and preview action returns to production and restores the timeline.
Basic has no drawer report entry. Reading settings reuse the five existing iPad setting groups.
The speech-playlist Learning action stays at the bottom. Learning settings use a small icon beside the target language.

Normal phone249 is installed and launch-verified. Two isolated native cases and direct zh-HK navigation checks pass.
Five saved project files and two latest files remain byte-identical.
Cold validation timing, processing animation with inference and full guide rendering remain unverified.
Guide15/control19 are exact package copies. This copy does not implement pending mobile generation rules.
No conversion core, frozen request, recording or spent allowance changes.
Evidence: mobile/Validation/iphone-workspace-249-2026-10-29.json.


## Phone reset location250

The phone circular reset arrow is immediately right of the filename eye.
The previous source-shelf copy is removed. The same confirmation and enabled conditions remain.
Normal phone250 is installed and launch-verified. Direct placement, confirmation and Cancel checks pass.
Five saved project files and two latest files remain byte-identical. Only the StoreKit check timestamp changes in preferences.
Guide17/control19 are exact package copies. Full guide rendering is not checked.
This appearance change does not change frozen requests, conversion rules or spent allowances.
The iPad and desktop layouts stay unchanged. Phone quarter-first recovery and native replacement adoption remain pending.
Evidence: mobile/Validation/iphone-reset-location-250-2026-10-29.json.
