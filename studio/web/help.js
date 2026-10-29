import {WORKFLOW_GUIDE} from './workflow-guide.js';
import {parameterCopy} from './voice-parameters.js';
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
            "en": "Welcome detects memory and the available processing backend. Full Drama 3 starts at 32 GB system/unified memory: on a 32 GB Apple Silicon Mac, the 28 GB model exceeds the 24 GB budget after reserving 8 GB for macOS, so loading may use swap, become very slow or fail. The 32 GB preset pairs it with Qwen 9B; 64 GB remains the tested best-quality recommendation for Drama 3 + Qwen 35B. On Windows, full Drama 3 Q2 offers a verified NVIDIA CUDA runtime with CPU expert offload according to the deployed VRAM profile, or CPU processing. AMD/Intel cannot use this NVIDIA runtime. It still needs about 22 GB system RAM; dedicated VRAM is shown separately. Available GPU memory can be lower when other apps are running. The download list shows each model's memory pool and size before setup. You may download an over-budget model and explicitly try to load it with a warning; the current working model stays active if verification fails. Mac and Windows offer Qwen 9B and 35B; 4B downloads are no longer offered. Only versions with reviewed licence evidence are selectable. Hardware details is collapsed by default. Models & storage groups missing downloads, installed models and cleanup; runtime cleanup stays inside its own section. Removal shows real file progress and a result, then refreshes setup without restarting on Mac. Windows runtime removal closes the app first so loaded files can be released. Memory figures remain estimates until setup tests the actual runtime. Intel Macs are not supported.",
            "zh-HK": "Welcome 會偵測記憶體同可用執行方式。完整 Drama 3 由 32 GB 系統／統一記憶體起可嘗試：32 GB Apple Silicon Mac 扣除畀 macOS 嘅 8 GB 預留後，模型預算只得 24 GB，但 Drama 3 預估用 28 GB；可能使用交換空間、嚴重變慢或載入失敗。32 GB 組合配 Qwen 9B；實測廣東話效果最佳嘅 Drama 3 + Qwen 35B 仍建議 Apple Silicon 64 GB。Windows 完整 Drama 3 Q2 可用已驗證嘅 NVIDIA CUDA 執行環境，按部署時 VRAM 配置將部分專家層放喺 CPU，亦可用 CPU 版；AMD／Intel 唔可以用 NVIDIA 執行環境。仍預估需要約 22 GB 系統 RAM，VRAM 分開顯示；其他 App 會減少可用顯示記憶體。下載前清單會列出每個模型嘅記憶體類型、估算同下載量。超出建議預算嘅模型仍可下載及明確選擇試載入；系統會警告，驗證失敗會保留原本可用模型。Mac 同 Windows 提供 Qwen 9B 同 35B；4B 唔再供新下載。可選版本均有授權核對資料。硬件詳情預設收起；模型與儲存空間集中顯示待下載、已下載同清理操作。清理會顯示進度，Windows 移除執行環境前要先關閉 App。記憶體數字係估算，部署會測試實際載入；唔支援 Intel Mac。"
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
      },
      {
        "title": {
          "en": "Same recovery rules on Mac and Windows",
          "zh-HK": "Mac 與 Windows 共用修復規則",
          "zh-CN": "Mac 与 Windows 共用修复规则",
          "ja": "Mac と Windows の共通修復ルール"
        },
        "steps": false,
        "body": [
          {
            "en": "Both desktop versions share the same first-audible retention, missing/damaged repair, bounded overlong-line shortening, retry budgets and checkpoint rules. Normal and High speed both preserve confidently identified isolated laughter, crying and breaths. Classifiers retain their validated context: Mac uses one-second windows and Windows AudioSet uses five seconds. A short-window Windows trial was rejected after confidence fell; OP/ED analysis stays separate. Evidence is cached across voice and language tracks. Restoring performance keeps the selected engine’s delivery sample rate instead of forcing 24 kHz. Classifier and inference models still differ by platform, so identical detection or generated voices are not guaranteed. Do not mix back the whole Japanese vocal stem to recover one laugh.",
            "zh-HK": "兩個桌面版共用保留首輪有聲錄音、補無聲／損壞、局部改短超時對白、重試上限同進度保存規則。一般及高速模式都會保留有把握、可獨立抽取嘅笑聲、哭聲及呼吸。分類保留各模型已驗證上下文：Mac 用一秒，Windows AudioSet 用五秒；Windows 直接改一秒嘅試驗信心下降，未採用。OP／ED 分析分開。分類證據可喺不同引擎及語言音軌之間沿用；補聲沿用引擎交付取樣率，唔再強制降成24 kHz。分類及推理模型仍有平台差異，唔保證辨識結果或聲線完全一樣；唔會為咗補笑聲而混返整條日文人聲。",
            "zh-CN": "两个桌面版共用保留首轮有声录音、补无声／损坏、局部缩短超时对白、重试上限和进度保存规则。一般及高速模式都会保留有把握、可独立提取的笑声、哭声和呼吸。分类保留各模型已验证的上下文：Mac 用一秒，Windows AudioSet 用五秒；Windows 直接改一秒的试验置信度下降，未采用。OP／ED 独立处理。分类证据在不同引擎和语言音轨间复用；补声沿用引擎交付采样率，不再强制降为24 kHz。分类和推理模型仍有平台差异，不保证识别结果或声线完全一致；不会为了补笑声混回整条日语人声。",
            "ja": "両デスクトップ版は、最初の有声音声の保持、欠損・破損補完、実測で長すぎる台詞の局所短縮、再試行上限と保存を共通化しています。標準・高速とも、確実に独立抽出できる笑い・泣き声・呼吸を保持。分類器に適した文脈を維持し、Macは1秒、Windows AudioSetは5秒を使用します。Windowsを直接1秒にした試験は信頼度が低下したため採用していません。OP／EDは別処理です。分類結果を音声エンジンと言語トラック間で再利用し、補完時もエンジンの出力サンプリング周波数を維持します。24 kHz に固定しません。分類・推論モデルは環境により異なるため、判定や生成音声の完全一致は保証しません。笑いを戻すために日本語の声全体を混ぜ戻すことはしません。"
          }
        ]
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
            "en": "The theme dots in Welcome change the accent colour, cover and assistant. While the app prepares local projects at launch, the selected assistant animates beside the progress indicator and you can choose Basic or Expert mode. The preview-off scene uses that theme’s assistant. The ensemble theme brings the assistants together. The app opens using your saved light, dark or system appearance. System appearance also follows changes while the app is open; reduced-motion system settings reduce decorative animation.",
            "zh-HK": "Welcome 的色點會切換主題色、封面與助手。啟動時，本機專案準備進度旁會顯示所選助手動畫；期間仍可揀基本或專家模式。關閉預覽時會顯示同一主題助手；同樂會主題會集合多位助手。啟動時會直接套用偏好設定嘅淺色、深色或跟隨系統；選擇跟隨系統後，開住 App 期間亦會隨系統切換；系統的減少動態效果設定會減少裝飾動畫。"
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
    "en": "Production controls",
    "zh-HK": "製作控制",
    "zh-CN": "制作控制",
    "ja": "制作設定"
  },
  "summary": {
    "en": "One standard pipeline with independent review, repair and duration controls.",
    "zh-HK": "同一個標準流程，覆核、修復同時長限制分開控制。",
    "zh-CN": "同一个标准流程，复核、修复和时长限制分别控制。",
    "ja": "標準処理で検査・修復・時間制限を個別に設定します。"
  },
  "sections": [
    {
      "title": {
        "en": "Standard conversion",
        "zh-HK": "標準轉換",
        "zh-CN": "标准转换",
        "ja": "標準変換"
      },
      "body": [
        {
          "en": "New desktop jobs record each line once. Missing or damaged audio can be recorded up to two extra times. These checks do not certify pronunciation. Paused jobs keep their saved policy.",
          "zh-HK": "新桌面工作每句先生成一次；無聲或損壞錄音最多額外補錄兩次，唔代表讀音已認證。已暫停工作保留原設定。",
          "zh-CN": "新桌面任务每句先生成一次；无声或损坏录音最多额外补录两次，不代表读音已认证。已暂停任务保留原设置。",
          "ja": "新しいデスクトップ処理では各台詞を1回生成します。無音・破損時は最大2回追加生成します。発音の保証ではありません。一時停止中の処理は保存済み設定を保持します。"
        }
      ],
      "steps": false
    },
    {
      "title": {
        "en": "Independent AI switches",
        "zh-HK": "獨立 AI 開關",
        "zh-CN": "独立 AI 开关",
        "ja": "個別のAI設定"
      },
      "body": [
        {
          "en": "Full AI review adds visual role analysis and ASR checks when the required models exist. With AI auto repair off, content and voice checks retain findings without a retake. AI auto repair enables bounded retries and the selected fallback options. Full review can take much longer.",
          "zh-HK": "完整 AI 覆核會在所需模型可用時加入角色畫面分析及語音覆聽。關閉 AI 自動修復時，內容及聲線檢查只保留結果，唔重錄。AI 自動修復會啟用有限重試及所選後備方法。完整覆核可能明顯增加時間。",
          "zh-CN": "完整 AI 复核会在所需模型可用时加入角色画面分析及语音复听。关闭 AI 自动修复时，内容及声线检查只保留结果，不重录。AI 自动修复会启用有限重试及所选后备方法。完整复核可能明显增加时间。",
          "ja": "完全AI検査は必要なモデルがある場合に画像による人物解析と音声検査を追加します。自動修復がオフの場合、内容・声質の検査結果だけ記録し、再生成しません。自動修復は回数制限付き再試行と選択した代替音声を有効にします。完全検査には時間がかかる場合があります。"
        }
      ],
      "steps": false
    },
    {
      "title": {
        "en": "Speech duration and overlap",
        "zh-HK": "配音時長及重疊",
        "zh-CN": "配音时长及重叠",
        "ja": "吹替時間と重複"
      },
      "body": [
        {
          "en": "Limit dubbing to original speech duration is off by default. Each recording starts at its source speech time and plays at natural speed. A long take can overlap the next generated line. Protected opening/ending ranges, manual source keeps and the video end remain limits.",
          "zh-HK": "「限制配音至原聲時長」預設關閉。配音按原聲起點，以自然速度播放；較長錄音可同下一句配音重疊。片頭片尾保護區、手動保留原聲區間及影片結尾仍受保護。",
          "zh-CN": "“限制配音至原声时长”默认关闭。配音按原声起点，以自然速度播放；较长录音可与下一句配音重叠。片头片尾保护区、手动保留原声区间及影片结尾仍受保护。",
          "ja": "時間制限は既定でオフです。原音の開始時刻から自然な速度で再生し、長い音声は次の吹替と重複できます。保護されたOP/ED、原音保持区間、動画の終端は越えません。"
        },
        {
          "en": "When enabled, measure the actual recording first. Remove only exact digital silence at the edges, with 80 ms padding. Retain internal pauses and quiet sounds. Only a measured overrun permits one meaning-preserving rewrite and retake with the same reference. Retain the first take if the new take does not fit. Record unresolved delivery in the report and continue export. Original embedded, external and OCR subtitle evidence stays unchanged.",
          "zh-HK": "開啟後先量度實際錄音，只移除首尾完全數碼靜音，保留 80 毫秒緩衝、句中停頓及微弱聲音。只有實測超時先容許按相同參考、保留意思縮稿重配一次。新錄音仍唔合適就保留首輪錄音供比較；未解決交付記入報告並繼續輸出。原裝內置、外掛及 OCR 字幕證據不變。",
          "zh-CN": "开启后先测量实际录音，只移除首尾完全数字静音，保留 80 毫秒缓冲、句中停顿及微弱声音。只有实测超时才允许按相同参考、保留意思缩稿重配一次。新录音仍不合适则保留首轮录音供比较；未解决的交付记入报告并继续输出。原始内置、外挂及 OCR 字幕证据不变。",
          "ja": "オンの場合は実際の録音を先に測定します。前後の完全なデジタル無音だけを除き、80msの余白、文中の間、弱い音を残します。実測で超過した台詞だけ、意味と同じ参照音声を保って1回短縮・再生成します。収まらない候補は採用せず、初回音声を比較用に保持します。未解決の箇所を記録して出力を続けます。元の内蔵・外部・OCR字幕は変更しません。"
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

const samplingLocales=['en','zh-HK','zh-CN','ja'];
const samplingText=key=>Object.fromEntries(samplingLocales.map(language=>[language,parameterCopy(language)[key]]));
CHAPTERS.push({id:'voice-sampling',title:samplingText('title'),summary:samplingText('newDefaults'),sections:[{title:{en:'Temperature',"zh-HK":'隨機度',"zh-CN":'随机度',ja:'Temperature'},body:[samplingText('temperature')],steps:false},{title:{en:'Top P',"zh-HK":'Top P',"zh-CN":'Top P',ja:'Top P'},body:[samplingText('topP')],steps:false},{title:{en:'Top K',"zh-HK":'Top K',"zh-CN":'Top K',ja:'Top K'},body:[samplingText('topK')],steps:false},{title:{en:'Defaults and saving',"zh-HK":'預設及儲存',"zh-CN":'默认及保存',ja:'既定値と保存'},body:[samplingText('newDefaults'),samplingText('common'),samplingText('autosave')],steps:false}]});

CHAPTERS.push({"id": "workflow70", "title": {"en": "Updating audio and source performances", "zh-HK": "更新配音與原聲表演", "zh-CN": "更新配音与原声表演", "ja": "音声更新と原音の演技"}, "summary": {"en": "Use Produce → Update dubbing to regenerate one line or all voices, add/replace a language and engine track, merge saved recordings, or run a new analysis. Every export keeps the previous version. Adding or replacing a track retains the other finished tracks; those recordings are not regenerated.", "zh-HK": "由「製作匯出 → 更新配音」可重生一句或全部配音、增加／替換指定語言及引擎音軌、合併已保存錄音，或者重新分析。每次匯出保留舊版本；增加或替換音軌時，其他已完成音軌唔會重新生成。", "zh-CN": "通过「制作导出 → 更新配音」可以重新生成一句或全部配音、添加／替换指定语言和引擎音轨、合并已保存录音或重新分析。每次导出保留旧版本；添加或替换音轨时，其他已完成音轨不重新生成。", "ja": "「制作・書き出し → 吹き替えを更新」で一行／全音声の再生成、言語・エンジントラックの追加・置換、保存済み録音の合成、再分析を選べます。旧版は保持します。追加・置換時に他の完成済みトラックは再生成しません。"}, "sections": [{"title": {"en": "Updating audio and source performances", "zh-HK": "更新配音與原聲表演", "zh-CN": "更新配音与原声表演", "ja": "音声更新と原音の演技"}, "body": [{"en": "Use Produce → Update dubbing to regenerate one line or all voices, add/replace a language and engine track, merge saved recordings, or run a new analysis. Every export keeps the previous version. Adding or replacing a track retains the other finished tracks; those recordings are not regenerated.", "zh-HK": "由「製作匯出 → 更新配音」可重生一句或全部配音、增加／替換指定語言及引擎音軌、合併已保存錄音，或者重新分析。每次匯出保留舊版本；增加或替換音軌時，其他已完成音軌唔會重新生成。", "zh-CN": "通过「制作导出 → 更新配音」可以重新生成一句或全部配音、添加／替换指定语言和引擎音轨、合并已保存录音或重新分析。每次导出保留旧版本；添加或替换音轨时，其他已完成音轨不重新生成。", "ja": "「制作・書き出し → 吹き替えを更新」で一行／全音声の再生成、言語・エンジントラックの追加・置換、保存済み録音の合成、再分析を選べます。旧版は保持します。追加・置換時に他の完成済みトラックは再生成しません。"}, {"en": "Source language is checked from the selected audio track, separately from subtitle language. Confirm any conflict. Project names and techniques live under Subtitle source and Produce. Lock translations explicitly; keeping source voice preserves the whole matching line. External subtitles are copied with a SHA-256 receipt for resume.", "zh-HK": "原聲語言會按所選音軌核對，同字幕語言分開；有衝突時請確認。人名及招式由「字幕來源」或「製作匯出」管理，可鎖定譯名；保留原聲會保留整句。外掛字幕會複製並保存 SHA-256 記錄，續做使用同一份內容。", "zh-CN": "原声语言按所选音轨核对，与字幕语言分开；有冲突时请确认。人名与招式由「字幕来源」或「制作导出」管理，可锁定译名；保留原声将保留整句。外挂字幕会复制并保存 SHA-256 记录，继续处理时使用同一份内容。", "ja": "原音の言語は選択音声から確認し、字幕言語とは別に扱います。不一致は手動確認してください。名前・技名は字幕ソースと書き出し画面で固定できます。原音保持は台詞全体です。外部字幕はコピーと SHA-256 記録を保存して再開します。"}, {"en": "Laughter, crying, screams and breaths use shared acoustic rules for every film. Tail checks compare original and separated audio, bounded to 16 candidate regions and cached. Recognised source words stay excluded: a spoken cry for help is translated speech. Uncertain sounds appear separately in Review, where you can audition both sources and explicitly keep a source interval. Apple’s classifier has no separate moan/groan category; this is not a promise to detect every performance.", "zh-HK": "笑、喊、叫聲及呼吸用所有影片共用嘅聲音規則；最多局部核對 16 段候選尾音，比較原聲同分離聲並保存結果。已辨識字句仍會排除，叫「救命」等實際對白要翻譯。未確認聲音另列校對報告，可試聽後明確選擇保留原聲時段。Apple 分類器冇獨立呻吟類別，唔保證每段表演都偵測到。", "zh-CN": "笑、哭、叫声和呼吸使用所有影片共用的声学规则；最多局部核对 16 段候选尾音，比较原声和分离声并保存结果。已识别字句仍会排除，喊「救命」等实际对白需要翻译。不确定声音单列校对报告，可以试听并明确选择保留原声区间。Apple 分类器没有独立呻吟类别，不保证检测到每段表演。", "ja": "笑い・泣き声・叫び・呼吸は全動画共通の音響規則を使います。最大16の候補区間で原音と分離音を比較し結果を保存します。認識済みの単語は除外し、「助けて」などの台詞は翻訳します。不確かな音は確認レポートで試聴し、原音保持を明示的に選択できます。Appleの分類器には独立したうめき声の分類がなく、全ての演技を検出する保証はありません。"}, {"en": "The first audible take is kept unless measured too long; genuinely missing speech can be retried. An identical text, reference and parameter input has at most three automatic submissions including its first generation. Deterministic input errors require changed inputs. Review shows counts and evidence; uncertain language/content alone does not discard the first audible take. Preview adds ±10 seconds, audio selection, volume, full screen and hover thumbnails. Overall progress may include saved work.", "zh-HK": "保留首輪有聲錄音，實測超長先局部精簡；真正缺聲先補。相同台詞、參考及參數最多自動提交三次，已包括首次生成；確定係輸入錯誤就要改輸入先重試。報告顯示次數及證據，唔會只因語言／漏字疑點丟棄首輪錄音。預覽支援前後 10 秒、音軌、音量、全螢幕及滑鼠時間縮圖；整體進度可能包括已保存工作。", "zh-CN": "保留首轮有声录音，实测超长才局部精简；真正缺声才补录。相同台词、参考与参数最多自动提交三次，包括首次生成；确定的输入错误需要更改输入后重试。报告显示次数与证据，不会仅因语言／漏字疑点丢弃首轮录音。预览支持前后 10 秒、音轨、音量、全屏和悬停缩略图；整体进度可能包括已保存工作。", "ja": "最初の有音テイクを保持し、実測で長すぎる場合に短縮します。欠落音声のみ再生成し、同じ台本・参照・設定の自動提出は初回を含め最大3回です。確定した入力エラーは入力変更が必要です。レポートに回数と証拠を表示します。プレビューは前後10秒、音声選択、音量、全画面、ホバーサムネイルに対応します。全体進捗には保存済み作業を含む場合があります。"}], "steps": false}]});

CHAPTERS.find(c=>c.id==='start').sections[1].body[0]['zh-CN']='部署会检测内存和受支持的运行环境。完整 Drama 3 建议 Apple Silicon 64 GB；32 GB 可能需要交换空间。Windows 完整 Q2 可使用已验证的 NVIDIA CUDA 与 CPU 专家层分配，或 CPU；仍预估需要约 22 GB 系统内存。AMD／Intel 不使用 NVIDIA 运行环境。独显 VRAM 与系统内存分开计算，集显共享内存不重复计算。实际可用容量受其他程序影响；部署测试模型载入，超出预算仍可能失败。模型清理保留用户项目、录音和源影片；Windows 清理运行环境前先关闭 App。不支持 Intel Mac。';
CHAPTERS.find(c=>c.id==='start').sections[1].body[0]['ja']='セットアップはメモリと対応ランタイムを検出します。完全版 Drama 3 は Apple Silicon 64 GB を推奨し、32 GB ではスワップが発生する場合があります。Windows Q2 は検証済み NVIDIA CUDA と CPU への expert 配置、または CPU を使用し、約22 GB のシステム RAM が必要です。AMD／Intel は NVIDIA 用ランタイムを使いません。専用 VRAM と RAM は別に計算し、内蔵 GPU の共有メモリは二重計上しません。他のアプリで空き容量は減少します。導入時にモデルを検証しますが、予算超過時は失敗する場合があります。削除はユーザーの動画・録音・プロジェクトを保持します。Intel Mac は非対応です。';

CHAPTERS.push({"id": "hardware71", "title": {"en": "Hardware acceleration", "zh-HK": "硬件加速", "zh-CN": "硬件加速", "ja": "ハードウェアアクセラレーション"}, "summary": {"en": "Preferences → Checking and repair keeps source speech processing on Automatic hardware acceleration by default. Apple Silicon uses the installed, verified MLX large-v3 model for source recognition, source-language sampling and independent listening. Large-v3 one-click setup includes the extra 3.1 GB model. Choose CPU compatibility to retain the previous beam-search decoder; MLX uses greedy decoding, so names and other words can differ. Existing saved project timing is not automatically regenerated.", "zh-HK": "偏好設定 → 檢查與修復嘅原聲辨識預設用自動硬件加速。Apple Silicon 會用已安裝並校驗嘅 MLX large-v3，處理原聲、來源語言取樣同獨立覆聽；large-v3 一按部署包括額外約 3.1 GB 模型。可選 CPU 相容模式，沿用舊有 beam search；MLX 用 greedy 解碼，人名等文字可能有差異。已保存專案唔會自動重新分句或改時間。", "zh-CN": "偏好设置 → 检查与修复默认自动加速原声识别。Apple Silicon 使用已安装并校验的 MLX large-v3 处理原声、语言采样和独立复听；large-v3 一键部署包括额外约 3.1 GB 模型。CPU 兼容模式保留原 beam search；MLX 使用 greedy 解码，人名等文字可能不同。不会自动重排已保存项目的分句或时间。", "ja": "環境設定の確認・修復で元音声処理は自動が既定です。Apple Silicon は導入・検証済み MLX large-v3 を原音認識・言語サンプル・独立確認に使います。large-v3 の一括導入には追加約3.1 GBを含みます。CPU互換モードは従来の beam search、MLX は greedy デコードのため固有名詞などが異なる場合があります。保存済み区間と時刻は自動変更しません。"}, "sections": [{"title": {"en": "Hardware acceleration", "zh-HK": "硬件加速", "zh-CN": "硬件加速", "ja": "ハードウェアアクセラレーション"}, "body": [{"en": "Preferences → Checking and repair keeps source speech processing on Automatic hardware acceleration by default. Apple Silicon uses the installed, verified MLX large-v3 model for source recognition, source-language sampling and independent listening. Large-v3 one-click setup includes the extra 3.1 GB model. Choose CPU compatibility to retain the previous beam-search decoder; MLX uses greedy decoding, so names and other words can differ. Existing saved project timing is not automatically regenerated.", "zh-HK": "偏好設定 → 檢查與修復嘅原聲辨識預設用自動硬件加速。Apple Silicon 會用已安裝並校驗嘅 MLX large-v3，處理原聲、來源語言取樣同獨立覆聽；large-v3 一按部署包括額外約 3.1 GB 模型。可選 CPU 相容模式，沿用舊有 beam search；MLX 用 greedy 解碼，人名等文字可能有差異。已保存專案唔會自動重新分句或改時間。", "zh-CN": "偏好设置 → 检查与修复默认自动加速原声识别。Apple Silicon 使用已安装并校验的 MLX large-v3 处理原声、语言采样和独立复听；large-v3 一键部署包括额外约 3.1 GB 模型。CPU 兼容模式保留原 beam search；MLX 使用 greedy 解码，人名等文字可能不同。不会自动重排已保存项目的分句或时间。", "ja": "環境設定の確認・修復で元音声処理は自動が既定です。Apple Silicon は導入・検証済み MLX large-v3 を原音認識・言語サンプル・独立確認に使います。large-v3 の一括導入には追加約3.1 GBを含みます。CPU互換モードは従来の beam search、MLX は greedy デコードのため固有名詞などが異なる場合があります。保存済み区間と時刻は自動変更しません。"}, {"en": "Drama 3, Qwen text/vision/ASR and supported GPT components retain their MLX or MPS paths on Mac. Some modules remain CPU: the current CosyVoice/WenetSpeech adapters and a WeSpeaker/CoreML combination that produced invalid values in testing. Apple framework placement is system managed. A requested provider alone is not evidence that every operation ran on GPU.", "zh-HK": "Mac 嘅 Drama 3、Qwen 文字／影像／語音同支援嘅 GPT 組件保留 MLX／MPS 加速。部分項目仍用 CPU：目前 CosyVoice／WenetSpeech 適配器，以及實測產生無效數值嘅 WeSpeaker／CoreML 組合。Apple 系統服務由系統分配硬件；指定 provider 唔代表全部運算都喺 GPU。", "zh-CN": "Mac 的 Drama 3、Qwen 文字／视觉／语音和受支持 GPT 组件使用 MLX／MPS。当前 CosyVoice／WenetSpeech 适配器，以及实测出现无效数值的 WeSpeaker／CoreML 组合保留 CPU。Apple 系统服务由系统分配硬件；指定 provider 不代表所有运算均在 GPU。", "ja": "Mac の Drama 3、Qwen テキスト・画像・音声と対応GPTは MLX／MPS を利用します。現在の CosyVoice／WenetSpeech アダプターと、検証で無効値を返した WeSpeaker／CoreML 組合せは CPU を保持します。Appleサービスの配置はOS管理です。providerの指定だけでは全処理がGPUで動いた証明にはなりません。"}, {"en": "Windows uses supported NVIDIA CUDA runtimes when available. Whisper and audio classification fall back to CPU on unavailable libraries, insufficient VRAM or inference failure. AMD only uses components supported by its installed runtime; unsupported AMD/Intel/iGPU models keep CPU. Memory planning reserves at least 8 GB or 15% system RAM and GPU/display headroom, uses reported free VRAM when available, and never counts shared iGPU memory twice. Drama retains its tested deployment profiles.", "zh-HK": "Windows 按已安裝並支援嘅 NVIDIA CUDA 環境加速；Whisper 同聲音分類遇到庫缺失、VRAM 不足或推理失敗會改用 CPU。AMD 只使用目前執行環境支援嘅組件；未支援嘅 AMD／Intel／iGPU 模型保留 CPU。預算至少預留 8 GB 或 15% 系統 RAM，同時留 GPU／顯示空間；有可用 VRAM 數字就會納入，唔重複計集顯共享記憶體。Drama 沿用已測試部署配置。", "zh-CN": "Windows 按已安装的受支持 NVIDIA CUDA 环境加速；Whisper 和声音分类遇到库缺失、显存不足或推理失败会回退 CPU。AMD 仅使用当前运行环境支持的组件，未支持的 AMD／Intel／集显模型保留 CPU。预留至少 8 GB 或 15% 系统内存及显示空间，有空闲显存数据时纳入预算，不重复计算共享内存。Drama 保留已测试的部署配置。", "ja": "Windows は対応する導入済み NVIDIA CUDA を利用します。Whisper・音響分類はライブラリ不足・VRAM不足・推論失敗時CPUへ切り替えます。AMDはランタイム対応部分のみ、非対応AMD／Intel／内蔵GPUモデルはCPUを使います。RAMを最低8 GBまたは15%と表示用GPU領域を予約し、取得可能な空きVRAMを考慮します。共有メモリは二重計上しません。Dramaは検証済み導入プロファイルを維持します。"}, {"en": "Hardware acceleration decisions shows the latest saved stage decisions, successful inference or CPU fallback, and available memory estimates. It is not a live utilisation meter. First audible recordings, saved work, source subtitles and bounded repair rules remain unchanged. Faster recognition does not guarantee correct pronunciation or a fixed full-film speed-up.", "zh-HK": "「硬件加速決策」顯示最近各階段保存嘅配置、推理成功或 CPU 後備同記憶體估算，唔係即時用量錶。保留首輪有聲錄音、保存進度、原裝字幕及有界修復規則。辨識快咗唔等於發音必定正確，亦唔保證整片固定加速倍數。", "zh-CN": "硬件加速决策显示各阶段最近保存的配置、推理成功或 CPU 回退及内存估算，不是实时用量表。首轮有声录音、进度、原装字幕和有界修复规则不变。加速不保证发音正确或整片固定速度提升。", "ja": "アクセラレーションの判断には各処理の最新保存設定・推論完了・CPU切替とメモリ見積を表示します。リアルタイム使用率ではありません。最初の有音テイク、進捗、元字幕、回数制限付き修復は維持します。高速化は発音の正確さや全編の一定倍率を保証しません。"}], "steps": false}]});

CHAPTERS.push({"id": "playback73", "title": {"en": "Watching a movie before conversion", "zh-HK": "轉換前直接睇片", "zh-CN": "转换前直接观看", "ja": "変換前の動画再生"}, "summary": {"en": "When the selected movie is not being converted, the workspace uses ordinary playback controls. Play loads and starts the source movie on the first click; it does not start conversion or run speech models. Preview and Follow processing appear only while that movie is being converted. Paused or finished work returns to ordinary playback.", "zh-HK": "所選影片冇轉換中時，用一般播放器操作；第一次按 Play 就會載入並播放原片，唔會開始轉換或執行語音模型。只有該影片轉換中先顯示預覽同跟隨處理，暫停或完成後回復一般播放。", "zh-CN": "选中影片未在转换时使用普通播放器；第一次点击 Play 会载入并播放原片，不开始转换或运行语音模型。仅该影片转换中显示预览和跟随处理，暂停或完成后恢复普通播放。", "ja": "選択した動画を変換していない時は通常の再生操作を使います。Playを一度押すと原動画を読み込み再生します。変換や音声モデルは開始しません。プレビューと処理位置追従は変換中のみ表示し、一時停止や完了後は通常再生に戻ります。"}, "sections": [{"title": {"en": "Watching a movie before conversion", "zh-HK": "轉換前直接睇片", "zh-CN": "转换前直接观看", "ja": "変換前の動画再生"}, "body": [{"en": "When the selected movie is not being converted, the workspace uses ordinary playback controls. Play loads and starts the source movie on the first click; it does not start conversion or run speech models. Preview and Follow processing appear only while that movie is being converted. Paused or finished work returns to ordinary playback.", "zh-HK": "所選影片冇轉換中時，用一般播放器操作；第一次按 Play 就會載入並播放原片，唔會開始轉換或執行語音模型。只有該影片轉換中先顯示預覽同跟隨處理，暫停或完成後回復一般播放。", "zh-CN": "选中影片未在转换时使用普通播放器；第一次点击 Play 会载入并播放原片，不开始转换或运行语音模型。仅该影片转换中显示预览和跟随处理，暂停或完成后恢复普通播放。", "ja": "選択した動画を変換していない時は通常の再生操作を使います。Playを一度押すと原動画を読み込み再生します。変換や音声モデルは開始しません。プレビューと処理位置追従は変換中のみ表示し、一時停止や完了後は通常再生に戻ります。"}, {"en": "Choose the audio track and subtitles in the player. Embedded SRT/ASS/SSA/WebVTT/mov_text tracks and the external subtitle selected for this movie can be shown on their original clocks; Off hides captions. Image subtitle tracks are labelled unsupported. Subtitle and audio choices also work in fullscreen. Changing playback subtitles does not change conversion settings or frozen job evidence.", "zh-HK": "播放器可選音軌同字幕，包括原片內置 SRT／ASS／SSA／WebVTT／mov_text 同本片已匯入外掛字幕；跟原時間顯示，可選關閉。圖片字幕會標示暫不支援。全螢幕亦可選擇。播放選項唔會更改轉換設定或已凍結嘅字幕證據。", "zh-CN": "播放器可选择音轨，以及内置 SRT／ASS／SSA／WebVTT／mov_text 和本片外挂字幕，沿用原始时间，或关闭字幕。图片字幕标示为暂不支持。全屏同样可选择。播放选择不修改转换设置或已冻结字幕证据。", "ja": "音声と字幕をプレーヤー内で選択できます。埋め込みSRT／ASS／SSA／WebVTT／mov_textと選択済み外部字幕を元の時刻で表示でき、オフも選べます。画像字幕は非対応と表示します。全画面でも選択可能です。再生の選択は変換設定や固定済み字幕証拠を変更しません。"}], "steps": false}]});

CHAPTERS.find(c=>c.id==='playback73').sections[0].body.push({"en": "The playback button shows Pause while playing and Play while paused or ended. Use the gear beside subtitles to adjust preview caption size from 12 to 48 px; this preference is remembered locally, works fullscreen, and does not change exported captions. Back/forward buttons move 10 seconds.", "zh-HK": "播放中按鈕會顯示暫停，暫停或播完則顯示播放。字幕旁嘅齒輪可調播放器字體大小（12–48 px），會喺本機記住，全螢幕亦適用；唔會更改匯出字幕。左右跳轉掣各移動 10 秒。", "zh-CN": "播放中显示暂停，暂停或播完显示播放。字幕旁齿轮可调整播放器字幕大小（12–48 px），本机记住，全屏同样适用；不更改导出字幕。左右跳转各移动10秒。", "ja": "再生中は一時停止、一時停止中・終了後は再生を表示します。字幕横の歯車で12～48 pxに変更でき、端末内に保存します。全画面にも適用され、書き出し字幕は変わりません。左右のボタンは10秒移動します。"});

CHAPTERS.find(c=>c.id==='playback73').sections[0].body.push({"en": "While converting, Automatic subtitles prioritises translated lines at the current source position. Unfinished lines are labelled; original subtitles remain a manual choice. The dialogue inspector follows playback, without moving away while you are typing. Basic mode includes left/right panel toggles and Preferences in the top-right. The duplicate header Save icon is removed; Pause & save also saves pending script edits. Keyboard Save and saves on navigation remain available.", "zh-HK": "轉換中，自動字幕優先顯示目前原聲位置已翻譯嘅台詞，未完成會標示；仍可手動揀原裝字幕。對白面板跟隨播放，輸入改稿期間唔會跳去另一句。基本模式右上有左右面板開關及偏好設定。移除頂欄重複磁碟圖示；暫停並保存亦保存未提交稿件，鍵盤保存及離開頁面時保存繼續保留。", "zh-CN": "转换中自动字幕优先显示当前位置已翻译台词，未完成将标示；可手动选择原装字幕。对白面板跟随播放，输入期间不跳句。基本模式右上提供左右面板开关及偏好设置。移除顶部重复保存图标；暂停并保存也保存稿件修改，键盘保存和页面切换保存保留。", "ja": "変換中の自動字幕は現在の原音位置の翻訳済み台詞を優先し、未完了を明示します。元字幕も手動選択できます。台詞パネルは再生に追従しますが、入力中は移動しません。基本モード右上にも左右パネルと環境設定を追加し、重複保存アイコンを削除します。一時停止・保存は編集中の台本も保存します。キーボード保存とページ移動時保存は維持します。"});

CHAPTERS.find(c=>c.id==='playback73').sections[0].body.push({"en":"While a desktop task runs, AniCanto requests protection from automatic idle sleep; the display may still turn off. Completion and pause release it, with a bounded idle fallback if the interface stops responding. Closing a laptop lid or deliberately putting the computer to sleep can still suspend conversion. Keep the computer awake for unattended work. Background queue hand-offs also reconcile saved native completion receipts after wake or a missed event; paused work is never silently restarted.","zh-HK":"桌面處理期間會請求防止自動閒置睡眠，螢幕仍可熄。完成或暫停後釋放；介面無回應時亦有有限閒置保底。合蓋或手動睡眠仍可令轉換暫停，無人看管時請保持電腦醒住。背景佇列喺喚醒或漏通知後會核對原生完成記錄接續；唔會偷偷重啟已暫停工作。","zh-CN":"桌面处理期间请求防止自动闲置睡眠，屏幕仍可关闭。完成或暂停后释放，界面无响应时也有有限闲置兜底。合盖或手动睡眠仍可能暂停转换，无人看管时请保持电脑唤醒。后台队列在唤醒或漏通知后核对原生完成记录接续，不会自动重启已暂停工作。","ja":"デスクトップで処理中は自動アイドルスリープを抑止しますが、画面は消灯できます。完了・一時停止後に解除し、画面が応答しない場合も待機時間に上限があります。蓋を閉じたり手動でスリープしたりすると変換は中断され得ます。無人処理中はコンピューターを起動状態にしてください。復帰や通知の欠落後はネイティブの完了記録を確認してキューを継続し、一時停止した作業は自動再開しません。"});

// Source-clock and bounded fallback workflow, desktop 0.24.80.
CHAPTERS.push({"id": "workflow80", "title": {"en": "Source timing, captions and fallback voices", "zh-HK": "原聲時間、字幕配對與後備聲線", "zh-CN": "原声时间、字幕匹配与备用声线", "ja": "原音時刻・字幕対応・代替音声"}, "summary": {"en": "New conversions use selected embedded/external subtitles as the primary dialogue content; Chinese subtitles are adapted directly into spoken Cantonese. Original speech recognition provides speech timing. Without usable subtitles, translate the recognized speech. Expert OCR compares OCR and speech at matching times and is opt-in. Choose the conversion source in Subtitle source above the preview; the player subtitle selector affects playback only. Shared subtitle clauses are allocated without duplicate or missing text; unresolved ownership or missing speech clocks appear in the review report. Original audio transcripts remain separate for voice references. Names, translation, shortening and missing-script recovery use the same primary text. Existing paused requests retain their old source policy and recordings. To test this workflow on an old item, reset its state, select/import subtitles, then Start. First audible takes and bounded voice repairs remain unchanged.", "zh-HK": "新轉換以已選內置／外掛字幕作主要內容，中文字幕直接改成廣東話口語；原聲辨識提供發聲時間。冇可用字幕先翻譯語音稿。OCR 係專家模式明確選項，按時間合併比較 OCR 同語音。喺預覽上方「字幕來源」選轉換來源；播放器揀字幕只影響播放。共用字幕先分配內容，檢查漏字、重複同次序；未確認分配或缺發聲時鐘會列入校對報告。原音逐字稿獨立保留作聲線參考。名稱、翻譯、精簡同補稿使用同一份主要文字。舊暫停工作保留原政策及錄音；要用舊片測新流程，先重設狀態，再選／匯入字幕及開始。保留首錄同有界補聲規則不變。", "zh-CN": "新转换以已选内置／外挂字幕为主要内容，中文字幕直接改成粤语口语；原声识别提供发声时间。无可用字幕才翻译语音稿。OCR 是专家模式明确选项，按时间合并比较 OCR 与语音。在预览上方“字幕来源”选择转换来源；播放器选择字幕只影响播放。共享字幕先分配内容，检查漏字、重复和顺序，未确认分配或缺少发声时钟列入校对报告。原音逐字稿独立保留作声线参考。名称、翻译、精简和补稿使用同一主要文字。旧暂停任务保留原政策和录音；用旧片测试新流程前先重设状态，再选择／导入字幕并开始。首录和有限补录规则不变。", "ja": "新規変換は選択した内蔵／外部字幕を内容の主な根拠とし、中国語字幕を直接広東語口語へ変換します。音声認識は発声時刻を提供し、字幕がない場合に認識文を翻訳します。OCRは上級モードで明示的に選び、時刻に沿って音声と比較します。プレビュー上の字幕ソースで変換用を指定し、プレーヤー側の字幕選択は再生だけを変更します。共有字幕の割当は重複・欠落・順序を検査し、未確定の割当と発声時刻の欠落は確認レポートに表示します。声の参照には別保存の原音認識文を使います。名前・翻訳・短縮・補完は同じ主要テキストを使用します。既存の一時停止中タスクと録音は維持し、新方式で試す場合は状態をリセットして字幕を選び直してください。"}, "sections": [{"title": {"en": "Source timing, captions and fallback voices", "zh-HK": "原聲時間、字幕配對與後備聲線", "zh-CN": "原声时间、字幕匹配与备用声线", "ja": "原音時刻・字幕対応・代替音声"}, "body": [{"en": "New conversions use selected embedded/external subtitles as the primary dialogue content; Chinese subtitles are adapted directly into spoken Cantonese. Original speech recognition provides speech timing. Without usable subtitles, translate the recognized speech. Expert OCR compares OCR and speech at matching times and is opt-in. Choose the conversion source in Subtitle source above the preview; the player subtitle selector affects playback only. Shared subtitle clauses are allocated without duplicate or missing text; unresolved ownership or missing speech clocks appear in the review report. Original audio transcripts remain separate for voice references. Names, translation, shortening and missing-script recovery use the same primary text. Existing paused requests retain their old source policy and recordings. To test this workflow on an old item, reset its state, select/import subtitles, then Start. First audible takes and bounded voice repairs remain unchanged.", "zh-HK": "新轉換以已選內置／外掛字幕作主要內容，中文字幕直接改成廣東話口語；原聲辨識提供發聲時間。冇可用字幕先翻譯語音稿。OCR 係專家模式明確選項，按時間合併比較 OCR 同語音。喺預覽上方「字幕來源」選轉換來源；播放器揀字幕只影響播放。共用字幕先分配內容，檢查漏字、重複同次序；未確認分配或缺發聲時鐘會列入校對報告。原音逐字稿獨立保留作聲線參考。名稱、翻譯、精簡同補稿使用同一份主要文字。舊暫停工作保留原政策及錄音；要用舊片測新流程，先重設狀態，再選／匯入字幕及開始。保留首錄同有界補聲規則不變。", "zh-CN": "新转换以已选内置／外挂字幕为主要内容，中文字幕直接改成粤语口语；原声识别提供发声时间。无可用字幕才翻译语音稿。OCR 是专家模式明确选项，按时间合并比较 OCR 与语音。在预览上方“字幕来源”选择转换来源；播放器选择字幕只影响播放。共享字幕先分配内容，检查漏字、重复和顺序，未确认分配或缺少发声时钟列入校对报告。原音逐字稿独立保留作声线参考。名称、翻译、精简和补稿使用同一主要文字。旧暂停任务保留原政策和录音；用旧片测试新流程前先重设状态，再选择／导入字幕并开始。首录和有限补录规则不变。", "ja": "新規変換は選択した内蔵／外部字幕を内容の主な根拠とし、中国語字幕を直接広東語口語へ変換します。音声認識は発声時刻を提供し、字幕がない場合に認識文を翻訳します。OCRは上級モードで明示的に選び、時刻に沿って音声と比較します。プレビュー上の字幕ソースで変換用を指定し、プレーヤー側の字幕選択は再生だけを変更します。共有字幕の割当は重複・欠落・順序を検査し、未確定の割当と発声時刻の欠落は確認レポートに表示します。声の参照には別保存の原音認識文を使います。名前・翻訳・短縮・補完は同じ主要テキストを使用します。既存の一時停止中タスクと録音は維持し、新方式で試す場合は状態をリセットして字幕を選び直してください。"}], "steps": false}]});
for (const c of CHAPTERS) for (const s of c.sections || []) {
 if (['When the original voice keeps producing the wrong language','An audible incomplete preview'].includes(s.title?.en)) s.body=CHAPTERS.find(c=>c.id==='workflow80').sections[0].body;
}

CHAPTERS.push({"id": "queue81", "title": {"en": "Video list and reset", "zh-HK": "影片清單與重設狀態", "zh-CN": "影片列表与重设状态", "ja": "動画リストと状態リセット"}, "summary": {"en": "Selecting a video highlights it while loading. Reordering is shown immediately; failed saves restore the displayed order. Adding a video selects the first newly added item. Restart / update dubbing → Reset state returns only that queue item to waiting, using current production defaults on its next start. Confirm before resetting. Existing media, recordings, exports and installed models remain on disk; earlier row metadata is archived. Imported subtitle choices, project terms, draft links and frozen requests are detached. Other videos and global preferences are unchanged. Reset does not start conversion. Pause active processing before resetting.", "zh-HK": "揀選影片時會即時加深選中框，載入期間顯示提示。調次序即時反映，保存失敗會還原顯示次序；加入影片會選中新加入嘅第一條。「重新製作／更新配音 → 重設狀態」只將呢條影片回復等待，下次使用目前製作預設；重設前需確認。原影片、錄音、舊成品及模型檔保留，舊清單資料會備存。影片嘅外掛字幕選擇、人名招式、草稿連結及鎖定工作設定會解除，其他影片及全域偏好不變。重設唔會自動開始轉換，處理中需先暫停。", "zh-CN": "选择影片时立即加深选中框，加载期间显示提示。调整顺序立即反映，保存失败则还原显示顺序；加入影片会选中新加入的第一条。“重新制作／更新配音 → 重设状态”只将此影片恢复为等待，下次使用当前制作默认设置，重设前需确认。源影片、录音、旧成品及模型保留，旧列表资料会备份。外挂字幕选择、项目术语、草稿链接及锁定任务设置会解除，其他影片及全局偏好不变。不自动开始转换，处理时需先暂停。", "ja": "動画の選択は読み込み中も強調表示します。並べ替えは即時表示し、保存失敗時は元に戻します。追加時は最初の新規動画を選択します。「再開始／吹替更新 → 状態をリセット」は確認後、この項目を待機状態に戻し、次回は現在の制作設定を使います。元動画・録音・既存出力・モデルは保持し、以前の項目データを保存します。外部字幕選択・用語・下書きリンク・固定リクエストは解除します。他の動画と環境設定は変更せず、自動変換も開始しません。処理中は先に一時停止してください。"}, "sections": [{"title": {"en": "Video list and reset", "zh-HK": "影片清單與重設狀態", "zh-CN": "影片列表与重设状态", "ja": "動画リストと状態リセット"}, "body": [{"en": "Selecting a video highlights it while loading. Reordering is shown immediately; failed saves restore the displayed order. Adding a video selects the first newly added item. Restart / update dubbing → Reset state returns only that queue item to waiting, using current production defaults on its next start. Confirm before resetting. Existing media, recordings, exports and installed models remain on disk; earlier row metadata is archived. Imported subtitle choices, project terms, draft links and frozen requests are detached. Other videos and global preferences are unchanged. Reset does not start conversion. Pause active processing before resetting.", "zh-HK": "揀選影片時會即時加深選中框，載入期間顯示提示。調次序即時反映，保存失敗會還原顯示次序；加入影片會選中新加入嘅第一條。「重新製作／更新配音 → 重設狀態」只將呢條影片回復等待，下次使用目前製作預設；重設前需確認。原影片、錄音、舊成品及模型檔保留，舊清單資料會備存。影片嘅外掛字幕選擇、人名招式、草稿連結及鎖定工作設定會解除，其他影片及全域偏好不變。重設唔會自動開始轉換，處理中需先暫停。", "zh-CN": "选择影片时立即加深选中框，加载期间显示提示。调整顺序立即反映，保存失败则还原显示顺序；加入影片会选中新加入的第一条。“重新制作／更新配音 → 重设状态”只将此影片恢复为等待，下次使用当前制作默认设置，重设前需确认。源影片、录音、旧成品及模型保留，旧列表资料会备份。外挂字幕选择、项目术语、草稿链接及锁定任务设置会解除，其他影片及全局偏好不变。不自动开始转换，处理时需先暂停。", "ja": "動画の選択は読み込み中も強調表示します。並べ替えは即時表示し、保存失敗時は元に戻します。追加時は最初の新規動画を選択します。「再開始／吹替更新 → 状態をリセット」は確認後、この項目を待機状態に戻し、次回は現在の制作設定を使います。元動画・録音・既存出力・モデルは保持し、以前の項目データを保存します。外部字幕選択・用語・下書きリンク・固定リクエストは解除します。他の動画と環境設定は変更せず、自動変換も開始しません。処理中は先に一時停止してください。"}], "steps": false}, {"title": {"en": "Confirmed target and queue order", "zh-HK": "確認目標與清單次序", "zh-CN": "确认目标与列表顺序", "ja": "確認対象と処理順"}, "body": [{"en": "The reset confirmation names the video chosen when the menu opened, even if the background selection changes. Preparing and resetting show progress; errors stay visible with a retry. Confirm reset closes the menu and selects that video. Start all follows the visible list order, including paused videos; selecting a video only changes what you inspect. Use its restart menu for an explicit single-video restart.", "zh-HK": "重設確認會清楚列出開選單時指定嘅影片，即使背景選中項目改變，目標都唔會變。準備及重設期間會顯示提示，失敗可見原因並重試；確認成功後會關閉選單並選中該片。「開始全部」依清單次序處理，包括暫停影片；揀選影片只影響檢視。要單獨重做某片，請用該片嘅重新製作選單。", "zh-CN": "重设确认会明确显示打开菜单时指定的影片，后台选择变化不会改变目标。准备和重设期间显示进度，失败显示原因并允许重试；成功后关闭菜单并选中该影片。“开始全部”按列表顺序处理，包括暂停影片；选择只影响查看。单独重做某片请使用该影片的重新制作菜单。", "ja": "リセット確認にはメニューを開いた動画名を表示し、背景の選択が変わっても対象を保持します。準備中と実行中の状態を表示し、エラーは再試行できる形で残します。成功後はメニューを閉じ、対象動画を選択します。一括開始は一時停止中の動画も含め、表示順に処理します。選択は閲覧対象のみを変更します。特定の動画だけを再開する場合は、その動画の再開始メニューを使ってください。"}], "steps": false}]});

CHAPTERS.push({id:'subtitle84',title:{en:'Source subtitle visible, dubbing missing','zh-HK':'睇到原字幕，但配音稿留白','zh-CN':'有原字幕，但配音稿为空',ja:'元字幕はあるのに台本が空'},summary:{en:'A source caption is separate from a generated dubbing script.','zh-HK':'原裝字幕同已生成配音稿係兩樣資料。','zh-CN':'原字幕与已生成配音稿是不同资料。',ja:'元字幕と生成済み吹き替え台本は別の情報です。'},sections:[{title:{en:'Check the source notice','zh-HK':'先睇原因提示','zh-CN':'先查看原因提示',ja:'理由を確認'},body:[{en:'If a source subtitle was read but its spoken-turn allocation was not confirmed, the editor now labels it explicitly and displays the source caption in a dashed timeline clip. This does not mean target-language dubbing was generated. New conversions ignore incidental subtitle display tails when assigning speech turns. If a shared-caption split still fails its bounded checks, the full caption is kept once at the main corroborated speech interval; uncertain fragments keep original audio and are listed for review. Check timing and speaker. Existing saved jobs retain their frozen policy. For an old blank script, use Reset state, select/import the subtitle source and start a new conversion. A voice-only update keeps the existing script. Earlier recordings and exports are retained.','zh-HK':'原字幕已讀入，但未確認屬於邊段原聲時，編輯器會顯示原因，時間線用虛線框顯示原字幕；呢個唔代表已生成廣東話配音。新轉換會忽略字幕尾部輕微重疊，避免串錯幾段原聲。共用字幕經有界檢查仍無法拆開時，完整文字會喺主要原聲時段保留一次，其餘不確定碎段保留原音並列入覆核，請比較時間同講者。舊保存工作沿用凍結規則；要修正舊空白稿，先重設狀態、選／匯入字幕再重新開始。只更新配音會沿用舊稿。舊錄音及成品保留。','zh-CN':'原字幕已读入但未确认对应的原声片段时，编辑器会显示原因，时间线以虚线框显示原字幕；这不代表已生成配音。新转换忽略字幕尾部轻微重叠。共享字幕经有限检查仍无法拆分时，全文在主要原声时段保留一次，其余不确定片段保留原音并列入复核，请比较时间与说话人。旧保存任务沿用冻结规则；修正旧空白稿需重设状态、选择／导入字幕并重新开始。仅更新配音会沿用旧稿，旧录音和成品保留。',ja:'元字幕を取得しても発話との対応が未確定の場合は理由を表示し、タイムラインに元字幕を破線で示します。吹き替え生成済みという意味ではありません。新規変換は字幕の短い表示の余韻で発話を誤結合しません。共有字幕の分割が検査を通らない場合、全文を主な発話区間へ一度だけ残し、不確定な断片は元音声を保持して確認対象にします。時刻と話者を確認してください。保存済みの処理は以前の規則を維持します。空の台本を修正するには状態をリセットし、字幕を選んで変換し直してください。音声のみの更新では古い台本が残ります。以前の録音と出力は保持します。'}]}]});

// Current priority defaults replace the historical .83 OCR opt-in description.
{const c=CHAPTERS.find(c=>c.id==='workflow80');c.summary={"en": "Content priority is configurable. Factory defaults: with usable selected embedded/external text subtitles, Subtitles > speech; otherwise OCR > speech. Basic mode applies Preferences → Default content priority automatically. Expert mode offers Use preference defaults, Speech > subtitles, Subtitles > speech, Speech > OCR and OCR > speech in Production settings. The first source determines meaning; the second assists. OCR paths only apply without usable text subtitles; speech timestamps always come from original audio. An incompatible manual path shows an actionable error instead of silently changing the chosen source. The effective path is recorded in source-workflow.json. No usable OCR text falls back locally to speech. A source-only caption is not a generated dubbing script. Old saved requests retain their frozen settings; reset/restart translation to test a new source workflow. Voice-only updates keep existing scripts. Earlier recordings and outputs remain on disk.", "zh-HK": "內容優先權可以設定。出廠預設：有已選內置／外掛文字字幕用「字幕 > 語音」，冇可用文字字幕用「OCR > 語音」。一般模式自動跟「偏好設定 → 預設內容優先流程」。專家模式喺製作設定可選跟隨預設、語音 > 字幕、字幕 > 語音、語音 > OCR、OCR > 語音。前者決定意思，後者輔助；OCR 只喺冇文字字幕時使用，發聲時間一律跟原音。手動選咗唔適用路徑會清楚報錯，唔會靜默改來源；實際路徑存喺 source-workflow.json；個別時段 OCR 冇可用文字則用原聲稿。原字幕唔等於已生成配音稿。舊工作沿用凍結設定；要試新流程需重設／重新開始翻譯，只更新配音會保留舊稿。舊錄音及成品檔保留。", "zh-CN": "内容优先权可设置。出厂默认：有已选内置／外挂文字字幕用“字幕 > 语音”，无可用文字字幕用“OCR > 语音”。一般模式自动遵循“偏好设置 → 默认内容优先流程”。专家模式在制作设置可选择跟随默认、语音 > 字幕、字幕 > 语音、语音 > OCR、OCR > 语音。前者决定含义，后者辅助；OCR 仅在无文字字幕时使用，发声时间始终跟随原音。不适用的手动路径会明确报错，不会静默更改来源；实际路径存入 source-workflow.json；个别时段无可用 OCR 文字则用原声稿。原字幕不等于已生成配音稿。旧任务沿用冻结设置；测试新流程需重设／重新开始翻译，仅更新配音保留旧稿。旧录音与成品保留。", "ja": "内容の優先度を設定できます。初期値はテキスト字幕ありなら「字幕 > 音声」、なしなら「OCR > 音声」です。基本モードは環境設定の既定値を自動使用し、上級モードは制作設定で四つの優先順または既定値を選べます。先頭を内容の主な根拠、後方を補助とします。OCRはテキスト字幕がない場合だけ使用し、発声時刻は原音に従います。適用できない手動選択は明確なエラーを表示し、黙って変更しません。実際の設定をsource-workflow.jsonに記録します。OCRが使えない区間は音声認識へ戻ります。元字幕は生成済み台本とは異なります。保存済み処理は以前の設定を保持し、新設定の確認には翻訳から再実行してください。音声のみ更新では以前の台本が残ります。録音と出力は保持します。"};c.sections[0].body=[c.summary];}

// Canonical desktop workflow: .85 new submissions; historical saved jobs remain frozen.
CHAPTERS.splice(1,0,{"id": "work85", "title": {"en": "Work modes and automatic completion", "zh-HK": "工作模式與自動完成", "zh-CN": "工作模式与自动完成", "ja": "作業モードと自動出力"}, "summary": {"en": "Balanced is the default. Full AI review is a separate switch, off by default. Review notes do not hold a usable output for approval.", "zh-HK": "預設平衡；完整 AI 覆核獨立開關、預設關閉。有疑點照樣保存可用成品，唔等逐句批准。", "zh-CN": "默认平衡；完整 AI 复核独立开关、默认关闭。有疑点仍保存可用成品，不等待逐句批准。", "ja": "既定はバランス。完全AI検査は独立した任意設定で、既定ではオフ。確認事項は報告し、出力を承認待ちにしません。"}, "sections": [{"title": {"en": "Three work modes", "zh-HK": "三種工作模式", "zh-CN": "三种工作模式", "ja": "3つの作業モード"}, "body": [{"en": "Performance: one baseline plus bounded missing-audio recovery and a generic fallback; no voice listening or shortening. Balanced: retain audible first takes, repair missing/damaged clips, and shorten only measured overruns in one local pass per repair stage. Quality: voice listening and up to two local repair/shortening passes. Only Full AI review enables deeper frame/character analysis. Model-deployment presets are separate.", "zh-HK": "效能：一輪基準、有限補聲及通用後備，唔覆聽或縮稿。平衡：優先保留有聲首錄，只補缺聲／損壞，實測超時先局部縮稿，各修復階段最多一輪。品質：覆聽配音，局部修復／縮稿最多兩輪。畫面／角色深入分析由「完整 AI 覆核」開關控制；部署頁模型推薦係另一項設定。", "zh-CN": "性能：一轮基准、有限补声及通用后备，不回听或缩稿。平衡：优先保留有声首录，只补缺声／损坏，实测超时才局部缩稿，各修复阶段最多一轮。质量：回听配音，局部修复／缩稿最多两轮。画面／角色深入分析由完整 AI 复核开关控制；模型推荐是另一项设置。", "ja": "パフォーマンスは初回生成と欠落復旧・汎用音声のみで、再認識検査や短縮を省略。バランスは初回音声を優先し、欠落と実測超過だけを各修復段階で最大1回修復。品質は音声を検査し最大2回の局所修復。画像・人物の詳しい分析は完全AI検査で有効化。モデル推奨プリセットとは独立です。"}], "steps": false}, {"title": {"en": "Content and timing", "zh-HK": "內容與時間", "zh-CN": "内容与时间", "ja": "内容と時刻"}, "body": [{"en": "With selected usable text subtitles, the factory priority is Subtitles > speech; without them it is OCR > speech. The first source determines meaning, the second assists. Original speech supplies timing. A completely missing primary may use the auxiliary with a report note; conflicting readable primary text is retained. New requests freeze the effective workflow before work starts.", "zh-HK": "有已選可用文字字幕，預設「字幕 > 語音」；冇文字字幕則「OCR > 語音」。前者決定意思，後者輔助；發聲時間跟原聲。主要內容完全缺失先用輔助並記錄，唔會用輔助推翻有字嘅主要來源。新工作開始前凍結實際流程。", "zh-CN": "有已选可用文字字幕，默认“字幕 > 语音”；没有则“OCR > 语音”。前者决定意思，后者辅助；发声时间跟原声。主要内容完全缺失才用辅助并记录，不会用辅助推翻有字的主要来源。新工作开始前冻结实际流程。", "ja": "選択済みテキスト字幕があれば「字幕 > 音声」、なければ「OCR > 音声」が既定。先頭が内容の根拠、後方は補助で、時刻は原音に従います。主資料が完全に欠落した場合だけ補助を使用し記録。新規処理開始前に実効設定を固定します。"}], "steps": false}, {"title": {"en": "Fallback and finished output", "zh-HK": "後備與正式輸出", "zh-CN": "后备与正式输出", "ja": "代替音声と完成ファイル"}, "body": [{"en": "Try a generic voice in the target language before source speech. Balanced/Quality can shorten a measured overlong generic take and try at most one other installed engine. If repair still cannot deliver, retain audible source continuity, export, and report untranslated intervals honestly. Laughs, cries and deliberately preserved OP/ED are separate original performances. A file with review notes is still exported; it is not a claim that every line passed. Unreadable media, missing required resources or output/storage errors remain real blockers. Old paused requests keep their frozen policy; voice-only updates retain old scripts.", "zh-HK": "先試通用目標語配音，再到原聲。平衡／品質可處理實測過長通用錄音，再試最多一款已安裝引擎；仍交付唔到先保留可聽原聲、輸出並列出未翻譯時段。笑喊及保留 OP／ED 另計。有覆核提示仍保存成品，唔代表每句已通過。媒體讀唔到、缺必要資源、磁碟／編碼錯誤仍會阻礙輸出。舊暫停工作沿用凍結規則；只更新配音會保留舊稿。", "zh-CN": "先试通用目标语配音，再到原声。平衡／质量可处理实测过长通用录音，再试最多一款已安装引擎；仍无法交付才保留可听原声、输出并列出未翻译时段。笑哭及保留 OP／ED 单独计算。有复核提示仍保存成品，不代表每句已通过。媒体不可读、缺必要资源、磁盘／编码错误仍会阻碍输出。旧暂停任务沿用冻结规则；只更新配音保留旧稿。", "ja": "原音より先に目的言語の汎用音声を試します。バランス・品質は実測超過の汎用音声を修復し、別の導入済みエンジンを最大1種類試行。失敗時は可聴原音を残し、未翻訳区間を報告して出力。笑い・泣き声や保持したOP/EDは別扱い。注意事項があっても出力しますが全台詞合格の保証ではありません。読めない素材・必要資源の不足・保存／エンコード障害は実際の停止要因です。保存済み処理は旧方針を維持し、音声のみ更新では旧台本を使用します。"}], "steps": false}]});

// Current new-job contract; historical paused requests keep their frozen rules.
CHAPTERS.find(c=>c.id==='work85').sections=[{"title": {"en": "Modes and attempts", "zh-HK": "模式與次數", "zh-CN": "模式与次数", "ja": "モードと回数"}, "body": [{"en": "Initial attempts per line: Performance 1, Balanced 1, Quality up to 3, stopping when audio is usable. Performance skips all content listening and shortening, including fallback. Balanced/Quality perform bounded listening: uncertainty is a warning, not a confirmed error. Same-actor measured timing operations: 0 / 0 with first-take policy (otherwise 1) / 2. Generic attempts: 1 / 1 / 2. Only a measured overrun may receive one faithful generic compact in Balanced/Quality. No pre-generation character-budget shortening.", "zh-HK": "每句首次生成上限：效能 1、平衡 1、品質 3 次，有可用錄音即停。效能所有後備亦唔覆聽或縮稿；平衡／品質有限覆聽，未確認只提示。實測同角色對時上限：0／首錄策略 0（其他 1）／2。通用聲線上限：1／1／2。平衡／品質只有實測過長先可作一次保義通用縮稿，禁止生成前按估算字數縮稿。", "zh-CN": "每句首次生成上限：性能 1、平衡 1、质量 3 次，有可用录音即停。性能所有备用也不回听或缩稿；平衡／质量有限回听，未确认只提示。同角色实测对时上限：0／首录策略 0（其他 1）／2。通用声线上限：1／1／2。平衡／质量只有实测过长才可作一次保义通用缩稿，禁止生成前按估算字数缩稿。", "ja": "初回生成は各台詞につきパフォーマンス1回、バランス1回、品質は最大3回で、可用音声があれば終了。パフォーマンスは全代替段階でも再認識・短縮なし。バランスと品質は限定的に検査し、不確かな結果は注意扱い。同役の実測時間調整は0／初回優先時0（他は1）／2回。汎用音声は1／1／2回。バランス・品質の汎用台詞短縮は実測超過時だけ最大1回。生成前の文字数推測で短縮しません。"}]}, {"title": {"en": "Translation source", "zh-HK": "翻譯來源", "zh-CN": "翻译来源", "ja": "翻訳元"}, "body": [{"en": "Subtitles > speech translates ONLY the selected embedded/external subtitles. Speech supplies timing and the reference voice. All gaps without subtitles keep original audio: no invented ASR script, no TTS, not missing dubbing. If ASR misses authored text, retain it with the original subtitle display clock and a timing warning. The other three routes use A for meaning, B as auxiliary. Saved source workflows stay frozen.", "zh-HK": "字幕 > 語音只翻譯已選內置／外掛字幕；語音只提供時間及聲線。所有冇字幕嘅空隙保留原音，唔用 ASR 補稿、唔配音，亦唔當漏配。有字幕但 ASR 漏認，保留原字幕時間並標示對時後備。另三路以 A 為主、B 輔助；舊工作來源規則維持凍結。", "zh-CN": "字幕 > 语音只翻译已选内置／外挂字幕；语音只提供时间及声线。所有无字幕空隙保留原音，不用 ASR 补稿、不配音，也不算漏配。有字幕但 ASR 漏识别，保留原字幕显示时间并提示。另三路以 A 为主、B 辅助；旧任务来源规则保持冻结。", "ja": "字幕 > 音声は選択済み内蔵・外部字幕だけを翻訳します。原音は発声時刻と参照声質に使用。字幕のない区間は原音を残し、ASRから台本を補わず、欠落配音と数えません。字幕をASRが見落とした場合は字幕の表示時刻を使用し注意事項を表示。他の3経路はAを主、Bを補助とし、保存済み方針は維持します。"}]}, {"title": {"en": "Time allowance and installed fallback", "zh-HK": "時間預算與已安裝後備", "zh-CN": "时间预算与已安装备用", "ja": "時間予算と導入済み代替"}, "body": [{"en": "Whole-film listening and repair allowance: 60 / 180 / 600 seconds. AI uses the first 75%; installed target-language system voices have the final 25%. The current inference may finish, but no new item/chunk starts after its deadline. Counters and spent time survive pause/restart; export is separate. One installed alternate AI engine is tried at most once, then installed system speech at most twice per line. No automatic voice/model download. The system fallback switch is shown before starting.", "zh-HK": "全片覆聽及修復預算：60／180／600 秒，前 75% 供 AI，最後 25% 留俾系統目標語聲線。當次推理可完成，到期後唔開新項目／分塊。暫停、重開唔重置已用時間及次數，匯出另計。另一已安裝 AI 引擎最多一次，系統目標語聲線每句最多兩次；唔自動下載模型或聲線，開始前可關閉系統後備。", "zh-CN": "全片回听及修复预算：60／180／600 秒，前 75% 供 AI，最后 25% 留给系统目标语声线。当前推理可完成，到期后不启动新项目／分块。暂停、重开不重置时间及次数，导出另计。另一已安装 AI 引擎最多一次，系统目标语声线每句最多两次；不自动下载，开始前可关闭系统备用。", "ja": "全編の検査・復旧予算は60／180／600秒。75%をAI、最後の25%をシステム目的言語音声に確保。進行中の推論は完了できますが期限後は次の項目・チャンクを開始しません。一時停止・再開で時間と回数はリセットされず、出力時間は別。別の導入済みAIは最大1回、システム音声は各台詞最大2回。自動ダウンロードせず、開始前に設定をオフにできます。"}]}, {"title": {"en": "Automatic completion and limits", "zh-HK": "自動完成與限制", "zh-CN": "自动完成与限制", "ja": "自動出力と制限"}, "body": [{"en": "Keep a usable first recording, then try generic target speech, one installed alternate AI engine, installed system speech, and original audio last. An explicit Original audio failure policy may go directly to source. Confirmed wrong content never revives merely because its first take is audible. Uncertainty remains a report warning. Ordinary AI/native failures still reach export; an all-source output explicitly reports zero target-language speech. Encode/subtitle packaging has one persistent retry, using saved takes; final-only resume does not regenerate the film. Unreadable input, storage errors, persistent encode errors and user cancellation remain real boundaries.", "zh-HK": "可用首錄 → 通用目標語 → 一個已安裝其他 AI → 系統目標語 → 原聲最後；明確選原聲策略可直接用原聲。確認錯內容唔會因首錄有聲就重新採用，未確認留報告。一般 AI／系統後備失敗仍嘗試交付；整片只得原音會明示目標語配音為 0。編碼／字幕包裝最多重試一次並保存次數，只續匯出唔重配整片；來源壞、儲存錯、持續編碼失敗及用戶取消仍如實處理。", "zh-CN": "可用首录 → 通用目标语 → 一个已安装其他 AI → 系统目标语 → 原声最后；明确原声策略可直接用原声。确认错误内容不会因首录有声就重新采用，未确认留报告。一般 AI／系统备用失败仍尝试交付；全片只有原音会明示目标语配音为 0。编码／字幕包装最多重试一次并保存次数，只续导出不重配整片；损坏来源、存储错误、持续编码失败及用户取消仍如实处理。", "ja": "可用な初回音声→汎用目的言語→別の導入済みAI→システム目的言語→最後に原音。明示した原音方針は直接原音を使用可能。確認済みの誤った初回音声を有音だけで復活させません。不確かな結果は報告。AI・システムの通常エラーでも出力に進み、全編原音なら目的言語配音0を明記。出力・字幕結合は保存済み音声で最大1回再試行し、出力だけの再開で全編を再生成しません。壊れた入力・保存障害・継続する出力エラー・キャンセルは明示します。"}]}];
CHAPTERS.find(c=>c.id==='automatic-recovery').sections=[{"title": {"en": "Time allowance and installed fallback", "zh-HK": "時間預算與已安裝後備", "zh-CN": "时间预算与已安装备用", "ja": "時間予算と導入済み代替"}, "body": [{"en": "Whole-film listening and repair allowance: 60 / 180 / 600 seconds. AI uses the first 75%; installed target-language system voices have the final 25%. The current inference may finish, but no new item/chunk starts after its deadline. Counters and spent time survive pause/restart; export is separate. One installed alternate AI engine is tried at most once, then installed system speech at most twice per line. No automatic voice/model download. The system fallback switch is shown before starting.", "zh-HK": "全片覆聽及修復預算：60／180／600 秒，前 75% 供 AI，最後 25% 留俾系統目標語聲線。當次推理可完成，到期後唔開新項目／分塊。暫停、重開唔重置已用時間及次數，匯出另計。另一已安裝 AI 引擎最多一次，系統目標語聲線每句最多兩次；唔自動下載模型或聲線，開始前可關閉系統後備。", "zh-CN": "全片回听及修复预算：60／180／600 秒，前 75% 供 AI，最后 25% 留给系统目标语声线。当前推理可完成，到期后不启动新项目／分块。暂停、重开不重置时间及次数，导出另计。另一已安装 AI 引擎最多一次，系统目标语声线每句最多两次；不自动下载，开始前可关闭系统备用。", "ja": "全編の検査・復旧予算は60／180／600秒。75%をAI、最後の25%をシステム目的言語音声に確保。進行中の推論は完了できますが期限後は次の項目・チャンクを開始しません。一時停止・再開で時間と回数はリセットされず、出力時間は別。別の導入済みAIは最大1回、システム音声は各台詞最大2回。自動ダウンロードせず、開始前に設定をオフにできます。"}]}, {"title": {"en": "Automatic completion and limits", "zh-HK": "自動完成與限制", "zh-CN": "自动完成与限制", "ja": "自動出力と制限"}, "body": [{"en": "Keep a usable first recording, then try generic target speech, one installed alternate AI engine, installed system speech, and original audio last. An explicit Original audio failure policy may go directly to source. Confirmed wrong content never revives merely because its first take is audible. Uncertainty remains a report warning. Ordinary AI/native failures still reach export; an all-source output explicitly reports zero target-language speech. Encode/subtitle packaging has one persistent retry, using saved takes; final-only resume does not regenerate the film. Unreadable input, storage errors, persistent encode errors and user cancellation remain real boundaries.", "zh-HK": "可用首錄 → 通用目標語 → 一個已安裝其他 AI → 系統目標語 → 原聲最後；明確選原聲策略可直接用原聲。確認錯內容唔會因首錄有聲就重新採用，未確認留報告。一般 AI／系統後備失敗仍嘗試交付；整片只得原音會明示目標語配音為 0。編碼／字幕包裝最多重試一次並保存次數，只續匯出唔重配整片；來源壞、儲存錯、持續編碼失敗及用戶取消仍如實處理。", "zh-CN": "可用首录 → 通用目标语 → 一个已安装其他 AI → 系统目标语 → 原声最后；明确原声策略可直接用原声。确认错误内容不会因首录有声就重新采用，未确认留报告。一般 AI／系统备用失败仍尝试交付；全片只有原音会明示目标语配音为 0。编码／字幕包装最多重试一次并保存次数，只续导出不重配整片；损坏来源、存储错误、持续编码失败及用户取消仍如实处理。", "ja": "可用な初回音声→汎用目的言語→別の導入済みAI→システム目的言語→最後に原音。明示した原音方針は直接原音を使用可能。確認済みの誤った初回音声を有音だけで復活させません。不確かな結果は報告。AI・システムの通常エラーでも出力に進み、全編原音なら目的言語配音0を明記。出力・字幕結合は保存済み音声で最大1回再試行し、出力だけの再開で全編を再生成しません。壊れた入力・保存障害・継続する出力エラー・キャンセルは明示します。"}]}];
CHAPTERS.find(c=>c.id==='modes').sections=[{"title": {"en": "Modes and attempts", "zh-HK": "模式與次數", "zh-CN": "模式与次数", "ja": "モードと回数"}, "body": [{"en": "Initial attempts per line: Performance 1, Balanced 1, Quality up to 3, stopping when audio is usable. Performance skips all content listening and shortening, including fallback. Balanced/Quality perform bounded listening: uncertainty is a warning, not a confirmed error. Same-actor measured timing operations: 0 / 0 with first-take policy (otherwise 1) / 2. Generic attempts: 1 / 1 / 2. Only a measured overrun may receive one faithful generic compact in Balanced/Quality. No pre-generation character-budget shortening.", "zh-HK": "每句首次生成上限：效能 1、平衡 1、品質 3 次，有可用錄音即停。效能所有後備亦唔覆聽或縮稿；平衡／品質有限覆聽，未確認只提示。實測同角色對時上限：0／首錄策略 0（其他 1）／2。通用聲線上限：1／1／2。平衡／品質只有實測過長先可作一次保義通用縮稿，禁止生成前按估算字數縮稿。", "zh-CN": "每句首次生成上限：性能 1、平衡 1、质量 3 次，有可用录音即停。性能所有备用也不回听或缩稿；平衡／质量有限回听，未确认只提示。同角色实测对时上限：0／首录策略 0（其他 1）／2。通用声线上限：1／1／2。平衡／质量只有实测过长才可作一次保义通用缩稿，禁止生成前按估算字数缩稿。", "ja": "初回生成は各台詞につきパフォーマンス1回、バランス1回、品質は最大3回で、可用音声があれば終了。パフォーマンスは全代替段階でも再認識・短縮なし。バランスと品質は限定的に検査し、不確かな結果は注意扱い。同役の実測時間調整は0／初回優先時0（他は1）／2回。汎用音声は1／1／2回。バランス・品質の汎用台詞短縮は実測超過時だけ最大1回。生成前の文字数推測で短縮しません。"}]}, {"title": {"en": "Full AI review", "zh-HK": "完整 AI 覆核", "zh-CN": "完整 AI 复核", "ja": "完全AI検査"}, "body": [{"en": "Full AI review is separate, off by default. It adds source and character/frame analysis; the selected work mode still limits voice recovery. Balanced is the default.", "zh-HK": "完整 AI 覆核係獨立開關，預設關閉。額外分析原意、角色／畫面；配音修復仍受所選模式限制。預設平衡。", "zh-CN": "完整 AI 复核是独立开关，默认关闭。额外分析原意、角色／画面；配音修复仍受所选模式限制。默认平衡。", "ja": "完全AI検査は独立設定で既定はオフ。原意・人物・画像を追加分析しますが音声復旧は選択モードの上限を維持。既定はバランス。"}]}];
CHAPTERS.find(c=>c.id==='workflow80').sections[0].body=[{"en": "Subtitles > speech translates ONLY the selected embedded/external subtitles. Speech supplies timing and the reference voice. All gaps without subtitles keep original audio: no invented ASR script, no TTS, not missing dubbing. If ASR misses authored text, retain it with the original subtitle display clock and a timing warning. The other three routes use A for meaning, B as auxiliary. Saved source workflows stay frozen.", "zh-HK": "字幕 > 語音只翻譯已選內置／外掛字幕；語音只提供時間及聲線。所有冇字幕嘅空隙保留原音，唔用 ASR 補稿、唔配音，亦唔當漏配。有字幕但 ASR 漏認，保留原字幕時間並標示對時後備。另三路以 A 為主、B 輔助；舊工作來源規則維持凍結。", "zh-CN": "字幕 > 语音只翻译已选内置／外挂字幕；语音只提供时间及声线。所有无字幕空隙保留原音，不用 ASR 补稿、不配音，也不算漏配。有字幕但 ASR 漏识别，保留原字幕显示时间并提示。另三路以 A 为主、B 辅助；旧任务来源规则保持冻结。", "ja": "字幕 > 音声は選択済み内蔵・外部字幕だけを翻訳します。原音は発声時刻と参照声質に使用。字幕のない区間は原音を残し、ASRから台本を補わず、欠落配音と数えません。字幕をASRが見落とした場合は字幕の表示時刻を使用し注意事項を表示。他の3経路はAを主、Bを補助とし、保存済み方針は維持します。"}];

CHAPTERS.find(c=>c.id==='work85').sections[0].body.push({"en": "Entering Basic mode without an explicit work-mode choice starts in Balanced. You can choose another mode before starting. Automatic processing groups the AI, OP/ED and fallback switches. A paused conversion no longer locks new-job settings; resuming it still uses its saved snapshot.", "zh-HK": "由開始畫面進入基本模式，未另選時用平衡；開始前可自行改模式。「自動處理」集中 AI、OP／ED 同後備左右開關。暫停影片唔再鎖死新工作設定；暫停續跑仍沿用已儲存流程。", "zh-CN": "从开始画面进入基本模式，未另选时用平衡；开始前可自行修改。「自动处理」集中 AI、OP／ED 和备用开关。暂停影片不再锁定新任务设置；暂停续跑仍沿用已保存流程。", "ja": "基本モードに入る際、作業モードを明示しなければバランスを使用し、開始前に変更できます。自動処理にAI・OP/ED・代替音声スイッチを集約。一時停止した変換は新しい設定をロックしませんが、再開時は保存済み設定を維持します。"});

// v3: repair and listening have independent persisted clocks.
CHAPTERS.find(c=>c.id==='work85').sections[0].body=[{"en": "All modes preserve authored subtitle authority and source clocks. Performance generates once and skips content listening and AI shortening; in new High-speed jobs only fully silent takes are re-recorded, at most twice, and alternate or system voice substitution is switched off. Balanced is the default: keep fitting first takes and permit one same-voice faithful timing rewrite only after measured audio overrun. Quality allows up to three initial attempts and two same-voice timing operations. Full AI frame review remains a separate switch, off by default. Older saved jobs keep their frozen policies.", "zh-HK": "三種模式都保留已選字幕內容及原聲時鐘。高速首錄一次，唔覆聽內容或 AI 縮稿；新建高速工作只有完全冇聲先補錄，最多兩次，並關閉後備／系統聲線替換。平衡預設保留合時首錄；只有真正音訊過長，先可用同聲線保義縮稿重配一次。品質首次最多三次，同聲線實測對時最多兩次。完整 AI 畫面覆核仍係獨立開關，預設關閉；舊工作沿用凍結規則。", "zh-CN": "三种模式都保留已选字幕内容及原声时钟。高速首录一次，不回听内容或 AI 缩稿；新建高速任务只有完全无声才补录，最多两次，并关闭后备／系统声线替换。平衡默认保留合时首录；只有实测音频过长，才可同声线保义缩稿重配一次。品质首次最多三次，同声线实测对时最多两次。完整 AI 画面复核仍是独立开关，默认关闭；旧任务沿用冻结规则。", "ja": "全モードで選択字幕の内容と原音時刻を保持。高速は初回1回で内容検査・AI短縮なし。新規の高速処理では完全な無音のみ最大2回再生成し、代替・システム音声への切替は無効。既定のバランスは時刻に合う初回を保持し、実測超過時だけ同声質で意味を保持した短縮・再生成を最大1回。品質は初回最大3回、同声質の時刻修復最大2回。完全AI画像検査は独立設定で既定オフ。保存済み旧処理は旧方針を維持します。"}];
CHAPTERS.find(c=>c.id==='automatic-recovery').sections[0].body=[{"en": "Required silence/corruption and measured timing repairs run before optional listening. A frozen plan uses the pending repair count and measured first-generation seconds per line; repair allowance starts at 60 / 180 / 600 seconds and is capped at 5 / 15 / 30 minutes for Performance / Balanced / Quality. Optional listening has separate 0 / 60 / 180-second clocks; Balanced inspects up to 24 suspect or changed lines, Quality a broader set. Listening cannot spend repair time. Native voices reserve 25% of repair time only when enabled. An in-flight operation may finish beyond the clock; no new operation starts after expiry. These are limits, not a promised delay or success rate.", "zh-HK": "先補無聲／損壞及修實測過長，再做額外覆聽。開始修復時按待修句數、首輪實測每句生成秒數凍結預算：高速／平衡／品質由 60／180／600 秒起，上限 5／15／30 分鐘。覆聽另有 0／60／180 秒；平衡最多選 24 句疑點或改動，品質較全面。覆聽唔會用補聲時間。只有開啟系統聲線後備先留 25% 修復時間俾佢；關閉時全部供 AI。當次操作可完成而超時，到期唔開新操作。上限唔等於必須等待或保證修好。", "zh-CN": "先补无声／损坏及修实测过长，再额外回听。按待修句数、首轮实测生成耗时冻结预算：高速／平衡／品质由 60／180／600 秒起，上限 5／15／30 分钟。回听另限 0／60／180 秒；平衡最多选 24 句疑点或改动，品质较全面。回听不能使用补声时间。仅开启系统声线备用时为它预留 25% 修复时间；关闭时全部供 AI。当前操作可完成而超时，到期不开始新操作。上限不是必须等待或保证修好。", "ja": "無音・破損と実測超過の復旧を先に行い、追加検査は後。待機台詞数と初回生成の実測時間で予算を固定。高速／バランス／品質は60／180／600秒から、上限5／15／30分。追加検査は別枠0／60／180秒で、バランスは変更・疑義の最大24台詞、品質は広範囲。検査は復旧時間を消費しません。システム音声が有効な場合だけ25%を確保。進行中の処理は期限を超えて完了可能ですが新規処理は開始しません。上限は待ち時間や成功の保証ではありません。"}, {"en": "Pause/resume keeps all spent clocks and per-line operation counts. A later confirmed listening defect can use only remaining repair allowance; uncertain ASR stays a warning. New settings apply to newly reset conversions; frozen old jobs retain their workflow. Output reports actual source fallback and incomplete target speech. Unreadable input, storage or persistent encoding failures still report an error.", "zh-HK": "暫停續跑唔退還時間及逐句次數；後續覆聽真係確認有錯，只可用剩餘修復額度，未確認 ASR 只留提示。新設定適用重設後新工作，舊凍結工作保持舊流程。報告如實列原聲後備、未完成目標語片段；來源損壞、儲存不足或持續編碼失敗仍會報錯。", "zh-CN": "暂停续跑不返还时间及逐句次数；后续回听确认有错，仅用剩余修复额度，未确认 ASR 只留提示。新设置适用重设后的新任务，旧冻结任务保持旧流程。报告如实列原声备用、未完成目标语片段；损坏来源、存储不足或持续编码失败仍报错。", "ja": "一時停止・再開で時間や台詞ごとの回数は戻りません。後の検査で確認した不具合は残り復旧枠だけを使用し、不確かなASRは警告。新規リセットした変換に新方針を適用し、旧保存済み方針は維持。実際の原音代替と目的言語未完成区間を報告。入力破損・保存障害・継続する出力エラーは報告します。"}];

CHAPTERS.push({"id": "safe-capacity89", "title": {"en": "Safe duration repair", "zh-HK": "安全時長修復", "zh-CN": "安全时长修复", "ja": "安全な長さ調整"}, "summary": {"en": "Keep complete speech; use verified gaps before shortening.", "zh-HK": "保留完整對白，先用有證據嘅空檔，真超時先縮稿。", "zh-CN": "保留完整对白，先用有证据的空档，真超时才缩稿。", "ja": "完全な台詞を保ち、確認済みの空きを先に利用。"}, "sections": [{"title": {"en": "What happens automatically", "zh-HK": "自動處理次序", "zh-CN": "自动处理顺序", "ja": "自動処理の順序"}, "steps": false, "body": [{"en": "For a measured overlong recording with a suspect noise tail, word-timed Whisper checks without a script prompt and local vocal detection must agree with complete text before a separate trimmed candidate is saved. Original recordings and native delivery rate are retained. Uncertain words or endings are not trimmed or shortened to hide missing speech. They use the existing bounded full-script fallback. This is conservative evidence, not pronunciation certification.", "zh-HK": "實測過長而疑似尾噪嘅錄音，須由無台詞提示嘅 Whisper 全文／末字時間同本機人聲檢查共同支持，先另存裁尾候選；保留原錄音及原取樣率。字詞／尾音未確認唔裁，亦唔用縮稿掩蓋漏讀，改用既有完整稿有界後備。呢個係保守證據，唔係發音認證。", "zh-CN": "实测过长且疑似尾噪的录音，须由无台词提示的 Whisper 全文／末字时间与本机人声检查共同支持，才另存裁尾候选；保留原录音及采样率。未确认不裁，也不用缩稿掩盖漏读，使用完整稿有界备用。这是保守证据，不是发音认证。", "ja": "実測超過と疑わしいノイズ末尾に限り、台詞を提示しないWhisperの全文・最終語時刻と音声検出が一致した場合のみ別候補を保存。元録音とサンプルレートを保持します。不確かな末尾は切らず、省略を短縮で隠さず、完全な台詞の有限代替を使います。発音の保証ではありません。"}, {"en": "The next verified non-vocal gap may accommodate complete speech. Missing subtitles alone do not prove silence. Music stays in the original mix once; other speech, laughter, crying, breaths, protected passages and OP/ED remain barriers. Only a genuinely overlong complete recording then receives a faithful rewrite and full regeneration: none in Performance, one same-actor pass in Balanced, two in Quality.", "zh-HK": "下一段有證據嘅無人聲空檔可容納完整配音；冇字幕唔等於冇人聲。背景保留原混音一次，其他對白、笑喊喘氣、保護段同 OP／ED 仍不可跨越。之後真係放唔落先保義縮稿、完整重配：高速不縮，平衡同聲線最多一次，品質兩次。", "zh-CN": "下一段有证据的无人声空档可容纳完整配音；无字幕不等于无人声。背景只混入一次，其他对白、笑哭喘气、保护段和 OP／ED 不可跨越。仍放不下才保义缩稿、完整重配：高速不缩，平衡同声线最多一次，品质两次。", "ja": "確認済みの無発声区間に完全な音声を延ばせます。字幕なしは無音の証拠ではありません。背景は一度だけ混合し、他の台詞・笑い・泣き・息・保護区間・OP/EDは守ります。それでも長い場合のみ意味を保持して全文再生成。高速は短縮なし、バランスは同声の1回、品質は2回。"}, {"en": "Extra endpoint checks have their own film-wide allowance: none in Performance, 60 seconds in Balanced, 180 in Quality. They cannot spend necessary repair time, start a whole-film recheck or download a missing model. Pausing keeps spent time and attempt counts. New/reset jobs use this workflow; saved old jobs remain frozen. Counts and unresolved passages appear in the review report.", "zh-HK": "端點額外檢查有全片獨立時間：高速不新增，平衡60秒，品質180秒；唔會用必要補聲時間、重開整集覆聽或自動下載缺少模型。暫停保留已用時間同次數。新／重設工作先用新流程，舊工作維持凍結；校對報告列裁尾同未確認數目。", "zh-CN": "端点额外检查有全片独立时间：高速不新增，平衡60秒，品质180秒；不消耗必要补声时间、不重开整片回听或自动下载缺失模型。暂停保留已用时间和次数。新／重设任务使用新流程，旧任务维持冻结；校对报告列裁尾和未确认数量。", "ja": "追加の末尾検査は映画全体で別枠。高速は追加なし、バランス60秒、品質180秒。必要な復旧時間を消費せず、全編再検査やモデルの自動ダウンロードをしません。停止・再開で時間や回数は戻りません。新規・リセット時のみ適用し、旧ジョブは維持。確認レポートに件数と未確認区間を残します。"}]}]});

CHAPTERS.push({"id": "report90", "title": {"en": "Understanding the review report", "zh-HK": "點睇校對報告", "zh-CN": "怎样查看校对报告", "ja": "確認レポートの見方"}, "summary": {"en": "Delivery problems and optional listening notes are different.", "zh-HK": "未交付目標配音同可選試聽提示係兩回事。", "zh-CN": "未交付目标配音与可选试听提示是两回事。", "ja": "音声の要対応と任意の試聴メモは別です。"}, "sections": [{"title": {"en": "Which lines are retried", "zh-HK": "邊啲對白會再補配", "zh-CN": "哪些对白会再补配", "ja": "再試行する台詞"}, "steps": false, "body": [{"en": "Saving an audible recording, an uncertain source boundary or an ASR spelling difference does not confirm a broken voice. The report separates undelivered target speech and confirmed defects from optional listening, subtitle allocation and earlier attempt notes. Repair delivery issues retries eligible lines and changed recordings, respecting manual choices. Original diagnostics remain in the debug report. Regenerating one line is still available when you choose it.", "zh-HK": "已保存錄音、原聲分句未確認，或者辨識器寫錯字，都唔等於配音已證實有問題。報告會將未交付目標配音／已確認缺陷，同可選試聽、字幕配對及舊嘗試提示分開。「補配需要處理嘅對白」只處理合資格項目同已改動錄音，保護人手選擇。原始診斷保留喺除錯報告；你仍可自行逐句重錄。", "zh-CN": "已保存录音、原声分句未确认，或识别器写错字，都不等于配音已证实有问题。报告将未交付目标配音／已确认缺陷与可选试听、字幕配对及旧尝试提示分开。补配仅处理合资格项与已更改录音，并保护手动选择。原始诊断保留在调试报告；仍可自行逐句重录。", "ja": "録音の保存、原音の未確認区切り、ASRの表記差だけで吹き替えの不具合は確定しません。目的言語音声の未完成・確認済み不具合と、任意の試聴・字幕対応・過去の試行メモを分けます。復旧は対象台詞と変更済み録音に限定し手動選択を守ります。元の診断はデバッグレポートに残り、個別再録音も選べます。"}, {"en": "Reaction sounds are a separate optional listening list, collapsed by default. Preserved intervals are counted once across the parent job and audio tracks. More notes do not mean more missed voices; a completed export is not a full pronunciation or meaning certification.", "zh-HK": "反應聲另有可選試聽清單，預設收起；同一原聲區間唔會因主工作同音軌各有記錄就重複計數。提示多唔等於漏配多；匯出完成亦唔代表全部讀音同原意已認證。", "zh-CN": "反应声另设可选试听列表，默认收起；同一原声区间不会因主任务和音轨分别有记录而重复计数。提示多不等于漏配多；导出完成不代表全部读音和原意已认证。", "ja": "反応音は別の任意試聴リストで、既定では折りたたみます。同一区間を親ジョブと各トラックで重複集計しません。メモ数は音声欠落数ではなく、出力完了は全発音や意味の保証ではありません。"}]}]});
// Build 245: one standard mode. Full AI review and AI auto repair are separate switches.
{const modes=CHAPTERS.find(c=>c.id==='modes');
modes.title={en:'Standard mode and the two switches',"zh-HK":'標準模式與兩個開關',"zh-CN":'标准模式与两个开关',ja:'標準モードと2つのスイッチ'};
modes.summary={en:'Every new job runs the standard mode. Full AI review and AI auto repair are separate switches, and both start off.',"zh-HK":'所有新工作都用標準模式。完整 AI 覆核同 AI 自動修復係兩個獨立開關，預設都關閉。',"zh-CN":'所有新任务都使用标准模式。完整 AI 复核与 AI 自动修复是两个独立开关，默认均关闭。',ja:'新規処理はすべて標準モードで実行します。完全AI検査とAI自動修復は独立したスイッチで、既定はオフです。'};
modes.sections=[
{title:{en:'What the standard mode does',"zh-HK":'標準模式做乜',"zh-CN":'标准模式做什么',ja:'標準モードの動作'},body:[{
en:'The app records each line once. It keeps the first recording that has audible speech. It records again only when a line has no sound at all or the file is damaged, and it makes at most two more attempts. It does not re-listen to a line to decide whether the words are correct, and it does not shorten a script that already fits the time window. Uncertain results stay as report notes. Review each line with the report and by listening.',
"zh-HK":'標準模式每句錄一次。有聲嘅第一條錄音會保留。只有完全冇聲或者檔案損壞先會再錄，最多再多試兩次。唔會因為懷疑用字而覆聽重錄，亦唔會改短已經啱時段嘅稿。唔確定嘅結果會留喺報告，請用報告同逐句試聽核對。',
"zh-CN":'标准模式每句录制一次。第一条有声音的录音会保留。只有完全无声或文件损坏才会重录，最多再试两次。不会因怀疑用词而回听重录，也不会缩短已经符合时段的台词。不确定的结果会记在报告中，请通过报告和逐句试听核对。',
ja:'標準モードは各台詞を1回録音します。音声がある最初の録音を保持します。音が全くない場合かファイルが壊れている場合だけ再録し、追加は最大2回です。言葉が正しいか確認する為の聞き返しや、時間に収まる台本の短縮は行いません。不確実な項目は報告に記録します。報告と試聴で確認してください。'}],steps:false},
{title:{en:'Script length follows the original speech',"zh-HK":'對白長短跟原聲',"zh-CN":'台词长度跟随原声',ja:'台本の長さは原音声に合わせる'},body:[{
en:'The app measures when the original Japanese line starts and ends. It counts the spoken units in that line and writes a Cantonese line with a similar number of characters. When the speaking speed is close, the new recording ends inside the same window, so lines do not run over into the next line. A small allowance of 0.35 seconds is added after the original end.',
"zh-HK":'程式會計日文原聲嘅開始同結束時間，再數嗰句嘅音節，寫字數接近嘅廣東話對白。語速相近時，新錄音會喺同一時段內完成，唔會疊落下一句。原本結束之後會預留 0.35 秒。',
"zh-CN":'程序会计算日文原声的开始与结束时间，并统计该句的音节数，据此撰写字数接近的粤语台词。语速接近时，新录音会在同一时段内结束，不会压到下一句。原声结束后预留 0.35 秒。',
ja:'アプリは元の日本語台詞の開始と終了を測定し、拍数を数えて同程度の文字数の広東語台詞を作成します。話す速さが近い場合、新しい録音は同じ区間で終わり、次の台詞に重がりません。元の終了後に0.35秒の余裕を置きます。'}],steps:false},
{title:{en:'Hong Kong wording',"zh-HK":'香港用字',"zh-CN":'香港用字',ja:'香港の表記'},body:[{
en:'The dialogue uses Hong Kong spoken Cantonese characters and particles, not written Chinese. This makes the lines sound natural and keeps the character count close to the original.',
"zh-HK":'對白用香港口語廣東話嘅字同語氣詞，唔係書面中文，聽落自然，字數亦接近原文。',
"zh-CN":'台词使用港式口语粤语用字和语气词，而非书面中文，听来更自然，字数也更接近原文。',
ja:'台詞は書き言葉ではなく香港の口語広東語の文字や助詞を使います。自然に聞こえ、文字数も原文に近づきます。'}],steps:false},
{title:{en:'Full AI review and AI auto repair',"zh-HK":'完整 AI 覆核同 AI 自動修復',"zh-CN":'完整 AI 复核与 AI 自动修复',ja:'完全AI検査とAI自動修復'},body:[{
en:'Full AI review adds frame and character analysis and allows one timing rewrite pass. AI auto repair lets the app try another installed voice model or a system voice when a line fails. Both switches are off by default, and both lock while a job runs. Saved jobs keep the settings they started with.',
"zh-HK":'「完整 AI 覆核」會加入畫格同角色分析，並容許一次時段改寫。「AI 自動修復」容許喺某句失敗時改用另一個已安裝語音模型或系統語音。兩個開關預設關閉，運行期間會鎖定；開始咗嘅工作會保留佢開始時嘅設定。',
"zh-CN":'“完整 AI 复核”会加入画面与角色分析，并允许一次时段改写。“AI 自动修复”允许在某句失败时改用另一个已安装的语音模型或系统语音。两个开关默认关闭，运行期间锁定；已启动的任务保留启动时的设置。',
ja:'完全AI検査はコマとキャラクター分析を追加し、タイミング書き換えを1回許可します。AI自動修復は、失敗した台詞で他の導入済み音声モデルまたはシステム音声を使うことを許可します。両スイッチは既定でオフで、処理中はロックされます。開始済みのジョブは開始時の設定を保持します。'}],steps:false}];
const work85=CHAPTERS.find(c=>c.id==='work85');if(work85){work85.title={en:'Standard mode and automatic completion',"zh-HK":'標準模式與自動完成',"zh-CN":'标准模式与自动完成',ja:'標準モードと自動完了'};
work85.summary={en:'One standard mode runs every new job. Review and repair options are separate switches, and both start off.',"zh-HK":'一個標準模式跑所有新工作；覆核同修復係獨立開關，預設關閉。',"zh-CN":'一个标准模式运行所有新任务；复核与修复是独立开关，默认关闭。',ja:'一つの標準モードが全ての新規処理を実行します。検査と修復は独立スイッチで既定オフです。'};
work85.sections=[
{title:{en:'Attempts',"zh-HK":'嘗試次數',"zh-CN":'尝试次数',ja:'試行回数'},body:[{
en:'Each line gets one recording. A line with no sound or a damaged file gets at most two more attempts. Same-actor timing rewrites: 0. Full AI review allows 1. Another installed voice model and a system voice are tried only when AI auto repair is on. The app never shortens a script by character estimate before recording.',
"zh-HK":'每句錄一次；完全冇聲或檔案損壞最多再多兩次。同角色時段改寫：0 次；開「完整 AI 覆核」先容許 1 次。只有開「AI 自動修復」先會試另一個已安裝語音模型或系統語音。錄音前唔會估算字數改短稿。',
"zh-CN":'每句录制一次；完全无声或文件损坏最多再试两次。同角色时段改写：0 次；开启“完整 AI 复核”才允许 1 次。只有开启“AI 自动修复”才会尝试另一个已安装语音模型或系统语音。录音前不会按字数估算缩短台词。',
ja:'各台詞は1回録音します。音がない場合やファイル破損時は最大2回追加します。同一キャラクターのタイミング書き換えは0回、完全AI検査時は1回です。他の導入済み音声モデルやシステム音声はAI自動修復がオンの時のみ試します。録音前の文字数見積もりによる短縮は行いません。'}],steps:false},
{title:{en:'Translation source and clocks',"zh-HK":'翻譯來源與時間',"zh-CN":'翻译来源与时间',ja:'翻訳元と時刻'},body:[{
en:'With usable selected embedded or external text subtitles, the priority is Subtitles > speech. Without them, it is OCR > speech. The first source decides the meaning, the second assists. Speech timing always comes from the original audio. New requests freeze the effective path before work starts.',
"zh-HK":'有已選可用內置／外掛文字字幕，優先順序係「字幕 > 語音」；冇文字字幕則係「OCR > 語音」。前者決定意思，後者輔助；發聲時間一律跟原聲。新工作開始前會凍結實際路徑。',
"zh-CN":'有可用的已选内置或外挂文字字幕时，优先级为“字幕 > 语音”；没有文字字幕时为“OCR > 语音”。前者决定含义，后者辅助。发声时间始终取自原声。新任务在开始前冻结实际路径。',
ja:'選択済みの利用可能なテキスト字幕がある場合は「字幕 > 音声」、ない場合は「OCR > 音声」が優先順位です。先頭が内容を決定し、後方は補助です。発声時刻は常に原音声から取得します。新規処理は開始前に実効パスを固定します。'}],steps:false},
{title:{en:'Finished output',"zh-HK":'正式輸出',"zh-CN":'最终输出',ja:'最終出力'},body:[{
en:'If a line still has no usable recording, the app exports the file anyway and lists the lines that are not dubbed. Laughs, cries and a preserved opening or ending song are separate original performances. A finished file with report notes is not a claim that every line passed. Unreadable media, missing required resources, disk errors and user cancellation still stop the job.',
"zh-HK":'如果某句仍然冇可用錄音，程式照樣輸出成品，並列出未配音嘅句子。笑聲、喊聲同保留嘅主題曲係獨立嘅原聲表演。有報告提示嘅成品唔代表每句已通過。媒體讀唔到、缺必要資源、磁碟錯誤同用戶取消仍會停止工作。',
"zh-CN":'如果某句仍没有可用录音，程序仍会输出成品，并列出未配音的句子。笑声、哭声和保留的主题曲是独立的原声表演。带报告提示的成品不代表每句都已通过。媒体不可读、缺少必要资源、磁盘错误和用户取消仍会停止任务。',
ja:'利用可能な録音がない台詞が残っていてもファイルは出力され、未配音の台詞が一覧に表示されます。笑い声、泣き声、保持された主題歌は別の原音声演技です。報告メモがある出力が全ての台詞の合格を示すものではありません。読めないメディア、必要な資源の欠落、ディスクエラー、ユーザーのキャンセルは処理を停止します。'}],steps:false}];}
}
{const SWEEP=[["none in Performance, one same-actor pass in Balanced, two in Quality","one same-actor pass in Standard mode"],["none in Performance, 60 seconds in Balanced, 180 in Quality","none in Standard mode"],["Balanced inspects up to 24 suspect or changed lines, Quality a broader set","Standard mode adds no extra listening pass"],["Performance / Balanced / Quality","Standard mode"],["Performance","Standard mode"],["Balanced","Standard mode"],["高速不縮，平衡同聲線最多一次，品質兩次","標準模式最多一次同聲線重配"],["高速不新增，平衡60秒，品質180秒","標準模式不新增"],["平衡最多選 24 句疑點或改動，品質較全面","標準模式不設額外覆聽"],["高速／平衡／品質","標準模式"],["高速不缩，平衡同声线最多一次，品质两次","标准模式最多一次同声线重配"],["高速不新增，平衡60秒，品质180秒","标准模式不新增"],["平衡最多选 24 句疑点或改动，品质较全面","标准模式不设额外回听"],["高速／平衡／品质","标准模式"],["高速は短縮なし、バランスは同声の1回、品質は2回","標準モードは同声の1回まで"],["高速は追加なし、バランス60秒、品質180秒","標準モードは追加なし"],["バランスは変更・疑義の最大24台詞、品質は広範囲","標準モードは追加検査なし"],["高速／バランス／品質","標準モード"],["60／180／600","600"],["5／15／30","30"],["0／60／180","0"],["60 / 180 / 600","600"],["5 / 15 / 30","30"],["0 / 60 / 180","0"]];
const sweep=s=>{for(const [a,b] of SWEEP)s=s.split(a).join(b);return s;};
const walk=v=>{if(typeof v==='string')return sweep(v);if(Array.isArray(v))return v.map(walk);if(v&&typeof v==='object'){const o={};for(const k in v)o[k]=walk(v[k]);return o;}return v;};
for(let i=0;i<CHAPTERS.length;i++)CHAPTERS[i]=walk(CHAPTERS[i]);
const modes=CHAPTERS.find(c=>c.id==='modes');
if(modes)modes.sections.push({"title":{"en":"Before recording starts","zh-HK":"錄音開始之前","zh-CN":"录音开始之前","ja":"録音開始の前"},"steps":false,"body":[{"en":"After translation and before the voice engine runs, one bounded pass rewrites only the lines whose estimated take would end after the original Japanese speech. The limit comes from the measured window and the Japanese mora count. A candidate is rejected when it drops a name grounded in the source, an explicit count, a negation, or when it reads as written Mandarin. Every accepted and rejected line is listed in the report, so nothing disappears without a record.","zh-HK":"翻譯之後、配音引擎開始之前，會做一次有界改寫，只處理估計會讀過日語原聲時段嘅句子。上限用實測時段同日語摩拉數計。候補如果少咗原聲佐證嘅名稱、明確數量、否定，或者讀落似書面語，就會拒絕，保留原稿。接納同拒絕嘅句子全部喺報告列明。","zh-CN":"翻译之后、配音引擎开始之前，进行一次有界改写，只处理估计会读超过日语原声时段的句子。上限由实测时段与日语 mora 数计算。候选若缺少原声佐证的名字、明确数量、否定，或读起来像书面语，则拒绝并保留原稿。接受与拒绝的句子均在报告中列出。","ja":"翻訳の後、音声エンジン開始前に一度だけ有限の書き直しを行い、日本語音声の区間を越えると推定される台詞だけを扱います。上限は実測区間と日本語モーラ数から算出。根拠のある名前、明確な数量、否定が消える場合や書き言葉に読める場合は候補を却下し原稿を保持します。採用・却下は全てレポートに記載します。"},{"en":"A line shorter than three seconds needs a longer reference before the engine can copy the voice. The fill now comes from quiet room tone in the same scene, and it is accepted only when its level is far below the speech in the reference. Music, sound effects and another speaker are never used. If no gap in the scene is quiet enough, silence is used as before.","zh-HK":"少於三秒嘅句子需要較長嘅參考先可以複製聲線。而家會用同一場環境嘅安靜環境音補足，而且只有音量明顯低於句內人聲先會用。音樂、音效同其他人嘅聲音一概唔會借用。如果該場冇足够靜嘅空檔，就用返以前嘅靜音。","zh-CN":"少于三秒的句子需要更长的参考才能复制声线。现在用同一场景的安静环境音补足，只有音量明显低于句内人声时才采用。音乐、音效与其他人的声音不会被借用。若该场景没有足够安静的空档，则照旧使用静音。","ja":"3秒未満の台詞は音声複製により長い参考が必要です。今は同じ場面の実環境音を使い、レベルが音声より十分に低い場合だけ採用します。音楽・効果音・他の話者は使用しません。十分に静かな間がなければ従来通り無音を使います。"}]});}

// The shared product copy is authoritative after historical mode migrations.
{const chapter=CHAPTERS.find(c=>c.id==='modes');if(chapter){chapter.title=WORKFLOW_GUIDE.title;chapter.sections=WORKFLOW_GUIDE.items.map(item=>({title:item.title,body:[item.body],steps:false}));}}
// Repair Help uses the same product rules as the controls. Historical copy above
// cannot leave a second, conflicting definition of the final fallback selector.
{const chapter=CHAPTERS.find(c=>c.id==='automatic-recovery');if(chapter){const ids=new Set(['repairCostWarning','contentReview','autoRepair','missingAudio','durationLimit','durationOff','durationOn','alternateEngine','systemVoice','resume','failedVoiceFallback']);chapter.sections=WORKFLOW_GUIDE.items.filter(item=>ids.has(item.id)).map(item=>({title:item.title,body:[item.body],steps:false}));}}
// These new mobile report controls have no desktop execution mapping yet.
// Keep their common source copy, but do not advertise unsupported desktop controls.
{const chapter=CHAPTERS.find(c=>c.id==='modes');if(chapter){const pending=new Set(['standardReviewOnly','voiceReviewLevels','reviewLow','reviewMedium','reviewHigh','reviewUnchecked','reviewAll','durationOff']);chapter.sections=WORKFLOW_GUIDE.items.filter(item=>!pending.has(item.id)).map(item=>({title:item.title,body:[item.body],steps:false}));chapter.sections.unshift({title:{en:'Desktop implementation status','zh-HK':'桌面版實作狀態','zh-CN':'桌面版实现状态',ja:'デスクトップ版の実装状況'},body:[{en:'This desktop build allows dialogue overlap when duration limiting is off. Retained source intervals, OP/ED and the selected video end still constrain delivery. Extending the video by holding its last frame is not implemented here. Original recordings remain available; unresolved delivery appears in the report. Mobile listening-report levels are not desktop controls yet. These are pending implementation items, not verified platform alignment.','zh-HK':'本桌面版本關閉時長限制後容許對白重疊，但保留原聲區間、片頭／片尾及所選影片終點仍然限制交付。以定格最後畫面延長影片尚未接駁。原始錄音會保留，未能交付嘅項目會列入報告。手機版新增覆聽評級亦未成為桌面控制。呢啲屬待實作項目，唔代表兩邊已完全對齊。','zh-CN':'本桌面版本关闭时长限制后允许对白重叠，但保留原声区间、片头片尾及所选视频终点仍限制交付。定格最后画面以延长视频尚未接入。原始录音会保留，未能交付的项目列入报告。手机版新增复听评级也尚未成为桌面控制。这些属于待实现项目，不代表两端已完全对齐。',ja:'このデスクトップ版は長さ制限がオフなら台詞の重なりを許可します。ただし原音保持区間、OP/ED、選択した動画の終端は引き続き出力の境界です。最終フレームの静止による動画延長は未実装です。元の録音は保持し、未出力の項目を報告します。モバイル版の新しい聴き取り評価もデスクトップの設定ではありません。これらは未実装の対応項目で、プラットフォームの一致を保証しません。'}],steps:false});}}

// Context editing keeps production controls separate from selected media.
CHAPTERS.push({
  "id": "context-editing-252",
  "title": {
    "en": "Dialogue, captions and mix",
    "zh-HK": "對白、字幕與混音",
    "zh-CN": "对白、字幕与混音",
    "ja": "台詞・字幕・ミックス"
  },
  "summary": {
    "en": "Production and optional repair stay in the right panel. Editing tools open beside the selected content.",
    "zh-HK": "右側集中製作與額外修復；編輯工具按選取內容開啟。",
    "zh-CN": "右侧集中制作与额外修复；编辑工具按所选内容打开。",
    "ja": "右パネルは制作と追加修復に集中し、編集ツールは選択した内容から開きます。"
  },
  "sections": [
    {
      "title": {
        "en": "Edit one dialogue line",
        "zh-HK": "編輯單句對白",
        "zh-CN": "编辑单句对白",
        "ja": "台詞を1行ずつ編集"
      },
      "steps": false,
      "body": [
        {
          "en": "Select a dialogue clip in the timeline, then use Edit dialogue beside the dialogue playback buttons. Listen compares original and saved takes. Retake edits the source transcript and target script, then generates one native-rate audio sample. Adjust contains timing, rate, trim, seed and display-caption controls. The editor keeps its selected line while you listen. Save and close stores the changes. New recordings remain available for comparison; choose Use recording to adopt one.",
          "zh-HK": "在時間軸選取對白，再按對白播放按鈕旁的「編輯對白」。試聽可比較原聲與已保存錄音；重錄可修改原聲文字及配音台詞，再生成一段原取樣率音訊；調整包含時間、語速、裁剪、種子及顯示字幕。試聽期間，編輯器會固定所選對白。「保存並關閉」會儲存修改；新錄音會保留供比較，請按「採用錄音」選取。",
          "zh-CN": "在时间轴选择对白，再按对白播放按钮旁的“编辑对白”。试听可比较原声与已保存录音；重录可修改原声文字和配音台词，再生成一段原采样率音频；调整包含时间、语速、裁剪、种子及显示字幕。试听期间，编辑器会固定所选对白。“保存并关闭”会保存修改；新录音会保留供比较，请按“采用录音”选择。",
          "ja": "タイムラインで台詞を選び、再生ボタン横の「台詞を編集」を押します。試聴では原音と保存済み音声を比較できます。再録音では原文と台詞を編集し、元のサンプルレートで音声だけを生成します。調整には時刻、速度、トリム、シード、表示字幕があります。試聴中も選択行を保持します。「保存して閉じる」で保存し、新しい音声は採用操作で選びます。"
        }
      ]
    },
    {
      "title": {
        "en": "Preview and display captions",
        "zh-HK": "預覽與顯示字幕",
        "zh-CN": "预览与显示字幕",
        "ja": "プレビューと表示字幕"
      },
      "steps": false,
      "body": [
        {
          "en": "Use the player subtitle menu to choose a track and its adjacent settings icon to change preview subtitle size. Preview size and playback volume do not change exported media. A display-caption edit in the line editor keeps the selected recording and review choices. A spoken-script, source-transcript or role change requires a new recording choice. Save the draft, then export a new version from Produce to apply media changes.",
          "zh-HK": "使用播放器字幕選單選擇字幕軌，旁邊的設定圖示可調整預覽字幕大小。預覽字體大小及播放音量不會改變成品。在逐句編輯器只修改顯示字幕，會保留所選錄音及覆核選擇；更改配音台詞、原聲文字或角色則需要重新選擇錄音。保存草稿後，從「製作匯出」輸出新版本，才會套用至影片。",
          "zh-CN": "使用播放器字幕菜单选择字幕轨，旁边的设置图标可调整预览字幕大小。预览字号和播放音量不会改变成品。在逐句编辑器只修改显示字幕，会保留所选录音和复核选择；更改配音台词、原声文字或角色则需要重新选择录音。保存草稿后，从“制作导出”输出新版本，才会应用到视频。",
          "ja": "プレーヤーの字幕メニューでトラックを選び、横の設定アイコンでプレビューの文字サイズを変えます。プレビューのサイズと再生音量は出力に影響しません。表示字幕だけの変更では採用音声を保持します。台詞、原文、役を変えた場合は音声を選び直してください。下書きを保存し、制作・書き出しから新版を出力します。"
        }
      ]
    },
    {
      "title": {
        "en": "Export mix",
        "zh-HK": "成品混音",
        "zh-CN": "成品混音",
        "ja": "出力ミックス"
      },
      "steps": false,
      "body": [
        {
          "en": "Open the mixer icon in the timeline toolbar. Export background level supports 0–150%. Lower background while speaking reduces music and effects during dialogue; it is not the source-separation switch. Mixer values follow the current Global or Individual settings scope. Save and close, then export a new version. Keep original audio track is available once in Production. This task does not regenerate or overwrite existing recordings.",
          "zh-HK": "按時間軸工具列的混音圖示。成品背景音量支援 0–150%；「對白時降低背景音」會在說話期間降低音樂與音效，並不是原聲分離開關。混音值會沿用目前的全域或個別影片設定範圍。保存並關閉後，請輸出新版本。「保留原聲音軌」集中在製作設定；調整混音不會重新生成或覆寫現有錄音。",
          "zh-CN": "按时间轴工具栏的混音图标。成品背景音量支持 0–150%；“对白时降低背景音”会在说话期间降低音乐和音效，并不是原声分离开关。混音值会沿用当前的全局或单独视频设置范围。保存并关闭后，请输出新版本。“保留原声音轨”集中在制作设置；调整混音不会重新生成或覆盖现有录音。",
          "ja": "タイムラインのミックスアイコンを開きます。背景音量は0〜150%です。「台詞中は背景音を下げる」は音楽・効果音の低減で、音源分離の切り替えではありません。全体・個別設定の範囲に従います。保存後に新版を書き出してください。原音トラックの保持は制作設定に集約されます。既存音声は再生成・上書きされません。"
        }
      ]
    },
{
    "title": {
        "en": "Source workflow availability",
        "zh-HK": "來源流程支援範圍",
        "zh-CN": "来源流程支持范围",
        "ja": "入力フローの対応範囲"
    },
    "steps": false,
    "body": [
        {
            "en": "This desktop update changes editing controls. It does not add the newer iPad automatic fallback for an explicitly selected subtitle workflow with no text subtitle. If the video has only burned-in captions, choose OCR > speech or Automatic before starting. A selected subtitle file that cannot be read must be corrected separately.",
            "zh-HK": "這次桌面更新調整編輯介面，尚未加入 iPad 新增的自動後備：明確選擇字幕流程但沒有文字字幕時，桌面版不會自動改選其他來源。只有畫面字幕的影片，請在開始前選擇「OCR > 語音」或自動。已選字幕檔無法讀取的問題，仍須另行處理。",
            "zh-CN": "本次桌面更新调整编辑界面，尚未加入 iPad 新增的自动后备：明确选择字幕流程但没有文字字幕时，桌面版不会自动改选其他来源。只有画面字幕的视频，请在开始前选择“OCR > 语音”或自动。已选字幕文件无法读取的问题，仍须另行处理。",
            "ja": "今回のデスクトップ更新は編集操作の変更です。字幕フローを明示的に選び、テキスト字幕がない場合の新しいiPad版の自動切り替えは未対応です。焼き込み字幕のみの動画は、開始前に「OCR > 音声」または自動を選んでください。選択した字幕ファイルの読み取りエラーは別途修正が必要です。"
        }
    ]
}
  ]
});
