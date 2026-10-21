# AniCanto rename / 改名紀錄

Version 0.24.17 (170), 18 October 2026.

The product is AniCanto, formerly CantoSync. Display names, future output names, debug reports, application grants, help/use terms and build deliverables use the new name. Original code and original vector brand artwork remain MIT, copyright SCKC; the root MIT text remains unchanged because its copyright holder has not changed.

## Upgrade compatibility / 升級相容

- Mac data remains in `~/Library/Application Support/SamCantoSync`.
- Windows data remains in `%LOCALAPPDATA%\CantoSync-Windows`.
- Existing `SAM_CANTO_*` and `CANTOSYNC_*` environment overrides remain valid.
- The shared desktop bundle identifier remains `com.sckc.cantosync.studio` to retain settings and webview storage. This is an internal upgrade identity, not the displayed product name.
- Existing burned-caption markers and old exported-file recognition are retained. Future export filenames use `-AniCanto`.
- Old grant files in historical evidence are retained verbatim. A cloned application replaces the active old application notice with `AniCanto-MIT.txt`; third-party notices remain unchanged.

改名唔會搬走／刪除模型、覆寫現有成品，亦唔會改第三方作者嘅授權。歷史證據及舊版安裝檔唔會冒充新版。

## Original icon / 原創圖示

`Resources/app-icon-art.png` is the current original source: a Japanese-inspired singer's silhouette sends a voice toward the brush-style 「廣」 character. The lavender palette matches the shared interface. Platform PNG/ICNS/ICO files derive from this artwork. `Resources/app-icon.svg` is retained as historical artwork from the earlier icon.

## Publication / 公開發佈

Renaming does not resolve the remaining binary/runtime source and model/data licence evidence conditions. See [distribution review](PUBLIC-DISTRIBUTION-REVIEW.md). No repository or release is published by this change.
