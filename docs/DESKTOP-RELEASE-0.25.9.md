# Desktop Beta 0.25.9

Task: Release the current Mac and Windows desktop application with matching source and interface images.

## Changes since 0.25.1

- Keep production settings and optional AI repair controls separate.
- Distinguish missing target audio from optional wording, timing and source-review notes.
- Preserve the first audible take. Use bounded missing-audio fill and the selected fallback settings.
- Keep captions with confirmed absent dialogue as text only by default. Preserve their display timing.
- Add contextual Hong Kong Cantonese wording guidance for new translations.
- Use the theme-coloured A-note mark in Welcome, the workspace header and About. Keep the operating-system application icon.
- Give all nine original assistants distinct resting poses and drawing styles. Use the same scenes in Settings and with preview off. Move only small hair regions and respect reduced motion.
- Refresh all four interface languages in the screenshot guide. Use light-purple appearance and preview off for editing screens.

## Package and test scope

Mac is 0.25.9/build262. Windows is built from the same shared interface and worker source.
Mac isolated startup, strict signing and the embedded interface hashes are checked.
Both WebGL and Canvas2D render all nine resting scenes. Fixed anchor samples and reduced motion pass.
Windows package structure, embedded content and hashes are checked on the build Mac.
This does not certify Windows device startup, GPU inference or whole-film quality for this package.
The public source and release attachments exclude private mobile application code and device records.
Models remain separate downloads under their own terms. Required third-party notices remain with the packages.

## Known limitation

Speech recognition with OCR can group several short conversations into one long subtitle.
A saved Ninja Cat example contains a sparse erroneous source transcript over approximately20seconds.
The source guard misses that grouping. OCR wording then enters one translated cue.
This release does not include the proposed correction. It does not certify complete translation or pronunciation.
A long subtitle does not by itself authorize replacing an accepted audible recording.
Source timing, caption display timing and generated audio must remain distinct.

## Rebuild

Use the matching source attachment and the existing BUILD-AND-RECOVERY.md instructions.
The source export includes the checksum-verified original desktop assistant activity art and common operation guide.
Do not copy private mobile implementation or real user media into a public rebuild.
