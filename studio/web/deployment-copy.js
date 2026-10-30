// Deployment and scoped production reset. Backend receipts remain authoritative.
const copy={
 checking:['Checking local models…','正在檢查本機模型…','正在检查本机模型…','ローカルモデルを確認中…'],
 reset:['Reset production parameters','重設製作參數','重置制作参数','制作パラメーターを初期化'],
 resetDone:['Production parameters reset. Saved jobs and recordings are kept.','已重設製作參數；已保存工作同錄音會保留。','已重置制作参数；已保存任务和录音会保留。','制作パラメーターを初期化しました。保存済みのジョブと録音は保持します。'],
 remove:['Remove all models…','移除所有模型…','移除所有模型…','すべてのモデルを削除…'],
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
