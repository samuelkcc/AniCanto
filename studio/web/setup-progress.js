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
