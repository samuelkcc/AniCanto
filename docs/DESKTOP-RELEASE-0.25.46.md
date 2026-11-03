# Desktop Beta 0.25.46 / build 306
> Language standard: English, ASD-STE100 style. See docs/DOCUMENTATION-STANDARD.md.

Task: Start automatic desktop jobs without an unknown-subtitle confirmation prompt.

When Accept detected language is on, use the first audio track unless another was explicitly selected.
Cantonese and Mandarin prefer Chinese captions. English prefers English captions, then Chinese.
Read language labels first. If necessary, inspect up to three unlabelled text subtitle tracks.
Each text inspection reads up to 65536 bytes from the first 600 seconds, with an eight-second extraction timeout.
This inspection runs no AI model and changes no source file.

If no suitable captions are found, continue from speech without OCR or a subtitle confirmation prompt.
The new request freezes this fallback. Worker initialization cannot select unrelated captions afterwards.
Keep explicitly confirmed subtitle choices. Turning the switch off retains the prior subtitle confirmation.
Speech / OCR remains an explicit choice. Subtitle text never replaces the detected audio language.

Paused requests retain their frozen sources, scripts, recordings, voice choices, settings and spent allowances.
Automatic inference, required missing-audio fill, first audible takes and optional repair permissions do not change.
The ordered review report and default-off LAN diagnostics from 0.25.45 remain available.

## Validation scope

Nine focused source tests cover text selection, language preference, switch-off confirmation, manual choice and frozen resume.
The real MKV fixture contains Chinese text with no language tag. Its selected track reaches the frozen request.
The desktop RPC fixture covers Mac and Windows routes with simulated audio-language detection.
Six actual backend submissions freeze the first audio and unlabelled Chinese subtitle across both desktop routes and three output languages.
Worker source initialization retains each selected subtitle. No conversion worker or AI model launches in this audit.
All 38 audio-language tests, 18 desktop-state tests, 13 four-mode cases and three user-guide cases pass.
The first-audio test includes a later track with a container default flag.

Record both package checks and exact consumer hashes in the release receipt before delivery.
The reported One Piece file is not inspected by these fixtures.
Windows execution, whole-film conversion, listening acceptance and mobile adoption remain unverified.
The Mac app uses an ad hoc signature. Optional model weights remain separate downloads.
Public desktop source excludes private mobile implementations and device validation.
