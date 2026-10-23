**繁體中文** · [English](README.en.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

<p align="center"><img src="docs/images/anicanto-cantonese-cover.png" alt="AniCanto — original Cantonese studio assistants" width="1100"></p>

# AniCanto

**你嘅動畫，另一把聲音。**

將日本動畫嘅日文對白轉成**香港廣東話或英文配音**。模型同執行環境準備好後，辨識、翻譯、配音及匯出都喺本機完成。

## 點解會有 AniCanto

AniCanto 係 SCKC 由興趣開始嘅小作品，初衷好簡單：**希望小朋友一邊聽香港廣東話，一邊睇中文字幕，接觸日常口語同學中文字。** 將熟悉嘅動畫換一把廣東話聲音，希望睇片亦可以成為認識語言嘅一點樂趣。

亦希望將呢份趣味分享俾對廣東話有興趣嘅人。你可以比較廣東話、英文同原裝日文，慢慢認識香港廣東話嘅表達同文化。介面提供繁中、英文、簡中同日文；配音輸出支援廣東話及英文。

## 下載 Beta · 0.24.58

**[下載 Mac](https://github.com/samuelkcc/AniCanto/releases/download/v0.24.58-beta/AniCanto-macOS-0.24.58.zip)** · **[下載 Windows](https://github.com/samuelkcc/AniCanto/releases/download/v0.24.58-beta/AniCanto.exe)** · [更新內容及對應源碼](https://github.com/samuelkcc/AniCanto/releases/tag/v0.24.58-beta)

## 先睇電腦配置

**首選配音模型：完整 Drama 3。** 翻譯配搭 Qwen 3.5：64 GB Mac 建議 35B；Windows 32 GB RAM 可配 9B。Drama 3 喺開發者試聽中較接近香港廣東話，實際效果仍受原聲同片段影響。

| 平台 | 建議系統及記憶體 | Drama 3 執行方式 |
| --- | --- | --- |
| **Mac** | Apple Silicon、macOS 14+；**64 GB 或以上統一記憶體**建議 | 完整 4-bit MLX，使用 Apple Silicon GPU／統一記憶體；估算約 28 GB |
| **Windows** | Windows 10／11 x64；**32 GB RAM 起，64 GB 較充裕** | 完整 GGUF Q2 **使用 CPU**；估算約 22 GB 系統 RAM |

**Windows：Drama 3 目前唔使用 NVIDIA／AMD／Intel GPU 加速。** 即使配備獨立顯示卡，Drama 3 仍用 CPU 同系統 RAM。其他支援模型可按顯示卡及驅動使用 GPU；獨立 VRAM 唔能代替 Drama 3 所需 RAM。今次 Windows 套件仍需實機測試。

32 GB Mac 可以嘗試較小嘅翻譯模型組合，但 Drama 3 可能令系統用交換空間、明顯變慢或載入失敗。上述數字係規劃估算。兩個平台建議預留 **100 GB 以上**作模型、執行環境及工作檔；長片要更多。

## App 可以做啲乜

| 功能 | 可以點用 |
| --- | --- |
| **廣東話／英文配音** | 可揀單語或雙語，同一條影片保留獨立音軌及字幕，喺相容播放器切換。 |
| **用中文字幕輔助核對** | 參考內置文字字幕、外掛字幕或畫面 OCR，幫助理解意思同人名；日文聲音仍係主要依據。 |
| **保留片頭片尾** | 自動偵測 OP／ED，預設保留日文歌曲及原聲。 |
| **基本及專家模式** | 基本模式自動處理；專家模式提供時間軸、改稿、時間調整及逐句編輯。 |
| **試聽、重錄及校對** | 比較原聲、分離聲音同生成配音；逐句重錄或揀舊錄音，再匯出新版，保留先前成品。 |
| **本機批次處理** | 排隊轉片、調整未開始影片次序、暫停保存同續做；模型準備好後可離線處理。 |

## 支援格式

| 類別 | 格式 |
| --- | --- |
| **輸入影片** | MP4 · MKV · MOV · M4V · AVI · WebM · TS |
| **外掛字幕** | SRT · ASS · SSA · VTT |
| **輸出成品** | MP4，按所選設定加入音軌及字幕。 |

影片副檔名相容，仍需檔案內嘅影音編碼可以讀取；燒入畫面嘅字幕可嘗試 OCR，唔代表一定可以乾淨移除。

## 今個 Beta 新增咗乜

- 影片按清單連續處理，未開始嘅影片可以調位。
- 字幕匯入集中喺「字幕來源」；校對報告可標記已檢查或稍後處理。
- 基本模式預覽更緊湊；Mac／Windows「暫停並保存」統一用紅色。

## 三步開始

1. 下載並開啟 App，完成模型同執行環境準備；首次設定需要網絡。
2. 加入影片，揀廣東話、英文或雙語。要用外掛字幕：預覽上方 **字幕來源 → 匯入字幕檔**（SRT／ASS／SSA／VTT）。
3. 開始處理；完成後播放成品。有疑點可打開校對報告，逐句聽原聲、分離聲音同配音，再重錄或改揀錄音，輸出另一個版本。

[字幕匯入說明](docs/zh-HK/GETTING-STARTED.md)

## 新版介面

以下係 0.24.58 真實介面，使用原創示範素材及示意模型／專案狀態，唔係轉換效能測試。

### 歡迎及部署

![歡迎及部署](docs/images/welcome-zh-HK.png)

### 基本模式：進度及試聽

![基本模式：進度及試聽](docs/images/basic-zh-HK.png)

### 專家模式：時間軸及逐句編輯

![專家模式：時間軸及逐句編輯](docs/images/timeline-zh-HK.png)

### 校對報告：疑點及錄音比較

![校對報告：疑點及錄音比較](docs/images/review-zh-HK.png)

[查看全部介面截圖](docs/zh-HK/SCREENSHOTS.md)

## 使用前須知

AI 仍可能出現口音、錯譯、缺字或聲線變化；重要片段請試聽。字幕輔助核對意思，日語聲音仍係主要依據。支援原聲、廣東話及英文獨立音軌，並可保留 OP／ED；效果視乎片段。

呢個小作品亦係靠失敗片段慢慢改善：逐句聽、追查問題，再調整流程。AI 可以協助檢查，但對白自然唔自然、角色感覺啱唔啱，仍然需要人去聽。

**配音係一門專業。** AniCanto 用於學習同創作實驗，AI 嘅演繹仍有不足；希望大家繼續欣賞同支持背後嘅專業配音員。

SCKC 嘅興趣作品。原創程式碼採 MIT；第三方組件及模型各有授權。Built with Fish Audio；Drama 3 使用 Fish Audio Community License 1.0。請只使用有權處理嘅影片、字幕及聲音。

[支持計劃](https://buymeacoffee.com/samuelchen) · [MIT](LICENSE) · [Licences](docs/LICENSING.md)
