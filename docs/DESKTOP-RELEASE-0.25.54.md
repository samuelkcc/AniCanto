# Desktop 0.25.54 / build 446
> Language standard: English, ASD-STE100 style. See docs/DOCUMENTATION-STANDARD.md.

Task: Publish the verified Mac and Windows desktop update.

- Keep the active video selected during conversion. Wait for Pause & save before switching videos.
- Keep confirmed voice-reference ranges inside their owned dialogue cue. Do not borrow adjacent dialogue audio.
- Improve subtitle-gap classification for new Automatic requests. Keep source uncertainty separate from confirmed sound effects.
- Reuse verified optional background audio during export. Keep saved source clocks, recordings and spent attempts.
- Include the shared four-language guide revision261 and control guide92.

Both exact package verifiers pass. The packaged producers pass25 reference, selection and continuation cases.
Three shared-interface cases pass. These checks do not certify whole-film voice quality or physical Windows GPU inference.
This release does not claim full parity with all later mobile workflow changes.
The public source excludes private mobile implementation and device validation.
