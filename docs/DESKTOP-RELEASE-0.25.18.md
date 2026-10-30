# Windows 0.25.18 deployment correction

Task: Restore Windows deployment and show actual installer progress.

Mac stays at 0.25.17. This release updates the Windows EXE and matching source only.

- Replace a deleted rolling FFmpeg release URL with a retained byte-exact archive. The original size and SHA-256 remain fixed. The matching source and notices remain available.
- Check the other seven tool URLs. Each returns HTTP 200 and the expected byte length. Download FFmpeg to an empty test folder and verify its full SHA-256.
- Retain healthy installed GPU and analysis packages. A changed requirements receipt alone does not cause reinstallation.
- Stream real installer output. Show package names, byte counts and transfer speed when pip reports them. Show elapsed time during installation and import checks. Do not add repeated timer updates to the installation log.
- Freeze the confirmed cleanup file list before exit. Remove only unchanged reviewed files. Retain files changed or added during exit. Partial cleanup does not prevent the next launch. Keep projects, recordings and exports.
- Include partial cleanup results in the support export.

The Windows EXE is cross-compiled and its embedded package is verified. Clean deployment and GPU inference on a Windows device remain user acceptance work. These checks do not certify conversion semantics, accents or whole-film quality. No conversion policy changes in this patch.

For an existing failed setup, open the new EXE and use Check and repair. Existing verified downloads are reused. For a deliberate clean test, use Reset and redeploy, confirm the removal list, then open the new EXE again and select Download and prepare.
