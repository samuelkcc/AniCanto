const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER});let results=[];
 for(const lang of ['en','zh-HK']){
 const p=await browser.newPage({viewport:{width:1500,height:960},reducedMotion:'reduce'});let errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{
  const listeners=new Map();window.qa={listeners,choices:[],calls:[],lag:false,installed:false,planFailure:false,instantFinish:false,hardware:{platform:'macos',memoryGB:64,backend:'metal'},memoryBudget:56};
  window.__TAURI__={core:{convertFileSrc:x=>'/media?path='+encodeURIComponent(x),invoke:async(name,args={})=>{
   window.qa.calls.push({name,args});
   if(name==='studio_start'){
    if(args.op==='maintain-model'){
     window.qa.installed=false;
     if(window.qa.instantFinish){window.qa.installed=true;await listeners.get('studio-finished')({payload:{runID:'repair-run',action:'model-maintenance',code:0,paused:false}});}
     return {id:'repair-run'};
    }
    return {id:'setup-run'};
   }
   if(name==='studio_rpc'&&args.op==='models')return [{id:'v2ProPlus',title:'GPT-SoVITS V2 Pro Plus',category:'voice',engine:'gpt-sovits-v2',bytes:1303247442,savedBytes:window.qa.installed?1303247442:995593004,installed:window.qa.installed,missingFiles:window.qa.installed?[]:[{path:'voice.pth',expectedBytes:307654438,actualBytes:0}],missingBytes:window.qa.installed?0:307654438}];
   if(name==='studio_rpc'&&args.op==='plan'){
    const selection=args.params,engine=selection?.engine||'drama3',models=selection?.models||{};
    const duration=window.qa.lag?(engine==='gpt-sovits-v2'?350:30):20;await new Promise(r=>setTimeout(r,duration));
    if(window.qa.planFailure){window.qa.planFailure=false;throw Error('plan connection interrupted');}
    const voice=window.qa.choices.find(r=>r.category==='voice'&&r.engine===engine),text=window.qa.choices.find(r=>r.category==='text');
    return {engine,hardware:window.qa.hardware,memoryBudgetGB:window.qa.memoryBudget,systemReserveGB:8,canDeployModels:true,roles:{text:models.text||text?.id,voice:models.voice||voice?.id},downloads:[],modelDownloadBytes:0};
   }
   const response=await fetch('/api',{method:'POST',body:JSON.stringify({name,args})});const data=await response.json();if(data.error)throw Error(data.error);
   if(name==='studio_rpc'&&args.op==='model-choices')window.qa.choices=data.result;return data.result;
  }},event:{listen:async(n,f)=>{listeners.set(n,f);return ()=>{}}}};
 });
 await p.goto('http://127.0.0.1:18732');await p.waitForSelector('#welcome-language');await p.selectOption('#welcome-language',lang);await p.locator('[data-action=mode][data-value=expert]').click();await p.locator('[data-action=enter]').click();await p.waitForSelector('.studio.expert');
 await p.locator('[data-action=page][data-value=models]').click();await p.waitForSelector('[data-action=repair-model]',{state:'attached'});
 await p.locator('[data-action=change-models]').click();await p.waitForSelector('#switch-engine');await p.waitForFunction(()=>!document.querySelector('[data-action=confirm-switch]').disabled);
 const listed=await p.locator('#switch-voice option').evaluateAll(options=>options.map(o=>({id:o.value,label:o.textContent})));
 const voices=await p.evaluate(()=>window.qa.choices.filter(r=>r.category==='voice'));
 assert.equal(listed.length,voices.length,'The voice dropdown must list every supported TTS variant');
 assert(voices.some(r=>r.engine==='drama3')&&voices.some(r=>r.engine==='gpt-sovits-v2'));
 assert(listed.every(row=>row.label.startsWith('🟢 ')||row.label.startsWith('🔴 ')),'Every variant needs a download-status dot');
 assert(listed.some(row=>row.label.includes(lang==='en'?'Download':'下載')&&row.label.includes('GB')),'Missing variants show download size');
 assert((await p.locator('.model-memory').innerText()).includes('64.0 GB'));
 await p.evaluate(()=>{window.qa.hardware={platform:'windows',memoryGB:64,backend:'cuda',acceleratorMemoryGB:24};window.qa.memoryBudget=19.2;});
 await p.selectOption('#switch-engine','gpt-sovits-v2');await p.waitForTimeout(70);
 const discrete=await p.locator('.model-memory').innerText();assert(discrete.includes('24.0 GB')&&discrete.includes('64.0 GB'),discrete);
 await p.evaluate(()=>{window.qa.hardware={platform:'windows',memoryGB:64,backend:'rocm',acceleratorMemoryGB:16};window.qa.memoryBudget=12.8;});
 await p.selectOption('#switch-engine','drama3');await p.waitForTimeout(70);
 const amd=await p.locator('.model-memory').innerText();assert(amd.includes('16.0 GB')&&amd.includes('64.0 GB'),amd);
 await p.evaluate(()=>{window.qa.hardware={platform:'windows',memoryGB:32,backend:'cpu',displayAdapters:[{vendorId:0x8086,name:'Intel UHD Graphics',dedicatedMemoryGB:0.5}]};window.qa.memoryBudget=24;});
 await p.selectOption('#switch-engine','gpt-sovits-v2');await p.waitForTimeout(70);
 const integrated=await p.locator('.model-memory').innerText();assert(integrated.includes('32.0 GB')&&!integrated.includes('24.0 GB VRAM'),integrated);
 await p.evaluate(()=>{window.qa.hardware={platform:'windows',memoryGB:32,backend:'cpu',displayAdapters:[{vendorId:0x1002,name:'AMD Radeon RX 6800',dedicatedMemoryGB:16}]};window.qa.memoryBudget=24;});
 await p.selectOption('#switch-engine','drama3');await p.waitForTimeout(70);
 const inactiveAmd=await p.locator('.model-memory').innerText();assert(inactiveAmd.includes('32.0 GB')&&inactiveAmd.includes('16.0 GB')&&inactiveAmd.includes(lang==='en'?'GPU inference unavailable':'模型推理'),inactiveAmd);
 await p.evaluate(()=>{window.qa.hardware={platform:'macos',memoryGB:64,backend:'metal'};window.qa.memoryBudget=56;});
 await p.selectOption('#switch-engine','gpt-sovits-v2');await p.waitForTimeout(70);await p.selectOption('#switch-engine','drama3');await p.waitForFunction(()=>!document.querySelector('[data-action=confirm-switch]').disabled);
 await p.evaluate(()=>{window.qa.drawer=document.querySelector('.drawer');window.qa.select=document.querySelector('#switch-engine');window.qa.lag=true;window.qa.planRenders=0;new MutationObserver(()=>window.qa.planRenders++).observe(document.querySelector('#drawer-root'),{childList:true});});
 await p.selectOption('#switch-engine','gpt-sovits-v2');assert(await p.locator('[data-action=confirm-switch]').isDisabled());
 await p.selectOption('#switch-engine','drama3');await p.waitForTimeout(450);
 assert(await p.evaluate(()=>document.querySelector('.drawer')===window.qa.drawer));assert(await p.evaluate(()=>document.querySelector('#switch-engine')===window.qa.select));assert.equal(await p.evaluate(()=>window.qa.planRenders),0);
 assert.equal(await p.locator('#switch-engine').inputValue(),'drama3');const engine=await p.locator('#switch-voice option:checked').getAttribute('value');assert((await p.evaluate(()=>window.qa.choices)).some(r=>r.id===engine&&r.engine==='drama3'));
 // A response arriving after cancellation must not recreate any drawer.
 await p.selectOption('#switch-engine','gpt-sovits-v2');await p.locator('.drawer [data-action=close-drawer]').last().click();await p.waitForTimeout(420);assert.equal(await p.locator('.drawer').count(),0);
 await p.evaluate(()=>window.qa.lag=false);await p.locator('[data-action=change-models]').click();await p.waitForSelector('#switch-engine');await p.waitForFunction(()=>!document.querySelector('[data-action=confirm-switch]').disabled);
 // Failure exposes a retry action and leaves the same controls available.
 await p.evaluate(()=>window.qa.planFailure=true);await p.selectOption('#switch-engine','gpt-sovits-v2');await p.waitForSelector('[data-action=retry-model-plan]');await p.locator('[data-action=retry-model-plan]').click();await p.waitForFunction(()=>!document.querySelector('[data-action=confirm-switch]').disabled);
 await p.locator('[data-action=confirm-switch]').click();await p.waitForSelector('.studio.expert .model-maintenance');
 assert.equal(await p.locator('.welcome').count(),0,'Expert model download jumped back to Welcome');
 await p.evaluate(async()=>{await window.qa.listeners.get('studio-finished')({payload:{runID:'setup-run',action:'setup',code:0,paused:false}});});
 await p.waitForSelector('[data-action=repair-model]:not([disabled])',{state:'attached'});
 await p.locator('[data-action=repair-model][data-value=v2ProPlus]').locator('xpath=ancestor::details[1]').evaluate(el=>el.open=true);
 await p.locator('[data-action=repair-model]').click();await p.waitForSelector('[data-action=start-model-maintenance]');await p.locator('[data-action=start-model-maintenance]').click();await p.waitForSelector('.model-maintenance');
 assert.equal(await p.locator('[data-action=change-models]').isDisabled(),true);
 const request=await p.evaluate(()=>window.qa.calls.filter(c=>c.name==='studio_start').at(-1));assert.deepEqual(request.args,{op:'maintain-model',params:{id:'v2ProPlus',mode:'repair'}});
 await p.evaluate(()=>window.qa.listeners.get('studio-event')({payload:{runID:'repair-run',event:{message:'voice.pth',download:{bytesReceived:100,totalBytes:200,state:'downloading'}}}}));await p.waitForFunction(()=>document.querySelector('.model-maintenance .download-fill i')?.getAttribute('style')?.includes('50%'));
 await p.evaluate(async()=>{window.qa.installed=true;await window.qa.listeners.get('studio-finished')({payload:{runID:'repair-run',action:'model-maintenance',code:0,paused:false}});});await p.waitForSelector('[data-action=repair-model]:not([disabled])',{state:'attached'});assert.equal(await p.locator('.model-maintenance').count(),0);
 await p.locator('[data-action=redownload-model][data-value=v2ProPlus]').locator('xpath=ancestor::details[1]').evaluate(el=>el.open=true);
 await p.screenshot({path:path.resolve(`.build/shared-studio-qa/${lang}-model-repair.png`)});
 // Redownload must have a distinct confirmation and a distinct service mode.
 await p.evaluate(()=>{window.qa.instantFinish=true;});await p.locator('[data-action=redownload-model]').click();await p.waitForSelector('[data-action=start-model-maintenance][data-mode=redownload]');await p.locator('[data-action=start-model-maintenance]').click();await p.waitForTimeout(100);
 assert.equal(await p.locator('.model-maintenance').count(),0,'Instant completion left a stale active task');
 const last=await p.evaluate(()=>window.qa.calls.filter(c=>c.name==='studio_start').at(-1));assert.equal(last.args.params.mode,'redownload');
 await p.locator('[data-action=change-models]').click();await p.waitForSelector('#switch-voice');
 await p.evaluate(()=>{window.qa.hardware={platform:'macos',memoryGB:32,backend:'metal'};window.qa.memoryBudget=24;});
 await p.selectOption('#switch-voice',voices.find(r=>r.engine==='drama3').id);
 await p.waitForFunction(()=>document.querySelector('.model-memory .warning'));
 assert(await p.locator('[data-action=confirm-switch]').isDisabled(),'Insufficient memory must prevent switching');
 assert(await p.locator('[data-action=download-selected-voice]').isEnabled(),'Insufficient memory must still permit download-only');
 await p.locator('[data-action=download-selected-voice]').click();
 assert.equal((await p.evaluate(()=>window.qa.calls.filter(c=>c.name==='studio_start').at(-1))).args.op,'maintain-model');
 assert.equal(errors.length,0,errors.join('\n'));results.push({language:lang,stableDrawer:true,stableNativeSelect:true,stalePlansIgnored:true,cancelStaysClosed:true,retryWorks:true,repairProgress:true,redownloadConfirmation:true,instantCompletionHandled:true});await p.close();
 }
 await browser.close();fs.writeFileSync('.build/model-ui-acceptance.json',JSON.stringify({nativeGPUInference:false,results},null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
