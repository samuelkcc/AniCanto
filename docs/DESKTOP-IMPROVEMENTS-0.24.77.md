# Desktop workflow improvements · 0.24.77 candidate

Independently authored AniCanto implementation; study product behaviour only. No external app code imported. No GitHub publication authorised.

## Implementation checklist
- [x] Native-owned durable queue and resume/pause boundary
- [x] Completion coverage and actionable report
- [x] Original / separated / generated waveforms and audition
- [x] External subtitle offset / two-anchor drift preview
- [x] Evidence-based source boundary proposals
- [x] Regeneration impact preview and retained recordings
- [x] Bulk list removal with all / none / completed selection and archived metadata
- [x] Hardware capability, memory-aware recommendations and CPU alternatives on Mac / Windows

Original media, submitted requests, recordings, installed models and previous exports must be preserved. Hardware advice is an estimate until actual inference is verified. No claim of Windows physical-machine acceptance from cross-build tests.

## Hardware paths

Windows: detect the adapter name, physical RAM and dedicated VRAM with DXGI/WMI; query compute capability with nvidia-smi when available. Select the pinned PyTorch 2.9.1 CUDA 12.6 profile for GTX 10/Pascal (also covered Maxwell devices), CUDA 12.8 for RTX 20/30/40/50. Unknown or unsupported architecture uses CPU. CUDA runtime flavour is included in each environment identity, so an existing cu128 environment cannot masquerade as the required cu126 environment. A changed environment forcibly replaces only Torch/torchaudio, with the remaining pinned requirements retained. Matrix and convolution kernels must pass; failed GPU preparation retries on CPU. Model loading and speech probes are still required. GPU vendor/VRAM is not proof of inference success.

The pinned Drama 3 GGML CUDA 12.4 archive has sm_61 architecture strings in the CUDA DLL and server; CUDA 13.3 remains the existing Blackwell-specific Drama path. Binary architecture inspection is not physical-card speech validation. PyTorch toolkit versions and the separate Drama executable toolkit need not be identical; each component loads its matching libraries.

Only the official Windows ROCm 7.2.1 Radeon allowlist is offered: RX 9070/9070 XT/9060 XT, Radeon AI PRO R9700, RX 7900 XTX, PRO W7900/Dual Slot and RX 7700. This is selected RDNA3/RDNA4 hardware, not every RDNA card. Unsupported RX 5000/6000 and unlisted 7000 models keep CPU. Drama 3 currently retains CPU on AMD; supported analysis modules may use ROCm after verification. Integrated GPU shared memory is never added again to system RAM.

Stages are sequential. Large translation or supported CPU-capable models may use system memory when they do not fit VRAM; the real stage device and free memory are checked again at load time. Full Drama CPU remains available as a slower choice. CPU alternatives are explicit model plans, not a promise of equal speed or voice quality. Apple Silicon retains Metal/MLX paths and a single unified-memory budget; unsupported Intel Macs are not silently offered unavailable Apple models.

Primary references (metadata and documentation only, no external application code imported):
- https://pytorch.org/get-started/previous-versions/
- https://raw.githubusercontent.com/pytorch/pytorch/release/2.9/.ci/pytorch/windows/cuda126.bat
- https://raw.githubusercontent.com/pytorch/pytorch/release/2.9/.ci/pytorch/windows/cuda128.bat
- https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2.1/docs/compatibility/compatibilityrad/windows/windows_compatibility.html

## Workflow boundaries

The native process owns future queue handoffs and persists attempted IDs before preparing each video. The live persisted list supplies next order and newly added items. Preparation requiring source-language confirmation is skipped with a visible per-video notice; other ready items continue. Explicit Pause cancels the generation token before any slow preparation can launch another child. A new process never silently restores an old automatic-run intention. Closing the whole app still pauses work; this is not an always-running system service.

List removal is metadata only, with all/none/completed selection, a locked running item and immediate Undo. Archived rows remain under studio/removed-videos.json; original videos, work, recordings and exports are untouched.

Audio inspection uses bounded cached PCM-derived peaks, never model inference. Original and separated intervals share source clocks; generated recordings show their own duration. Interval audition and loop do not edit source audio. Waveforms are inspected in a consistent side drawer; whole-film spectrogram rendering is not part of this patch.

External subtitle correction offers constant offset and two ordered anchors with a preview. It preserves original subtitle bytes and original evidence times, applies only the explicit mapping to playback/new submissions, and rejects changes to a running/paused submission. The imported script remains context; original speech supplies dialogue times.

Source split/merge suggestions require actual ASR word clocks and pauses. There is no character-count interpolation or new ASR pass. Split application requires both text halves for every existing script/custom display caption. Draft/analysis fingerprints reject stale suggestions. Prior recordings/exports stay retained; changed lines require new takes.

Regeneration preview shows affected dialogue IDs/count, exact language/engine tracks, retained tracks, retained source/script work and parameters. The submission revalidates the preview fingerprint. Previous recordings/exports remain available. Coverage reports count stored recordings and missing line IDs; presence is never labelled a pronunciation pass. Language uncertainty stays advisory under the existing first-audible-take policy; missing/corrupt audio is the automatic repair target, and existing duration-shortening remains intact.

## Validation and delivery

Candidate validation and packaging receipts are stored privately under .build/product77. Physical Windows GPU speed/quality, whole-film background operation and previously documented model limitations still require field validation. No GitHub publication requested for this patch. No iPad source changes.

## Follow-up: CUDA 13 and private iPad publication

Driver-qualified RTX 40/50 (and compatible newer architectures) now prefer the pinned PyTorch 2.9.1/cu130 profile when the NVIDIA driver major is at least 580. Unknown/older drivers retain cu128; GTX 10/Pascal remains cu126. CUDA 13 is not inherently required for RTX 40. Failed CUDA13 matrix/convolution validation tries the compatible cu128 runtime before CPU. A successful fallback is remembered against GPU name/driver; a failed GPU runtime can retain the verified CPU path rather than making Welcome demand deployment repeatedly. Physical GPU and system memory remain separate even when CPU execution is selected. Model-specific Drama CUDA speech failure also retains its verified CPU choice under Auto. Explicit GPU redeployment still requires real loading and speech checks.

PyTorch and the separate full Drama executable use their own matched toolkit/libraries. The existing Drama CUDA13.3 CUDA DLL has sm_89 markers as well as other architectures; on a driver-qualified RTX40 this profile can be offered. Architecture string inspection alone is never claimed as physical inference validation. CUDA12 remains a compatible fallback, and unsupported native model paths use CPU.

Primary references:
- https://raw.githubusercontent.com/pytorch/pytorch/release/2.9/.ci/pytorch/windows/cuda130.bat
- https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html

Samuel requires the iPad implementation to remain private. Public desktop main and the published .75 source-material archive were checked (archive SHA matched the published checksum). No mobile application tree, private Xcode project or IPA was present. Public privacy policies and generic cross-platform workflow documentation are retained. Local export/ignore rules and tests now explicitly exclude private app paths, accidental nested copies, iPad/StoreKit Swift implementation names and iOS build products. No Git or remote publication/visibility change was made. See PUBLIC-DESKTOP-PRIVATE-IPAD.md; this is not a complete historical exposure audit.

Native queue parity also retains the explicit Resume-all-attention intention. Already-exported attention items do not repeat source-language detection. Any native-owned completion clears the frontend scheduling intent, including repair tasks whose action differs from a full batch; only the native session schedules subsequent workers. Added a persisted-attention queue test and a browser handoff test to prevent duplicate launches.
