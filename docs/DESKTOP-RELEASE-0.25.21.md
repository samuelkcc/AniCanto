# Windows Beta0.25.21

Task: Distinguish cached cloud files from active recall and resume temporary short reads.

Windows uses OFFLINE, RECALL_ON_OPEN and RECALL_ON_DATA_ACCESS file attributes to decide whether recall is required. A folder name alone no longer forces a full hydration read for a regular locally available Windows file. Unknown provider state remains conservative. A pinned preference alone does not override recall flags.

The provider reader resumes after temporary EOF or an OSError. It retains the byte position and checksum. Active progress has no total deadline. A120-second interval without new bytes fails. Real file-identity changes still fail, incomplete input receives no readiness receipt, and cancellation retains its owned-process boundary. Failed preparation uses failed state instead of generic cloud waiting. Diagnostics retain the reader stderr.

Evidence: Isolated cached-file, recall-flag, unknown-provider, interrupted EOF/read-error and failed-state tests pass. Existing cloud-read and cancellation cases pass. The user's Google Drive device failure has no new diagnostic yet; do not claim its exact triggering cause or a complete Windows device acceptance from these fixtures. Mac release remains0.25.17.

Attribute reference: https://learn.microsoft.com/windows/win32/fileio/file-attribute-constants

Use the shared desktop download record and synchronization script for all homepage languages. Existing media, models, recordings and frozen jobs remain.
