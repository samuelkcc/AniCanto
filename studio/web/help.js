import {esc} from './model.js';
// The two languages share chapter IDs, section order and release limitations.
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
                  "en": "On first launch, the app follows the system language: Chinese and Cantonese use Hong Kong Traditional Chinese; other languages use English. Your manual selection is remembered. You can browse the studio during setup. A bottom-right notification shows model download progress; click it for full installation details. The compact summary stays short while the expandable, scrollable log retains filenames and package messages. Conversion remains unavailable until the selected models and required runtimes are ready.",
                  "zh-HK": "首次啟動會跟隨系統語言：中文及廣東話用香港繁體中文，其他語言用英文；之後記住你手動揀嘅語言。部署期間可以瀏覽工作室，右下角提示會顯示模型下載進度，按一下可睇完整安裝詳情。主畫面只顯示簡短分類，詳細檔名同套件記錄放喺可展開、捲動嘅記錄內。所選模型同必要執行環境準備好後，先可以開始轉換。"
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
            "en": "Welcome detects memory and the available processing backend. Highest quality uses full Drama 3 + Qwen 35B; our best Cantonese listening results so far were on Apple Silicon with 64 GB memory. Balanced uses a smaller compatible combination. Mac and Windows offer Qwen 9B and 35B; 4B downloads are no longer offered. The plan shows the actual voice, translation and recognition models before any download. Only selectable versions with reviewed licence evidence are offered; an unavailable preset cannot start a download. One recognition version is selected per purpose, not every quantization. Hardware details is collapsed by default. Models & storage groups missing downloads, installed models and cleanup; runtime cleanup stays inside its own section. Removal shows real file progress and a result, then refreshes setup without restarting on Mac. Windows runtime removal closes the app first so loaded files can be released. Rebuilding a removed runtime repairs dangling app-owned Python links while retaining projects and packages. Memory figures include headroom and remain estimates until setup tests the actual runtime. Intel Macs are not supported.",
            "zh-HK": "Welcome 會偵測記憶體同可用執行方式。最高品質使用完整 Drama 3 + Qwen 35B；目前廣東話試聽效果最佳嘅實測組合係 Apple Silicon 64 GB 記憶體。平衡方案採用較小嘅相容組合；Mac 同 Windows 統一提供 Qwen 9B 同 35B，取消 4B 新下載。下載前清單會顯示實際配音、翻譯同辨識模型；只提供可選並已有授權核對資料嘅版本，未能使用嘅方案唔會開始下載。每類用途選一個辨識版本，唔會因為選最高品質而下載所有量化版本。硬件詳情預設收起；模型與儲存空間集中顯示待下載項目、已下載模型同移除操作，執行環境清理另外收起。移除會顯示實際檔案進度同結果，Mac 完成後即時恢復部署，唔使重開；Windows 移除執行環境要先關閉 App 釋放使用中檔案。重新部署會修復失效嘅 App 專用 Python 連結，保留專案同套件。記憶體數字包括預留，仍需部署測試實際執行環境。唔支援 Intel Mac。"
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
            "zh-HK": "透過里程碑查看進度。成品儲存後可按「播放成品」或「顯示檔案」；專案／成品管理會保留成品位置及處理時間。"
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
      "en": "How Normal mode handles translation, timing and missing dialogue automatically, and what the result labels mean.",
      "zh-HK": "一般模式點樣自動處理翻譯、時長與缺聲，以及輸出狀態代表甚麼。"
    },
    "sections": [
      {
        "title": {
          "en": "Recovery order",
          "zh-HK": "修復次序"
        },
        "body": [
          {
            "en": "Before voice generation, Normal mode screens potentially verbose or repeated translations. A matching original subtitle or OCR caption can guide brevity, but its length is never a hard limit. Japanese/source speech remains primary when OCR is wrong or absent. Only meaning-verified edits are adopted. Natural-speed audio may be longer than the source utterance when it fits before the next turn or protected section.",
            "zh-HK": "配音前，一般模式會篩選疑似冗長或重複嘅翻譯。對應原裝字幕或 OCR 可提示精簡，但字數唔係硬性上限。OCR 錯誤或缺漏時，仍以日文／來源原聲為準；只有通過意思核對嘅改稿先會採用。自然語速配音可以長過原句，只要喺下一句或受保護片段前講完。"
          },
          {
            "en": "Known defects receive targeted repairs first. If unresolved, the selected local text model chooses among existing mechanisms: source-grounded concise adaptation, complete-clause retakes, conditioning the same original reference, or removal of measured near-silent padding. It cannot execute generated code, install arbitrary models or claim success without audio evidence. Each turn has at most two additional mechanism attempts, saved across resumes. The extra recovery director shares a five-minute text-model budget per output language, with no repeated connection attempts when the model stops responding. Voice generation has its own recorded processing time.",
            "zh-HK": "已知問題先作局部修復；仍未完成，先由所選本機文字模型揀既有方法，包括按原聲重新精簡、完整分句重錄、處理同一位角色嘅原聲參考，或者移除量度到嘅近乎純靜音邊位。模型不能執行生成程式碼、任意安裝模型或冇錄音證據就宣稱成功。每句最多再試兩種機制，續做會沿用保存紀錄。額外修復調度每種輸出語言共用五分鐘文字模型預算；模型停止回應時唔會反覆連線。錄音生成時間會另外記錄。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Natural timing and processing limits",
          "zh-HK": "自然語速與處理上限"
        },
        "body": [
          {
            "en": "Automatic Normal production first trims only measured silent edges and uses safe neighbouring gaps, with onset shifts of at most 0.5 seconds. Visual shot changes are advisory: safe timing is based on dialogue and preserved source ranges, without arbitrary twelve-second divisions. Complete final fallback recordings receive the same measured gentle-tempo trial before rejection. OP / ED, simultaneous speech and manual recordings remain protected. If that is insufficient, the app requests faithful shorter wording and new complete readings. Up to three distinct shorter phrasings receive separate meaning checks; a second timing retry can use another approved phrasing. If grounded meaning checks reject all proposals, one fresh source-only rewrite uses the quoted defects as feedback, then receives another independent meaning check. Name lists recognised only as generic Chinese remain dialect-unconfirmed and can trigger recovery. Clear nonverbal cries with an empty translation are preserved as vocalizations. A final automatic tempo adjustment is normally limited to 5% and at most 0.18 seconds saved. Only recordings up to 2 seconds that exceed the safe window by at most 0.12 seconds may use up to 10%, measured cumulatively; speech is never cut to fit. If a cut scan is unavailable, source timing is retained. Text length alone cannot predict spoken duration. Short source fragments and copied caption text can also be the cause. Counting rewrites require independent source confirmation, high recognition confidence and no contradictory caption or source warning. A sequence of uncertain ASR digits alone never proves counting. Manual scripts are protected.",
            "zh-HK": "一般模式會先移除實測靜音邊位，利用安全空檔，配音起點最多微調 0.5 秒；鏡頭切換只作參考，會按實際對白同保留原聲範圍編排，唔會被固定十二秒分組截走可用時間。完整後備錄音亦會先實測微量調速，再判斷能否採用。OP／ED、原本同時發聲同手動錄音仍受保護。仍然唔夠時間就保留意思精簡譯文，再完整重讀。最多會儲存三個唔同精簡講法，逐個核對意思；第二輪時長重試可以改用另一個已核對講法。若全部候選都被有來源證據嘅語意問題拒絕，會用問題作回饋，從原文重新翻譯一次，再獨立核對；唔會不停保留有問題嘅舊稿。人名清單若只辨識為籠統 Chinese，仍屬口音未確認並可觸發修復。清楚嘅非語言喊聲即使冇譯文，亦會作原聲喊聲保留。最後微量調速通常上限係 5%，最多節省 0.18 秒。只有錄音不超過 2 秒、超時不超過 0.12 秒嘅近似合格短句，先容許累計最多 10%；唔會截斷說話。未能確認畫面邊界就保留來源時間。字數相近唔代表讀出嚟一樣長。來源切得太碎或字幕串入都可能係原因；數數改寫必須有獨立聽寫確認、足夠辨識信心，而且冇字幕矛盾或來源警告；唔會單靠一串低信心數字就判定係數數，手動稿件亦受保護。"
          }
        ],
        "steps": false
      },
      {
        "title": {
          "en": "Complete output versus incomplete preview",
          "zh-HK": "完整成品與未完整預覽"
        },
        "body": [
          {
            "en": "If recovery succeeds, the normal movie is exported. If some dialogue still cannot be delivered, automatic Normal mode saves a clearly named -AniCanto-Preview.mp4 and marks it Preview saved — dubbing incomplete. This is a playable partial result, not a complete or certified dub. The report records missing positions and attempted mechanisms. When every dub line fails and an original audio track is available, that original track is the default preview audio. Original media, recordings and earlier exports are retained. A damaged/unreadable source or failed movie encoding can still prevent any playable export.",
            "zh-HK": "修復成功就輸出正常成品；若仍有對白未能交付，一般模式會保存名稱清楚嘅 -AniCanto-Preview.mp4，標示「預覽已保存・配音未完整」。呢個係可以觀看嘅部分結果，唔係完整或已認證配音。報告會記錄缺聲位置同已試機制。如果所有配音句都失敗，而原裝音軌可用，預覽會預設播放原聲。原片、錄音及舊輸出會保留。如果來源已損壞／無法讀取，或者影片編碼失敗，仍可能無法產生可觀看檔案。"
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
            "en": "Choose English or 香港繁體中文 in Welcome. English applies default Cantonese and English dubbing, the Japanese original audio track, and Cantonese and English subtitles. Review the production settings before starting. A running or resumed job keeps the settings submitted with that job.",
            "zh-HK": "在 Welcome 選 English 或香港繁體中文。英文介面預設提供廣東話及英文配音、日文原聲音軌，以及廣東話與英文字幕；開始前仍可檢視製作設定。已提交或恢復中的工作會沿用該工作的原有設定。"
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
            "zh-HK": "偏好設定亦有介面語言選項，位置喺左邊「專案／成品管理」下方；喺度換語言會保留製作語言設定。新流程紀錄用新介面語言，舊紀錄同第三方／模型原始紀錄保留原文。主題顏色會套用到工作區、選單同面板；Welcome 同關閉預覽畫面會沿用同一主題助手身份。"
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
          "en": "Remove downloaded models",
          "zh-HK": "移除已下載模型"
        },
        "body": [
          {
            "en": "In Welcome, choose Remove all downloaded models. Review the listed folders and confirm removal. This removes app-owned model downloads and partial downloads; source videos, finished movies and project data are retained. Models must be downloaded again before the next conversion.",
            "zh-HK": "在 Welcome 按「移除所有已下載模型」，檢視列出的資料夾後確認。這會清除程式管理的模型及未完成下載，保留原片、成品及專案資料；下次轉換前需要重新下載模型。"
          },
          {
            "en": "Remove models & runtimes, inside download management, also removes the downloaded execution environments. If the app needs to exit to finish cleanup, allow it to close and launch again when you next need it. The portable app file and its downloaded working data occupy different locations.",
            "zh-HK": "下載管理內的「移除模型及執行環境」亦會移除已下載的執行元件。如程式需要退出才能完成清理，請讓它關閉，下次使用時再啟動。Portable 程式檔與下載的工作資料會存放於不同位置。"
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
            "en": "Drag the handle on the left of a video, or use its up/down arrows, to reorder the queue. The same order is saved in the video list, Work queue and Projects and exports. A running video continues; later videos follow the new order. On a focused handle, Arrow Up/Down moves one position; Escape cancels a drag. In Basic mode, Start conversion processes all waiting episodes in queue order, one at a time. Resume continues the paused episode with its saved settings, then starts the remaining waiting episodes. When the selected episode is complete but others are waiting, Start remaining videos skips completed outputs. Pause & save stops automatic continuation. Failed episodes keep their error for review while the remaining queue continues; they are not repeatedly retried. In Expert mode, Start conversion processes only the selected episode; use Work queue or Projects and exports → Start all waiting for a batch. Produce a new version is shown when no waiting episodes remain.",
            "zh-HK": "拖動影片左邊嘅把手，或用上下箭嘴調整次序；影片清單、工作佇列同專案／成品管理會同步保存。正在處理嘅影片會繼續，其餘按新次序處理。把手獲焦點時可用上下方向鍵逐格移動；Escape 取消拖動。基本模式按「開始轉換」會依清單順序逐集處理全部等待影片。「繼續處理」會先沿用儲存設定恢復暫停的影片，再處理其餘等待影片。如所選影片已完成而其他影片仍等待，會顯示「開始餘下影片」，跳過已有成品。「暫停並保存」會停止自動接續；失敗影片會保留錯誤供檢查，其他影片繼續處理，不會反覆重試失敗項目。專家模式的「開始轉換」只處理所選影片，批量處理請到工作佇列或專案／成品管理按「開始全部待處理」。沒有餘下等待影片時才顯示「製作新版」。"
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
            "en": "Uses each line’s Japanese source voice as an independent reference. It runs targeted checks for missing speech, names and language, and preserves detected Japanese OP / ED. It avoids full speaker grouping and visual character analysis. Local checks improve coverage but do not certify every word, accent or speaker identity.",
            "zh-HK": "逐句使用日文原聲作獨立模仿參考，局部檢查缺聲、人名及語言，並保留偵測到的日文 OP／ED。此模式不進行完整聲紋分組或角色影像分析。局部檢查可改善完整性，但不代表逐字、口音或角色身分認證。"
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
            "zh-HK": "左邊導覽可選剪輯、角色、校對報告、製作匯出、工作佇列、終端機、製作預設、模型中心、偏好設定及專案／成品管理。影片清單選專案；右邊檢查器有製作、對白、畫面及混音。上方的面板圖示可獨立開關導覽、影片清單及檢查器。"
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
            "en": "Automatic subtitles + Japanese audio first looks for a matching external subtitle file, then an embedded text subtitle track. If neither exists, it automatically checks the lower part of the video for burned-in captions. No manual subtitle rectangle is needed. Japanese speech is recognised first; OCR adds time-matched evidence for names and meaning before the final Cantonese / English translation. OCR must not remove dialogue that was heard in Japanese. If the picture contains no readable captions, processing continues using Japanese speech. The terminal and input-source record identify the actual source and automatically detected region.",
            "zh-HK": "「自動字幕＋日文原聲」會先搵同名外掛字幕，再檢查內嵌文字字幕軌；兩者都冇就自動檢查畫面下方嘅硬字幕，唔需要手動畫框。先辨識日文原聲，再將相應時間嘅 OCR 文字作為人名同意思嘅參考，最後整合翻譯廣東話／英文。OCR 漏字唔應該刪走已聽到嘅日文對白。畫面本身冇可辨識字幕時，會繼續用日文語音；終端機及輸入來源紀錄會列明實際來源同自動偵測範圍。"
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
            "zh-HK": "成功匯出後，「播放成品」會在預覽開啟完成影片，「顯示檔案」會顯示位置。「輸出資料夾」控制新成品存放位置。專案／成品管理保留集數、狀態、累計時間及可用輸出；已有版本會保留，除非另行透過相關清理操作移除。"
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
            "zh-HK": "可按影片清單的 ×，或專案／成品管理的垃圾桶；確認專案名稱後移除。這會清除該專案的處理資料，保留原片、完成成品及下載模型。正在執行的工作須先暫停。「返回預覽」可於兩種介面模式返回剪輯頁。"
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
            "zh-HK": "「專案／成品管理 → 清理暫存」會直接掃描 App 自己嘅儲存目錄，包括舊預覽副本、套件／編譯快取，同冇連結到清單嘅中斷工作。顯示 0 只代表掃描分類入面冇可移除項目，唔代表整個資料目錄係空。未連結工作可能仍有有用錄音，移除前應檢視選擇。清理暫存會保留已下載模型、執行環境、原片同成品，並顯示掃描、刪除進度同最後釋放容量；掃描時唔會刪嘢。"
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

export function chapters(language){const lang=language==='en'?'en':'zh-HK';return CHAPTERS.map((c,i)=>({...c,number:i+1,title:c.title[lang],summary:c.summary[lang],sections:c.sections.map(s=>({title:s.title[lang],body:s.body.map(p=>p[lang]),steps:s.steps}))}));}
export function searchChapters(rows,query){const words=String(query).normalize('NFKC').toLocaleLowerCase().trim().split(/\s+/u).filter(Boolean);return rows.filter(c=>{const text=[c.title,c.summary,...c.sections.flatMap(s=>[s.title,...s.body])].join(' ').normalize('NFKC').toLocaleLowerCase();return words.every(w=>text.includes(w));});}
export function articleHTML(c){return `<div class="help-eyebrow">ANICANTO / ${String(c.number).padStart(2,'0')}</div><h1 id="help-article-title">${esc(c.title)}</h1><p class="help-lead">${esc(c.summary)}</p>${c.sections.map(s=>`<section class="help-section"><h2>${esc(s.title)}</h2>${s.steps?`<ol>${s.body.map(p=>`<li>${esc(p)}</li>`).join('')}</ol>`:s.body.map(p=>`<p>${esc(p)}</p>`).join('')}</section>`).join('')}`;}
