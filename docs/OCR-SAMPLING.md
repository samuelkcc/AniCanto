# OCR sampling and timing / 字幕辨識抽樣與耗時

AniCanto 0.24.17 retains ASR as the primary translation source. Subtitle OCR provides time-local hints; missing, wrong or unsampled captions cannot remove a heard utterance.

## Speech-guided auxiliary OCR

1. Recognise source speech and retain its timestamps.
2. Inspect at most 18 lower-screen samples to locate caption bands.
3. Decode/crop a 0.4-second candidate grid once, then retain adjacent image pairs near each heard turn. Long turns receive additional pairs about every two seconds. Very short turns may have one usable sample.
4. Run the retained frames through one helper/model instance. Windows uses pinned RapidOCR 1.4.4 on ONNX CPU with bounded threads; this change does not claim CUDA OCR or introduce a vision language model. Identical image bytes reuse an OCR result while preserving every selected frame index.
5. Associate OCR text with the original heard turn. Never synthesize caption-only dialogue from sparse samples.

Pure OCR, where no ASR timing is available, retains the previous 0.2-second dense pass. Sparse timestamps come from actual source PTS, not a dense-frame ordinal. Sparse single-hit hints are allowed because they are auxiliary evidence; they cannot delete or retime a source turn.

## Resume and diagnostics

A completed OCR cache is keyed by source identity/size/modification time, trim window, OCR region/auto-region settings, colour/stability, source speech windows, platform and sampling revision. A changed source or setting invalidates it. An incomplete helper result never becomes a successful cache.

`ocr-progress.json` records completed/total frames; `ocr-metrics.json` records sampling mode, extracted/recognised counts, baseline dense count and elapsed seconds. Debug conversion details preserve these metrics after finalisation. These files belong to app-private jobs, not the user's export folder. Timing depends on video decoding, OCR engine, CPU and subtitle density; Windows laptop runtime must be measured on that laptop.

原聲為主時，OCR 只讀對白附近嘅代表畫面，唔再對同一句反覆辨識十幾次。純 OCR 保留精細掃描。日文聽寫仍然係翻譯依據，唔會因為 OCR 漏字而刪走對白。完成辨識可以續用快取；轉換記錄會保留實際畫面數同耗時，方便測試後比較。
