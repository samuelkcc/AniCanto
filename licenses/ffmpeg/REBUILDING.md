# FFmpeg source delivery / FFmpeg 源碼附件

AniCanto invokes FFmpeg and FFprobe as separate command-line tools. The selected native builds contain GPL components and are GPL-3.0-or-later; the original AniCanto application code remains MIT. Preserve all upstream notices. Do not describe the complete download as entirely MIT.

## What accompanies a binary release

Distribute the verified source-material archive beside the application downloads with equivalent access. It includes original application source, the exact native-library archives and recipes, locked desktop crates (including MPL-covered files), and the Windows FFmpeg materials listed in `windows-source.json`. A list of URLs is not a substitute for supplying these materials. No public hosting has been performed by the preparation tools.

每次分享程式下載版，都要一併提供已驗證嘅源碼附件。附件包含原創程式碼、原生工具及函式庫來源、編譯方法、版本對照及相關 Rust 套件。單獨提供來源網址清單並不足夠。準備工具唔會自行上傳或發佈。

## macOS arm64

`licenses/native-source-manifest.json` records the exact 12 Homebrew components used by the bundled FFmpeg/FFprobe and libraries. The source-material archive includes each retained source archive, any recipe patches, the original formula, a build receipt, the FFmpeg configuration, and AniCanto's relocation code in `scripts/build.py`. System Apple frameworks and the compiler/SDK are supplied by the build environment, not redistributed in this archive.

Build the dependencies using the supplied versions and formula options, then FFmpeg with the retained configuration. Only FFmpeg and FFprobe are distributed; FFplay is not shipped. The formula may build additional development tools. `scripts/build.py` copies the required libraries and rewrites their install names. The audit checks every actual non-system dependency against the supplied source mapping; it does not claim a bit-identical rebuild across different compilers or SDKs.

## Windows x64

The selected binary is `n8.1.3-18-g46d899d7a0`, from BtbN's `autobuild-2026-10-16-13-04` release. Its archive hash, full FFmpeg source commit, build-recipe commit and actual embedded configuration are recorded in `windows-source.json` and `windows-buildconf.txt`.

The retained BtbN recipes use a Linux/Docker build environment, target `win64`, variant `gpl`, addin `8.1`. Follow the upstream build README in the supplied recipe archive. The original entry points are `./generate.sh win64 gpl 8.1` and `./build.sh win64 gpl 8.1`. Restore the listed working trees from the supplied source archives and place submodule/build sources at their recorded parent paths; the original recipes otherwise fetch them from upstream. Source archives omit Git history. Set the FFmpeg working source to the recorded full commit rather than the moving release branch.

`windows-submodules.json` records exact gitlinks and explicit extra build downloads; `windows-cargo-source.json` records the locked registry archives with upstream checksums. Two immutable SVN snapshots (LAME revision 6835 and Xvid revision 2204) include per-file hashes. The upstream rav1e recipe updates the `cc` build helper; that general-purpose build-tool resolution is not represented as a promise of bit-identical compiler output.

AMF includes only the header source installed by the exact recipe and its original notice, excluding unrelated prebuilt SDK/FFmpeg binaries. OpenAPV test media and unused VMAF MATLAB/research binaries are also excluded. `source-subsets.json` records every retained file's hash against the original archives; all compiled library inputs and notices are retained. Test/source supersets for other dependencies remain under their own original terms.

## Verification and publication boundary

Run `scripts/ffmpeg_source_audit.py` against the actual application/native archive and retained materials, then `scripts/source_materials.py` against a fresh reviewed source candidate. The checks reject missing or changed inputs and a mismatching Windows executable version/configuration. A successful engineering check is not a rights-holder approval, legal opinion, application-quality guarantee, or permission to publish user media. Before posting a release, verify its final inventory/source mapping and obtain the developer's publication authorization.
