# Optional voice models: CosyVoice 3 and WenetSpeech-Yue

The in-app Help centre (`studio/web/help.js`) is AniCanto's main bilingual manual. This page records the current model choice in a compact form.

## CosyVoice 3

CosyVoice 3 can be selected in **Model centre** or **Change models**. On Apple Silicon Macs, AniCanto uses the pinned official FunAudioLLM PyTorch weights and CPU inference. Windows continues to use the official model with NVIDIA CUDA. The optional model download is about 9.7 GB; runtime and source packages add more. The Mac planning estimate is 12 GB of model working memory, plus system headroom. This is an estimate, not a measured peak. A Mac CPU render can be much slower than Drama 3, so test a short line before processing an episode. Cantonese accent, English clarity and speaker similarity require listening checks. Model setup checks hashes and model loading; this release does not claim a completed Mac end-to-end speech benchmark.

After setup, inference uses local files without cloud calls. Internet access is needed for first download or repair. The official model and source are published under Apache-2.0; AniCanto keeps pinned revisions, per-file SHA-256 values and upstream licence evidence. The earlier third-party MLX conversions remain unavailable because their individual provenance review was not completed. Old recordings and existing downloaded files are not deleted by this change.

## WenetSpeech-Yue

For new downloads, AniCanto offers **ZoengJyutGaai**, the Cantonese fine-tune. **Base** is retired from the download picker; an already installed copy remains visible so it can be reviewed or removed. WenetSpeech-Yue supports Cantonese only and is unavailable for English or bilingual dubbing.

## How to use / 使用方法

1. Open Model centre or Change models / 開啟「模型中心」或「更改模型」。
2. Select the voice engine and inspect download and memory estimates / 選配音引擎，核對下載量與記憶體估算。
3. Download and wait for file verification and model-load check / 下載並等待檔案校驗及模型載入檢查。
4. Audition a short Cantonese or English line / 先試聽一小句廣東話或英文，再決定是否轉完整影片。

If you keep more than one voice engine installed, AniCanto can use another compatible engine during its automatic voice recovery, but a fallback may sound different. The review report records the change. / 如保留多個已安裝引擎，自動修復可嘗試相容後備；聲線可能不同，校對報告會記錄。
