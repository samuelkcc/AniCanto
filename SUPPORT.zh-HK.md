# AniCanto 桌面版技術支援

[English](SUPPORT.md) · [繁體中文](SUPPORT.zh-HK.md) · [简体中文](SUPPORT.zh-CN.md) · [日本語](SUPPORT.ja.md)

[主頁及部署](README.zh-HK.md) · [現行流程](docs/DESKTOP-WORKFLOW-0.25.0.md)

呢個倉庫由 SCKC 提供 **macOS／Windows 桌面開源版本**。桌面使用、部署問題及意見請到[問題列表](https://github.com/samuelkcc/AniCanto/issues)回報。

## 回報桌面問題

[建立回報](https://github.com/samuelkcc/AniCanto/issues/new?title=%5BDesktop%5D%20)，請提供：

1. AniCanto 版本／build、作業系統版本。
2. CPU、系統 RAM、顯示卡及 VRAM，並註明使用 CPU、Apple Metal／MLX 定 NVIDIA CUDA。
3. 翻譯、辨識及配音模型、字幕來源類型，同已開啟嘅修復選項。
4. 重現步驟、預期結果、實際錯誤、最後處理階段／句數，以及停留咗幾耐。
5. 有需要可附上已移除私人資料嘅診斷片段或截圖。

請先搜尋已有回報，同一問題喺原有 issue 繼續回覆。求助毋須贊助。

## 常見檢查

- **部署失敗：** 檢查儲存空間、記憶體估算、執行環境及相關模型下載。偵測到硬件唔代表所有顯示卡及模型都已驗證。
- **轉換慢或暫停：** 睇最新階段同句數；關閉前先「暫停並保存」，之後續跑。百分比冇變唔一定係卡住。
- **字幕／配音問題：** 註明內置文字字幕、外掛 SRT／ASS／SSA／VTT，定燒入畫面 OCR，並提供時間位置；喺逐句編輯比較原聲、分離聲及配音。
- **測試新流程：** 舊暫停工作保留原設定。請重設測試影片或建立新轉換，先會使用新預設。
- **成品：** 刪除專案或錄音前，先確認所選輸出資料夾嘅影片可以正常播放。

## 公開回報及內容

所有回報都係公開嘅。上載記錄前請移除私人路徑、帳戶、影片、錄音、文字稿及個人資料，唔需要提供完整私人媒體。

模型及執行環境準備好後，預設轉換喺本機完成；下載同更新需要上網。雲端資料夾同步按你所選儲存服務處理。支援頁及問題列表由 GitHub 託管，適用 [GitHub 私隱聲明](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement)。請只處理有權使用嘅影片、字幕及聲線參考。
