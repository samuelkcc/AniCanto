# Desktop Beta 0.25.14

Task: Simplify model setup and prevent an optional cloud-media stall.

## Changes

- Keep downloaded models on normal switches. Reuse verified files and activate the verified current selection without installation. Other selections still need loading and speech checks.
- Show the Windows requested Drama3 path and verified processing separately. Remove the fixed native CPU model label. Permit explicit CUDA retry after automatic CPU fallback.
- Adapt optional visual-role changes only after verified required model and speech checks.
- Put Remove all models on Welcome. It opens a removal review; deletion needs a separate confirmation. Keep user videos, recordings and outputs.
- Put Reset production parameters in the Production settings header. Respect Global or individual scope. Keep models, languages and frozen work.
- Fix the Mac source PCM lookup across tracks and versions. An optional performance check must not re-extract a Google Drive movie when valid local PCM exists. Bound optional child work and keep conservative sound rules on failure.

## Limits

These changes do not certify pronunciation or a complete movie. Native Windows CUDA and the resumed Mac conversion still need user testing. Caption-only suppression remains enabled and conservative. The observed Mac stall was an optional tail check; a separate MobileCal crash does not prove an AniCanto crash. Private mobile source is excluded.
