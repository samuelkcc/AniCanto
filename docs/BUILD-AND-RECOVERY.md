# Source delivery and restoring AniCanto

## What to keep

For each desktop release, keep the matching Mac ZIP or Windows EXE, `available-source-materials.tar.gz`, and `SHA256SUMS.txt`. The source attachment contains the published desktop application source and the checked third-party source inputs, patches, lockfiles and available build recipes assembled by `scripts/source_materials.py`. `SOURCE-MATERIALS.json` identifies its contents; `AniCanto/SOURCE-MANIFEST.json` identifies application files. GitHub's automatic source ZIP contains the repository snapshot, **not** all separately attached third-party source materials.

This can recover the published application code if the development computer is lost. It is **not a complete computer or project backup**, a bundled development environment, or a guarantee of a clean-machine/bit-identical rebuild. User videos, projects, generated takes, settings, installed runtimes, downloaded model weights and credentials are not published. The iPad development tree is outside this desktop source delivery.

Back up personal projects, media and any locally held model files separately, with the app closed. If only the application is lost, reinstalling the matching published binary is the simplest recovery; rebuilding requires a development setup.

## Restore and verify the source

1. Download the four release assets from the same version. Check the three archive/executable digests against `SHA256SUMS.txt` (for example, `shasum -a 256` on macOS or `Get-FileHash -Algorithm SHA256` on Windows).
2. Extract `available-source-materials.tar.gz` to a new development folder. The `AniCanto/` subfolder is the application source. Keep the neighbouring `native/`, `tools/`, `desktop-crates/` and other source materials alongside it for reference and licence obligations.
3. Verify files against the two JSON manifests. Preserve notices, licence texts and patches when rebuilding or redistributing. Optional model weights have separate licences and download revisions.

## Development environment and build entry points

The desktop interface uses Tauri/Rust with a shared Python worker. The current Mac adapter also needs Swift/Xcode on an Apple Silicon Mac. Windows uses the x64 MSVC target; builds from macOS use `cargo-xwin`. Python 3, Rust/Cargo, the platform SDKs, FFmpeg and the applicable native/Python prerequisites must be installed or prepared. Model inference has its own deployment requirements.

- `VERSION.json`, `core/Cargo.lock`, `studio/src-tauri/Cargo.lock` and `windows/launcher/Cargo.lock` pin release identity and Rust dependencies.
- `scripts/prepare_shared_studio.py` generates the shared interface assets from checked source originals.
- `scripts/build_shared_host.py` builds the Mac host; `--target x86_64-pc-windows-msvc` builds the Windows host. Its `--locked --offline` build requires the Cargo dependency cache to be prepared first. Attached crate files are source inputs, not an automatically configured Cargo vendor directory.
- `scripts/build.py` is the cold Mac native application entry point. It expects its native tools and assets to be prepared; choose an isolated output through `CANTO_BUILD_APP`. It is not a one-command replacement for installing all prerequisites.
- `scripts/stage_release.py` is an incremental Swift worker build and requires an existing bundled application in `dist`; it cannot bootstrap a missing base release by itself.
- `scripts/package_shared_studio.py` combines the built Mac host with the versioned staged native application. `scripts/build_portable_windows.py` combines the built Windows host, launcher, helpers and prepared tool payload; it also requires prepared tools and cached locked dependencies.

See [shared desktop architecture and build validation](SHARED-STUDIO.md) and the native/component manifests under `licenses/` for details. The checked build paths used an existing prepared development environment. **A full clean-computer rebuild has not been certified.** General-purpose compilers/SDKs and optional model downloads remain external prerequisites; changes in those tools or download availability may require maintenance.

## Before replacing an installed application

Build into a separate staging directory. Check source/payload identity, required notices, private-data scans, signatures and startup before installation. Stop the application before replacing its files, keep a rollback copy, and preserve user projects. Test actual inference on the intended hardware: cross-compilation and a matching archive hash do not establish Windows GPU or voice quality acceptance.

## 中文說明

每個桌面版本會同時提供對應源碼及第三方來源包，可以下載返嚟繼續修改或重建。呢份包唔係成部電腦嘅備份，亦未驗證全新電腦一鍵重建：需要另外準備編譯工具、SDK、執行環境同模型。你自己嘅影片、專案、錄音、設定同已下載模型要另外備份；唔會公開放上 GitHub。只需要恢復使用時，直接安裝相同版本嘅 Mac ZIP／Windows EXE 會較簡單。
