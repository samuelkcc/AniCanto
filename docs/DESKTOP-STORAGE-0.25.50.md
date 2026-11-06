# Desktop storage cleanup 0.25.50 / build 400

> Language standard: English, ASD-STE100 style. See docs/DOCUMENTATION-STANDARD.md.

An empty video list could leave older saved work outside the previous cache list.
The cleanup screen now lists owned saved jobs and separated audio as an explicit option.
The option starts unchecked. The video list must be empty, with no pending batch work.

Selecting this option removes old recordings, saved progress, intermediate job movies and separated audio.
Original media, registered exports, installed models and runtimes remain.
The cleanup screen links to the complete application storage breakdown.
Combined cleanup reports one continuous file count across saved work and temporary files.
The result names data removed. Shared blocks and backup snapshots can delay physical space recovery.

Source checks cover stale plans, path links, batch guards, registered exports and ordinary temporary-file cleanup.
The canonical operation guide is revision 166. The workflow control guide remains revision 61.
This desktop-only guide change does not require a mobile binary update.
Existing marketing screenshots remain. Native Windows execution requires separate acceptance.

See `BUILD-STORAGE-POLICY.md` for the development build and download retention procedure.
Development cache cleanup and application storage cleanup have separate roots and permissions.
