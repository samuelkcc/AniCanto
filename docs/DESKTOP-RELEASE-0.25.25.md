# Desktop Beta 0.25.25

Task: Load long cloud sources without a false timeout, keep the stored voice reference on a retake, and correct the review report, take label, notice and settings panel defects.

This release carries the desktop work from build 276 through build 279 (0.25.22 to 0.25.25).

## Changes

- Source loading: a file that must come from a provider or a network share has no total deadline. The app names the real owner, shows exact bytes read, and keeps its own elapsed clock. After 45 seconds with no new byte it asks. **繼續等** resumes the same read at its byte offset and grants 600 seconds, then asks again. **唔再等** keeps the list, the saved work and the bytes already read, and names the provider in the fault line. A local path uses a 15 second quiet limit. The app no longer blames a cloud supplier for a file that sits on a local drive.
- New switch **桌面：自動接納偵測到的原聲語言** under **全域**, in Standard and in Export more. It is on by default. When it is on, the app applies the detected source language without a confirmation. An audio window with no confirmed speech still asks.
- Review report: one summary card, one filter row, one search box, 25 lines per page, and one card per line. The classification panel and the separate report tables are gone. New tabs **已覆核** and **待處理** carry the per-line listening state.
- Takes: one **首次生成** label per first take. The first take lists first, and later takes follow creation order. An unused first take can be removed; the in-use list has one owner. A retake uses the line's stored voice reference, so the reference voice does not change between takes.
- Video preview notices: warnings and errors now show as a wide badge inside the preview area. They do not stop a bulk conversion, and the queue does not wait for a click.
- Settings panel: **全域** and the auto-approve switch scroll with the Production settings body, and their switch columns line up with the other switches.
- A one-line retake no longer fails because a saved editor draft sets the storage folder twice.
- Removal copy names the real folder `discarded-recordings/`.
- Added the missing English entry for the short reference note, so an English reader no longer sees the raw Cantonese key.

## Evidence

- Focused suites pass: 92 Python cases across `test_source_wait278`, `test_source_cloud278`, `test_source_cloud274`, `test_source_access`, `test_source_language`, `test_source_preparation264`, `test_voice_reference278`, `test_review_status278`, `test_review_line277` and `test_worker_stall278`. All 21 `tests/*.mjs` suites pass. `tests/test_ui_localization.py` passes.
- A native probe against the installed host reports `autoApproveSkipsConfirmationForKnownLanguage: true` and `unconfirmedAudioStillAsksEvenWhenAutoApproved: true`, with `userLibraryChanged: false`.
- Mac package `AniCanto.app` (0.25.25 / build 279) passes isolated native startup, the exact embedded interface manifest, `codesign --verify --deep --strict`, and a privacy scan of 3,063 files with 0 private path hits.
- Windows package `AniCanto.exe` is 322,078,720 bytes, sha256 `f021a237b7c275858e4b64172b4a9d4ec9b7cac7446fdc3fef8679a3176967de`, with 3,043 embedded payload files verified against the built host.

## Limits and open acceptance

- Not verified: no whole-film conversion ran on any platform after these changes. No real Google Drive or OneDrive load ran. The Windows package has not been started on a Windows machine.
- Partial parity, stated plainly: the Windows pages do not show the auto-approve source language switch or the **已覆核** / **待處理** tabs. The Windows worker has no question channel to its interface, so on Windows the read waits and the user stops the movie in the queue instead of answering the wait question.
- This public release contains the desktop edition only. The iPad and iPhone applications, their sources, Xcode projects, IPAs and private device validation stay outside this repository.

## Homepage maintenance

Read `docs/DESKTOP-DOWNLOADS.json` before each public release. Update the released platform version there, then run `scripts/update_desktop_downloads.py`. Run it again with `--check` before publication. It updates all five homepage files from one record. Verify the published assets before reporting the download ready. Do not publish a local-only build as a released download.
