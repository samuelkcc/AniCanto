// Keep the core privacy promises aligned with the iPad PrivacyPolicyView.
const COPY={
 en:{title:'Privacy policy',sections:[
  {title:'Processing on your computer',text:'Video recognition, translation, dubbing, subtitles and export are processed on your computer. AniCanto does not upload your videos, recordings, subtitles, transcripts or generated content to the developer or a third-party AI server.'},
  {title:'Network connections',text:'Downloading or repairing models and processing runtimes connects to their file providers. Those providers receive connection information needed for a download, such as your IP address. Model downloads do not include your videos, audio or transcripts. Opening an external project or licence link connects to that site.'},
  {title:'Files, sharing and backups',text:'Imported copies, work in progress, recordings and exports remain in local folders you select or in app-managed storage. Content goes to another app or cloud file provider only when you choose to share, export or save it there. Backups and cloud synchronization follow your computer and account settings.'},
  {title:'Logs and deletion',text:'AniCanto has no advertising tracker or usage analytics SDK and does not automatically send usage logs to the developer. Processing logs stay on your computer unless you choose to share them. You can remove projects and downloaded models in the app; copies saved elsewhere must be removed at their destination.'},
  {title:'Questions and updates',text:'For privacy questions, use the AniCanto GitHub project link above. This policy will be updated if data handling changes. Effective date: 23 October 2026.'}
 ]},
 'zh-HK':{title:'私隱政策',sections:[
  {title:'電腦本機處理',text:'影片辨識、翻譯、配音、字幕及匯出均在你的電腦上進行。AniCanto 不會將你的影片、錄音、字幕、文字稿或生成內容上載到開發者或第三方 AI 伺服器。'},
  {title:'網絡連線',text:'下載或修復模型及處理環境，需要連接檔案供應商；對方會接收下載所需的連線資料，例如 IP 位址。模型下載不包含你的影片、聲音或文字稿。開啟外部項目或授權連結時，亦會連接相關網站。'},
  {title:'檔案、分享與備份',text:'匯入副本、工作進度、錄音及成品保存在你選擇的本機資料夾或 App 管理的儲存空間。只有在你主動分享、匯出或另存到其他 App 或雲端檔案服務時，內容才會交給該服務。備份及雲端同步依照你的電腦和帳戶設定運作。'},
  {title:'記錄與刪除',text:'AniCanto 不包含廣告追蹤或使用分析 SDK，亦不會自動向開發者傳送使用記錄。處理紀錄保存在你的電腦，除非你自行分享。你可在 App 內移除專案及下載模型；已另存到其他位置的副本須在該位置另行刪除。'},
  {title:'聯絡與更新',text:'如對私隱有疑問，可使用上方的 AniCanto GitHub 項目連結聯絡我們。如資料處理方式有更改，本政策亦會更新。生效日期：2026 年 10 月 23 日。'}
 ]},
 'zh-CN':{title:'隐私政策',sections:[
  {title:'在电脑本地处理',text:'视频识别、翻译、配音、字幕和导出均在你的电脑上进行。AniCanto 不会将你的视频、录音、字幕、文字稿或生成内容上传到开发者或第三方 AI 服务器。'},
  {title:'网络连接',text:'下载或修复模型及处理环境需要连接文件提供商；对方会收到下载所需的连接信息，例如 IP 地址。模型下载不包含你的视频、音频或文字稿。打开外部项目或许可链接时，也会连接相应网站。'},
  {title:'文件、分享与备份',text:'导入副本、工作进度、录音和成品保存在你选择的本地文件夹或应用管理的存储空间。只有在你主动分享、导出或另存到其他应用或云文件服务时，内容才会交给该服务。备份和云同步遵循你的电脑和账户设置。'},
  {title:'日志与删除',text:'AniCanto 不包含广告跟踪或使用分析 SDK，也不会自动向开发者发送使用日志。处理日志保存在你的电脑，除非你自行分享。你可以在应用内移除项目和下载的模型；已保存到其他位置的副本需要在那里另行删除。'},
  {title:'联系与更新',text:'如有隐私疑问，可以使用上方的 AniCanto GitHub 项目链接联系我们。如果数据处理方式改变，本政策也会更新。生效日期：2026 年 10 月 23 日。'}
 ]},
 ja:{title:'プライバシーポリシー',sections:[
  {title:'パソコン内での処理',text:'動画の認識、翻訳、吹き替え、字幕作成、書き出しはパソコン内で行います。AniCanto は動画、録音、字幕、文字起こし、生成コンテンツを開発者や第三者の AI サーバーにアップロードしません。'},
  {title:'ネットワーク接続',text:'モデルや処理環境のダウンロード・修復時はファイル提供元に接続します。提供元には IP アドレスなど、ダウンロードに必要な接続情報が渡ります。動画、音声、文字起こしはモデルのダウンロードに含まれません。外部のプロジェクト・ライセンスリンクを開いた場合も、そのサイトに接続します。'},
  {title:'ファイル、共有、バックアップ',text:'読み込んだコピー、作業データ、録音、完成品は、選択したローカルフォルダーまたはアプリの管理領域に保存されます。別のアプリやクラウドストレージには、共有、書き出し、保存を自分で選んだ場合にのみ渡されます。バックアップやクラウド同期はパソコンとアカウントの設定に従います。'},
  {title:'ログと削除',text:'AniCanto には広告トラッカーや利用状況分析 SDK は含まれず、利用ログを開発者に自動送信しません。処理ログは自分で共有しない限りパソコン内に残ります。アプリ内でプロジェクトやダウンロードしたモデルを削除できます。他の場所に保存したコピーは、その場所で別途削除してください。'},
  {title:'お問い合わせと更新',text:'プライバシーに関するお問い合わせには、上記の AniCanto GitHub プロジェクトリンクをご利用ください。データの取り扱いが変わった場合は本ポリシーを更新します。発効日：2026 年 10 月 23 日。'}
 ]}
};
export function privacyCopy(language){return COPY[language]||COPY.en;}
