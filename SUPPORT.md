# AniCanto Support / 技術支援

[English](#english) · [繁體中文](#繁體中文) · [AniCanto home](README.md) · [iPad privacy policy / iPad 私隱政策](docs/IPAD-PRIVACY-POLICY.md)

## English

AniCanto is an independent project by **SCKC**. This page covers help, bug reports and feedback for iPad, Mac and Windows. The iPad edition is currently in development; these instructions also apply to development testers. Availability and supported features follow the release announcements for your platform.

### Contact SCKC

- [Report an iPad issue](https://github.com/samuelkcc/AniCanto/issues/new?title=%5BiPad%5D%20).
- [Report a Mac or Windows issue](https://github.com/samuelkcc/AniCanto/issues/new?title=%5BDesktop%5D%20).
- [Read existing reports or send general feedback](https://github.com/samuelkcc/AniCanto/issues).

GitHub Issues is the current contact channel. Reading this page does not require an account; posting an issue requires a GitHub account. Reports are **public**. Do not post private videos, voice recordings, scripts, account details, purchase receipts or unedited diagnostic logs. For a general privacy question, describe the concern without including personal data.

Please include:

1. Platform, device model, operating-system version, and AniCanto version/build.
2. What you were trying to do and the steps that reproduce the problem.
3. What you expected and what actually happened, including the exact error text.
4. Selected translation/voice models and the stage where processing stopped, if relevant.
5. An optional screenshot or short diagnostic excerpt with personal information removed.

Support and bug reporting do not require a donation. Please keep replies about the same problem in the same issue.

### iPad help

| Question | What to check |
| --- | --- |
| Can my iPad enter the studio? | The current development edition requires an M1 or newer M-series iPad with at least 8 GB RAM and supported GPU capabilities. Check **About and licences → iPad compatibility** in the app. Meeting the requirements does not mean every model or workload has been tested on that device. |
| Why does initial setup need the internet? | AI models and Apple-managed speech resources may need downloading. Download size and storage needs depend on your selection; check the model manager before starting. Recognition, translation and dubbing run on the iPad after the required resources are ready. |
| A download or model check failed. | Check the connection and available storage, then retry or repair the affected model in model management. Report the model name and error if it keeps failing. Avoid deleting the app to troubleshoot: this can remove local projects and recordings. |
| Processing paused or is taking a long time. | Keep the app in the foreground. Use its pause/save and resume controls; backgrounding can interrupt or pause work. Processing time depends on the video, selected models, memory and temperature. Include the last visible stage in a report. |
| Recording is unavailable or silent. | Check AniCanto's microphone permission in iPad Settings and the connected microphone/audio accessory. Permission is needed for recording, not for typing text or importing an existing file. Report your device, audio route and error if the problem persists. |
| Where are my finished files? | Open the saved-output player and use **Save video to Files…**, **Save subtitles to Files…** or the audio export/share action. Verify the saved copy in Files or your chosen cloud provider before removing the app or deleting a project. |
| How do I restore Expert? | When App Store purchasing is available for your build, open the Expert introduction and choose **Restore purchases**, using the Apple Account that made the purchase. A development-test entitlement is separate from a real App Store purchase. Never post a receipt or account information in a public issue. |
| The translation or voice sounds wrong. | Listen to the output and check the text. AI can mistranslate, omit words or change pronunciation and voice character. Where available, use Expert review and retained takes to revise a line. Automated checks do not certify translation or performance quality. |

### Mac and Windows help

See the [desktop setup, model requirements and workflow](README.md). Desktop and iPad requirements are different; desktop installation instructions, downloadable runtimes and model recommendations do not apply automatically to iPad. For a desktop report, also include CPU, system RAM, graphics card/VRAM and whether you selected CPU, MLX or NVIDIA CUDA processing.

### Privacy and content

Read the [iPad privacy policy](docs/IPAD-PRIVACY-POLICY.md#english) for local processing, model connections, sharing, backups and deletion. That policy describes the iPad app. This support page and its public issue tracker are hosted by GitHub, whose [privacy statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement) applies when you visit or post there. Only use video, subtitles and voice references you have permission to process.

## 繁體中文

AniCanto 由 **SCKC** 獨立開發。呢頁提供 iPad、Mac 同 Windows 嘅使用支援、問題回報及意見入口。iPad 版目前仍在開發，以下亦適用於開發測試用戶；實際供應情況及功能以各平台發佈公告為準。

### 聯絡 SCKC

- [回報 iPad 問題](https://github.com/samuelkcc/AniCanto/issues/new?title=%5BiPad%5D%20)。
- [回報 Mac／Windows 問題](https://github.com/samuelkcc/AniCanto/issues/new?title=%5BDesktop%5D%20)。
- [查看已有回報或提出一般意見](https://github.com/samuelkcc/AniCanto/issues)。

現時透過 GitHub Issues 聯絡。閱讀呢頁毋須帳戶，發表回報需要 GitHub 帳戶。**所有回報都係公開嘅**，請勿上載私人影片、錄音、文字稿、帳戶資料、購買收據或未移除私人資料嘅完整記錄。一般私隱問題只需概括描述，唔好附上個人資料。

回報時請提供：

1. 平台、裝置型號、系統版本，以及 AniCanto 版本／build。
2. 想完成嘅操作，同可以重現問題嘅步驟。
3. 預期結果、實際情況及完整錯誤文字。
4. 如有關，列出翻譯／配音模型及停喺邊個處理階段。
5. 可選擇附上已移除私人資料嘅截圖或短段診斷記錄。

求助同回報問題毋須贊助。同一問題請喺原有 issue 繼續回覆，方便追蹤。

### iPad 常見問題

| 問題 | 可以先檢查 |
| --- | --- |
| 呢部 iPad 可唔可以進入工作室？ | 目前開發版需要 M1 或更新 M 系列 iPad、至少 8GB RAM 及所需 GPU 能力。請查看 App **關於及授權 → iPad 相容性**。符合規格唔代表每個模型或工作量都已喺該機型實測。 |
| 點解第一次準備需要上網？ | AI 模型及 Apple 管理嘅辨識資源可能需要下載。容量同儲存空間按所選模型而定，開始前請查看模型管理。所需資源準備好後，辨識、翻譯及配音喺 iPad 本機執行。 |
| 模型下載或檢查失敗點算？ | 檢查網絡同剩餘空間，再喺模型管理重試或修復相關模型。持續失敗請回報模型名及錯誤。唔好為排查而直接刪 App，否則可能移除本機專案及錄音。 |
| 處理暫停咗，或者好慢。 | 保持 App 喺前景，使用 App 內暫停／保存及繼續功能；轉到背景可能令工作暫停或中斷。速度視乎影片、模型、記憶體及溫度。回報時請提供最後顯示嘅處理階段。 |
| 錄唔到音，或者錄音無聲。 | 檢查 iPad 設定內 AniCanto 嘅咪高峰權限，同已接駁嘅咪高峰／音訊配件。錄音先需要咪高峰權限，輸入文字或匯入現有檔案毋須呢項權限。持續有問題請回報裝置、收音來源及錯誤。 |
| 去邊度搵成品？ | 喺成品播放器使用「儲存影片到檔案…」、「儲存字幕到檔案…」或音訊匯出／分享。移除 App 或刪專案前，先喺「檔案」或所選雲端服務確認副本已保存。 |
| 點樣恢復專家模式？ | 當所用版本已提供 App Store 購買，喺專家模式介紹按「恢復購買」，並使用原先購買嘅 Apple 帳戶。開發測試權限同正式購買係分開嘅。請勿喺公開 issue 貼收據或帳戶資料。 |
| 翻譯或配音有錯。 | 請試聽並核對文字；AI 可能錯譯、漏字或改變口音及音色。版本提供相關功能時，可用專家校對及保留錄音逐句修訂。自動檢查唔等於翻譯或聲演品質認證。 |

### Mac／Windows 支援

請參閱[桌面版設定、模型要求及操作流程](README.zh-HK.md)。桌面同 iPad 嘅硬件及安裝方式不同，桌面執行環境下載及模型建議唔會自動適用於 iPad。回報桌面問題時，請另外列出 CPU、系統 RAM、顯示卡／VRAM，同使用 CPU、MLX 定 NVIDIA CUDA。

### 私隱及內容

[iPad 私隱政策](docs/IPAD-PRIVACY-POLICY.md#繁體中文)說明本機處理、模型連線、分享、備份及刪除方式，適用範圍係 iPad App。呢個支援頁同公開回報由 GitHub 託管；瀏覽或發表內容時適用 [GitHub 私隱聲明](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement)。請只處理你有權使用嘅影片、字幕及聲線參考。
