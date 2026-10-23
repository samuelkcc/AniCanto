import {esc} from './model.js';
import {localeData} from './locale-data.js';
// Four interface languages share chapter IDs, section order and release limitations.
export const CHAPTERS=[
  {
    "id": "start",
    "title": {
      "en": "Getting started",
      "zh-HK": "開始使用"
    },
    "summary": {
      "en": "From your first launch to your first dubbed episode.",
      "zh-HK": "由首次啟動到完成第一條配音影片。"
    },
    "sections": [
      {
        "title": {
          "en": "Language and background downloads",
          "zh-HK": "語言與背景下載"
        },
        "body": [
          {
            "en": "On first launch, the interface follows your system language: Japanese uses Japanese; Mainland or Singapore Chinese uses Simplified Chinese; other Chinese and Cantonese locales use Traditional Chinese; other languages use English. Your manual choice is remembered. Interface language does not change dubbing or subtitle settings. You can browse the studio during setup. A bottom-right notification shows model download progress; click it for full installation details. The compact summary stays short while the expandable, scrollable log retains filenames and package messages. Conversion remains unavailable until the selected models and required runtimes are ready.",
            "zh-HK": "首次啟動會跟隨系統語言：日文用日文，中國內地或新加坡中文用簡體中文，其他中文同廣東話用繁體中文，其餘語言用英文；之後會記住你手動揀嘅語言。介面語言唔會更改配音或字幕設定。部署期間可以瀏覽工作室，右下角提示會顯示模型下載進度，按一下可睇完整安裝詳情。主畫面只顯示簡短分類，詳細檔名同套件記錄放喺可展開、捲動嘅記錄內。所選模型同必要執行環境準備好後，先可以開始轉換。"
          },
          {
            "en": "AniCanto uses local language and voice models. After the required models and runtimes have downloaded, recognition, translation, dubbing and export work offline. First setup, adding models, download repair and updates need internet access.",
            "zh-HK": "AniCanto 使用本機語言及語音模型。所需模型同執行環境下載完成後，辨識、翻譯、配音同匯出可離線使用。首次部署、新增模型、修復下載同更新需要網絡。"
          },
          {
            "en": "An uninstalled voice engine is marked Automatic download. Selecting it checks compatibility and starts setup while keeping existing models. WenetSpeech-Yue is Cantonese-only and cannot be selected for English or bilingual dubbing. Audio grouping and visual character analysis enable Full AI review; visual analysis takes about three times the processing time of Normal mode. Expanded production options and scroll position are retained when settings change.",
            "zh-HK": "未安裝語音引擎會標示「自動下載」；揀選後先檢查相容性，再開始部署，保留現有模型。WenetSpeech-Yue 只支援廣東話，英文或雙語配音時不可選。聲音分組及影像角色分析會啟用完整 AI 檢測模式；影像分析處理時間約為一般模式嘅 3 倍。更改設定後會保留製作選項嘅展開狀態同捲動位置。"
          },
          {
            "en": "Dubbing does not have to match the original speech duration exactly. Natural delivery can use an empty following gap, including one or two extra seconds when available, before another source turn, preserved passage or detected scene boundary. An overlong recording is not a reason to change the actor voice. A generic Chinese transcript alone cannot certify Cantonese pronunciation. Automatic repair can still fail; the review report distinguishes language evidence and a bundled target-language fallback from a successful imitation of the original voice.",
            "zh-HK": "配音唔需要同原聲秒數完全一致；下一句、保留原聲段落或已偵測場景界線之前，如有安全空檔，可以自然講長少少，包括可用嘅一兩秒。單純錄音偏長唔應成為換角色聲線嘅理由。「Chinese」聽寫結果本身唔代表已確認廣東話發音。自動修復仍可能失敗；校對報告會分清語言核對證據、內置目標語言後備聲線，同成功模擬原角色聲線。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Choose a conversion quality preset",
          "zh-HK": "選擇轉換品質方案"
        },
        "body": [
          {
            "en": "Welcome detects memory and the available processing backend. Full Drama 3 starts at 32 GB system/unified memory: on a 32 GB Apple Silicon Mac, the 28 GB model exceeds the 24 GB budget after reserving 8 GB for macOS, so loading may use swap, become very slow or fail. The 32 GB preset pairs it with Qwen 9B; 64 GB remains the tested best-quality recommendation for Drama 3 + Qwen 35B. On Windows, full Drama 3 Q2 runs on the CPU and is estimated to need 22 GB system RAM; dedicated VRAM does not accelerate this build. Other supported GPU models show their VRAM separately. The download list shows each model's memory pool and size before setup. You may download an over-budget model and explicitly try to load it with a warning; the current working model stays active if verification fails. Mac and Windows offer Qwen 9B and 35B; 4B downloads are no longer offered. Only versions with reviewed licence evidence are selectable. Hardware details is collapsed by default. Models & storage groups missing downloads, installed models and cleanup; runtime cleanup stays inside its own section. Removal shows real file progress and a result, then refreshes setup without restarting on Mac. Windows runtime removal closes the app first so loaded files can be released. Memory figures remain estimates until setup tests the actual runtime. Intel Macs are not supported.",
            "zh-HK": "Welcome 會偵測記憶體同可用執行方式。完整 Drama 3 由 32 GB 系統／統一記憶體起可嘗試：32 GB Apple Silicon Mac 扣除畀 macOS 嘅 8 GB 預留後，模型預算只得 24 GB，但 Drama 3 預估用 28 GB；可能使用交換空間、嚴重變慢或載入失敗。32 GB 組合配 Qwen 9B；實測廣東話效果最佳嘅 Drama 3 + Qwen 35B 仍建議 Apple Silicon 64 GB。Windows 完整 Drama 3 Q2 用 CPU，預估佔 22 GB 系統 RAM；獨立顯示卡 VRAM 唔會加速呢個版本。其他支援 GPU 嘅模型會另外顯示 VRAM。下載前清單會列出每個模型嘅記憶體類型、估算同下載量。超出建議預算嘅模型仍可下載及明確選擇試載入；系統會警告，驗證失敗會保留原本可用模型。Mac 同 Windows 提供 Qwen 9B 同 35B；4B 唔再供新下載。可選版本均有授權核對資料。硬件詳情預設收起；模型與儲存空間集中顯示待下載、已下載同清理操作。清理會顯示進度，Windows 移除執行環境前要先關閉 App。記憶體數字係估算，部署會測試實際載入；唔支援 Intel Mac。"
          },
          {
            "en": "Each preset has a short accent subtitle. Highest quality is closer to Hong Kong Cantonese; Balanced may retain a Japanese accent. This compares imitation from Japanese reference speech, not a guarantee for every sentence. Results vary with the reference recording, character voice and content.",
            "zh-HK": "標籤說明廣東話配音嘅大概表現：最高品質（較接近香港廣東話口音）、平衡（可能帶日語口音）。呢個係以日文原聲模擬角色聲線時嘅試聽比較，唔代表每句效果都有保證；實際效果會因參考錄音、角色聲線及內容而異。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "What AniCanto does",
          "zh-HK": "AniCanto 可以做甚麼"
        },
        "body": [
          {
            "en": "AniCanto turns Japanese anime dialogue into Hong Kong Cantonese, English, or both. It recognises speech, translates the script, generates speech and exports a movie with your selected audio and subtitle tracks. Translation and voice imitation can contain mistakes; audition important passages before sharing.",
            "zh-HK": "AniCanto 將日本動畫對白轉成香港廣東話、英文或雙語，依次辨識原聲、翻譯台詞、生成配音，再輸出所選音軌及字幕。翻譯與聲音模仿可能有偏差，分享前請試聽重要段落。"
          },
          {
            "en": "Basic and Expert are two views of the same library, settings, scripts and recordings. A view change does not restart processing. Production modes determine the work performed; interface modes determine which controls are visible.",
            "zh-HK": "基本模式與專家模式共用同一個影片庫、設定、台詞及錄音。切換介面不會重新開始轉換。「製作模式」決定執行哪些工序；「介面模式」決定顯示哪些操作。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Your first conversion",
          "zh-HK": "第一次轉換"
        },
        "body": [
          {
            "en": "In Welcome, choose the interface language and Basic mode. Review One-click setup and download the missing components. Wait until setup reports Ready to use.",
            "zh-HK": "在 Welcome 選擇介面語言與基本模式，檢視「一按部署」，下載所需元件，等候顯示可供使用。"
          },
          {
            "en": "Enter the studio. Choose Add videos in the workspace header, or drag one or more local video files into the app. Select a video in the left list.",
            "zh-HK": "進入工作室，在工作區上方按「加入影片」，或拖入一條或多條本機影片，再於左邊清單選片。"
          },
          {
            "en": "Choose a voice engine, dubbing languages and output subtitles. Leave Normal mode selected for everyday use, then choose Start conversion.",
            "zh-HK": "選擇配音引擎、配音語言與輸出字幕。日常使用可保留一般模式，再按「開始轉換」。"
          },
          {
            "en": "Follow the milestones. When output is saved, choose Play output or Show file. The exported movie and processing time remain in Projects and exports.",
            "zh-HK": "透過里程碑查看進度。成品儲存後可按「播放成品」或「顯示檔案」；專案及輸出會保留成品位置及處理時間。"
          }
        ],
        "steps": true
      }
    ]
  },
  {
    "id": "automatic-recovery",
    "title": {
      "en": "Automatic recovery and saved previews",
      "zh-HK": "自動修復與預覽交付"
    },
    "summary": {
      "en": "Retain first recordings, restore missing audio, and use optional independent listening.",
      "zh-HK": "保留首輪錄音、補回缺聲，再按需要獨立覆聽。",
      "zh-CN": "保留首轮录音、补回缺声，按需独立复听。",
      "ja": "最初の録音を保持し、欠けた音声を補完して必要に応じて聴き直します。"
    },
    "sections": [
      {
        "title": {
          "en": "Keep audible recordings",
          "zh-HK": "保留有聲錄音",
          "zh-CN": "保留有声录音",
          "ja": "有声音声を保持"
        },
        "body": [
          {
            "en": "Normal mode defaults to retaining the first audible recordings. Only missing or damaged audio is automatically regenerated, with at most two persistent extra attempts. Language labels and suspected missing words do not trigger retakes. Measured overlong lines still receive local meaning-preserving shortening, at most two passes, without restarting language review; only healthy recordings that fit are adopted, and originals remain saved. These recordings are not certified as correct; use the report and per-line audition. Detailed checking and repair remains an explicit Preferences option.",
            "zh-HK": "一般模式預設保留首輪有聲錄音，只自動補無聲或損壞，最多兩次額外嘗試並保存進度。語言標籤及懷疑漏句唔會再觸發重錄；實際超出安全時段嘅對白仍會局部保留意思改短，最多兩輪，唔重啟語言覆聽；新錄音有聲兼適合時段先採用，原錄音保留。唔代表已認證正確，請用報告同逐句試聽核對。偏好設定仍可明確選擇詳細檢查及修復。",
            "zh-CN": "一般模式默认保留首轮有声录音，只自动补无声或损坏，最多两次额外尝试并保存进度。语言标签及疑似漏句不再触发重录；实际超出安全时段的对白仍会局部保留意思改短，最多两轮，不重启语言复听；新录音有声且适合时段才采用，原录音保留。这不代表已认证正确，请使用报告和逐句试听核对。偏好设置仍可明确选择详细检查及修复。",
            "ja": "通常モードは最初の有声音声を保持し、無音・破損だけ最大2回追加生成します。言語ラベルや語の欠落の疑いでは再生成しません。実測で長すぎる台詞は意味を保って最大2回局所的に短縮し、言語確認を再開しません。正常で時間内に収まる録音のみ採用し、元音声も保持します。正しさの認証ではなく、レポートと行ごとの試聴で確認してください。詳細な自動確認と修復は環境設定で明示的に選べます。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Optional accelerated listening",
          "zh-HK": "可選加速覆聽",
          "zh-CN": "可选加速复听",
          "ja": "任意の高速聴き直し"
        },
        "body": [
          {
            "en": "On Apple Silicon, Preferences offers Auto, Apple MLX and CPU independent listening. Download and verify the optional 3.1 GB Whisper model before selecting MLX. Auto uses it only when fully installed. Each completed item is checkpointed; unchanged audio and model settings are reused across repair stages. A stalled item is left unconfirmed and later items can continue; unfinished items remain eligible on resume. Faster decoding is not proof of fewer recognition mistakes.",
            "zh-HK": "Apple Silicon 可喺偏好設定揀自動、Apple MLX 或 CPU 獨立覆聽；先下載及校驗約 3.1 GB Whisper 模型。自動只喺模型完整時用 MLX。每句完成即保存，相同錄音及模型設定跨修復階段沿用；單句超時會留作未確認並接續後面，未完成句子可喺續跑時再試。解碼快咗唔代表辨識更準。",
            "zh-CN": "Apple Silicon 可在偏好设置选择自动、Apple MLX 或 CPU 独立复听；先下载并校验约 3.1 GB Whisper 模型。每句完成即时保存，相同录音及模型设置跨修复阶段复用；单句超时保留为未确认并继续后续，未完成句子可在续跑时再试。速度更快不代表识别更准。",
            "ja": "Apple Silicon の環境設定で自動・Apple MLX・CPUを選択できます。MLXには約3.1 GBのWhisperモデルを事前導入・検証してください。各完了結果を保存し、同じ音声とモデル設定の結果を再利用します。タイムアウトした項目は未確認として残し、後続を続行できます。高速化は認識精度の向上を保証しません。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "welcome",
    "title": {
      "en": "Welcome, language and themes",
      "zh-HK": "Welcome、語言與主題"
    },
    "summary": {
      "en": "Choose your workspace and prepare the computer.",
      "zh-HK": "選擇工作模式並準備電腦環境。"
    },
    "sections": [
      {
        "title": {
          "en": "Interface language",
          "zh-HK": "介面語言"
        },
        "body": [
          {
            "en": "Welcome offers Traditional Chinese, Simplified Chinese, Japanese and English. Interface language does not change the selected dubbing or subtitle languages. Review production settings before starting. A running or resumed job keeps the settings submitted with that job.",
            "zh-HK": "Welcome 可揀繁體中文、簡體中文、日本語或 English。介面語言唔會改動配音或字幕語言；開始前請檢視製作設定。已提交或恢復中的工作會沿用該工作的原有設定。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Basic or Expert",
          "zh-HK": "基本或專家"
        },
        "body": [
          {
            "en": "Basic keeps import, production choices, progress and output together. Expert adds the editor, inspector, timeline, roles, review report, work queue, model centre, terminal and preferences. The Current mode button switches the view without duplicating the project.",
            "zh-HK": "基本模式集中處理匯入、製作選項、進度及成品。專家模式另有剪輯器、檢查器、時間軸、角色、校對報告、工作佇列、模型中心、終端機及偏好設定。「目前模式」按鈕可切換介面，不會建立重複專案。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Theme assistants",
          "zh-HK": "主題助手"
        },
        "body": [
          {
            "en": "The theme dots in Welcome change the accent colour, cover and assistant. While the app prepares local projects at launch, the selected assistant animates beside the progress indicator and you can choose Basic or Expert mode. The preview-off scene uses that theme’s assistant. The ensemble theme brings the assistants together. Appearance preferences control light, dark or system colours; reduced-motion system settings reduce decorative animation.",
            "zh-HK": "Welcome 的色點會切換主題色、封面與助手。啟動時，本機專案準備進度旁會顯示所選助手動畫；期間仍可揀基本或專家模式。關閉預覽時會顯示同一主題助手；同樂會主題會集合多位助手。偏好設定可選淺色、深色或跟隨系統；系統的減少動態效果設定會減少裝飾動畫。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Language and workspace preferences",
          "zh-HK": "語言與工作區偏好"
        },
        "body": [
          {
            "en": "Interface language is also available in Preferences, below Projects and exports in the left navigation. Changing it there preserves production language choices. New workflow entries use the new interface language; older entries and raw third-party/model logs keep their original wording. Theme colour is applied across the workspace, menus and panels. Each theme retains its own assistant identity in Welcome and the preview-off scene.",
            "zh-HK": "偏好設定亦有介面語言選項，位置喺左邊「專案及輸出」下方；喺度換語言會保留製作語言設定。新流程紀錄用新介面語言，舊紀錄同第三方／模型原始紀錄保留原文。主題顏色會套用到工作區、選單同面板；Welcome 同關閉預覽畫面會沿用同一主題助手身份。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "setup",
    "title": {
      "en": "Models, downloads and cleanup",
      "zh-HK": "模型、下載與移除"
    },
    "summary": {
      "en": "Install, switch, repair and remove downloaded packages.",
      "zh-HK": "部署、更換、修復或移除下載元件。"
    },
    "sections": [
      {
        "title": {
          "en": "One-click setup",
          "zh-HK": "一按部署"
        },
        "body": [
          {
            "en": "Setup detects the platform and available memory, then proposes a suitable model for each purpose. The plan separates text translation, speech generation, speech recognition, reference transcription, background separation, audio classification and runtimes. AudioSet classifies music and speech to assist OP / ED analysis; it does not generate dubbing.",
            "zh-HK": "部署會偵測平台與可用記憶體，按用途建議合適模型。清單分開列出文字翻譯、語音生成、語音辨識、參考轉錄、背景分離、音訊分類及執行環境。AudioSet 用來區分音樂與語音，協助 OP／ED 分析，不負責生成配音。"
          },
          {
            "en": "The download panel shows the current file, transferred size, total size and speed when the server supplies those values. Verification and runtime installation may continue after the last download. Pause download before quitting. Existing verified files are reused.",
            "zh-HK": "下載面板會顯示目前檔案、已傳輸容量、總容量與速度；部分資料視伺服器回應而定。最後一個檔案下載後仍可能需要驗證及安裝執行環境。退出前可暫停下載；已驗證檔案會重用。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Choose and switch models",
          "zh-HK": "選擇與更換模型"
        },
        "body": [
          {
            "en": "Use Change models in Basic, or Model centre → Add / switch model in Expert. Pick the voice engine and available model variants, review the download plan, then confirm. Memory suitability can differ between CPU, Apple unified memory and dedicated GPU memory; the largest model is not always the best choice for your computer.",
            "zh-HK": "基本模式可按「更改模型」，專家模式可用「模型中心 → 新增／更改模型」。選引擎及可用模型版本，檢視下載清單後確認。CPU、Apple 統一記憶體與獨立顯示記憶體的容量要求不同，最大模型未必最適合目前電腦。"
          },
          {
            "en": "In Basic, replacement normally keeps one selected model per purpose. The replacement must download and verify before the previous package is removed. Expert can keep multiple variants. Switching a model does not rewrite a job already submitted.",
            "zh-HK": "基本模式一般每類用途保留一個所選模型；新模型下載並驗證後才移除舊模型。專家模式可保留多個版本。更換模型不會改寫已提交工作的設定。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Repair download or Download again",
          "zh-HK": "修復下載與重新下載"
        },
        "body": [
          {
            "en": "In Model centre, a partial package shows the saved size and missing files. Repair download checks file checksums and retrieves only missing or damaged files. Download again stages fresh copies and verifies them before replacing current files. Pause conversion before maintenance.",
            "zh-HK": "模型中心會顯示未完整下載的容量及缺少檔案。「修復下載」會檢查校驗碼，只補缺少或損壞的檔案。「重新下載」會先下載及驗證新副本，再取代現有檔案。維護模型前請先暫停轉換。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Clean up downloads",
          "zh-HK": "清理下載內容",
          "zh-CN": "清理下载内容",
          "ja": "ダウンロード済みファイルの整理"
        },
        "body": [
          {
            "en": "Welcome → Models & storage has one Clean up downloads entry. Choose Models only to remove model files and partial downloads while retaining execution environments, or Models and execution environments to clear all downloaded components. The latter requires preparing the environments again on the next setup. Videos, projects and finished exports are kept.",
            "zh-HK": "開始畫面「模型及儲存空間」只保留一個「清理下載內容」入口。揀「只移除模型」會刪模型及未完成下載，保留執行環境；揀「模型及執行環境」會清理全部下載元件，下次需重新準備環境。影片、專案同已完成作品會保留。",
            "zh-CN": "开始画面「模型与存储空间」只保留一个「清理下载内容」入口。选择「仅移除模型」会删除模型和未完成下载，保留运行环境；选择「模型和运行环境」会清理全部下载组件，下次需要重新准备环境。影片、项目和已完成作品会保留。",
            "ja": "開始画面の「モデルとストレージ」にある「ダウンロード済みファイルを整理」から範囲を選びます。「モデルのみ」はモデルと未完了のダウンロードを削除し、実行環境を残します。「モデルと実行環境」は全ダウンロード済みコンポーネントを削除するため、次回に環境の再準備が必要です。動画・プロジェクト・完成作品は保持されます。"
          },
          {
            "en": "Review removal scans the selected scope and shows the folders, file count and space before the final confirmation. Cancel keeps all files. Changing the scope alone does not remove anything. Pause processing before cleanup. Windows may close the app to finish removing files in use.",
            "zh-HK": "按「檢視清理內容」會先掃描所選範圍，列出資料夾、檔案數量同容量，再確認先刪除；取消會保留全部檔案，單純改選項唔會清理。處理影片期間請先暫停。Windows 有時需要關閉 app，先可以清理使用中嘅元件。",
            "zh-CN": "按「查看清理内容」会先扫描所选范围，列出文件夹、文件数量和容量，最终确认后才删除。取消会保留全部文件，仅切换选项不会清理。请先暂停影片处理。Windows 有时需要关闭应用，才能清理使用中的组件。",
            "ja": "「削除内容を確認」で選んだ範囲をスキャンし、フォルダー・ファイル数・容量を確認してから削除します。キャンセルすれば全ファイルが残ります。範囲の選択だけでは何も削除されません。処理中は先に一時停止してください。Windowsでは使用中のファイルを削除するためにアプリ終了が必要な場合があります。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "CosyVoice 3 availability",
          "zh-HK": "CosyVoice 3 平台限制"
        },
        "body": [
          {
            "en": "CosyVoice 3 is an optional voice engine on Apple Silicon Macs and Windows PCs with NVIDIA CUDA. It downloads pinned official FunAudioLLM PyTorch weights (about 9.7 GB) and retains the published Apache-2.0 notice. On Mac, inference uses CPU and may be considerably slower than Drama 3. Setup verifies files and model loading; always audition Cantonese, English and character resemblance before relying on a full episode.",
            "zh-HK": "CosyVoice 3 係 Apple Silicon Mac 同配備 NVIDIA CUDA 嘅 Windows 電腦可選配音引擎。佢會下載固定版本嘅 FunAudioLLM 官方 PyTorch 權重（約 9.7 GB），並保留模型公布嘅 Apache-2.0 授權資料。Mac 會用 CPU 推理，可能明顯慢過 Drama 3。部署會校驗檔案同載入模型；轉完整一集之前，請先試聽廣東話、英文同角色聲線。"
          },
          {
            "en": "To add CosyVoice 3, open Model centre or Change models, select CosyVoice 3, check its download size and memory estimate, then download and switch. You can keep Drama 3 and another installed voice engine for automatic retries. WenetSpeech-Yue ZoengJyutGaai is the available Cantonese-only version; the older Base version is no longer offered for new downloads. Already installed Base files and earlier recordings remain available. Unverified community MLX CosyVoice 3 conversions remain unavailable; Windows AMD, Intel and CPU-only CosyVoice 3 are not offered.",
            "zh-HK": "要加 CosyVoice 3，去「模型中心」或「更改模型」選 CosyVoice 3，睇清下載量同記憶體估算，再下載及切換。可以同時保留 Drama 3 同另一款已安裝語音引擎，供自動重試使用。WenetSpeech-Yue 現時提供 ZoengJyutGaai 廣東話版；舊 Base 版唔再提供新下載，已安裝檔案同舊錄音會保留。未核清來源嘅社群 MLX CosyVoice 3 轉換版仍停用；Windows AMD、Intel 同純 CPU 暫不提供 CosyVoice 3。"
          },
          {
            "en": "Other engines may support selected AMD cards through the pinned ROCm stack. That is separate from CosyVoice 3 availability and from AMD hardware video encoding. Supported GPU model, driver, runtime and a real model test all matter; no AMD voice backend is advertised as fully hardware-qualified without such a test.",
            "zh-HK": "其他引擎可以按固定版本嘅 ROCm 執行環境支援部分 AMD 卡，呢個同 CosyVoice 3 選項、AMD 硬件影片編碼係分開嘅功能。顯示卡型號、驅動、執行環境同實際模型測試都要配合；未通過實機模型測試，唔會標示為已完整驗證嘅 AMD 配音。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Remove one version and shared files",
          "zh-HK": "移除單一版本與共用檔案"
        },
        "body": [
          {
            "en": "Use the Remove button beside a downloaded model in Model centre. A selected model or a model required by a waiting/paused job is protected; choose a replacement or resolve that job first. Removing GPT V2 or V4 can retain common files still used by the other version. The result distinguishes the space actually freed from shared files retained. A logical removal must not keep showing the removed version merely because another version owns a common file.",
            "zh-HK": "模型中心每個已下載模型旁邊有「移除」。目前使用，或者等待／暫停工作仍需要嘅模型會受保護；先換另一個模型或處理相關工作。移除 GPT V2 或 V4 時，另一版本仍需要嘅共用檔案會保留；結果會分開顯示實際釋放空間同保留共用容量，唔會因為共用檔案仍在而將已移除版本繼續當作已安裝。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "basic",
    "title": {
      "en": "Basic mode and batch conversion",
      "zh-HK": "基本模式與批量轉換"
    },
    "summary": {
      "en": "Set up one episode or a queue of episodes with minimal controls.",
      "zh-HK": "以少量選項製作單集或多集影片。"
    },
    "sections": [
      {
        "title": {
          "en": "Import and select",
          "zh-HK": "匯入與選片"
        },
        "body": [
          {
            "en": "Add videos accepts local MP4, MKV, MOV and other supported video containers. You can select multiple files or use drag and drop. The left list shows each episode’s status and accumulated processing time. Selecting another episode changes the preview and project shown; it does not change the running job.",
            "zh-HK": "「加入影片」接受 MP4、MKV、MOV 等支援的本機影片容器，可多選或拖放。左邊清單顯示各集狀態及累計處理時間。選另一集只會切換目前顯示的專案，不會更改正在執行的工作。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Production choices",
          "zh-HK": "製作選項"
        },
        "body": [
          {
            "en": "In Basic mode, choose Cantonese, English or both. The app keeps the original audio track, background music and sound effects automatically. Voice engines, additional engine tracks, production modes, OP / ED overrides and custom subtitle combinations belong to Expert mode. Change models remains available for reviewing a model replacement download plan.",
            "zh-HK": "基本模式只需選廣東話、英文或雙語，程式自動保留原聲音軌、背景音樂及音效。配音引擎、多引擎音軌、製作模式、OP／ED 自訂及字幕組合在專家模式設定；基本模式仍可按「更改模型」檢視模型更換與下載方案。"
          },
          {
            "en": "For new conversions, translated subtitles follow the dubbing language automatically. Cantonese output includes Cantonese captions; English output includes English captions; bilingual output includes separate Cantonese and English captions and one combined learning track. One preferred original text subtitle is retained when available. Burnt-in text and OCR evidence do not create another original track. Cantonese is the default caption when present, followed by English, the learning track and original captions. Expert starts with these defaults and can deselect tracks; Restore automatic subtitles follows the current dubbing languages again. Multiple voice engines do not duplicate caption tracks.",
            "zh-HK": "新轉換的字幕會跟隨配音語言：廣東話輸出附廣東話譯文；英文輸出附英文譯文；雙語輸出有獨立廣東話、獨立英文及一條雙語學習字幕。有可抽取的原裝文字字幕時保留一條優先原裝軌，燒錄文字及 OCR 參考不會另建原裝字幕。廣東話字幕優先並設為預設，之後依次為英文、雙語學習及原裝字幕。專家模式沿用同一預設，可自行剔除，或按「還原自動字幕設定」再次跟隨配音語言。多引擎不會重複字幕軌。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Start, resume and batches",
          "zh-HK": "開始、繼續與批量"
        },
        "body": [
          {
            "en": "Basic and Expert use the same queue workflow. Start processes every unfinished video in the video-list order, one at a time. Completed outputs are skipped. Resume continues a paused video with its saved settings and then the remaining queue. Videos added during a running queue join the remaining work. Drag a waiting video handle or use its up/down arrows to change future order; a running video is not restarted or moved out of its current processing slot. Order is shared by the video list, Work queue and Projects and exports. Pause & save stops automatic continuation. Failed videos retain their reason and the next waiting video continues; the same failed video is not retried repeatedly in one session. An explicit Retry or Produce a new version remains a separate selected-video action.",
            "zh-HK": "基本同專家模式共用同一佇列流程。「開始」會按影片清單順序逐條處理全部未完成影片，跳過已完成成品。「繼續」先用已保存設定續做暫停影片，再接續餘下清單；轉換中加入嘅影片亦會排入。未開始影片可拖曳左邊手柄或用上下箭嘴調位；正在處理嗰集唔會重開或被移走。影片清單、工作佇列同專案及輸出共用排序。「暫停並保存」會停止自動接續。失敗影片保留原因後繼續下一條，同一輪唔會無限重試。明確按「重試」或「製作新版本」仍然係指定影片嘅獨立操作。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Resume unfinished work",
          "zh-HK": "繼續全部未完成影片"
        },
        "body": [
          {
            "en": "Continue all unfinished videos follows the left-hand queue one episode at a time, reusing saved scripts and matching completed recordings. It includes paused and attention items when that command explicitly says all unfinished; an incomplete preview is not a finished dub. Opening the app alone does not restart conversion. A queue summary or 100% progress is not proof that every sentence was repaired; read the individual result labels.",
            "zh-HK": "「繼續全部未完成影片」會按左邊清單逐條處理，沿用已儲存台詞同相符嘅完成錄音；當按鈕明確寫全部未完成，會包括暫停同需要處理項目，未完整預覽唔當作完整配音。單純開啟 App 唔會自行重啟轉換；批次摘要或 100% 進度亦唔代表每句都已修好，要以各片結果標籤為準。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "modes",
    "title": {
      "en": "Normal, High speed and Full AI review",
      "zh-HK": "一般、高速與完整 AI 模式"
    },
    "summary": {
      "en": "Understand what each production mode checks and why time differs.",
      "zh-HK": "了解不同製作模式的檢查範圍與時間差異。"
    },
    "sections": [
      {
        "title": {
          "en": "Normal mode — recommended",
          "zh-HK": "一般模式：日常建議"
        },
        "body": [
          {
            "en": "Normal mode defaults to retaining the first audible recordings. Only missing or damaged audio is automatically regenerated, with at most two persistent extra attempts. Language labels and suspected missing words do not trigger retakes. Measured overlong lines still receive local meaning-preserving shortening, at most two passes, without restarting language review; only healthy recordings that fit are adopted, and originals remain saved. These recordings are not certified as correct; use the report and per-line audition. Detailed checking and repair remains an explicit Preferences option.",
            "zh-HK": "一般模式預設保留首輪有聲錄音，只自動補無聲或損壞，最多兩次額外嘗試並保存進度。語言標籤及懷疑漏句唔會再觸發重錄；實際超出安全時段嘅對白仍會局部保留意思改短，最多兩輪，唔重啟語言覆聽；新錄音有聲兼適合時段先採用，原錄音保留。唔代表已認證正確，請用報告同逐句試聽核對。偏好設定仍可明確選擇詳細檢查及修復。",
            "zh-CN": "一般模式默认保留首轮有声录音，只自动补无声或损坏，最多两次额外尝试并保存进度。语言标签及疑似漏句不再触发重录；实际超出安全时段的对白仍会局部保留意思改短，最多两轮，不重启语言复听；新录音有声且适合时段才采用，原录音保留。这不代表已认证正确，请使用报告和逐句试听核对。偏好设置仍可明确选择详细检查及修复。",
            "ja": "通常モードは最初の有声音声を保持し、無音・破損だけ最大2回追加生成します。言語ラベルや語の欠落の疑いでは再生成しません。実測で長すぎる台詞は意味を保って最大2回局所的に短縮し、言語確認を再開しません。正常で時間内に収まる録音のみ採用し、元音声も保持します。正しさの認証ではなく、レポートと行ごとの試聴で確認してください。詳細な自動確認と修復は環境設定で明示的に選べます。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "High speed",
          "zh-HK": "高速模式"
        },
        "body": [
          {
            "en": "Skips quality review and quality-driven retakes. It still needs speech recognition, translation, speech generation and movie encoding. It can be faster, but may leave missing, incomplete, incorrectly pronounced or mismatched voices. Choose it when you want an unreviewed first pass.",
            "zh-HK": "跳過品質覆核及因品質問題觸發的重錄，但仍需辨識、翻譯、生成配音及封裝影片。速度較快，惟可能有缺句、不完整、讀音或聲線不符，適合試看未經覆核的初稿。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Full AI review",
          "zh-HK": "完整 AI 檢測模式"
        },
        "body": [
          {
            "en": "Expert mode exposes fuller review, audio grouping and optional visual role analysis. Expect roughly three times Normal conversion time as a planning guide; actual time varies with hardware, episode length, model sizes and retries. Visual analysis is optional and off by default.",
            "zh-HK": "專家模式提供較完整的覆核、聲音分組及可選的角色影像分析。規劃時可估約一般轉換的三倍時間；實際仍視硬件、片長、模型與重試次數而定。影像分析為選項，預設關閉。"
          },
          {
            "en": "Changing the interface to Expert does not automatically enable Full AI review. Select the production mode before starting a new conversion.",
            "zh-HK": "切換到專家介面不會自動啟用完整 AI 檢測，須在新轉換前另選製作模式。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "preview",
    "title": {
      "en": "Preview, playback and follow",
      "zh-HK": "預覽、播放與跟隨處理"
    },
    "summary": {
      "en": "Load video only when needed and compare original and generated speech.",
      "zh-HK": "有需要才載入影片，比較原聲與配音。"
    },
    "sections": [
      {
        "title": {
          "en": "Open or close preview",
          "zh-HK": "開啟或關閉預覽"
        },
        "body": [
          {
            "en": "Video preview starts off. The themed assistant scene occupies the preview area without decoding a movie. Choose Open preview to load the current source; Close preview stops playback and releases the video source. Conversion continues independently of whether preview is open.",
            "zh-HK": "影片預覽預設關閉，由主題助手畫面代替，毋須解碼影片。「開啟預覽」才載入目前原片；「關閉預覽」會停止播放並釋放影片來源。預覽開關不影響轉換繼續執行。"
          },
          {
            "en": "Some MKV or HEVC sources need a compatible preview copy before playback. The assistant and preparing message remain visible while that copy is made. A preview error does not delete the project. Retry preview or leave it off to continue conversion.",
            "zh-HK": "部分 MKV 或 HEVC 影片需先製作相容預覽副本。準備期間仍會顯示助手與提示。預覽錯誤不會刪除專案，可重試預覽或保持關閉繼續轉換。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Playback controls",
          "zh-HK": "播放操作"
        },
        "body": [
          {
            "en": "Play original starts the Japanese source. The time slider seeks within the selected video. Preview captions chooses Cantonese, English, original subtitles or none; this changes the monitor only. Use Output subtitles to choose tracks in the finished movie.",
            "zh-HK": "播放原聲會播放日文來源，時間滑桿可跳到指定位置。「預覽字幕」可選廣東話、英文、原片或關閉，只影響監看畫面；成品字幕需在「輸出字幕」另選。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Follow processing and audition",
          "zh-HK": "跟隨處理與試聽"
        },
        "body": [
          {
            "en": "Follow processing moves the playhead to the line reported by processing. It does not restart work or force the progress percentage. Turn it off when browsing manually. Auditioning a generated recording uses a separate audio player; selecting Follow processing stops that audition before following.",
            "zh-HK": "「跟隨處理」會將播放位置移到目前處理的對白，不會重新開始工作或更改進度百分比。手動查看其他位置時可關閉；配音試聽使用獨立播放器，再開啟跟隨處理時會先停止試聽。"
          },
          {
            "en": "Listen plays the available generated take for that line and engine; Play original plays the source. A disabled recording button means no matching playable take is available yet. Stop stops the current audio or video playback.",
            "zh-HK": "「試聽」播放該句及該引擎已有的配音；原聲按鈕播放來源。配音按鈕停用代表目前沒有對應可播放錄音。「停止」可停止目前音訊或影片。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "progress",
    "title": {
      "en": "Progress, timing and pause",
      "zh-HK": "進度、耗時與暫停"
    },
    "summary": {
      "en": "Read milestones and distinguish elapsed time from an estimate.",
      "zh-HK": "理解里程碑、實際耗時與預計時間。"
    },
    "sections": [
      {
        "title": {
          "en": "Milestones",
          "zh-HK": "階段里程碑"
        },
        "body": [
          {
            "en": "Basic shows preparation, Japanese recognition, translation, dubbing and export. Expert also shows roles and repair/review when relevant. A completed milestone shows its recorded processing time; cached work may be labelled as existing data. A skipped stage was not executed.",
            "zh-HK": "基本模式顯示準備、日語辨識、翻譯、配音及匯出；專家模式會按需要顯示角色及修復／覆核。已完成階段會顯示記錄耗時；重用快取可能顯示已有資料。「略過」代表沒有執行該階段。"
          },
          {
            "en": "Progress belongs to an attempt. It should not move backward within that attempt. Starting a new output version begins a new attempt, while previously accumulated processing time remains. Repairs can take time without moving the bar much.",
            "zh-HK": "進度屬於每一次處理工作，同一次工作內不應倒退。製作新版本會展開新工作，之前的累計時間仍會保留。修復過程可能花時間而進度條變化不大。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Time and ETA",
          "zh-HK": "耗時與預計時間"
        },
        "body": [
          {
            "en": "Accumulated processing is the total recorded active processing across attempts. This run is the current attempt’s active time. Remaining time is an estimate that needs completed work samples; model loading, downloads, cache reuse and retries make early estimates uncertain. A blank estimate is not proof that processing stopped.",
            "zh-HK": "累計處理時間是歷次工作記錄的有效處理時間總和；本次時間是目前工作。預計剩餘時間需要已完成工序的樣本；載入模型、下載、快取與重試會令早期估算不穩定。暫未有估計時間不代表工作停止。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Pause and resume safely",
          "zh-HK": "暫停與恢復"
        },
        "body": [
          {
            "en": "Choose Pause & save before quitting during conversion. Wait for the paused status. Resume reuses saved scripts and valid recordings where possible. Do not delete downloaded models during a running conversion. If a job reports Needs attention, read Terminal and export a debug report before retrying.",
            "zh-HK": "轉換期間退出前請按「暫停並保存」，等候顯示已暫停。恢復時會盡量重用已存台詞及有效錄音。轉換中不要移除模型；如顯示需要處理，先看終端機並匯出除錯報告，再重試。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "expert",
    "title": {
      "en": "Expert workspace and timeline",
      "zh-HK": "專家工作區與時間軸"
    },
    "summary": {
      "en": "Navigate panels, select dialogue and save an editing draft.",
      "zh-HK": "操作面板、選取對白並儲存剪輯草稿。"
    },
    "sections": [
      {
        "title": {
          "en": "Workspace layout",
          "zh-HK": "工作區佈局"
        },
        "body": [
          {
            "en": "The left navigation selects Edit, Roles, Review report, Produce, Work queue, Terminal, Production defaults, Model centre, Preferences or Projects and exports. The video list selects the project. The right inspector provides Production, Dialogue, Picture and Mix. Header panel icons independently show or hide navigation, video list and inspector.",
            "zh-HK": "左邊導覽可選剪輯、角色、校對報告、製作匯出、工作佇列、終端機、製作預設、模型中心、偏好設定及專案及輸出。影片清單選專案；右邊檢查器有製作、對白、畫面及混音。上方的面板圖示可獨立開關導覽、影片清單及檢查器。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Select and navigate dialogue",
          "zh-HK": "選取與瀏覽對白"
        },
        "body": [
          {
            "en": "Click a dialogue clip in the timeline or use Previous / Next in the transcript. HK and EN select the script or recording language. The timeline shows video, Japanese audio, background, subtitles, delivery windows and generated tracks. Different rows describe different data; a subtitle rectangle alone does not prove that audio exists.",
            "zh-HK": "在時間軸按對白片段，或用台詞區的上一句／下一句。HK、EN 可切換台詞或錄音語言。時間軸分開顯示影片、日文原聲、背景、字幕、配音時段與已生成音軌。各列代表不同資料；有字幕方塊不表示已有錄音。"
          },
          {
            "en": "Click a timeline time position to seek. Use zoom to change the visible time scale. Split video divides the current video clip at the playhead; clip settings control enabled ranges and ripple behaviour. Add dialogue creates a manual line at the playhead. These are draft edits until saved and exported.",
            "zh-HK": "按時間軸位置可跳轉；縮放可改變時間刻度。「分割影片」在游標位置拆分片段，剪接設定可控制啟用範圍及連動；「新增對白」在游標位置加入手動句子。儲存及匯出前，這些更改屬於草稿。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Drafts, undo and export",
          "zh-HK": "草稿、復原與匯出"
        },
        "body": [
          {
            "en": "Save draft preserves script, timing, role, take and clip choices. Ctrl+S on Windows or Command+S on Mac saves the draft. Undo and Redo apply to edits held in this editing session. Export video renders a new output using the saved choices; it is distinct from generating one line again.",
            "zh-HK": "「儲存草稿」保留台詞、時間、角色、錄音及片段選項。Windows 用 Ctrl+S，Mac 用 Command+S。「復原／重做」處理本次編輯中的更改。「匯出影片」按草稿產生新版成品，與逐句重新配音不同。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Browse without losing your place",
          "zh-HK": "保留位置與左右瀏覽"
        },
        "body": [
          {
            "en": "Selecting a subtitle or voice clip, receiving new recordings or refreshing the editor keeps the timeline scroll position. Selecting a line updates its inspector and playhead without enabling video preview. Use the left/right navigation buttons to move through the visible range, drag the Browse timeline slider for longer distances, or drag the time ruler horizontally. Shift + mouse wheel and horizontal trackpad gestures also browse sideways. Show playhead centres the current playback position. Zoom changes the scale while retaining the visible time range as closely as possible.",
            "zh-HK": "點選字幕或配音片段、收到新錄音，或者更新剪輯器，都會保留時間線捲動位置。選句只更新檢查器同播放位置，唔會因此開啟影片預覽。可用左右按鈕移動可見範圍、拖「左右瀏覽時間線」滑桿跳到遠處，或拖住時間尺左右移動；Shift 加滑鼠滾輪同觸控板橫向手勢亦可左右瀏覽。「移到播放位置」會將目前播放位置移到畫面中央；縮放時會盡量保留正在睇嘅時間範圍。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "retakes",
    "title": {
      "en": "Listen, retake and recording history",
      "zh-HK": "試聽、重錄與錄音歷史"
    },
    "summary": {
      "en": "Compare engines and regenerate an individual line.",
      "zh-HK": "比較引擎並重新生成個別句子。"
    },
    "sections": [
      {
        "title": {
          "en": "Listen and Use recording",
          "zh-HK": "試聽與採用錄音"
        },
        "body": [
          {
            "en": "In Dialogue → Listen, choose the dubbing language and a recording engine with an available take. Listen first, then Use recording to adopt that take in the draft. The engine displayed for adoption matters; the production engine and a comparison take can differ.",
            "zh-HK": "在對白 → 試聽，選配音語言及已有錄音的引擎。先試聽，再按「採用錄音」寫入草稿。請留意採用按鈕旁顯示的引擎；主要製作引擎與比較用錄音可以不同。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Retake one line",
          "zh-HK": "逐句重錄"
        },
        "body": [
          {
            "en": "Select a dialogue line and choose Retake. Edit the text for the selected language, choose an installed engine and generate that line. The model must be ready. Existing project audio is retained while a new take is produced. Listen to the result, choose the take you want, save the draft and export a new movie version.",
            "zh-HK": "選對白後進入重錄，修改目前語言台詞，選已部署引擎並生成本句。模型須已準備好；產生新錄音時會保留現有專案錄音。聽過結果後採用所需版本、儲存草稿，再匯出新版影片。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Adjust and history",
          "zh-HK": "調整與歷史"
        },
        "body": [
          {
            "en": "Adjust exposes the line’s enabled state, timing, rate and trim fields available in the inspector. Earlier or rejected recordings may be listed in history and the review report. Listen to a retained failure before deciding whether it is acceptable; incomplete speech is different from a merely imperfect accent. Availability depends on which attempts were recorded.",
            "zh-HK": "調整頁可修改檢查器提供的啟用、時段、語速及修剪欄位。歷史與校對報告可能列出先前或未採用錄音。先聽保留的失敗版本再判斷是否接受；缺少半句與口音未臻理想是不同問題，歷史內容取決於已有處理紀錄。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "multiengine",
    "title": {
      "en": "Multiple TTS engines and tracks",
      "zh-HK": "多個 TTS 引擎與音軌"
    },
    "summary": {
      "en": "Generate separate engine and language tracks for comparison.",
      "zh-HK": "產生獨立引擎及語言音軌作比較。"
    },
    "sections": [
      {
        "title": {
          "en": "Select additional engines",
          "zh-HK": "選擇額外引擎"
        },
        "body": [
          {
            "en": "In Expert → Production defaults, or Edit → Production, expand Additional voice engines. Select each engine to include. The main Voice engine remains the default track and cannot be unchecked there. Deploy extra engines in Model centre before starting.",
            "zh-HK": "專家模式的製作預設，或剪輯 → 製作內，展開「額外配音引擎」並選取。主要配音引擎仍為預設音軌，不能在這裏取消。新工作開始前請先在模型中心部署額外引擎。"
          },
          {
            "en": "New conversions generate separate tracks for selected supported engine/language pairs. Engines run sequentially to limit memory use; more tracks take longer. WenetSpeech-Yue is for Cantonese, so it does not supply an English track. Selecting an extra engine does not add it to an already running or resumed job.",
            "zh-HK": "新轉換會按支援的引擎／語言組合建立獨立音軌。引擎依次執行以控制記憶體，音軌越多時間越長。WenetSpeech-Yue 用於廣東話，沒有英文音軌。新勾選引擎不會加入已開始或恢復的工作。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "subtitles",
    "title": {
      "en": "Translation sources and subtitles",
      "zh-HK": "翻譯來源與字幕"
    },
    "summary": {
      "en": "Understand original captions, translated scripts and timing.",
      "zh-HK": "分清原片字幕、翻譯台詞及時間。"
    },
    "sections": [
      {
        "title": {
          "en": "Automatic screen subtitles and OCR",
          "zh-HK": "自動畫面字幕與 OCR"
        },
        "body": [
          {
            "en": "OCR speed and progress: when recognised speech is the primary source, screen captions are sampled near heard turns instead of recognising every 0.2-second image. Short turns retain adjacent samples and long turns receive additional samples. Pure OCR keeps dense sampling. Progress shows completed frames; debug reports record actual frame count and elapsed time. Completed OCR is cached and invalidated when the source or OCR settings change. This optimisation does not delete heard dialogue.",
            "zh-HK": "OCR 速度與進度：原聲聽寫作主要來源時，按已聽到對白位置抽樣，唔再每 0.2 秒反覆辨識。短句保留相鄰樣本，長句增加樣本；純 OCR 保留密集掃描。進度顯示已處理畫面數，除錯紀錄保留實際張數與耗時。完成嘅 OCR 會快取；影片或 OCR 設定改變就重新辨識，唔會因此刪走已聽到嘅對白。"
          },
          {
            "en": "For an external SRT, ASS, SSA or VTT file, select a video, then open Subtitle source above the preview and choose Import subtitle file. The selected file belongs only to that video and takes priority over a matching sidecar or embedded track. Without an import, automatic detection looks for a matching sidecar, then an embedded text track, then lower-screen OCR. Source speech remains primary for translation; subtitles provide timed context for names and meaning. A running or paused conversion retains its original subtitle choice. If the file moves, choose it again before starting a new conversion.",
            "zh-HK": "外掛 SRT、ASS、SSA 或 VTT 字幕：先揀影片，再喺預覽上方開「字幕來源」並按「匯入字幕檔」。所揀檔案只屬於呢條影片，優先於同名外掛檔或內嵌字幕軌。未匯入時會自動搵同名外掛檔、內嵌文字字幕，最後檢查畫面下方 OCR。翻譯仍以原聲為主要依據，字幕提供對時嘅人名同意思參考。轉換中或已暫停工作沿用提交時嘅字幕；檔案如有移動，開始新轉換前要重新選擇。"
          },
          {
            "en": "In Expert mode, select Japanese audio + screen OCR to force this speech-first OCR route even when a text subtitle track exists. Japanese audio only disables all caption evidence. These settings apply to newly submitted conversions; paused work retains its submitted settings.",
            "zh-HK": "專家模式可選「日文原聲＋畫面 OCR」，即使有文字字幕軌都使用先聽原聲、再讀畫面嘅流程。「只用日文語音」會停用所有字幕參考。呢啲設定用於新提交轉換；已暫停嘅工作保留提交時設定。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Other source languages — experimental",
          "zh-HK": "其他原聲語言：實驗功能"
        },
        "body": [
          {
            "en": "Before a new conversion, the app checks the selected audio track, not the subtitle language. When audio metadata is unavailable, it samples three parts of the source with the installed recogniser. Non-Japanese sources require a confirmation showing the detected language and planned conversion. Unsupported or uncertain languages do not start automatically. Cancelling also stops automatic queue continuation. Model and voice-reference compatibility vary by language and engine; this is not a claim that all languages have equal quality.",
            "zh-HK": "新轉換前會核對所選原聲音軌，而非字幕語言；缺少音軌語言資料時，會用已部署辨識器抽樣三個位置。非日文來源會先顯示偵測語言與轉換內容，等候確認；未確認或不支援的語言不會自動開始。取消亦會停止自動接續佇列。不同語言及引擎的模仿相容性有差異，不代表全部語言有相同品質。"
          },
          {
            "en": "English source generates Cantonese dubbing and Cantonese translated subtitles only. Other supported source languages retain the selected Cantonese / English / bilingual output. Non-Japanese sources use Normal mode with independent source references, and the transcript heading identifies the original language.",
            "zh-HK": "英文原聲只生成廣東話配音及廣東話譯文字幕；其他支援語言保留廣東話／英文／雙語輸出選項。非日文來源使用一般模式及逐句獨立原聲參考，原文欄會標示來源語言。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Natural speech and concise translation",
          "zh-HK": "自然語速與精簡翻譯"
        },
        "body": [
          {
            "en": "English drafts use concise spoken phrasing and a duration budget. Suspected copied neighbouring text is checked against the source, preserving genuine repetition. Overlong automatic recordings trigger bounded, saved shortening and regeneration attempts. Safe gaps and small onset shifts are considered before rewriting; final tempo follows the measured 5% normal limit and the narrowly bounded short-line exception described above. Manual scripts and audio are protected. Unresolved timing remains visible and is not certified as complete.",
            "zh-HK": "英文稿會按時長目標使用簡潔口語；疑似串入鄰句會對照來源核對，真正重複對白仍會保留。超時錄音會觸發有限次、可續做嘅精簡同重錄；先考慮安全空檔同小幅起點微調，再改寫，最後按上述一般 5% 上限同短句例外作實測微量調速。手動稿件同錄音會保留；未解決嘅時長問題會清楚顯示，唔會標為完整通過。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Audio and subtitles",
          "zh-HK": "語音與字幕"
        },
        "body": [
          {
            "en": "The default combines Japanese speech evidence with available source subtitles. Automatic subtitles per video looks for matching external subtitles, embedded tracks and, where supported and configured, OCR. Recognition timing helps align the translated speech. Original captions and generated dialogue are separate records and can have different boundaries.",
            "zh-HK": "預設會結合日語語音證據與可用原片字幕。「逐片自動選字幕」會尋找對應外置字幕、內嵌軌及已支援並設定的 OCR。語音辨識時間協助配音對齊；原片字幕與生成台詞是獨立紀錄，時間範圍可能不同。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Japanese audio only — Expert",
          "zh-HK": "只用日語原聲：專家選項"
        },
        "body": [
          {
            "en": "Choose Translation source → Japanese audio only before submitting a new conversion. Translation ignores OCR and original Chinese subtitles and uses recognised Japanese speech. You can generate Cantonese, English or both. Missing or incorrect Japanese recognition will affect the translation, even if a source subtitle is visible elsewhere.",
            "zh-HK": "新轉換前選「翻譯來源 → 只用日語原聲」。翻譯會忽略 OCR 與原裝中文字幕，使用日語辨識結果，可生成廣東話、英文或雙語。日語漏認或錯認會影響翻譯，即使其他位置仍能看到原片字幕。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Edit scripts and preview captions",
          "zh-HK": "修改台詞與預覽字幕"
        },
        "body": [
          {
            "en": "The translated script is what TTS speaks. A caption override changes displayed subtitle text for that line; leaving it empty follows the dubbing script. Subtitle start/end and speech start/end can be edited independently where shown. Keep speech inside its allotted window to avoid overlap, and audition after timing changes.",
            "zh-HK": "配音台詞是 TTS 實際朗讀內容；字幕覆寫只改顯示文字，留空便跟隨配音台詞。介面有提供時，可分別調整字幕與語音起訖。配音應留在本句時段內，避免重疊，修改時間後請試聽。"
          },
          {
            "en": "For study, select Cantonese + English together (learning). It adds one switchable subtitle track with Cantonese on the first line and English beneath it; both appear at once in a player. This also works with only one dubbed language. Separate Cantonese and English tracks remain independent choices. When selected, Cantonese is first and default, English is next, the learning track follows, and original subtitles are last.",
            "zh-HK": "學習時可選「廣東話＋英文同時顯示（學習用）」，加入一條可切換的雙行字幕：上行廣東話、下行英文，播放器會同時顯示。即使只選一種配音語言亦可使用。獨立廣東話及英文字幕仍可另選。已選字幕依次為廣東話（第一及預設）、英文、學習字幕，最後為原片字幕。"
          },
          {
            "en": "Output subtitles selects the tracks stored in a new movie. Preview captions selects the monitor’s current display. A media player must support switching subtitle and audio tracks to compare the exported languages.",
            "zh-HK": "輸出字幕決定新版影片內的字幕軌；預覽字幕只控制監看畫面。播放成品時，播放器須支援切換字幕與音軌才能比較語言。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "roles",
    "title": {
      "en": "Roles and source-voice references",
      "zh-HK": "角色與原聲參考"
    },
    "summary": {
      "en": "When role analysis is needed and how it affects time and voices.",
      "zh-HK": "了解角色分析用途及對耗時、聲線的影響。"
    },
    "sections": [
      {
        "title": {
          "en": "Independent references in Normal",
          "zh-HK": "一般模式的逐句參考"
        },
        "body": [
          {
            "en": "Normal mode gives each line its own original Japanese reference without identifying a shared person across scenes. It is intended to preserve local expression and avoid replacing every uncertain line with a generic role voice. Short or mixed-speaker source clips can still produce inconsistent voices.",
            "zh-HK": "一般模式逐句採用自己的日文原聲，不跨場景辨識同一人物，目的是保留本句情緒，避免將所有不確定句子都改成通用角色聲。原聲太短或混合多位說話者時，仍可能聲線不穩。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Full AI roles",
          "zh-HK": "完整 AI 角色"
        },
        "body": [
          {
            "en": "The Roles page displays available analysed profiles and reference recordings. Full AI review is required for the complete grouping workflow. Audio grouping compares voices; optional visual analysis also examines frames. Budget roughly three times Normal time, and potentially more for visual analysis. These are inferred groups, not verified identities.",
            "zh-HK": "角色頁顯示已分析的資料與參考錄音。完整分組流程需要完整 AI 模式；聲音分組會比較聲線，可選影像分析則再看畫格。時間可預留約一般模式三倍，影像分析可能更久。分組屬推斷，並非已認證人物身分。"
          },
          {
            "en": "Changing a role assignment in the dialogue inspector changes draft routing. It does not automatically rerecord all affected lines. Generate the desired retakes and export a new version after reviewing them.",
            "zh-HK": "在對白檢查器更改角色會改變草稿的配音分配，不會自動重錄所有相關句子。請生成所需重錄、覆聽後再匯出新版。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "review",
    "title": {
      "en": "Review report and audio problems",
      "zh-HK": "校對報告與配音問題"
    },
    "summary": {
      "en": "Interpret generation failures, warnings and retained takes.",
      "zh-HK": "解讀生成失敗、警告與保留錄音。"
    },
    "sections": [
      {
        "title": {
          "en": "Report filters and actions",
          "zh-HK": "篩選與操作"
        },
        "body": [
          {
            "en": "The report lists current line-level findings, automatic repair progress and available prior attempts. An empty report while processing is still running means checks are pending, not that all speech is complete. Edit/Retake target one line; retained takes remain available for comparison.",
            "zh-HK": "報告會列出目前逐句問題、自動修復進度同已有嘅過往嘗試。處理期間空白報告只代表核對未完成，唔代表全部對白完整。剪輯／重錄針對單句，保留錄音可作比較。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "What a failure means",
          "zh-HK": "失敗代表甚麼"
        },
        "body": [
          {
            "en": "Generation-limit means the speech decoder reached its generation budget without a normal ending; it does not mean that too many quality checks rejected a good recording. The result may be incomplete. Low level, silence, bad timing, language drift and uncertain recognition are separate issues. Read the specific reason and listen to the evidence.",
            "zh-HK": "generation-limit／解碼達上限代表語音解碼在正常結束前用盡生成預算，並不代表品質檢查拒絕太多正常錄音；結果可能缺少後半句。音量低、靜音、時段不符、語言偏移或辨識不確定是其他問題，應看具體原因並試聽證據。"
          },
          {
            "en": "A source reference with some background sound is not automatically unusable. A generated recording can inherit unwanted sounds or switch language despite having a correct script. A transcript checker can also mishear similar Cantonese syllables. Prefer evidence-based review over replacing an expressive take only because one recogniser disagrees.",
            "zh-HK": "參考聲有少量背景音不代表必定不能使用。即使台詞正確，生成錄音仍可能帶入雜聲或轉了語言；覆聽辨識亦可能聽錯相近粵語音節。應根據證據判斷，避免只因單一辨識結果不同便取代有表情的錄音。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "After a problem",
          "zh-HK": "發現問題後"
        },
        "body": [
          {
            "en": "Keep the project and recordings. Compare original and generated audio, shorten an overly long translated line while preserving meaning, and retake the affected line with a ready engine. Save and export a new version. For a repeated process error, export the full debug report rather than only copying a warning line.",
            "zh-HK": "先保留專案與錄音，比較原聲及生成聲音；如台詞過長，可在保留意思下精簡，再用已部署引擎重錄該句。儲存並匯出新版。如程序重複出錯，請匯出完整除錯報告，而非只複製一行警告。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Read the evidence before choosing a fallback",
          "zh-HK": "診斷資料與後備選擇"
        },
        "body": [
          {
            "en": "A useful line report identifies its source words, translated script, detected generated words, available time and measured recording length. It records which repair mechanisms were attempted and why they were accepted, rejected or still pending. Original mix and the completed separated dialogue use the same source timeline and identical start/end times; a short voice-conditioning reference is never substituted for the full separated track. Playback and live refresh preserve the item being read, scroll position and expanded evidence. Generated/retained recordings serve a separate comparison; an unavailable source is labelled instead of played as silence. During processing, awaiting recheck is not a final failure or a quality pass.",
            "zh-HK": "逐句報告需要列出原文、翻譯稿、生成錄音辨識結果、可用時段同實際錄音長度，並記錄試過乜修復、點解採用／拒絕，或者仍等待乜工序。原裝混音同完整分離對白使用同一時間軸、相同起止時間，唔會用聲線參考短片代替完整分離音軌。播放同背景更新會保留目前項目、捲動位置及展開證據。生成／保留錄音係另一份比較材料；缺少來源會明確標示，唔會用靜音假扮。處理期間「等待重新核對」唔係最終失敗，亦唔代表已通過品質檢查。"
          },
          {
            "en": "AI repair is the default. After pausing or finishing, optional choices can keep the original source voice with translated captions or explicitly accept a retained recording with reported defects. Listening never adopts a take. Saving an override does not certify its language or completeness; export a new version to apply it. Successful original recordings and earlier versions remain available.",
            "zh-HK": "預設由 AI 自動修復。暫停或完成後，先可選擇保留原裝聲音配翻譯字幕，或者明確接受有已知問題嘅保留錄音；試聽唔會採用錄音。保存選擇亦唔代表語言／完整性已通過認證，要匯出新版本先會套用；成功錄音同舊版本仍然保留。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "output",
    "title": {
      "en": "Exports, projects and removal",
      "zh-HK": "成品、專案與移除"
    },
    "summary": {
      "en": "Find completed movies and understand what Remove deletes.",
      "zh-HK": "尋找成品，了解移除範圍。"
    },
    "sections": [
      {
        "title": {
          "en": "Find your movie",
          "zh-HK": "尋找成品"
        },
        "body": [
          {
            "en": "After a successful export, Play output opens the finished movie in the preview and Show file reveals its location. Output folder controls new exports. Projects and exports keeps the episode, status, accumulated time and available output. Existing movie versions remain unless you explicitly remove them through a corresponding cleanup operation.",
            "zh-HK": "成功匯出後，「播放成品」會在預覽開啟完成影片，「顯示檔案」會顯示位置。「輸出資料夾」控制新成品存放位置。專案及輸出保留集數、狀態、累計時間及可用輸出；已有版本會保留，除非另行透過相關清理操作移除。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Remove a project",
          "zh-HK": "移除專案"
        },
        "body": [
          {
            "en": "Use the × in the video list or the trash button in Projects and exports. Confirm the project name before removal. Processing files for that project are cleared; source videos, completed exports and downloaded models are preserved. Pause running work first. Back to preview returns from management to the editor in either interface mode.",
            "zh-HK": "可按影片清單的 ×，或專案及輸出的垃圾桶；確認專案名稱後移除。這會清除該專案的處理資料，保留原片、完成成品及下載模型。正在執行的工作須先暫停。「返回預覽」可於兩種介面模式返回剪輯頁。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "A completed queue is not always a successful export",
          "zh-HK": "佇列結束不等於全部成功"
        },
        "body": [
          {
            "en": "A batch may finish while one episode Needs attention. Check each episode’s status and saved output, not just the overall percentage. An output marked for review is a saved movie with outstanding warnings; a processing failure without an output has no finished movie yet.",
            "zh-HK": "批量工作可能已結束，但其中一集仍需要處理。請查看各集狀態與成品，而非只看總百分比。「已輸出、待覆核」代表已有影片但仍有警告；程序失敗而沒有輸出則未有完整成品。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Find the destination, not working files",
          "zh-HK": "成品位置與工作檔案"
        },
        "body": [
          {
            "en": "Export destination is the chosen output folder, including a Google Drive folder if selected. Working files opens the app’s internal project directory; it is not the export destination. Play output/Show file refers to the actual versioned movie when one exists. Incomplete previews have Preview in their names and remain clearly labelled. Selecting another episode does not imply that the queue has exported it.",
            "zh-HK": "「成品輸出位置」係你選定嘅目標資料夾，包括已選嘅 Google Drive 資料夾；「工作檔案」則開啟 App 內部專案目錄，唔係成品位置。有實際輸出時，「播放成品／顯示檔案」會指向該版本影片；未完整預覽檔名有 Preview，介面亦會標示。選中另一條片唔代表清單已經輸出咗佢。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Clean cache with progress",
          "zh-HK": "清理暫存與進度"
        },
        "body": [
          {
            "en": "Projects and exports → Clear temporary files scans the app-owned storage directly, including old preview copies, package/compiled caches and unlinked interrupted work. A zero cache total means no removable items in the scanned categories, not that application storage is empty. Unlinked work can contain useful recordings; review that selection before deletion. Downloaded models, runtimes, original media and finished exports are preserved by cache cleanup. Scanning, deletion progress and the final freed-space result are shown. Nothing is removed during the scan.",
            "zh-HK": "「專案及輸出 → 清理暫存」會直接掃描 App 自己嘅儲存目錄，包括舊預覽副本、套件／編譯快取，同冇連結到清單嘅中斷工作。顯示 0 只代表掃描分類入面冇可移除項目，唔代表整個資料目錄係空。未連結工作可能仍有有用錄音，移除前應檢視選擇。清理暫存會保留已下載模型、執行環境、原片同成品，並顯示掃描、刪除進度同最後釋放容量；掃描時唔會刪嘢。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "terminal",
    "title": {
      "en": "Terminal, diagnostics and troubleshooting",
      "zh-HK": "終端機、診斷與故障排查"
    },
    "summary": {
      "en": "Choose log categories, search evidence and save a debug report.",
      "zh-HK": "選擇記錄分類、搜尋及儲存除錯報告。"
    },
    "sections": [
      {
        "title": {
          "en": "Log categories",
          "zh-HK": "記錄分類"
        },
        "body": [
          {
            "en": "Expert → Terminal offers Workflow summary, Process output, Model / setup output, Application process, MLX translation, Ollama translation and available job-specific logs. The same categories are shown on Mac and Windows. An unused service has no entries yet; for example, Windows uses native Ollama rather than Apple MLX.",
            "zh-HK": "專家模式 → 終端機提供流程摘要、程序詳細紀錄、模型／部署紀錄、應用程式紀錄、MLX 翻譯、Ollama 翻譯及已有的工作記錄。Mac 與 Windows 顯示相同分類；未使用的服務暫未有記錄，例如 Windows 使用原生 Ollama 而非 Apple MLX。"
          },
          {
            "en": "Search logs filters displayed lines. Errors only narrows the view to likely failures. Follow latest scrolls as entries arrive. Refresh reloads the selected source. Copy logs copies the selected log, while Export debug report includes bounded diagnostic evidence from multiple sources.",
            "zh-HK": "搜尋紀錄會篩選顯示行；「只看錯誤」縮窄到疑似錯誤，「跟隨最新」隨新行捲動，「重新整理」重讀目前來源。「複製紀錄」複製所選來源；「匯出除錯報告」會整合多個來源的有限診斷資料。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "File conversion details",
          "zh-HK": "檔案轉換資料"
        },
        "body": [
          {
            "en": "This log source records each file’s submitted model settings, application and computer versions, actual voice backend, generation sampling parameters, timing and missing dialogue reports. Earlier conversions may not contain all fields; unknown parameters are labelled rather than guessed. Export debug report includes this evidence for comparing results from different computers.",
            "zh-HK": "此紀錄來源會保存每條影片提交時嘅模型設定、程式及電腦版本、實際配音執行後端、生成參數、耗時及漏句資料。舊轉換可能缺少部分欄位；未知參數會明確標示，唔會推測。「匯出除錯報告」會包含呢啲資料，方便比較不同電腦嘅效果。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Send a useful failure report",
          "zh-HK": "提供有效故障資料"
        },
        "body": [
          {
            "en": "Choose Export debug report, select a save location in the system dialog and save the text file. Include the app version, operating system, GPU, production mode and where processing stopped when reporting a problem. The report includes local paths, settings relevant to processing and log excerpts; review it before sharing publicly.",
            "zh-HK": "按「匯出除錯報告」，於系統視窗選位置並儲存文字檔。報告問題時可一併提供版本、系統、顯示卡、製作模式及停止階段。報告會包括本機路徑、相關製作設定與記錄節錄，公開分享前請先檢視。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Common remedies",
          "zh-HK": "常見處理方法"
        },
        "body": [
          {
            "en": "Incomplete model: use Model centre → Repair download. Memory error: choose a smaller compatible model and avoid other GPU-heavy tasks. Silent or cut-off take: audition its history, revise the line if necessary and retake. Black or slow preview: leave preview off or retry after processing. Repeated process failure: preserve the project and export the report; repeatedly starting a new project discards useful reuse opportunities.",
            "zh-HK": "模型不完整：在模型中心修復下載。記憶體不足：改選較小兼容模型，並減少其他 GPU 工作。靜音或半句：聽歷史錄音、必要時修改台詞再重錄。黑畫面或預覽慢：可保持預覽關閉，或處理後重試。程序反覆失敗：保留專案並匯出報告；反覆建立新專案會失去可重用資料。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Numbered workflow entries and language",
          "zh-HK": "編號流程紀錄與語言"
        },
        "body": [
          {
            "en": "Workflow summary is a readable sequence such as 001, 002 and 003, with a timestamp, stage and message on each line. Current status (JSON) is a separate diagnostic view, not the default history. Language switching affects newly written workflow entries; earlier entries stay intact. yue is the language code for Cantonese, not an engine or an error.",
            "zh-HK": "「流程摘要」會以 001、002、003 等逐項顯示，每行有時間、工序同訊息。「目前狀態（JSON）」係另一個診斷檢視，唔係逐項歷史紀錄。切換語言後新寫嘅流程紀錄會跟新語言，舊紀錄會保留。yue 係廣東話嘅語言代碼，唔係引擎名或錯誤。"
          }
        ],
        "steps": false
      }
    ]
  },
  {
    "id": "preferences",
    "title": {
      "en": "Preferences, hardware and licences",
      "zh-HK": "偏好設定、硬件與授權"
    },
    "summary": {
      "en": "Understand platform differences and third-party component notices.",
      "zh-HK": "了解平台差異與第三方元件授權。"
    },
    "sections": [
      {
        "title": {
          "en": "Appearance and processing hardware",
          "zh-HK": "外觀與處理硬件"
        },
        "body": [
          {
            "en": "Preferences controls the appearance and available workspace options. Mac and Windows share the same interface and project workflow; their inference backends differ. Apple Silicon can use MLX, NVIDIA uses supported CUDA components, and other hardware uses available native backends or CPU fallbacks. A visible GPU does not guarantee every model supports it. Setup probes the selected backend before marking it ready.",
            "zh-HK": "偏好設定提供外觀及可用的工作區選項。Mac 與 Windows 共用介面與專案流程，但推論後端不同：Apple Silicon 可用 MLX，NVIDIA 可用支援的 CUDA 元件，其他硬件使用可用原生後端或 CPU 後備。看到顯示卡不代表每個模型都支援；部署會在標示就緒前檢查所選後端。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "About and licence notices",
          "zh-HK": "關於與授權"
        },
        "body": [
          {
            "en": "About & licences names SCKC as the developer and displays the MIT licence for AniCanto original code. Third-party libraries, bundled native components, downloaded runtimes and model weights retain their own licences. Search components to find a package, expand its row to read available notices and check the origin information.",
            "zh-HK": "關於與授權列明開發者 SCKC，以及 AniCanto 原創程式碼的 MIT 授權。第三方函式庫、原生元件、下載執行環境與模型權重仍受各自授權約束。搜尋元件可找套件，展開條目閱讀已有授權文字及來源。"
          },
          {
            "en": "AniCanto is a hobby project intended to share the fun of dubbing and Hong Kong Cantonese culture. The software licence does not grant rights to source anime, cloned voices or third-party model content.",
            "zh-HK": "AniCanto 是分享配音樂趣及香港廣東話文化的興趣作品。程式授權不代表取得來源動畫、模仿聲音或第三方模型內容的使用權利。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Memory and model handoff",
          "zh-HK": "記憶體與模型交接"
        },
        "body": [
          {
            "en": "Qwen translation/recovery and Drama 3 generation run in separate phases. Before starting a model child process, the app requests text-model unloading and checks the MLX acknowledgement or Ollama resident-model list. A failed or timed-out check stops the next model load and retains progress. Generation children release their own model on exit. Work is batched to reduce reloads. The largest single model plus runtime and system overhead must still fit; other applications can also consume memory.",
            "zh-HK": "Qwen 翻譯／修復判斷同 Drama 3 生成分階段執行。啟動模型子程序前，App 會要求卸載文字模型，檢查 MLX 回覆或 Ollama 常駐模型清單；檢查失敗或逾時會停止載入下一個模型，保留進度。生成子程序結束會釋放自己載入嘅模型，並以批次減少重新載入。單個最大模型連執行開銷同系統用量仍然要放得落；其他應用程式亦會佔用記憶體。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Download sources and publication status",
          "zh-HK": "下載來源與發佈狀態"
        },
        "body": [
          {
            "en": "About & licences groups selectable downloads by purpose; text translation offers Qwen 3.5 9B and 35B without presenting every historical quantization as a choice. Expand a model for its publisher, pinned revision, original download address and expected SHA-256. Some reviewed files are community conversions; not all downloads are original developer releases. The full third-party licence texts remain available separately even when a variant is disabled. A checksum checks file identity, not copyright permission.",
            "zh-HK": "「關於與授權」按用途分組顯示可選下載；文字翻譯只提供 Qwen 3.5 9B 同 35B，唔會將所有歷史量化版本都當作可選項。展開模型可睇發佈者、固定版本、原始下載地址同預期 SHA-256。部分已審核檔案係社群轉換，唔係所有下載都由原開發者發佈；停用版本嘅完整第三方授權原文亦會另外保留。校驗碼只核對檔案身份，唔係版權許可。"
          },
          {
            "en": "AniCanto original code uses MIT. Drama 3 and other models retain their own terms, including Fish Audio’s model conditions; on-demand downloading does not remove licence obligations. Before a public GitHub binary release, the exact enabled downloads, bundled notices, required matching source/build materials and final release artifacts must be checked together. A local test build or a successful conversion is not itself confirmation that public release has been cleared.",
            "zh-HK": "AniCanto 原創程式碼採用 MIT；Drama 3 同其他模型各有條款，包括 Fish Audio 嘅模型條件，按需要下載唔會免除授權責任。公開 GitHub 二進位版本之前，仍要一併核對實際啟用下載、內置授權通知、所需對應來源碼／建置資料同最終發佈檔案。本機測試版或者轉換成功，唔等於已確認可以公開發佈。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "When the original voice keeps producing the wrong language",
          "zh-HK": "原裝聲線持續讀錯語言時"
        },
        "body": [
          {
            "en": "A fitting original-voice take is kept. After original-voice rewriting, reference repair and bounded gentle tempo fitting are exhausted, automatic Normal mode may try the same selected engine with a bundled, licensed target-language reference. This can improve language reliability but changes the voice resemblance; the report says so. A fully adopted candidate must pass language/content checks and measured timing. An audible, fitting take with uncertain verification may be used only in a labelled incomplete preview, with the unresolved check retained. No extra engine or model download is started. Earlier recordings remain available. A reference fallback is not a claim that character identity or every pronunciation has been certified.",
            "zh-HK": "放得落嘅原角色錄音會保留。原聲線精簡、參考修復同微量調速都用盡仍失敗時，一般模式先可用同一個已選引擎，配合內置並有授權嘅目標語言參考再試。呢個方法可能改善語言，但聲線相似度會有變，報告會列明；正式採用嘅錄音須通過語言／完整性核對同實測時長；可聽、時長符合但核對未確定嘅錄音，只會用喺標明未完整嘅預覽，保留待核對狀態，唔會另外下載引擎或模型。舊錄音會保留，採用後備參考唔代表已認證角色身分或每個發音。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "An audible incomplete preview",
          "zh-HK": "保留聲音嘅未完整預覽"
        },
        "body": [
          {
            "en": "If all automatic attempts still leave a line without a safely timed translated take, Normal mode tries to retain that line’s original source speech in the labelled Preview output. Separated dialogue is preferred; if unusable, the original mix may be used and can include background sound. The report continues to mark the translated line incomplete, preserves the failed recordings and identifies source substitution. This avoids a silent gap without calling Japanese speech successful Cantonese. Source extraction can also fail; the report retains that failure rather than claiming every possible input can be repaired.",
            "zh-HK": "所有自動嘗試後，仍未有可安全放入時段嘅翻譯錄音時，一般模式會嘗試喺標明 Preview 嘅預覽中保留本句原聲，優先用分離對白；分離聲音不可用先試原片混音，可能包括背景聲。報告會繼續標示翻譯未完成，保留失敗錄音同列明原聲代替，避免靜音漏句，但唔會將日文當成成功廣東話。原聲擷取亦可能失敗，報告會保留問題，唔會聲稱所有輸入都一定修復到。"
          }
        ],
        "steps": false
      }
    ]
  }
];

CHAPTERS.push({"id": "speech-studio", "title": {"en": "Dubbing studio", "zh-HK": "配音器", "zh-CN": "配音器", "ja": "吹き替えスタジオ"}, "summary": {"en": "Create a Cantonese clip, keep versions and compare source and generated speech.", "zh-HK": "製作廣東話片段，保存不同錄音版本，再對照原聲同配音。", "zh-CN": "制作广东话片段，保存不同录音版本，再对照原声和配音。", "ja": "広東語の音声クリップを作成し、版を保存して元音声と比較します。"}, "sections": [{"title": {"en": "Input, review and translate", "zh-HK": "輸入、核稿及翻譯", "zh-CN": "输入、核稿及翻译", "ja": "入力・原稿確認・翻訳"}, "body": [{"en": "Open Dubbing studio from the video list in Basic mode or the navigation menu in Expert mode. No video import is needed. Type a source script, or record/import up to two minutes of audio. Recognise the recording first, correct names and missing words in the editable source, then translate. Choose an installed local text model and check the Cantonese script before generating. Recording recognition detects the source language automatically; model language coverage still applies.", "zh-HK": "基本模式由影片列表底部開「配音器」，專家模式由功能表進入；毋須匯入影片。可以打原稿，或者錄音／匯入最長兩分鐘聲音。先辨識錄音，喺原稿修正人名同漏字，再翻譯；揀已安裝嘅本機文字模型，核對廣東話稿後先生成。錄音會自動偵測語言，但仍受辨識模型支援範圍限制。", "zh-CN": "基本模式从影片列表底部打开「配音器」，专家模式从菜单进入；无需导入影片。可以输入原稿，或者录音／导入最长两分钟声音。先识别录音，在原稿修正人名和漏字，再翻译；选择已安装的本机文字模型，核对广东话稿后再生成。录音会自动检测语言，但仍受识别模型支持范围限制。", "ja": "基本モードでは動画一覧の下、エキスパートモードではメニューから開けます。動画の読み込みは不要です。文章を入力するか、最長2分の音声を録音・読み込みます。先に音声認識し、名前や抜けた語を原稿で修正してから翻訳してください。インストール済みのローカル翻訳モデルを選び、広東語原稿を確認して音声を生成します。録音の言語は自動判定しますが、認識モデルの対応範囲に依存します。"}], "steps": false}, {"title": {"en": "Generate, listen and review", "zh-HK": "生成、試聽及覆核", "zh-CN": "生成、试听及复核", "ja": "生成・試聴・確認"}, "body": [{"en": "Choose an installed voice engine, a reference voice and speech speed. In recording mode, using your own voice requires recognition to find a complete 3–10 second reference; otherwise choose a preset voice. Expand supported generation parameters when needed. Independent listening checks run after generation. Automatic repair makes at most two additional attempts per confirmed missing-audio, language or content problem. Uncertain spelling alone does not replace a take. Retained audio, attempts and review notes remain available. A flagged recording requires your explicit acceptance before saving; this does not certify its quality.", "zh-HK": "揀已安裝嘅配音引擎、參考聲線同語速，亦可展開支援嘅生成參數。錄音模式如要用自己聲線，需要先辨識並搵到完整 3–10 秒參考；否則請揀範本聲線。生成後會獨立覆聽；只有確認缺聲、語言或內容失敗，先會額外重試，逐段最多兩次。單純錯字疑點唔會自動換聲。錄音、嘗試同檢查說明會保留；有疑點嘅版本要由你明確接受後先保存，唔代表音質已認證。", "zh-CN": "选择已安装的配音引擎、参考声线和语速，也可展开支持的生成参数。录音模式如要用自己声线，需要先识别并找到完整 3–10 秒参考；否则请选择模板声线。生成后会独立复听；只有确认缺声、语言或内容失败，才会额外重试，每段最多两次。单纯错字疑点不会自动换声。录音、尝试和检查说明会保留；有疑点的版本需由你明确接受后再保存，不代表音质已认证。", "ja": "インストール済みの音声エンジン、参照音声、話速を選びます。対応する生成パラメーターも調整できます。録音した声の模倣には、認識で見つかった完全な3〜10秒の参照が必要です。参照がない場合はテンプレートを選んでください。生成後に独立した認識で確認し、無音・言語・内容の失敗が確認された部分だけ最大2回追加生成します。不確かな表記だけでは録音を置換しません。試行と確認結果は保持します。注意付きの録音は明示的に承認して保存できますが、品質認証にはなりません。"}], "steps": false}, {"title": {"en": "Saved recordings and learning", "zh-HK": "已保存錄音與學習", "zh-CN": "已保存录音与学习", "ja": "保存した録音と学習"}, "body": [{"en": "Save to the separate Dubbing studio player category. Each take retains its own scripts, reference, settings and output hash; generating another version does not overwrite it. Saved & learning lets you switch versions, choose the preferred take, reopen its settings for editing, rename the document, export a WAV or remove just one take. Source and generated audio, dual text, part playback, speed, volume and loop controls support comparison. Playback position is remembered separately for each audio file. Original and Cantonese speech do not share word timestamps. Changing the interface language changes the category label without moving or deleting recordings. Video projects and production settings remain separate.", "zh-HK": "保存後會放入獨立「配音器」播放器分類。每個版本保留自己嘅稿、參考、參數及音檔指紋，再生成唔會覆寫舊版。「已保存／學習」可切版本、揀採用版本、載入設定再修改、改名、匯出 WAV 或只刪一個版本。可對照整段原聲／廣東話、雙語文字，按配音段落試聽，調速度、音量及循環；每條音檔分開記住播放位置。兩種語言唔共用逐字時間。轉介面語言只會改分類顯示名，唔會搬移或刪錄音；影片專案同製作設定亦保持獨立。", "zh-CN": "保存后会放入独立「配音器」播放器分类。每个版本保留自己的稿、参考、参数和音档指纹，再生成不会覆盖旧版。「已保存／学习」可切换版本、选用版本、载入设置再修改、改名、导出 WAV 或只删除一个版本。可对照整段原声／广东话、双语文字，按配音段落试听，调速度、音量和循环；每个音档分别记住播放位置。两种语言不共用逐字时间。切换界面语言只会改变分类显示名，不会移动或删除录音；影片项目和制作设置亦保持独立。", "ja": "保存した録音は独立したスタジオ分類に表示されます。各版の原稿、参照、設定、音声ハッシュは保持され、新しい生成で上書きしません。「保存・学習」では版の切り替え、採用、設定の再編集、改名、WAV書き出し、特定の版だけの削除ができます。元音声と広東語、対訳、生成部分の再生、速度、音量、ループで比較できます。再生位置は音声ごとに記憶します。両言語の語単位タイムスタンプは共通ではありません。UI言語の変更では分類名のみ変わり、録音を移動・削除しません。動画プロジェクトや制作設定とは独立しています。"}], "steps": false}]});

export function chapters(language){const locale=localeData(language),lang=language==='zh-HK'?'zh-HK':'en';return CHAPTERS.map((c,i)=>({...c,number:i+1,title:c.title[language]??locale?.help[`${i}.title`]??c.title[lang],summary:c.summary[language]??locale?.help[`${i}.summary`]??c.summary[lang],sections:c.sections.map((s,j)=>({title:s.title[language]??locale?.help[`${i}.${j}.title`]??s.title[lang],body:s.body.map((p,k)=>p[language]??locale?.help[`${i}.${j}.${k}`]??p[lang]),steps:s.steps}))}));}
export function searchChapters(rows,query){const words=String(query).normalize('NFKC').toLocaleLowerCase().trim().split(/\s+/u).filter(Boolean);return rows.filter(c=>{const text=[c.title,c.summary,...c.sections.flatMap(s=>[s.title,...s.body])].join(' ').normalize('NFKC').toLocaleLowerCase();return words.every(w=>text.includes(w));});}
export function articleHTML(c){return `<div class="help-eyebrow">ANICANTO / ${String(c.number).padStart(2,'0')}</div><h1 id="help-article-title">${esc(c.title)}</h1><p class="help-lead">${esc(c.summary)}</p>${c.sections.map(s=>`<section class="help-section"><h2>${esc(s.title)}</h2>${s.steps?`<ol>${s.body.map(p=>`<li>${esc(p)}</li>`).join('')}</ol>`:s.body.map(p=>`<p>${esc(p)}</p>`).join('')}</section>`).join('')}`;}

CHAPTERS.find(c=>c.id==="subtitles").sections.push({"title": {"en": "Import, replace and remove a subtitle file", "zh-HK": "匯入、更換及移除字幕檔"}, "body": [{"en": "Select the intended video in the video queue. Open Subtitle source above the preview, then Import subtitle file. Supported formats are SRT, ASS, SSA and VTT. This pairs a subtitle file with a video; a subtitle-only audio project is not provided by this entry.", "zh-HK": "先喺影片清單揀啱影片，再開預覽上方「字幕來源」→「匯入字幕檔」。支援 SRT、ASS、SSA、VTT。呢個入口係為影片配對字幕，唔係純字幕轉音檔工具。"}, {"en": "The selected filename appears in Subtitle source and Production settings. Replace subtitle file changes the association for the selected video. Remove subtitle file restores automatic detection; it does not delete the original subtitle file. Keep the external file accessible until processing finishes.", "zh-HK": "「字幕來源」同製作設定會顯示檔名。「更換字幕檔」只更改所選影片嘅配對；「移除字幕檔」會恢復自動偵測，唔會刪除原檔。處理完成前請保留檔案喺可讀取位置。"}, {"en": "Import is locked for running and paused submissions because Resume must use the saved source choice. Pausing does not unlock it. Finish the current version before choosing another subtitle file for a new conversion. Existing movies and recordings are retained.", "zh-HK": "轉換中同已暫停提交會鎖定匯入，因為「繼續處理」必須沿用已保存嘅來源；按暫停唔會解鎖。完成目前版本後，先可以為新轉換更換字幕檔。舊影片同錄音會保留。"}, {"en": "Imported captions are reference evidence, not a promise to read every Chinese line verbatim. Original subtitle times are separate from translated dialogue and generated voice timing. Use the original-caption display to compare meaning; use the review report to check missing words, language and timing.", "zh-HK": "匯入字幕係參考證據，唔代表會逐字照讀每句中文字幕。原裝字幕時間、翻譯對白時間同配音時間係分開嘅；可用原裝字幕比對意思，再用校對報告檢查漏字、語言同時間問題。"}], "steps": false});

CHAPTERS.find(c=>c.id==="review").sections.push({"title": {"en": "Review notes and affected recordings", "zh-HK": "覆核狀態與受影響錄音"}, "body": [{"en": "Use the review status tabs and Issue type menu to focus on missing voice, wording/language, timing, reference or fallback notes. Checked by me and Review later are saved in the project and can be undone. They are human review states, not an automatic quality pass, and do not change the exported voice.", "zh-HK": "用覆核狀態分頁同「問題類型」選單集中處理缺聲、字句／語言、時間、參考或替代聲音。「我已覆核」同「稍後處理」會保存喺專案，亦可復原；佢哋係人手覆核狀態，唔代表自動品質通過，亦唔會改動成品聲音。"}, {"en": "Changed words, role references or diagnostic evidence reopen the note. Known saved recording provenance identifies affected lines for regeneration; earlier audio and videos remain available. Human-selected recordings are protected from bulk regeneration. Export a new video to apply changed audio choices. A quiet worker message is not proof that processing stopped; the progress area separates last notification from last measurable progress.", "zh-HK": "台詞、角色參考或診斷證據改變後會重新提示覆核。已有來源記錄嘅錄音會列出受影響句子供重生成，舊聲音同影片繼續保留；手動選用錄音受保護，唔會被批量重做。聲音選擇要匯出新影片先會套用。暫時冇新回報唔等於已停止，進度區會分開顯示上次程序回報同進度變動。"}], "steps": false});

CHAPTERS.find(c=>c.id==="start").sections.push({"title": {"en": "Three output languages", "zh-HK": "三種配音語言", "zh-CN": "三种配音语言", "ja": "3種類の出力言語"}, "body": [{"en": "Choose Hong Kong Cantonese, Mainland Mandarin or English in Production settings. Mandarin uses Mainland spoken wording and Simplified Chinese subtitles. You can select one language or a combination. The source audio stays separate when Keep original audio is selected. WenetSpeech-Yue supports Cantonese only; use another installed engine for Mandarin or English.", "zh-HK": "喺製作設定揀香港廣東話、中國大陸普通話或英文，可以單選或組合。普通話使用大陸口語用字同簡體中文字幕；勾選保留原聲時，原片聲音會獨立保存。WenetSpeech-Yue 只支援廣東話，普通話或英文請揀其他已安裝引擎。", "zh-CN": "在制作设置中选择香港广东话、中国大陆普通话或英文，可以单选或组合。普通话使用大陆口语和简体中文字幕。勾选保留原声时，原片声音会独立保存。WenetSpeech-Yue 仅支持广东话；普通话或英文请选择其他已安装引擎。", "ja": "制作設定で香港広東語・中国大陸の標準中国語・英語を選びます。単独または組み合わせて出力できます。標準中国語には中国大陸の口語表現と簡体字字幕を使います。元音声を残す場合は独立した音声トラックになります。WenetSpeech-Yueは広東語のみ対応します。"}, {"en": "In Expert mode, select a line and switch HK / 普 / EN in the Dialogue inspector. Each language keeps its own script and saved recordings. Regenerating one line does not require exporting the whole movie. To apply changed recordings to a finished movie, export a new version from Production/export. The red Pause & save button only pauses and saves work.", "zh-HK": "專家模式揀一句對白，再喺對白檢查器切換 HK／普／EN；每種語言分開保存稿件同錄音。重生一句可以直接試聽，毋須重包成條片。要將新錄音套用到成品，去製作匯出建立新版本；紅色「暫停保存」只負責暫停同保存工作。", "zh-CN": "专家模式选择一句对白，在对白检查器切换 HK／普／EN；每种语言分别保存稿件与录音。重生成单句可直接试听，无须重新导出整部影片。应用到成品时，请在制作导出中新建版本。红色暂停保存按钮只暂停并保存工作。", "ja": "エキスパートモードで台詞を選び、台詞インスペクターのHK／普／ENを切り替えます。原稿と録音は言語別に保存され、1行の再生成後すぐ試聴できます。完成動画に適用するには制作・書き出しから新しい版を書き出します。赤い一時停止・保存ボタンは作業を保存して停止する操作です。"}], "steps": false});

CHAPTERS.find(c=>c.id==="subtitles").sections.push({"title": {"en": "OCR context and source timing", "zh-HK": "畫面字幕參考同原聲時間", "zh-CN": "画面字幕参考和原声时间", "ja": "OCR字幕の参照と元音声のタイミング"}, "body": [{"en": "Without a usable text subtitle track, AniCanto recognises source speech and samples lower-screen captions as translation evidence. Centred subtitle-sized text is preferred over text in the scene. OCR confidence stays attached to the evidence. Caption text never sets the audio clock. An unusually stretched ASR word spanning separate spoken turns gets one bounded local re-listen; confirmed turns are separated using audio timestamps. Unconfirmed turns retain source audio and a review note.", "zh-HK": "冇可用文字字幕軌時，AniCanto 會辨識原聲，再抽樣畫面下方字幕作翻譯參考。會優先選置中、字幕字體大小嘅文字，保留 OCR 信心資料，避免背景文字混入。配音時間仍跟聲音；如果辨識器將一個字異常拉長、跨過幾段說話，會有限度局部重聽，按真實聲音時間分句。未確認嘅段落保留原聲並列覆核提示。", "zh-CN": "没有可用文字字幕轨时，AniCanto 先识别原声，再抽样画面下方字幕作为翻译参考。优先选择居中且符合字幕字号的文字，保留 OCR 置信度，避免场景文字混入。配音时间仍依据声音；识别器将单字异常拉长并跨越多段说话时，会有限度地局部重听，按声音时间分句。未确认的段落保留原声并提示复核。", "ja": "利用可能なテキスト字幕がない場合、元音声を認識し、画面下部の字幕を翻訳の補助資料として読み取ります。中央寄りの字幕サイズの文字を優先し、OCRの信頼度も保持します。音声の時刻を字幕から作りません。1語が複数の発話にまたがって異常に長い場合のみ、回数を制限した局所再認識を行います。未確認の区間は元音声と確認メモを残します。"}, {"en": "These checks cannot certify every OCR word or pronunciation. An already exported movie keeps its previous source analysis. If its source timing was wrong, start a new conversion with the corrected app; regenerating voices alone retains the old line boundaries. Original subtitle tracks continue to use their original times.", "zh-HK": "呢啲檢查唔代表每個 OCR 字或發音都已認證。已輸出影片仍沿用舊分析；原聲分句時間錯咗，要用修正版重新轉換，淨係重生聲音會沿用舊界線。原裝字幕軌繼續跟原來時間播放。", "zh-CN": "这些检查不代表每个 OCR 字或发音都已认证。已导出影片仍沿用旧分析；如果原声分句时间有误，请用修正版重新转换，仅重生成声音仍沿用旧边界。原装字幕轨继续使用原有时间。", "ja": "OCRの全単語や発音を保証するものではありません。既存の書き出しには以前の解析が残ります。元音声の分割時刻が誤っていた場合は修正版で新規変換してください。音声だけの再生成では元の区間境界が使われます。元字幕は元の時刻で表示されます。"}], "steps": false});
