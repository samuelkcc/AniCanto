# Desktop playback and workspace controls · 0.24.74 / build227

Samuel's five UI follow-ups are delivered in both dist packages. Replacement occurred only after explicit confirmation that the app was closed, with the exclusive instance lock. Prior .73 retained under .build/seek74/rollback. App remains closed; no conversion launched, no user project/recording/model modified, no GitHub publication.

## Controls

- Back/forward 10 seconds: only the backward SVG arrow rotates. The button and its numeric label are upright. Actions remain the same.
- Play/Pause follows actual video play, pause, ended and emptied events. The main playback button's icon, title, accessibility label and pressed state are refreshed, including on rebinding.
- A gear beside player subtitles opens a 12–48 px size slider. It lives inside the player card, so fullscreen uses the same control. The value is saved in localStorage and changes only the preview caption style, never output subtitle settings.
- During processing, Automatic subtitle selection prioritises already translated lines for the selected dubbing language at the source playback position. Partial progress does not substitute an earlier/next line or silently use original subtitles for an unfinished translation. Explicit original/embedded/external/off choices remain honoured. Caption display windows/overrides and source-versus-output excerpt offsets are respected.
- Dialogue/inspector selection follows playback and seeking, including clearing selection in a gap. It does not jump away while a script field has focus. Timeline viewport is retained.
- Basic mode adds top-right left-video-panel/right-inspector toggles plus Preferences, using the same actions/positions as Expert. Expert keeps its navigation toggle as well.
- Duplicate header Save icon removed. Keyboard Save and navigation saves remain. Pause & save attempts to save pending draft edits; source fingerprint safeguards still reject stale overwrite, while queue auto-continuation is disabled even if saving reports a conflict.

## Actual checks

61 affected Python tests passed. Node shared-model tests include partial translations, disabled/gap windows, display overrides, English and source/output clocks. Four browser languages passed real movie playback, play/pause pressed state, subtitle size28px and persistence inside fullscreen, subtitle/audio switching, automatic translated preview versus manual original choice, unfinished-line indicator, dialogue sync, Basic header panel toggles (actual hide/show) and opening Preferences, no header disk icon,1080px layout and no JavaScript errors/conversion-start command. Initial pause-event assertion raced the browser event task; fixed the test to wait for both actual pause and updated control state.

Final native hosts embed exactly the final frontend hashes. A late pause-save finally guard necessitated refreshing the Mac host once; final Mac and Windows manifests match current sources. Fresh Swift worker, Mac strict signature and native startup passed;164 shared Python files match Windows payload. Privacy scan5994files/0privatebuildidentifiers. Installed native movie endpoint also passed embedded/external/off/read-only/no-conversion checks. Windows executable is cross-built/package-verified; no real Windows playback acceptance is claimed.

Evidence: private .build/seek74/ verification.json, final-receipt.json, tests.json, installed-native-player.json, privacy.json and ui/playback-acceptance.json. Private test media is not published. Whisper/source segmentation remains the existing desktop implementation; the rejected .build/segmentation74 experiment is not part of this UI release.
