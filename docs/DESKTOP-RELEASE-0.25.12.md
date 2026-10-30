# Desktop Beta 0.25.12

Task: Publish matching Mac and Windows desktop packages with source materials.

## Changes since 0.25.9

- Wait for cloud video data before media checks. Show read progress or a waiting state and allow cancellation. Keep the original source path and subtitle selection. Do not use a media-probe timeout as the complete download deadline.
- Keep source preparation outside the long worker request lock. Ignore stale preparation receipts after the app restarts. Cancel of a preparation must not start the next video or pause a separate active conversion.
- Use bounded source-clock recovery and exact caption ownership. Do not dub a continuation twice when an earlier cue already covers it. Keep uncertain source evidence in the report.
- Keep optional text review, audio repair, duration limits and source checks separate. Keep frozen requests and spent allowances on resume.
- Retain confirmed silent screen captions as text only by default. Missing or uncertain speech evidence is not proof of silence.
- Add small breathing, rigid head movement and local hair motion to nine distinct assistant rest scenes. Respect Reduced Motion.
- Show error notifications with a sharp red background and white text in both appearances. Normal notices retain theme colors.

## Package and verification scope

Mac and Windows are 0.25.12 / build 265. The interface and shared worker sources match.
The Mac package has isolated native startup, exact asset hashes and strict signature checks.
Windows uses cargo-xwin for the x64 MSVC host and portable launcher. Package structure, embedded payload hashes and notices are checked on the build Mac.
Native Windows startup, model deployment and GPU inference still require Windows device testing.
The checks do not certify complete translation, accent or whole-film listening quality.

The frozen desktop operation guide is revision 36; workflow-control help is revision 23.
Later mobile-only manual changes remain separate. Public source and attachments exclude private iPad/iPhone implementation and device records.
Models remain separate downloads under their own terms. Required third-party notices remain in each package.

## Known limits

- An uncertain OCR window can still collect repeated or long subtitle text. Bounded source-clock recovery is a partial improvement, not complete acceptance of every caption group.
- The observed unavailable Google Drive placeholder stayed at zero readable bytes. Cancellation passed. Complete provider download remains dependent on network, provider access and the source file.
- Existing saved jobs keep their frozen settings. Updating the application does not regenerate old exports.
- A voiced recording is not proof that its meaning, pronunciation or accent is correct. Optional review does not guarantee a better result.

## Recovery

Keep the matching binary, source attachment and SHA256SUMS.txt. Follow BUILD-AND-RECOVERY.md.
User videos, recordings, projects, downloaded models and credentials are not public backup assets.
The existing demo videos remain unchanged.
