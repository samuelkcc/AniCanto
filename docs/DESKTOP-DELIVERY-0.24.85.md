# Desktop 0.24.85 / build 238

- 新工作三模式：效能／平衡／品質；平衡預設，完整 AI 覆核（含畫面分析）獨立開關、預設關閉。模型部署建議不等於工作模式。
- 修正 Normal/Fast 入口漏套 source workflow；先按 metadata 選有效路線、再 freeze/cache。原廠有字幕 subtitles-speech，無字幕 ocr-speech。
- 初稿移除字數硬預算及 pre-TTS compact。只實測 overrun 才允許縮稿；語意＋自然口語獨立批准，保留原稿。
- 通用語音時長修復及最多一個已安裝引擎目標語後備，最後才原聲延續。缺目標語錄音但每必需區間已有可聽原聲時，可完成輸出並如實記錄 0 目標語交付；不當品質合格。
- 舊暫停請求不遷移；只更新聲音不會修舊縮稿。所有更新只在 stage、驗證並確認 App 已關閉後替換 dist。

完整行為、模式上限及失敗條件：[DESKTOP-WORKFLOW.md](DESKTOP-WORKFLOW.md)。

私人測試收據不入公開 source；不包含 iPad 實作。
