// Deployment and scoped production reset. Backend receipts remain authoritative.
const copy={
 cleanupPartial:['Cleanup kept files changed during shutdown. Check and repair can continue.','清理已保留關閉期間新增或改動嘅檔案，可以繼續「檢查並修復」。','清理已保留关闭期间新增或改动的文件，可以继续「检查并修复」。','終了時に変更または追加されたファイルを保持しました。確認と修復を続行できます。'],
 captionCovered:['Subtitle content is assigned to dialogue','字幕內容已合併至對白','字幕内容已合并至对白','字幕内容の割り当て先の台詞'],
 captionCoveredNote:['This continuation shares a subtitle with its owner. Open that dialogue to compare its script and recording; no duplicate take is required here.','此延續片段同相鄰對白共用字幕。請開啟所列對白比較台詞同錄音，呢度無須重複配音。','此延续片段与相邻对白共用字幕。请打开所列对白比较台词和录音，此处无需重复配音。','この続きの区間は前後の台詞と字幕を共有します。割り当て先の台詞と録音を確認してください。ここでの重複生成は不要です。'],
 openOwner:['Open assigned dialogue','查看所屬對白','查看所属对白','割り当て先を開く'],
 checking:['Checking local models…','正在檢查本機模型…','正在检查本机模型…','ローカルモデルを確認中…'],
 reset:['Reset production parameters','重設製作參數','重置制作参数','制作パラメーターを初期化'],
 resetDone:['Production parameters reset. Saved jobs and recordings are kept.','已重設製作參數；已保存工作同錄音會保留。','已重置制作参数；已保存任务和录音会保留。','制作パラメーターを初期化しました。保存済みのジョブと録音は保持します。'],
 remove:['Repair / redeploy…','修復／重新部署…','修复／重新部署…','修復／再セットアップ…'],
 maintenance:['Deployment maintenance','部署維護','部署维护','セットアップの管理'],
 repair:['Check and repair','檢查並修復','检查并修复','確認して修復'],
 repairNote:['Keep installed models. Verify components and install only missing or incompatible packages.','保留已下載模型；檢查元件，只安裝缺失或版本不相容嘅部分。','保留已下载模型；检查组件，仅安装缺失或版本不兼容的部分。','モデルを保持し、構成要素を検証します。不足や互換性のないパッケージのみをインストールします。'],
 redeploy:['Reset and redeploy…','完全重新部署…','完全重新部署…','初期化して再セットアップ…'],
 redeployNote:['Review removal of all downloaded models and runtimes first. Videos, recordings, projects and exports stay. On Windows, the app closes before removal; open the EXE again to deploy.','先確認移除所有已下載模型及執行環境；影片、錄音、專案同成品會保留。Windows 會先關閉程式再移除，之後請重新開啟 EXE 部署。','先确认移除所有已下载模型及运行环境；视频、录音、项目和成品保留。Windows 会先关闭程序再移除，随后请重新打开 EXE 部署。','ダウンロード済みモデルと実行環境の削除を先に確認します。動画、録音、プロジェクト、出力は保持します。Windows では終了後に削除するため、EXE を再度開いてセットアップしてください。'],
 local:['Local model setup','本機模型部署','本机模型部署','ローカルモデルの設定'],
 verified:['Verified voice processing','已驗證配音運算方式','已验证配音运算方式','検証済みの音声処理'],
 unverified:['Not verified for this selection','此選擇尚未驗證','此选择尚未验证','この選択は未検証'],
 reuse:['Local files available for reuse','可重用嘅本機檔案','可复用的本机文件','再利用できるローカルファイル'],
 reused:['Verified local models activated. No installation was needed.','已啟用驗證過嘅本機模型，無須重新安裝。','已启用验证过的本机模型，无需重新安装。','検証済みのローカルモデルを有効にしました。再インストールは不要です。'],
 verifySwitch:['Verify & switch','驗證並切換','验证并切换','検証して切り替える'],
 advanced:['Advanced model and hardware choices','進階模型及硬件選擇','高级模型及硬件选择','モデルとハードウェアの詳細設定'],
 fallback:['Why CPU fallback was used','點解使用 CPU 後備','为何使用 CPU 后备','CPU に切り替えた理由']
};
export function deploymentCopy(key,language='en'){return copy[key]?.[{'en':0,'zh-HK':1,'zh-CN':2,'ja':3}[language]??0]||key;}
