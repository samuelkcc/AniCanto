// Use backend verification reasons. Downloaded weights alone never authorize conversion.
const copy={
 en:{verify:'Finish setup verification',missing:'Some required files are missing. Verified downloads will be reused.',verifyHint:'Files are present. Complete model and speech verification before starting.'},
 'zh-HK':{verify:'完成啟動驗證',missing:'仍缺少必要檔案；已驗證下載會重用。',verifyHint:'檔案已齊備；完成模型及語音驗證後即可開始。'},
 'zh-CN':{verify:'完成启动验证',missing:'仍缺少必要文件；已验证的下载会复用。',verifyHint:'文件已齐备；完成模型和语音验证后即可开始。'},
 ja:{verify:'起動確認を完了',missing:'必要なファイルが不足しています。確認済みのダウンロードは再利用します。',verifyHint:'ファイルは揃っています。モデルと音声の確認を完了すると開始できます。'}
};
const text=language=>copy[language]||copy.en;
export function setupActionLabel(plan,language){return plan?.setupReady!==true&&plan?.setupStatus?.filesPresent===true?text(language).verify:'Download & prepare';}
export function setupReadinessHint(plan,language){if(plan?.setupReady===true||!plan?.setupStatus)return '';return plan.setupStatus.filesPresent?text(language).verifyHint:text(language).missing;}
