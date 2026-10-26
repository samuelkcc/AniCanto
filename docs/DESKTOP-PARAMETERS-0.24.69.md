# Desktop 0.24.69 · Drama 3 sampling controls

2026-10-24 · build 222 · local dist delivery only; no Git/GitHub publication.

## Behaviour

Drama 3 uses Temperature 1.0, Top P 0.9, Top K 30 when no explicit value is saved. Existing explicit custom values remain unchanged. The model reset button applies this combination; production preferences save automatically after editing a field. Existing saved recordings are not regenerated. These sampling controls do not guarantee voice similarity, emotion or accent accuracy.

Production defaults and Dubbing studio share the same three question-mark controls. Each opens a keyboard-accessible native dialog with parameter meaning, supported range, defaults and reference guidance. Escape, close and backdrop dismissal restore focus. English, Traditional Chinese, Simplified Chinese and Japanese are provided. Production numeric validation prevents saving out-of-range values and the backend error includes the accepted range.

The built-in guide includes the same sampling explanations and automatic-saving instructions. Temperature supports 0.3–1.2; Top P 0.3–1; Top K integer 5–80. These remain the app's supported bounds.

## Verification and limits

- 205 applicable Python regressions plus 6 Windows CUDA/setup adapter tests passed: 211 unique tests. Includes persistence across reopening, rejected values leaving preferences untouched, immutable explicit job snapshots, new clip defaults and actual Mac/Windows generation request sampling (mocked inference boundary).
- Four-language browser tests cover both pages, edits, reset, rejected values, modal focus/Escape and a 900×700 viewport. Traditional Chinese additionally checked in dark appearance. These use isolated RPC fixtures, not a live user library.
- Mac native startup, code signature and production contract passed. Embedded interface hashes match source on Mac and Windows. All 154 shared Python files match final packages; actual installed deployment plan remains ready with no model download.
- Mac native worker was freshly compiled, incorporating the previously validated SP1/SP2/NS1 safeguards in DESKTOP-RECOVERY-PENDING.md. Packaging signatures are removed only from temporary comparison copies to confirm executable code identity with the freshly built Swift worker.
- Release containers scanned for local account/build markers: 5,974 files, zero hits.
- Windows exe was cross-built with cargo-xwin. No physical Windows/CUDA inference or human listening assessment was performed in this patch. No model inference or video conversion was started.

Evidence, screenshots, previous binaries and install/final receipts: `.build/parameters69/`. Earlier 0.24.68 binaries are retained under its `rollback/` directory. User videos, installed models, recordings and conversion state were not edited. The app remains closed after installation. GitHub remains at the earlier published release, by user request.
