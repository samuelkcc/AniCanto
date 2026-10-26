# Desktop queue / wake recovery · 0.24.76 / build 229

## Observed incident

Read-only local records: episode817 finished at 01:24:14 UTC on 26 October; episode818 started at03:57:46. At03:57:49 macOS entered Clamshell Sleep. Multiple 9–22 minute gaps in 818's stages coincide with actual sleep/maintenance-wake cycles. A full lid/user wake at06:37:26 was followed by resumed work;818 subsequently completed and819 started automatically. No generation crash, missing source, or automatic AI-repair failure was logged in the inspected gap evidence.

The system power log available for this inspection begins at03:57. It does not establish the reason for the earlier817→818 gap. Native completion depended on a transient webview event, and the pinned Tauri default permits a hidden/minimised webview to suspend after roughly five minutes. These are confirmed architectural risks; an actual missed817 event was not directly recorded by the old version. Do not claim that log evidence proves every queue delay was a webview suspension.

## Changes

- macOS14+ webview background throttling explicitly Disabled, preserving the same frontend queue policy while hidden. This API is unsupported on Windows; completion reconciliation is shared independently.
- Native TaskLifecycle retains the latest completion payload in the host's memory, after existing persistent finalisation and before releasing active-task ownership. Native status reports both the current owned worker and retained completion. This is a same-host webview-reload/wake mechanism, not an automatic restart after quitting the whole app or rebooting.
- Frontend polling and focus/pageshow/visible events reconcile a matching unseen native completion. They never infer success from a stale bar, quiet log, timeout or missing worker. RunID deduplication and the current running-worker guard prevent duplicate/overlapping starts. Reload only restores the queue when its saved autoQueue intent is enabled. Pause/finalisation error does not restart work. Waiting-item ordering/import/reorder behavior remains.
- macOS uses an owned `/usr/bin/caffeinate -i -w <hostPID>` assertion while processing; screen idle-off is allowed. It is released after a final acknowledged completion or pause, and process death also ends it. Normal queue handoffs reuse the assertion. If no work remains and the interface fails permanently, a120-second idle grace expires; a stale receipt cannot release another active run's protection.
- Windows requests ES_CONTINUOUS|ES_SYSTEM_REQUIRED on a dedicated owned thread and clears it on that same thread, respecting Windows thread-local semantics. There is no ES_DISPLAY_REQUIRED request. No global power preference is changed. Failure logs a diagnostic rather than discarding a conversion.
- Sleep prevention is automatic-idle protection, not a promise to keep working through manual sleep, lid sleep, thermal sleep, loss of power or hibernation. Explicitly sleeping the machine can suspend CPU/GPU work; wake resumes the OS process. No code tries to override those system decisions.

- Error handling also covers early click-action branches: unsupported source confirmation now displays the validation error while leaving correction/cancel available. Previously that branch escaped the later safely wrapper and left an unhandled rejection. This was found by the isolated legacy-test investigation, not assumed from the sleep incident.

## Verification / limits

Receipts live privately under .build/queue76. Rust native tests include an actual macOS pmset assertion for the owned caffeinate PID and its disappearance after Drop; retained completion/stale acknowledgement and existing ownership tests run alongside appearance tests. JavaScript policy tests cover receipt matching, duplicate/stale receipts, active ownership and queue intent. UI fixtures exercise dropped completion followed by wake/focus, duplicate wake, same-host reload, explicit stop and pause, plus existing append/reorder/failed-job scenarios.

No user job was paused, killed, resubmitted or rewritten. No real system-sleep test is initiated on the user's computer. Windows is cross-built/package-tested, not a Windows power-management runtime certification. No whole-film or model rerun is needed for the control-plane change. Samuel confirmed the app was closed after tests. The exclusive library lock and process check passed; dist/AniCanto.app and AniCanto.exe are now .76/build229, left closed. Prior .75 binaries are retained under .build/queue76/rollback. GitHub remains .75 unless separately authorised.

## Final results

- 7 native Rust tests passed, including real owned idle-sleep assertion creation/release on macOS.
- 47 related Python tests passed (queue ordering, desktop operation contract, shared desktop state).
- 33 browser queue cases passed with no JS errors, including missed completion, same-host reload, pause/explicit stop, new imports, failure handoffs and drag/reorder during completion. This uses an isolated native transport fixture, not real model inference.
- Investigation of the prior broad-suite failure found an actual early-click error handling gap; wrapping the delegated action in safely fixed the missing unsupported-source error. An isolated reproduction verified visible error and zero starts. Other historical assertions were updated to current language-selection rules; projects-page fixture lacked projects/engines/textModels and was corrected to the real backend schema. No production behavior was changed merely to satisfy a mock.
- Native startup, fresh Swift worker, contract, signature, matching164 Python sources, embedded Mac/Windows frontend hashes, payload/exe checksums passed. Privacy scan5994files,0private build/account identifiers. Windows power management remains untested on a Windows PC; no actual system-sleep experiment or full-film/model rerun was performed.
