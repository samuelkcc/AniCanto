# Desktop Beta 0.25.45 / build 305
> Language standard: English, ASD-STE100 style. See docs/DOCUMENTATION-STANDARD.md.

Task: Publish the ordered review workflow and opt-in LAN diagnostics for Mac and Windows.

## Review report

Each dialogue card separates eight parts:

1. Read-only system translation.
2. Editable translation with Save words.
3. Original video audio.
4. Separated source voice.
5. Protected first generated recording with Listen.
6. Voice model and bounded parameters for one manual recording.
7. Later recordings with Listen and removal for unused takes.
8. The saved recording choice for the next export.

Save edited words before recording. A progress indicator appears before the native launch returns.
Launch failures clear the indicator and leave a visible error. A later attempt can start normally.
New recordings retain the source reference and recording seed. Sampling parameters can change the result.
Parameters affect the manual submission only. Frozen conversion settings and spent recovery allowances stay unchanged.

The first recording cannot be removed. Exported and selected recordings stay protected.
A saved choice keeps both its source path and its protected copy. The report highlights the correct source row.
Mandarin choices validate against saved Mandarin text. Other languages retain their own saved fields.
Export again creates another output from saved choices. Earlier outputs remain available.

## LAN diagnostics

Diagnostics is off after each app start. Open Welcome, Help centre, then the final LAN diagnostics chapter.
One switch selects the device IP and an available port. The app displays a fresh access code.
A read-only browser page refreshes settings, frozen requests and bounded log tails every three seconds.
Advanced connection settings permits a manual address and port while the service is stopped.

The service does not expose application RPC, command execution, media, or arbitrary filesystem access.
Known credential fields and credential-bearing log lines are omitted. Dialogue and local paths can still be visible.
Use a trusted private network. HTTP is not encrypted. Stop diagnostics after use.
Unrecorded failures and crashes before host startup remain outside this view.

## Validation scope

The source passes 42 focused Python cases and five Node review scripts.
Four-language browser flows cover saved edits, source playback controls, manual parameter requests, loading, choices and export submission.
The launch-failure case clears loading and permits another attempt.
The browser uses real isolated draft and choice RPC. It simulates model execution and uses synthetic audio.
The earlier native Mac diagnostic switch and authenticated HTTP endpoint pass their isolated checks.

Final release package verification and artifact hashes are recorded in the release receipt.
Windows execution, Windows firewall access, cross-computer diagnostics, whole-film inference and listening acceptance remain unverified.
The Mac app uses an ad hoc signature and is not notarized. Optional model weights are separate downloads.
Private mobile applications and device validation are excluded from public source delivery.
