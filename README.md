<p align="center">
  <img src="docs/images/anicanto-cantonese-cover.png" alt="AniCanto — 廣東話. Original assistants celebrating Hong Kong Cantonese around a studio microphone." width="1200">
</p>

# AniCanto · 你嘅動畫，另一把聲音。

**Your anime. A Cantonese voice.**

Local AI dubbing for Japanese animation — made with a love of Hong Kong Cantonese, and a welcome for anyone curious to learn it.

用本機 AI 為日本動畫配上廣東話或英文，玩配音、比較語言，一齊感受香港廣東話嘅節奏同趣味。

[Explore the interface · 睇介面](#a-look-inside--介面導覽) · [Models & hardware · 模型與硬件](#start-with-the-right-voice--先揀啱聲音) · [Workflow · 處理流程](#from-scene-to-speech--由片段到配音) · [Limitations · 使用限制](#what-to-expect--使用限制) · [☕ Support · 支持](#support-a-little-more-cantonese--支持廣東話小作品)

> **Development preview / 開發預覽**  
> This repository currently introduces the project. Public app downloads and the complete source release are being prepared; they are not available here yet.  
> 呢個儲存庫目前用作專案介紹；正式 App 下載同完整原始碼仍在整理，暫未提供。

## A new way to hear a familiar scene · 熟悉嘅場景，聽出新趣味

The big entrance. The awkward confession. The perfectly timed “出發啦！” (“Let’s go!”). AniCanto is an animation-focused desktop dubbing studio that lets you explore how a scene feels in Hong Kong Cantonese — with English alongside it when you want a little help following along.

熱血登場、搞笑對答，甚至一句「一齊出發啦！」，換成廣東話可以有另一種親切感。AniCanto 專注動畫 AI 配音；想聽廣東話、想自己執稿，或者想用英文對照學幾句，都可以由同一個工作室開始。

**Cantonese curious?** Use the English interface, generate Cantonese and English audio, and compare the subtitle options. It is a playful listening companion, rather than a pronunciation course or a certified translation service.

**想用英文學廣東話？** 可以用英文介面，同時製作廣東話及英文音軌，再配合字幕比較意思。適合試聽同探索語言；AI 翻譯同發音仍要留意準確度。

## A hobby project, made for learning · 由學習開始嘅興趣作品

AniCanto began with a small family wish: helping the developer’s children hear everyday Hong Kong Cantonese while reading Chinese subtitles and learning Chinese characters. Animation made that idea fun. Sharing it is a way to invite more people — including English speakers — to discover Cantonese expression and culture.

AniCanto 最初係一個家庭入面嘅小想法：希望小朋友一邊聽香港廣東話，一邊睇中文字幕，接觸日常口語同學中文字。動畫令學習多一份趣味；分享呢個興趣作品，亦希望世界各地、包括講英文嘅朋友，都可以認識廣東話嘅表達同文化。

**With respect to voice performers.** Dubbing is a craft: character interpretation, emotion, timing, pronunciation and dramatic intent come from people’s training, creativity and dedication. AniCanto is for personal learning and creative experiments. **It is not intended to replace professional voice actors, and its AI output does not meet the standard of a professional performance.** Please recognise and support the performers behind the voices you love.

**向專業配音員及聲優致敬。** 角色理解、情緒、節奏、發音同戲劇表達，背後都係表演者嘅訓練、創意同付出。AniCanto 係個人學習同創作實驗工具，**唔係用嚟取代專業配音員；AI 配音亦未達專業演繹水準。** 希望大家繼續欣賞同支持鍾意嘅聲音背後嗰位表演者。

## What makes it different · 有乜特別

| | |
|---|---|
| **🎵 Keep the opening and ending**<br>Detect OP/ED songs and preserve their original Japanese audio by default.<br>**片頭片尾保留日文**：辨識 OP／ED 歌曲，預設保留原裝日文。 | **🔁 Repair, then listen again**<br>Automatic repair can adapt a line, regenerate a take and check the new recording.<br>**AI 自動修復再檢測**：按問題改稿、重錄，再核對新錄音。 |
| **🌏 Cantonese + English**<br>Separate audio tracks and subtitle choices help you compare the same scene across languages.<br>**廣東話加英文**：分開音軌同字幕，方便試聽同語言比較。 | **🎬 Simple start, detailed control**<br>Basic mode for automatic production; Expert mode adds a timeline, line editing and retakes.<br>**同一專案，兩種模式**：基本模式自動處理；專家模式逐句編輯同重錄。 |
| **🎧 Hear the evidence**<br>Compare the original mix, separated voice and generated recording in the review report when available.<br>**聽返問題所在**：校對報告可比較原裝混音、分離聲音同生成配音。 | **💻 Run on your own computer**<br>Model inference runs locally after setup. Queue videos, pause, save and resume your work.<br>**本機運算**：部署後本機處理，支援影片排序、暫停保存同續做。 |

OP/ED detection and repair are automatic attempts, not a guarantee that every song boundary, voice or line will be recognised correctly. The report keeps unfinished work visible.

OP／ED 偵測同修復都會自動嘗試，但唔保證每個歌曲邊界、聲線同對白都判斷正確；未完成項目會保留喺報告。

## A look inside · 介面導覽

Screenshots use the real application interface with original demonstration dialogue and illustrative project/model states. They contain no commercial anime footage and are not conversion benchmarks.

以下係實際 App 介面，使用原創示範對白及示意專案／模型狀態；冇使用商業動畫片段，亦唔代表效能測試結果。

### 01 · Pick your way in / 揀你嘅操作方式

![English Welcome screen with Basic and Expert mode choices](docs/images/welcome-en.png)

An English or Traditional Chinese interface, original assistants and two ways into the same studio.  
中英文介面、原創助手，基本同專家模式共用同一個專案。

### 02 · Start simply / 簡單開始

![Traditional Chinese Basic mode showing a demonstration video queue and automatic production settings](docs/images/basic-zh-HK.png)

Import your videos, choose a dubbing language and an output folder, then let the workflow proceed.  
匯入影片，揀配音語言同輸出位置，由流程自動逐步處理。

### 03 · Get close to every line / 逐句細執

![English Expert mode with a timeline, source Japanese text, Cantonese script and recording controls](docs/images/timeline-en.png)

Browse the timeline, compare source text and the dubbing script, audition a line and keep earlier takes.  
左右瀏覽時間線、對照日文同配音稿、逐句試聽，保留舊錄音作比較。

### 04 · See what the AI checked / 睇清楚修復過程

![English review report showing dialogue, timing measurements, automatic attempts and audio comparisons](docs/images/review-en.png)

The report shows the source line, translated script, recognised generated speech, timing and repair attempts. Unresolved lines remain labelled.  
報告列出原文、譯稿、生成錄音辨識、時長同修復嘗試；未解決嘅項目會明確標示。

### 05 · Keep a batch in order / 一次整理多條影片

![Traditional Chinese projects page with queue ordering controls and export destinations](docs/images/batch-zh-HK.png)

Reorder waiting videos, see each project’s status and resume unfinished work.  
重新排列待處理影片，查看逐條狀態，同埋繼續未完成工作。

<details>
<summary><strong>More screenshots · 更多中英文介面</strong></summary>

| Models & setup · 模型與部署 | Preferences · 偏好設定 |
|---|---|
| ![English model quality and setup options](docs/images/models-setup-en.png) | ![Traditional Chinese language, theme and appearance preferences](docs/images/preferences-zh-HK.png) |

[View all 16 screenshots · 查看全部 16 張中英文介面圖](docs/SCREENSHOTS.md)

</details>

## Start with the right voice · 先揀啱聲音

**For a Hong Kong Cantonese accent, our recommendation is Drama 3 with Qwen 3.5 35B.** In the developer’s listening tests, Drama 3 sounded closest to the Cantonese commonly heard in Hong Kong. Accent and voice resemblance still depend on the reference recording and scene.

**想接近香港廣東話口音，建議用 Drama 3 + Qwen 3.5 35B。** 開發者目前試聽中，Drama 3 嘅發音較接近香港日常廣東話；實際口音同聲線相似度仍受參考錄音及場景影響。

| Voice model / 配音模型 | What to expect / 口音預期 |
|---|---|
| **Drama 3 — recommended / 建議** | Closest to a Hong Kong Cantonese accent in current listening tests.<br>目前試聽中較接近香港廣東話口音。 |
| **GPT-SoVITS** | May retain a Japanese accent when imitating a Japanese source voice.<br>模仿日文原聲時，廣東話可能帶日語口音。 |
| **CosyVoice 3** | May retain a Japanese accent in this workflow. Offered only with official native weights on Windows NVIDIA/CUDA; unavailable on Mac.<br>呢個流程下可能帶日語口音；只提供 Windows NVIDIA／CUDA 官方原生版本，Mac 不提供。 |

Qwen translates and helps plan repairs; Drama 3 generates speech. Download choices for text translation are **Qwen 3.5 9B and 35B**. Model versions without confirmed licence evidence have been removed from the download catalogues.

Qwen 負責翻譯同協助修復判斷，Drama 3 負責生成聲音。文字翻譯下載只保留 **Qwen 3.5 9B、35B**；未確認授權嘅版本已從下載清單移除。

### Recommended Mac / 建議 Mac 規格

| | Recommendation / 建議 |
|---|---|
| Computer / 電腦 | **Apple Silicon Mac with 64 GB or more unified memory**<br>Apple Silicon Mac，**64 GB 或以上統一記憶體**。 |
| System / 系統 | macOS 14 or later / macOS 14 或以上。 |
| Voice / 配音 | Drama 3 · 35B · 4-bit MLX。 |
| Translation / 翻譯 | Qwen 3.5 · 35B-A3B · 4-bit MLX。 |
| Storage / 儲存 | Plan for **100 GB or more free space** for models, environments and working files; long videos need additional room.<br>建議預留 **100 GB 或以上可用空間**，長片另留暫存同輸出空間。 |
| First setup / 首次部署 | Internet access for model and runtime downloads; inference runs locally afterwards.<br>首次下載模型及執行環境需要網絡，之後喺本機運算。 |

Lower-memory presets are compromises, not the same quality at a smaller size. Windows candidates are being prepared and still need real-device startup and GPU testing. Intel Macs are not supported by this Apple Silicon setup.

較省記憶體嘅組合喺口音、聲線表情同翻譯細節可能有差異。Windows 候選版仍需真機啟動同 GPU 測試；以上 Apple Silicon 部署唔支援 Intel Mac。

### Conversion time reference / 轉換時間參考

| Input / 片長 | Mode / 模式 | Machine / 電腦 | Models / 模型 | Approximate processing / 約需時間 |
|---|---|---|---|---|
| 25-minute animation / 約 25 分鐘動畫 | Normal / 一般 | MacBook Pro M2 Max | Qwen 3.5 35B + Drama 3 | **45 minutes / 約 45 分鐘** |

This is a developer-provided reference, not a newly repeated benchmark or a time guarantee. Dialogue density, first-time downloads, video encoding, memory pressure and automatic retakes can change the total substantially.

以上係開發者提供嘅實測參考，唔係今次重新跑嘅基準測試或時間保證；對白密度、首次下載、影片編碼、記憶體壓力同自動重錄次數都會影響總時間。

## From scene to speech · 由片段到配音

1. **Prepare / 準備** — Read the video, audio and subtitle tracks; prepare the project and working files. / 讀取影音字幕軌，建立專案及工作檔。
2. **Find the dialogue / 整理對白** — Recognise Japanese speech, use available subtitle evidence and detect OP/ED regions. / 辨識日文，參考可用字幕，偵測片頭片尾。
3. **Prepare source references / 準備原聲參考** — Separate dialogue from background audio and collect reference clips for the chosen voice strategy. / 分離人聲及背景，按策略抽取聲線參考。
4. **Translate / 翻譯** — Adapt dialogue into Cantonese and/or English while considering meaning and the available speaking window. / 兼顧意思同可用時段，改編成廣東話及／或英文。
5. **Generate and repair / 配音及修復** — Generate takes, check language/content/timing, then try targeted rewriting, retakes, reference repair or bounded timing and tempo adjustments when needed. / 生成配音，檢查語言、內容同時長；有需要時針對改稿、重錄、修復參考，或有限微調時間同語速。
6. **Review and export / 校對及輸出** — Mix the selected voices with the background, keep the original track and produce a versioned export with the selected subtitles. / 混合配音及背景，保留原裝音軌，按字幕設定輸出新版本。

Normal mode attempts automatic checks and repair. High-speed mode skips quality review and quality-driven retakes. If a complete dub cannot be verified, a labelled incomplete preview may retain source speech for affected lines; that is not presented as a finished Cantonese dub.

一般模式會嘗試自動檢測同修復；高速模式跳過品質核對及相關重錄。若未能確認完整配音，標示為未完整嘅預覽可能保留個別原聲，唔會當成完整廣東話成品。

## What to expect · 使用限制

- **Animation first, Japanese first.** The main workflow targets Japanese animated dialogue, not live dubbing or every possible source language. / **以日本動畫為主**，唔係即時配音，亦唔保證適用所有原聲語言。
- **Difficult audio is still difficult.** Overlapping speakers, shouting, whispers, songs, effects and noisy separation can affect recognition, reference quality and completeness. / **重疊對白、叫喊、細聲、歌曲、音效同分離雜音**都可能影響辨識、參考聲線及完整度。
- **One character, not always one consistent voice.** Normal mode imitates a source reference for each line; it does not lock a character’s identity or timbre across a whole episode. Voice colour, accent and expression can vary between takes. / **同一角色，聲線唔一定完全一致**：一般模式逐句參考原聲模擬，唔係全片鎖定角色身份或音色；不同錄音之間仍可能有聲線、口音同情緒差異。
- **Expressive acting can confuse the AI.** Professional Japanese performers may change timbre dramatically for whispers, shouting, comedy or emotion. When role analysis is used, AI can split the same character into different roles, or merge similar voices. That is a limit of AI recognition, not a flaw in the acting. / **精彩演繹亦可能令 AI 分錯角色**：日本聲優喺耳語、叫喊、搞笑或情緒轉換時，聲線可以有好大變化；做角色分析時，AI 可能將同一角色拆成幾個，亦可能將相似聲音合併。呢個係 AI 辨識限制，唔係表演者嘅問題。
- **Automatic repair has limits.** Translation, names, accent, emotion, speaker identity and lip sync can still be wrong. A voice-per-line reference is not proof of a recognised character. / **自動修復唔係零錯誤保證**；翻譯、人名、口音、情緒、角色身份同嘴形同步仍可能有誤，逐句原聲參考亦唔等於已識別角色。
- **No cut-off speech as a shortcut.** The workflow tries shorter wording, full retakes and safe timing changes; small tempo adjustments are bounded. Some lines can remain unresolved. / **唔以斬尾作捷徑**；流程會嘗試精簡、完整重錄同安全時間安排，調速幅度有限，仍可能有未解決對白。
- **Opening/ending songs stay Japanese by default.** Detection can miss unusual arrangements; inspect the result. / **OP／ED 預設保留日文**；特殊編排可能偵測唔準，需要留意成品。
- **Subtitles have boundaries.** Embedded text and speech recognition are useful evidence; burned-in captions cannot be cleanly replaced in every video. / **字幕有格式限制**；內嵌文字同語音辨識可作參考，燒錄字幕唔保證可乾淨移除或取代。
- **Local does not mean lightweight.** Large models need substantial memory, storage and processing time. / **本機唔等於輕量**；大型模型需要足夠記憶體、儲存空間同處理時間。

[Read the first-run guide · 首次使用指南](docs/GETTING-STARTED.md) · [Full screenshot gallery · 完整介面圖集](docs/SCREENSHOTS.md)

## Your media, your choices · 影音與授權

Use only video, subtitles and voices you have permission to process. AniCanto does not provide anime episodes or grant rights to another person’s voice. Recognition and inference run locally after model setup; setup and updates contact the relevant download hosts.

請只處理你有權使用嘅影片、字幕同聲音。AniCanto 唔提供動畫片源，亦唔授予他人聲線權利。部署後辨識及生成喺本機執行；部署及更新會連接相關下載來源。

Original application code is **MIT · © 2026 SCKC**. Third-party tools, models and assets keep their own licences. **Built with Fish Audio** — Drama 3 uses the [Fish Audio Community License](https://huggingface.co/fishaudio/drama-3/blob/main/LICENSE), with separate use, commercial and hosted-service conditions. The MIT application licence does not replace those model terms.

原創 App 程式碼採 **MIT · © 2026 SCKC**；第三方工具、模型及素材各依原有授權。Drama 3 採 Fish Audio Community License，使用、商用同託管服務另有條件，唔會因 App 採 MIT 而改變。

[Licence details · 授權說明](docs/LICENSING.md)

## Support a little more Cantonese · 支持廣東話小作品

If AniCanto helps you discover a new phrase, enjoy a new voice, or share a little Hong Kong Cantonese with a friend, you can support its continued development. A coffee is optional; curiosity is always welcome.

如果 AniCanto 令你識多一句廣東話、聽到另一種配音趣味，或者可以同朋友分享香港廣東話文化，歡迎請我飲杯咖啡，支持繼續改善。支持隨心，多謝你試玩。

<a href="https://buymeacoffee.com/samuelchen"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Samuel a coffee — 支持 AniCanto" width="217"></a>

Made by SCKC · For the fun of hearing Cantonese in a new scene.  
由 SCKC 製作 · 讓廣東話喺另一個場景繼續有聲。
