# Restore and rebuild the desktop application
> Language standard: English, ASD-STE100 style. See docs/DOCUMENTATION-STANDARD.md.

## Keep the source and matching release assets

The public desktop repository contains Mac and Windows application source only.
Private iPhone and iPad implementation belongs in the separate private mobile repository.
Keep the matching source-materials attachment. GitHub automatic source ZIP files do not include every third-party source attachment.
The 0.25.54 release keeps its original `v0.25.54-beta` tag. It is now the latest formal release.

## Recovery command

Install Python 3.12 or newer, compatible Xcode tools, Rust and cargo-xwin on an Apple Silicon Mac.
The tested environment uses Xcode 27.2, Python 3.14.7, Rust 1.97.0 and cargo-xwin 0.23.0.
Install the Rust Windows MSVC target. The recovery build selects Microsoft SDK 10.0.22621.

Clone the current public desktop repository. From that checkout, run:

```sh
python3 scripts/restore_desktop_release.py --destination ../desktop-recovery --assets ../release-downloads --download --build
```

Use a new destination. The tool does not replace an installed App or read personal projects.
The tool downloads the exact Mac ZIP, Windows EXE and source attachment for 0.25.54.
It checks their pinned SHA-256 values, 4,700 source-material files and 3,422 application-source files.
It restores unchanged native tools and the framed icon from the matching public binary package.
It creates an isolated Cargo home and vendors 479 locked crates from the source attachment.
The older notice recipe needs a checked adapter to read that Cargo home. The original recipe remains available beside its hash.
The build prepares both hosts, packages both platforms and runs both product verifiers.
The output receipt and logs remain inside the recovery directory.

## Verification limits

On 2026-11-18, the separate preparation and build commands pass in an isolated directory.
Both Mac and Windows product verifiers pass. The new combined `--build` entry point has not been rerun as one command.
The rebuilt Mac App passes signature and native-contract checks. Windows hardware execution and GPU inference remain untested.
This is an application-source rebuild with checked released third-party binary tools.
It is not a complete compiler, operating-system SDK or third-party-tool rebuild from source.
It does not certify a bit-identical output or future upstream availability.
Xcode, Microsoft SDK access, platform accounts and compatible development tools remain external prerequisites.

## Source and asset coverage

The source attachment includes application code, active interface artwork, synthetic voice references, notices, patches and locked dependencies.
The older source allowlist omitted `Resources/app-icon-art-framed.png`.
The restore tool recovers that asset from the checked Mac release. New source exports include it directly.
The ZIP extractor omits AppleDouble metadata so those files cannot break bundle signing.
Required source-delivery and relink materials remain separate from disposable compiler output.

## Personal recovery

User films, saved projects, generated recordings, model libraries, account credentials and signing keys are outside this code backup.
Back up personal data separately with the App closed.
Optional models use pinned download definitions. Do not publish personal media or signing material with application source.

## Local retention

From 2026-11-18, keep only the latest generated desktop version and latest generated mobile version.
Keep all required source, assets, records and matching-source materials.
Run the reviewed retention tool before removal. Never treat source workspaces as ordinary compiler caches.
