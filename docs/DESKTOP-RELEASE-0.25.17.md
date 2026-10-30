# AniCanto Desktop Beta 0.25.17 (build 270)

Task: Centre the navigation rail and make Windows runtime repair clear.

- Fix a reproduced Mac WebKit layout fault. Separate the scrolling area from rail geometry. Native WebKit measured left/right gaps of10/37pixels before the fix and10/11after it, including the right border.
- Show each Windows runtime check or install step and elapsed seconds. Send a heartbeat every five seconds. Show GPU component installation before it starts. Do not show a fabricated download percentage.
- Reuse matching PyTorch vendor wheels when only the dependency list changes or the old runtime receipt is absent. Keep version, import and GPU checks. Repair mismatched GPU packages and damaged packages. Missing app requirement files no longer trigger Python recreation.
- Welcome has one Repair / redeploy menu. Check and repair keeps model files. Reset and redeploy shows a removal review, then removes app-managed models and runtimes after confirmation. Videos, recordings, projects and exports stay. Windows closes before full removal; open the EXE again to deploy.
- Fix the false missing-recording warning for a subtitle continuation that has a valid assigned dialogue. Link to its owner for script and recording comparison. Do not infer a recording from ownership alone.
- New Mac caption-only requests can use a bounded paired sound check for near-quiet music-only credits. The exact reported opening fails the old gate and passes the new isolated replay, with its caption text and clock retained. Actual-caption lexical speech, quiet voices, incomplete coverage and uncertain classifications remain protected. This adds no translation or TTS retry permission. Old frozen requests keep their earlier gate. Windows AST thresholds remain pending; its conservative caption gate stays active.
- Repair shared manual schema1 types. All30chapters and151sections decode through an actual Swift JSONDecoder before platform filtering. Add a pre-packaging format gate. Update four-language Help and setup screenshots.

252 targeted Python regression cases pass. Four-language interface checks and native Mac WebKit geometry checks pass. Actual Windows setup and GPU conversion still require on-device testing. The latest user report ends during a fresh dependency installation, without a final failure or completion. Earlier reports contain missing files in an older app package; their removal cause is not proven. Models, conversion policies and saved work are not reset by this update.

Close the old app before opening the new EXE. Try Check and repair first. Full redeployment is optional and requires a removal confirmation. Share a new debug report if setup fails.
