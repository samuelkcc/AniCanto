# Build storage and download retention

> Language standard: English, ASD-STE100 style. See docs/DOCUMENTATION-STANDARD.md.

## Decision

Samuel changed generated-build retention on 2026-11-18.
Keep only the latest desktop build version and the latest iOS/iPadOS build version.
This rule replaces the previous five-version budget.
Remove obsolete generated App bundles, archives, installation packages and compiler caches.
Keep source, records, required assets, matching-source and relink materials, installed models and owner data.
Keep App Store and TestFlight state records even when their obsolete local packages are removed.
A protected source parent must not protect obsolete generated children.

Samuel changed the storage rule on 2026-11-06.
Do not keep an obsolete download only because a new download takes time.
Remove an unused copy when its fixed source, revision and checksum permit restoration.
Keep installed application models and active build inputs.
Keep user videos, recordings, saved progress and finished outputs unless Samuel explicitly permits their removal.

## Previous defects

The retention tool rescued every recognized model file into `_retained-models`.
The tool did not give these files an expiry or an active-use check.
The archive reached approximately 118 GB.
This archive was separate from the installed desktop models.

The tool protected the complete `closure340` directory because it contained active source and required SDK inputs.
That protection also retained old generated applications and archives.
The directory reached approximately 95 GB.
Its old generated products bypassed the five-build rule.

The desktop cache screen listed temporary files and unlinked jobs.
An empty queue did not remove 60 older database projects.
Those projects protected job data that the queue-only project page did not show.
Separation data was outside the previous cleanup list.
The explicit saved-work cleanup implementation remains unshipped at this record revision.

## Removal procedure

1. Read the newest handover entries and identify active source, SDK and release inputs.
2. Measure allocated directory sizes and available volume bytes separately.
3. Find the original model download in the pinned catalog.
4. Read the complete local file and compare its SHA-256 value with the pinned value.
5. Verify HTTP 200 for the fixed revision download URL. Keep the URL, revision and checksum in a receipt.
6. Reject paths used through an active native dependency link.
7. Run `scripts/build-retention.py --retire-download-plan <plan>` without `--apply`.
8. Run the same command with `--apply` after its dry-run passes.
9. Run `scripts/build-retention.py --prune-nested-products` without `--apply`, then with `--apply`.
10. Verify active source hashes, current application metadata and retained build identities after removal.

The nested product pass removes only recognized old `.app` and `.xcarchive` directories inside `closure340`.
It keeps the latest mobile build number. Desktop products use a separate latest-version identity.
It does not remove parent workspaces, SDK directories, source delivery materials or loose evidence.
The tool rescues unique source and licence files before product removal.
Unknown product identities remain untouched.

Native protection reads the canonical project, the phone workspace and the actual production workspace.
It also resolves source-tree links before selecting old folders. A linked tools folder is an active input.
This check does not depend on the newest handover window. Do not follow compiler-cache trees during this scan.
The410dry run exposes this gap through the live producer scripts link to voice-delivery333.
The reviewed cleanup keeps that target. Regression tests cover this target without a handover entry.

Normal retention stops when a work folder contains loose media or recordings.
Such a folder needs an explicit review. A file extension alone does not prove that a recording is disposable.
An unmatched model hash also requires review. Do not identify it as the current catalog version.

## CoreDevice installation cache, 2026-11-12

CoreDevice stores generated installation deltas outside the project and outside the installed AniCanto data folder.
The path is `~/Library/Containers/com.apple.CoreDevice.CoreDeviceService/Data/Library/Caches/AppInstallationBinaryDeltas`.
The project retention script does not cover this Apple-managed path.
Repeated development and QA installations can retain older app copies under separate bundle identifiers.
The November12inspection finds ten AniCanto cache folders. The screenshot reports194.62GB.
Finder removal leaves zero items. This does not delete a device application's Documents or Application Support data.
Check that no installation is active before a reviewed cache cleanup. Limit removal to the approved bundle identifiers.
If macOS blocks direct cache access, use the approved Finder route. Do not weaken privacy permissions to run cleanup.
Measure physical free space after removal. APFS clones and local snapshots can retain deleted file blocks.
Do not report the directory size as physical recovered space.
Samuel approves reclamation of thirteen named local snapshots. Time Machine thins eleven.
The remaining two November10snapshots are mounted. APFS refuses deletion with error-69528.
Do not interrupt backups, force unmounts or expand the approved snapshot list to hide that limit.
The cleanup receipt is `mobile/Validation/conversion-audit427-2026-11-12.json`.

## Restoration

Read the exact file URL and revision from the removal receipt.
Download that file again when a future task requires the retired model.
Verify its full SHA-256 value before inference.
Use the retained build source and SDK inputs to rebuild a removed generated product.
Historical installed packages are not required to reproduce every old QA result.
Keep the original test results and record the tested package hash.

Required corresponding source, licence text, patches and relink materials are not ordinary caches.
Their source-delivery obligation can require retention even when an upstream download still exists.

## Space accounting

Logical bytes removed do not equal physical SSD space recovered.
Hard links, APFS clones and local backup snapshots can retain the same blocks.
Measure volume availability after deletion and report the actual difference.
Do not remove Time Machine snapshots as part of this procedure.
Samuel must make a separate explicit decision about local backup restore points.

## Matching-source archive placement

On2026-11-13 the retention script removes the scratch welcome-aspect430 copy of the cleaned SDK source archive.
The private recovery release still holds the exact archive. Its verified digest is unchanged.
Restore it to .build/compliance/source-delivery430/anicanto-local-media-sdk-sources.tar.gz.
The compliance parent is protected. Future builds refer to this protected path.
Do not put the only local matching-source archive in an expiring build folder.
Keep historical receipt paths as recorded; resolve the same source digest through the current material-delivery guide.
See mobile/Validation/source-delivery-retention438-2026-11-13.json.

## Required source-delivery archives, 2026-11-17

Keep explicitly named corresponding-source, source-delivery and source-offer archives outside the generated-build budget.
Also protect anicanto-local-media-sdk-sources archives. These are required matching-source materials.
The rule applies to .tar.gz, .tar.xz and .zip files. Keep these archives under compliance where possible.
Generic available-source-materials release snapshots now use the one-release budget. They are not a matching-source obligation marker.
The first guard also exempted generic release snapshots. A regression test exposed that overbroad classification.
The final guard preserves explicit delivery materials and retains the existing release-snapshot budget.

## Reviewed generated cleanup, 2026-11-18

Use `--scan-generated-caches <plan>` to record generated compiler-cache paths and tree identities.
Use `--generated-cache-plan <plan>` for a dry run. Then use the same command with `--apply`.
The pass excludes source, dependency checkouts, installed models and active native inputs.
It keeps an exact current Windows host when the delivered-product verifier requires that host.
AppleDouble metadata can be removed from an isolated restored App after its header and content hash pass.
These metadata files are not ordinary bundle resources. A ZIP restore must omit them.

Use `--scan-generated-products <plan>` to read older AniCanto App, archive and IPA identities.
Use `--generated-product-plan <plan>` for a dry run. Then use the same command with `--apply`.
The pass keeps the latest desktop version and the latest mobile version independently.
Unknown identities, newer products, live dependency targets and changed plans stop removal.
Before removal, the pass preserves copied program text with content hashes and original paths.
Loose films, recordings, source workspaces, required SDK inputs and records outside bundles remain unchanged.
Record logical bytes removed and the change in available volume space separately.

## Completed recovery checks

A successful isolated recovery check must not become a permanent duplicate source and binary tree.
Use `--retire-recovery-check <plan>` for a dry run, then use the same command with `--apply`.
Require successful desktop build and product-verifier receipts.
Keep all three exact release inputs locally outside the selected scratch child. Verify their SHA-256 values again.
Check all source-material rows. A changed recipe must match its recorded adapter and the retained canonical source.
Reject an unexpected top-level input, a unique source change, an active native link or a changed tree.
Copy the verified recovery receipt outside scratch before removal. Keep the source archive, maintenance tools and logs.
This removes a reproducible test workspace. It does not remove authoritative source, installed models or owner media.
