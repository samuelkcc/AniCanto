# Shared workflow rules: public desktop projection
> Language standard: English, ASD-STE100 style. See docs/DOCUMENTATION-STANDARD.md.

This export copies the active shared rules without changes. Private platform implementation logs and device validation are omitted.
Read APPLICATION-USER-GUIDE.json and WORKFLOW-CONTROLS-GUIDE.json for product controls. Read the matching release notes for verified delivery.
The internal shared authority remains the source. This public projection does not define a separate platform workflow.

| Rule ID | Shared requirement |
| --- | --- |
| WF-01 | New Basic jobs use the fast standard flow. Expert adds optional controls to that same flow. Extra AI controls default off or zero. |
| WF-02 | Missing, silent, or damaged required dubbing always receives bounded fill attempts. Allow at most two retries after first generation. |
| WF-03 | The default flow keeps the first audible TTS take. AI/ASR findings alone cannot replace it. Mandatory fill handles missing, silent, or damaged audio; optional mutation needs its own explicit permission. |
| WF-04 | Preserve each requested control through all initializers and resume. One control must not silently switch another on or off. |
| WF-05 | Inspection and mutation are distinct permissions. Review alone reports findings; a separate enabled repair control authorizes recording changes. |
| WF-06 | Content repair does not enable timing repair. Timing repair does not enable global content or visual review. |
| WF-07 | Freeze finite per-stage counts and whole-job time limits. Reserve before inference. Resume never refunds spent budgets. |
| WF-08 | Use the selected TTS engine by default. Cross-engine and system-voice fallback need separate explicit permission. Low available memory grants no fallback permission. |
| WF-09 | Attempt final output with saved valid work and report genuine missing target dubs. Storage, source, or encode failure stays an explicit error. |
| WF-10 | New jobs use four source modes. Automatic selects Subtitle first with readable authored text, otherwise Speech first. Speech / OCR is explicit and ignores authored tracks/files. Speech supplies dubbing clocks. Speech-first drafts receive later same-turn caption proofreading. |
| WF-11 | Preserve OP/ED and nonverbal performances. A subtitle gap does not authorize new translated dialogue or prove silence. |
| WF-12 | Cantonese uses spoken Hong Kong grammar and Traditional Chinese. Preserve source meaning and keep source captions separately selectable. |
| WF-13 | Keep source, subtitle display, and delivered audio clocks distinct. Do not drop captions because audio or caption intervals overlap. |
| WF-14 | Each platform proves output decoding, audio/caption coverage, timing, and listening separately. Metadata alone is not acceptance. |
| WF-15 | Freeze the duration choice. Off keeps full first takes at source onset, with overlap and a held final frame if needed. On permits one measured timing rewrite. Source clocks, captions, and internal pauses stay unchanged. |
| WF-16 | Budget the first translation against original speech time in Cantonese, Mandarin, and English. Use language-aware soft limits; preserve complete meaning. This is first-draft work, not an extra review or retake. |
| WF-17 | Excessive audible-overlap repair is an independent Expert option, default off. Only more than two seconds of confirmed simultaneous target speech permits one faithful rewrite and retake per affected line. Silence and empty gaps do not trigger it. |
