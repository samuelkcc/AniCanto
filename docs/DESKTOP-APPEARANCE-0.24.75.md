# 桌面啟動外觀 · 0.24.75 / build 228

啟動會直接跟偏好設定的「跟隨系統／淺色／深色」。沒有設定時跟隨系統；不把深色強制改成預設，亦不更改使用者既有選擇。

先前原生視窗固定淺色，前端亦先用淺色，等 Python 狀態回傳後才知道儲存的深色選項，造成切換。現在原生 host 在建立視窗前只讀取外觀列舉，經 initialization script 傳入；appearance.js 在樣式和 module 前套用。第一次 render 同步原生背景與 titlebar，再顯示視窗，無須等待 runtime、模型或專案。若前端錯誤，五秒後顯示視窗保底，不會永久隱藏。保底不載入模型、不執行轉換。

偏好設定仍為設定來源；localStorage 只供無原生值的瀏覽器備援，不能覆蓋原生儲存設定。無效／無設定／損壞 metadata 回到跟隨系統。跟隨系統可在開住 App 時即時更新，指定淺／深色則保持使用者選擇。視窗背景與前端色彩同步。沒有改轉換、配音、字幕、已安裝模型或 iPad。

## 驗證

- Rust 兩項：有效列舉、安全 script、損壞／無 metadata 回退、讀取不改寫原檔。
- `tests/shared_appearance_ui.cjs`：淺／深／系統乘兩種 OS 外觀共六組；刻意延遲狀態回傳，每組約100個畫格均一致；過時 cache 不覆蓋設定、開住時切換 OS 的行為、新 profile 兩組跟系統、零 JS error。
- Mac 封裝候選三種外觀使用獨立空白資料夾實際開窗，0.51–0.76秒可見，早於五秒保底；此檢查證明原生／前端 handshake 成功，沒有宣稱量測原生視窗每一像素的啟動影片。
- Node 共用 UI 模型合約及真正封裝 native 播放器字幕／音軌端點回歸通過。播放器檢查首次漏傳隔離 runtime interpreter，補上 fixture 環境後通過；沒有因此變更 production runtime 政策。
- 兩平台重建，Mac strict 簽章／native startup，frontend manifest、164個 shared Python SHA、Windows payload／exe hash、公開封裝私隱檢查。
- Windows為cross-build及封裝驗證，尚未 Windows PC 實機啟動畫面驗收；未跑整片或模型推理，亦未聲稱全套歷史測試全綠。

GitHub 發布依使用者指示繼續暫停。本機 dist 交付／回退紀錄見交接及私有 .build/appearance75 收據。
