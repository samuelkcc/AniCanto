# Lightweight Mac deployment

Introduced in 0.22.11 and installed with 0.22.12 (build 140), the lightweight package keeps the native interface, media player, FFmpeg,
verified pip installer wheel and artwork in the signed app. Python environments, optional
Ollama and large model weights live in
`~/Library/Application Support/SamCantoSync`, alongside existing model storage.
Replacing the app does not remove projects, exports or downloaded models.
`SAM_CANTO_DATA` can redirect storage for isolated tests.

Welcome shows installed models and the required runtime status. Setup retains
compatible existing model selections, including a larger installed model when
the shared hardware policy can use it. Runtime packages use exact tested
versions; a newer Python library is not automatically compatible.

The one-click setup checks each required environment's Python version,
architecture, installed package versions and actual imports. Healthy packages
are left in place. Missing/version-mismatched packages are installed with standard pip;
its cache remains available across retries. If imports fail despite matching
metadata, wheel RECORD hashes identify the damaged distributions. Only those
packages are reinstalled, once, from cache when possible. An unexplained import
failure does not trigger a blind complete reinstall. An interrupted/failed check
cannot leave a successful verification receipt.

Receipts include a fingerprint of the requirements and import probe. Welcome
rechecks package versions and imports before reporting a previously verified
runtime ready. Auxiliary model readiness checks the actual separator/speaker
files as well as markers. Existing pinned model download helpers verify size
and SHA-256 on download/repair and preserve resumable partial files. Welcome's
model inventory uses file completeness checks; it does not hash every large
model file on every opening.

Required initial runtimes are base Python/audio, text/Drama, independent ASR and
separation, plus the selected voice engine's environment. Unselected voice
engines are not installed by the initial setup. Engine-specific installers
reuse a matching runtime receipt instead of running a second dependency
resolver. Downloaded runtime license metadata and notices appear in About.

## Building and verification

`python scripts/stage_release.py` stages and signs a lightweight app by default.
A cold native build uses `scripts/build.py`. `CANTO_BUNDLE_RUNTIMES=1` is an
explicit development option for a larger embedded-runtime build. This release
remains Apple Silicon; changing the packaging does not create an Intel build.

Evidence is kept in `.build/mac-thin/`: pinned wheel availability, actual clean
runtime installs/imports, repeated setup with zero package changes, an offline
missing/corrupt-package repair retaining an untouched healthy package, Python
regressions, native deployment checks, signature checks and the installation
receipt. Runtime availability tests do not certify an entire episode's voice
quality. Windows/CUDA execution remains a separate user-machine validation.

Welcome bulk download cleanup and export-progress corrections are documented in
`WELCOME-DOWNLOAD-MANAGEMENT.md`. Release / installation evidence for 0.22.12
is in `.build/qa291/`; user project metadata was preserved during replacement.


## Private Python installer migration

New candidates use CPython standalone 3.11.17 (macOS arm64) and 3.12.15
(Windows x64), pinned to the official 20261013 release, and pip 26.2.1.
`Resources/python-installer.json` records archive sizes, SHA-256 checksums and
exact retained notices. System Python, user pip settings and Homebrew are not
used at runtime. `python -m venv --without-pip` creates each isolated environment;
pip runs from its verified bundled wheel inside that environment.

Healthy existing environments, their private Python bases, model downloads and
receipts remain usable. Missing environments use the new pinned base; failed
installs retain download/cache data, and a ready receipt is written only after
package versions and imports pass. Corruption repair reinstalls only the
identified damaged packages with `--no-deps`; it does not force-reinstall the
complete lock. NVIDIA/AMD/Intel/CPU PyTorch selection remains explicit.

New Mac/Windows payloads exclude uv and its notices. Historical uv evidence in
the development source is retained for older builds; it is not an active
dependency or proof that previously delivered binaries no longer contain uv.
The new pip cache and historical uv cache are both covered by app cache cleanup.
For a source checkout, run `python3 scripts/python_installer_assets.py` to fetch
the pinned pip wheel before building (release build entry points also do this).

macOS fresh install and repair are tested in isolated data. Windows bootstrap
and CUDA/ROCm/XPU execution require a Windows test computer; cross compilation
and mocked command checks must not be described as Windows execution tests.
