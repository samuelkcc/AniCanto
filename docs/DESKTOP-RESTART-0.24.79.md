# Desktop restart and voice updates · 0.24.79/build 232

Each video card has a circular-arrow action in Basic and Expert mode. Open it without removing the video from the queue:

- **Restart conversion**: create a new source-analysis request using current production settings; recognise speech, process subtitles, translate and dub again. A paused task is restarted only by this explicit action. Normal Resume continues the original frozen request.
- **Regenerate voices only**: retain current dialogue, translations, source timing and exact audio-channel pairs; generate fresh recordings and export a new version. Existing recordings and movies remain available.
- **Add a voice track**: choose an installed engine and a supported language. The existing workflow prepares missing target-language text for the new track. Retain other channels and earlier movies. Duplicate channels require Replace rather than silent replacement.

The update drawer previews affected dialogue/channels and retained work before submitting. Engine/language selectors appear only when relevant; regenerating all channels does not pretend to use one engine selected in an unused field. Updates require an existing translated draft. Full restart also works on imported/unprocessed videos. Running work must be paused before starting another job. Selecting another video invalidates an open update's submission context.

The iPad sheet was used as a product-behaviour reference only. Desktop implementation uses its own existing native queue, immutable requests and versioned render/update plans. No private iPad code enters the desktop payload.

Validation/delivery receipts: .build/product79 (private). Windows remains a cross-built executable until tested on a physical PC. No GitHub publication is part of this task.
