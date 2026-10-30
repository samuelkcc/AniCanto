# Desktop Beta 0.25.16

Task: Use the current packaged core and keep support export available during setup failures.

## Changes

- Packaged Python policy lookup uses its own executable. A stale inherited developer override cannot select a removed old package. Source checkouts retain explicit developer overrides. Catalogue verification remains mandatory.
- The Windows launcher and desktop host bind child processes to the current shared resources and core. Windows setup checks the core before changing deployment receipts or installing runtimes.
- Native debug export works when Python fails or returns invalid output. It records the original error, component locations, file presence and bounded app-owned logs. Credential-bearing lines are omitted. It does not read model weights, media or files through symlinks outside app storage.
- An unwritable selected destination falls back to a unique file in app support logs. The interface displays the actual saved path. One failed Python report section does not discard other sections.
- Welcome includes Cantonese, Mandarin and English in all four interface languages. Available languages still depend on the selected voice engine.

## Evidence and limits

242 targeted checks pass:232selected regressions,4packaged-core and preflight cases, and6native support-export tests. The intact-package/stale-override fixture fails before correction and passes afterwards. The native Mac host exports through its real command when an isolated Python stub fails. Four-language interface and package results are recorded separately.

The268payload contains the core executable. The exact on-device cause of the reported Windows error is not confirmed by that fact. The user also reports a different export error without its text. The new diagnostic path records these failures rather than claiming Windows acceptance. Actual Windows startup, setup and GPU conversion remain user tests. Catalogue mismatch, missing files and failed speech checks remain blocked. Conversion policies and saved work do not change.

Additional historical tests that assume retired model tiers or omit source-media fixtures still fail against both the old and patched policy bridge. This is not a full-suite pass. Mixed-language ASS selection and OCR long-group limits remain separate. Private mobile implementation is excluded.
