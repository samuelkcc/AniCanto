# Public distribution review / 公開分發審核

Reviewed: 19 October 2026; patch candidate 0.24.27 in preparation; previous Mac test build 0.24.25 (AniCanto, formerly CantoSync). **No public release is approved or authorized.** This document records the engineering evidence reviewed; it is not legal advice or approval from a rights holder. The issue register is [licenses/distribution-review.json](../licenses/distribution-review.json).

## Original code and third-party materials / 原創程式碼與第三方材料

SCKC's original application code remains MIT. Preserve the root LICENSE and the original third-party notices. Vendored libraries, fonts, icon geometry, models and voice recordings retain their own terms. A root MIT label does not relicense the whole distribution. Separate subprocess execution is relevant to the integration analysis, but does not waive obligations for the executable being distributed.

AniCanto 原創程式碼維持 MIT。第三方程式庫、字型、圖示、模型及錄音各依其授權；根目錄 MIT 唔會將它們重新授權。以獨立程序執行 FFmpeg，亦唔會免除分發 FFmpeg 本身嘅通知與源碼要求。

## Corrections made / 已補正

- Added missing upstream licence notices for bundled ANTLR, jieba and jieba_fast wheels, with provenance and hashes.
- Added the Feather geometry acknowledgement and actual bundled Noto font copyright.
- Distinguished WeSpeaker's **CC BY 4.0 weights** from its code licence; preserved attribution, source, revision and licence link. New setup installs the evidence beside its model.
- Completed B02 exact auxiliary model/data evidence: publisher MIT declaration for RoFormer, all converted GPT auxiliary tensors compared with official weights, exact RapidOCR/Paddle model hashes and licence terms, plus pinned NLTK/Open JTalk data notices. See the retained manifests; inference weights were not changed.
- Added an allowlisted local source export that rejects executable files, symlinks, private paths and common credential formats. It excludes release files, tool binaries, wheels, voice recordings, build output and historical reports.
- Added a checksum-verifying source-material archive builder. The archive is labelled incomplete until exact binary/build-input coverage is verified.

已補回隨附套件通知、圖示及字型署名，分清聲紋模型權重授權，並加入安全原始碼匯出及配套源碼整理。呢啲修正唔代表所有安裝包已獲准公開。

## Remaining conditions / 仍須完成

B01–B04 are now recorded as resolved for the prepared profile, subject to the exact final candidate/source-attachment receipt. This includes the uv-free installer, model/data evidence, native/desktop source coverage, retained notices and original synthetic reference bank. B05 remains the final receipt and publication hold. Windows on-device startup/GPU tests are functional acceptance work and have not been represented as executed. Fetch failures or a missing notice must not be concealed by supplying an invented copyright statement.

**Source-only publication and binary releases are separate decisions.** A clean source candidate does not authorize uploading the development checkout, an installed app, downloaded runtimes/models, or the private test folder. Conversely, an unresolved binary-only dependency does not automatically prohibit sharing independently licensed original code. Review the exact candidate's contents and retained third-party notices.

原始碼候選版同 `.app`／`.exe` 下載版要分開判定。乾淨嘅候選版唔等於可以直接上傳整個開發資料夾；而只影響二進位套件嘅問題，亦唔代表獨立原創程式碼必然唔可以分享。需要按實際包含嘅檔案判定。

## Fish Audio and media rights / 模型與影音權利

Built with Fish Audio. Optional Drama 3 weights retain the [Fish Audio Community License 1.0](https://huggingface.co/fishaudio/drama-3/blob/main/LICENSE), including attribution, consent, commercial and hosted-service conditions. They are not MIT or an unrestricted open-source model. AniCanto does not grant rights in anime, subtitles, performances, trademarks or a person's voice. The UI acceptance flow is evidence of the app's consent mechanism, not proof that every future use is lawful or that a legal contract is enforceable in every jurisdiction.

Drama 3 權重依 Fish Audio Community License，唔係 MIT。軟件唔會授予動畫、字幕、演出、商標或真人聲線權利。使用條款確認功能唔等於已證明所有用途合法。

## Alternatives checked / 已檢視替代方向

The 19 October checkpoint records alternatives in the issue register. These are engineering candidates, not cleared replacements:

- **uv / SeaHash:** replaced in current source and packaging paths with pinned standalone CPython + standard venv/pip. The signed Mac component-test app contains no uv and passed its real native cold-start entry point, installation of 35 pinned worker dependencies, repeat setup and selective repair. Python install-only bytes were checked against all 2,026 Mac and 3,384 Windows files in the exact full builds; build metadata and notices are retained in `licenses/python-installer`, including the missing zlib-ng notice recovered from the exact pinned dependency archive. Windows GPU command selection is regression tested, and Windows execution remains pending. Actual v0.24.22 packages passed the recorded binary/privacy/source checks; v0.24.23 requires its own matching receipt before replacement. See the [standard venv documentation](https://docs.python.org/3/library/venv.html).
- **Separation weights:** replacement is unnecessary: the original publisher selected MIT at the pinned RoFormer revision. The exact weight and declaration are retained with standard MIT terms and attribution, without inventing a copyright holder/year. [Hugging Face licence documentation](https://huggingface.co/docs/hub/repositories-licenses) explicitly recognises standard licence declarations in model-card metadata. Converted HuBERT/RoBERTa and OCR evidence are also verified separately.
- **FFmpeg:** retain the existing architecture and supply matching source/build materials. A different download location does not remove the applicable obligations. An LGPL-only rebuild is an alternative only after codec and export compatibility checks, with its own remaining obligations. See [FFmpeg guidance](https://ffmpeg.org/legal.html).
- **Reference speech:** bank revision 3 replaces all four human Common Voice clips with original synthetic Cantonese conditioned only on the existing synthetic Kokoro mixtures. Independent large-v3 ASR and signal checks screened the candidates; Mandarin-drift candidates were rejected. Preserve generator notices and generation evidence. CC0 applies only to rights SCKC holds in the recordings/prompts, without re-licensing upstream models or guaranteeing identity rights. The retained synthetic-reference evidence applies to the current reviewed profile.
- **Public media:** use original/generated demonstrations. Exclude private episode frames, transcripts and generated episode audio.

暫時保留已測試嘅本機功能；替代工具或模型需要先完成授權證據及 Mac／Windows 相容測試。唔會為咗清空審核清單而直接換入未驗證嘅組件。已安裝 0.24.23；v0.24.24 候選配對獨立封裝及檢查後先換檔。Windows 仍待真機啟動與 GPU 驗收。

## Preparing local candidates / 本機候選版

Use a fresh destination under `.build/public-review/`:

```sh
python3 scripts/public_source.py --output .build/public-review/candidate/source
python3 scripts/source_materials.py --source .build/public-review/candidate/source --output .build/public-review/candidate/available-source-materials.tar.gz
```

The source export omits executable prerequisites, models and private recordings. It includes only the seven hash-approved original synthetic reference clips. Before building, supply the separately reviewed native tools or rebuild them from the supplied matching source, then regenerate frontend assets with `scripts/prepare_shared_studio.py`. Preserve the source manifest; do not add user videos to make screenshots. The source-materials command checks its inputs and fails if a required collected archive is missing; a successful run verifies the known selected source-input coverage and archive readback, without authorising publication or promising legal clearance for future media uses.

No command above creates a repository, uploads files, publishes a release, or modifies installed user projects/models. Keep publication disabled until the exact selected distribution passes review and the developer authorizes it.

## Primary guidance / 官方依據

- [FFmpeg distribution guidance](https://ffmpeg.org/legal.html)
- [Mozilla MPL 2.0 FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
- [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)

These are upstream requirements and guidance. Compatibility and rights conclusions still depend on the exact combination and distribution method.

## Prepared profile and final delivery / 本次準備範圍

The root MIT grant remains unchanged. Eleven model conversions without sufficient licence evidence remain disabled for new downloads; unlicensed converter model-card text is excluded from public files. All active reviewed models retain their own terms. Windows FFmpeg notices include the actual upstream notices and source package declarations; full editable corresponding sources are supplied in the matching-source attachment. Publisher Cargo SPDX declarations are retained together with applicable standard terms, as described by the [Cargo manifest reference](https://doc.rust-lang.org/cargo/reference/manifest.html#the-license-and-license-file-fields); no author or copyright year is fabricated.

已確認嘅組件保留各自授權；未能確認嘅 11 個模型變體唔會開放新下載。原創程式碼維持 MIT，唔會將其他模型或工具重新授權。最終分享需要連同匹配嘅源碼附件及通知，並繼續排除私人影片、字幕與錄音。GitHub 發佈仍按開發者要求暫停。

## Release privacy / 發佈檔私隱

Release Rust builds use compiler path remapping and omit hardcoded development checkout discovery. Retained native C/C++ inputs have only same-length diagnostic source-location text normalised, including UTF-16 strings; machine-instruction sections are verified byte-identical. Original tool inputs remain private and the modification notice/provenance is supplied. The final receipt records a scan of actual Mac files, the outer Windows executable and every embedded payload entry for local account/build identifiers. Required third-party author attributions remain intact.

## Retained optional voices / 保留可選配音引擎（0.24.23）

VoxCPM2 and both WenetSpeech-Yue / CosyVoice2-Yue variants remain active. The exact model revisions in `licenses/model-evidence.json` contain publisher Apache-2.0 declarations; their notices and pinned download hashes remain included. They are separate from the eleven optional conversions lacking confirmed licence evidence. WenetSpeech-Yue here refers to the downloadable TTS models, not redistribution of the training corpus.

Windows now registers these native PyTorch variants and installs them in the same app-owned folders used by inference. Model selections persist per engine. Each engine and selected variant must pass its own model-load and speech probe; a successful probe for another engine does not certify it. WenetSpeech-Yue uses the CPU adapter and supports Cantonese only. Native Windows device execution and quality testing remain required; deployment-planner tests do not establish GPU inference acceptance.

VoxCPM2 同 WenetSpeech-Yue 兩款配音模型保留，官方模型卡均標示 Apache-2.0；唔屬於停用嘅 11 個可選轉換版本。Windows 已補上模型登記、共用安裝路徑及每個引擎獨立測試。WenetSpeech-Yue 只提供廣東話，現用 CPU 路徑。Windows 實機載入、出聲及品質仍需驗證。

CosyVoice 3 official native Windows weights and the existing Mac Drama 3 remain available. The three unverified third-party CosyVoice 3 MLX conversions remain blocked. An official-weights local conversion requires provenance checks for every additional input, including the converter's speaker encoder; no such conversion or full Windows Drama 3 GPU support is claimed in this patch.

## Assistant identity correction (0.24.24)

Eight original generated assistant atlases now follow the existing mixed-style Welcome cast; the original lavender assistant and all 36 covers are unchanged. Generator prompts, input roles, original atlas hashes and exact canonical cover hashes are retained in the artwork records. This is an original-art asset correction, with no added third-party dependency or model licence. It does not claim legal clearance of future media or other external content.

## 0.24.25 source transparency and recovery patch

About now shows a searchable expected-file inventory generated from pinned model manifests: source URLs, revisions, per-file SHA-256 and explicit blocked/retired labels. The catalogue is not proof of a fresh check of installed bytes. Model centre repair performs that check separately. No download block or model licence decision was relaxed. The supplied mlx-community CosyVoice3 8-bit link is already the blocked catalogue artifact at revision `177baf277ac75e04e810f7db7f0d9c0ce5a17854`; its model card links the Apache-2.0 original but provides no separate licence declaration for the converted artifact. Official-weight local MLX conversion remains an alternative under investigation, including its speaker encoder and tokenizer inputs. No new rights-holder approval is claimed.

The exclusive native host now recovers interrupted queue metadata once before owning a worker, retaining requests, scripts and recordings. Ordinary RPC polls and preview adapters never perform that recovery. Real owned tasks still block destructive model operations. Missing diagnostic sidecars no longer prevent terminal queue state from being saved. Native finalization failures stop automatic queue continuation and surface a recovery message. Publication remains on hold.

The source inventory distinguishes the download publisher from any declared base model, using the retained model-evidence index. Missing base-model declarations are shown as unrecorded rather than inferred from a repository name. The repair path verifies existing blocked-model files locally but does not bypass the download licence gate.

### Other CosyVoice 3 MLX candidates

The `aufklarer/CosyVoice3-0.5B-MLX-4bit` and `-8bit` model cards explicitly declare Apache-2.0 and name the FunAudioLLM base model. They are alternatives from another publisher, not additional mlx-community variants. Their documented speech-swift format separates LLM, flow, vocoder and reference-tokenizer weights; AniCanto currently uses mlx-audio-plus with a consolidated `model.safetensors`. No new download was enabled, no speech inference or peak-memory benchmark was performed, and these alternatives have not been represented as tested drop-in replacements. References and candidate status are retained in `licenses/cosyvoice-alternatives.json`.

## 0.24.26 shared-model removal correction

Explicit removal now records ownership separately from file presence. A removed GPT variant is not rediscovered solely because another variant still owns their common encoder. Removing the final unprotected owner releases the common files. Selected/pending variants remain protected. Successful verified installation or repair restores ownership. Confirmation and completion report retained shared bytes separately from freed storage. No model weights or model licence decisions were changed.

The same pending Mac patch keeps automatic Japanese source-language checks in the existing start status; the confirmation drawer appears only when a source-language decision is required. Welcome Basic/Expert selection and return-to-Welcome journeys are covered in both interface languages. Model licence decisions are unchanged.

## 0.24.27 current distribution profile

The selectable CosyVoice 3 path uses official weights on Windows with an NVIDIA GPU and CUDA. Mac MLX and Windows AMD/Intel/CPU CosyVoice 3 are not offered. Previously generated audio is retained and remains playable. No local MLX conversion tool is included. Other engines retain their separate hardware requirements.

About groups the currently selectable model downloads by Qwen 3.5 4B / 9B / 35B, voice, recognition and supporting models. Fixed source revisions and expected file SHA-256 values remain inspectable; they are not a fresh scan of installed files. Historical evidence for unavailable conversions remains in the licence register.

The automatic last-reference recovery uses the existing seven hash-allowlisted synthetic reference clips, with their retained generator/licence evidence; it adds no model downloads or outside voice recordings. A changed voice resemblance and any unverified content remain explicitly reported. The complete bilingual operational manual is embedded in `studio/web/help.js`.

Final artifact receipts bind the actual `.app`, `.exe`, source snapshot and matching build materials. A successful component evidence review does not constitute publication authorisation or real Windows hardware acceptance.
