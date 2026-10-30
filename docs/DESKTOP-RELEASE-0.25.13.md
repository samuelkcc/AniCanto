# Desktop Beta 0.25.13

Task: Correct Windows setup readiness after a successful installation.

## Fixes

- Keep the optional visual role from the verified deployment. A later free-memory estimate must not turn a usable installation into a new setup requirement.
- Keep a completed automatic CPU deployment until the user selects and verifies a different backend. Do not silently promote it to unverified CUDA after restart.
- Refresh setup status after model maintenance. Enable Start when backend checks pass.
- Distinguish missing files from incomplete verification. If files are present, show Finish setup verification. Reuse verified downloads.
- Retain required model-load, speech, file and CUDA checks. A download alone is not a successful deployment.

## Using the patch

Close the older Windows application and open the new AniCanto.exe. Installed models and saved jobs remain in application data.
If Start is enabled, continue normally. If Finish setup verification appears, select it once to complete the missing checks. Do not delete models first.
To change a verified CPU path to CUDA, choose the CUDA path in setup and complete its verification. The same Q2 weights are reused.

## Evidence and limits

An isolated real-planner test reproduces the readiness failure on a synthetic 32 GB RAM / 16 GB VRAM configuration. The fix passes the regression.
Four-language UI tests confirm the setup action, failed-check gate and Start refresh after maintenance.
The user's exact PC cause is not confirmed: only a Waiting log line was available. Native Windows startup and GPU conversion still need device testing.
This patch does not change translation, speech sampling, frozen jobs or repair allowances.
Private mobile application source and device records are excluded. Existing OCR and cloud-provider limits remain.
