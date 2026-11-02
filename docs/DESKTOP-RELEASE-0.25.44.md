# Desktop Beta 0.25.44 / build 304
> Language standard: English, ASD-STE100 style. See docs/DOCUMENTATION-STANDARD.md.

Task: Publish the current desktop controls, source playback, storage fixes and matching source materials.

## Changes

- Production settings use four closed groups: Voice & language, Subtitles & source, Opening & ending, and Advanced.
- Settings scope names Shared defaults and This video only. Existing inheritance and frozen requests remain unchanged.
- Additional AI repair uses closed groups. Optional checks and repairs retain their separate permissions and finite counts.
- Reset / rebuild has one entry in Production settings. The duplicate video-card restart button is removed.
- Welcome uses the current shared design. Theme assistants retain their faces. Progress has more space above its small assistant.
- Compatible source files open directly. Other codecs use bounded preview segments instead of a complete preview movie copy.
- Audio and subtitle inventories load before playback. Preview choices remain separate from conversion source choices.
- Automatic detection selects Subtitle first when readable authored subtitles exist. Otherwise it selects Speech first.
- Subtitle first translates the selected subtitles and uses speech timing. Speech first translates speech before same-turn subtitle proofreading.
- Speech / OCR uses speech and OCR only. It ignores embedded and imported subtitle files.
- Cantonese and Mandarin prefer Chinese subtitles. English prefers English, then Chinese. Uncertain subtitle language requires a choice.
- Accept detected language uses the first audio track unless explicitly changed. Other recognised source languages do not require Japanese.
- Dub dialogue only defaults off. It compares independent speech meaning with captions before excluding a clear mismatch.
- Missing or uncertain recognition never proves wrong speech. This caption option grants no recording-replacement permission.
- Storage controls inspect application storage, clear temporary files and repair application folders. Installed models and saved work remain protected.
- Runtime redeployment no longer depends on removed legacy data. New application storage uses AniCanto.
- Eighteen temporary-write sites in eleven modules now use owned staging and bounded replacement retries.
- An optional MLX audit write no longer discards generated text or masks the real generation error.

## Workflow preservation

New requests retain the first audible take. Required missing audio receives bounded fill.
Optional controls remain off or zero by default. Resume keeps frozen source choices and spent allowances.
Source clocks, caption display clocks and delivered audio clocks remain distinct.
These changes grant no new automatic retake permission.

## Verification

- Both installed product verifiers pass against 0.25.44/build304.
- Mac checks cover the shared interface manifest, native worker contract and deep, strict ad hoc signature validation.
- Windows checks cover the x64 executable, exact shared host, 3,052 payload files and payload hashes.
- The release privacy scan checks 6,125 Mac and Windows payload files. It finds zero private account or build-path markers.
- The earlier storage-write task passes 76 focused Python cases. This publication adds source-boundary and archive checks.
- Nineteen new native Mac captures cover four interface languages. The isolated library uses original test media.
- The source attachment includes checked application inputs, notices, native sources, dependency archives and available build recipes.
- The public workflow projection keeps all 17 active shared rules. It omits private platform validation history.

## Limits

This task does not run a whole-film conversion or certify listening quality.
This Windows build has not run on a Windows device. Structural checks do not prove GPU inference or playback acceptance.
Real cloud-provider loading remains separate acceptance work. The screenshots do not prove conversion quality.
The Mac application uses an ad hoc signature. It is not notarized.
Optional model weights are not bundled and keep their own terms.
Private mobile applications, Xcode projects, purchase implementation and device validation are excluded.

The matching source archive and SHA256SUMS.txt accompany both desktop installers.
