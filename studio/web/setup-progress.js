// Only short, recognised descriptions belong in the summary. Full worker
// messages stay in the bounded, plain-text installation log.
export function installationSummary(event={},previous={}){
 const raw=[event.stage,event.message,event.download?.file,event.modelID].filter(Boolean).join(' ');
 let category=previous.category||'Processing environment',model=previous.model||'';
 const known=[[/qwen3[.-]?asr|whisper/i,'Speech recognition',''],[/drama.?3/i,'Voice generation','Drama 3'],[/gpt.?sovits|v2proplus/i,'Voice generation','GPT-SoVITS'],[/cosyvoice/i,'Voice generation','CosyVoice 3'],[/voxcpm/i,'Voice generation','VoxCPM2'],[/wenet|wsyue/i,'Voice generation','WenetSpeech-Yue'],[/qwen3[.-]?5|qwen.*(?:35b|9b)/i,'Text translation','Qwen 3.5'],[/separat|分離/i,'Background separation','']];
 for(const [pattern,label,name] of known)if(pattern.test(raw)){category=label;model=name;break;}
 if(/installing collected packages|collecting |pip |python|runtime|\.whl|extract|解壓/i.test(raw)){category='Processing environment';model='';}
 const state=event.download?.state;
 let phase=event.download?'Downloading model files…':'Preparing components…';
 if(/installing|building wheel|安裝/i.test(raw))phase='Installing components…';
 if(state==='verifying'||event.setupStep==='verify'||event.componentProgress)phase='Verifying downloaded files…';
 if(['connecting','resuming','retrying'].includes(state))phase='Connecting / resuming…';
 if(/error|failed|錯誤/i.test(event.stage||''))phase='Setup needs attention';
 return {category,model,phase};
}
export class InstallationLog{
 constructor(limit=98304){this.limit=limit;this.text='';this.summary={};}
 reset(){this.text='';this.summary={};}
 append(value){const line=String(value??'').replace(/\x1b\[[0-?]*[ -/]*[@-~]/g,'').replace(/\r/g,'');if(!line)return;this.text=(this.text+line+'\n').slice(-this.limit);}
 event(event){this.summary=installationSummary(event,this.summary);if(event.message)this.append(event.message);}
}

// Step clocks are elapsed time, never a fabricated download percentage.
const runtimeSteps={
 'Preparing private Python':['Preparing private Python','準備專用 Python','准备专用 Python','専用 Python を準備中'],
 'Repairing private Python':['Repairing private Python','修復專用 Python','修复专用 Python','専用 Python を修復中'],
 'Detecting the GPU runtime':['Detecting the GPU runtime','偵測 GPU 執行環境','检测 GPU 运行环境','GPU 実行環境を検出中'],
 'Checking installed package versions':['Checking installed package versions','檢查已安裝元件版本','检查已安装组件版本','インストール済みのバージョンを確認中'],
 'Checking installed GPU packages':['Checking installed GPU packages','檢查已安裝 GPU 元件','检查已安装 GPU 组件','GPU パッケージを確認中'],
 'Installing GPU or CPU runtime components':['Installing GPU or CPU runtime components','下載及安裝 GPU／CPU 執行元件','下载及安装 GPU／CPU 运行组件','GPU／CPU 実行環境をインストール中'],
 'Reading verified runtime versions':['Reading verified runtime versions','讀取執行環境版本','读取运行环境版本','実行環境のバージョンを取得中'],
 'Installing missing runtime packages':['Installing missing runtime packages','下載及安裝缺失元件','下载及安装缺失组件','不足するパッケージをインストール中'],
 'Checking runtime imports':['Checking runtime imports','測試元件載入','测试组件加载','パッケージの読み込みを検証中'],
 'Checking damaged package files':['Checking damaged package files','檢查損壞元件檔案','检查损坏组件文件','パッケージの破損を確認中'],
 'Repairing damaged GPU packages':['Repairing damaged GPU packages','修復損壞 GPU 元件','修复损坏 GPU 组件','GPU パッケージを修復中'],
 'Repairing damaged runtime packages':['Repairing damaged runtime packages','修復損壞執行元件','修复损坏运行组件','実行パッケージを修復中'],
 'Verifying installed package versions':['Verifying installed package versions','驗證安裝結果','验证安装结果','インストール結果を検証中'],
 'Checking runtime package inventory':['Checking runtime package inventory','核對執行元件清單','核对运行组件清单','パッケージ一覧を確認中'],
 'Removing unused runtime components':['Removing unused runtime components','移除無須使用嘅執行元件','移除无需使用的运行组件','不要な実行パッケージを削除中']
};
export function runtimeProgressCopy(value,language='en'){
 const i=({'en':0,'zh-HK':1,'zh-CN':2,'ja':3})[language]??0;
 const phase=(runtimeSteps[value.phase]||runtimeSteps['Checking installed package versions'])[i];
 const labels={worker:['Base','基本','基础','基本'],analysis:['Audio analysis','音訊分析','音频分析','音声解析'],asr:['Speech recognition','語音辨識','语音识别','音声認識'],gpt:['GPT-SoVITS','GPT-SoVITS','GPT-SoVITS','GPT-SoVITS']};
 const name=labels[value.name]?.[i]||value.name||'';
 return [name,phase,Math.max(0,Math.floor(Number(value.elapsedSeconds)||0))+' s'].filter(Boolean).join(' · ');
}
