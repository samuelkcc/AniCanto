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
 await p.locator('[data-action=page][data-value=models]').click();await p.waitForSelector('.voice-library',{state:'attached'});
 await p.locator('[data-action=change-models]').click();await p.waitForSelector('#switch-voice-list input[data-role=voice]');await p.waitForFunction(()=>!document.querySelector('[data-action=confirm-switch]').disabled);
 const listed=await p.locator('#switch-voice-list input[data-role=voice]').evaluateAll(options=>options.map(o=>o.value));
 const voices=await p.evaluate(()=>window.qa.choices.filter(r=>r.category==='voice'));
 const voiceID=engine=>voices.find(r=>r.engine===engine).id;
 const choose=async engine=>p.locator(`#switch-voice-list input[data-role=voice][value="${voiceID(engine)}"]`).check();
 assert.equal(listed.length,voices.length,'The voice list must show every supported TTS variant');
 assert(voices.some(r=>r.engine==='drama3')&&voices.some(r=>r.engine==='gpt-sovits-v2'));
 assert.equal(await p.locator('#switch-voice-list .model-choice-dot').count(),0,'No coloured status dots in the voice list');
 assert((await p.locator('#switch-voice-list').innerText()).includes(lang==='en'?'Download':'下載'));
 assert((await p.locator('#switch-voice-list').innerText()).includes('GB'),'Missing variants show download size and memory');
 assert((await p.locator('#switch-memory').innerText()).includes('64.0 GB'));
 assert.equal(await p.locator('.switch-other-models').getAttribute('open'),null,'Other model roles start collapsed');
 assert(await p.locator('#switch-memory').evaluate(el=>getComputedStyle(el).position==='sticky'),'Memory panel stays pinned while browsing models');
 await p.evaluate(()=>{window.qa.hardware={platform:'windows',memoryGB:64,backend:'cuda',acceleratorMemoryGB:24};window.qa.memoryBudget=19.2;});
 await choose('gpt-sovits-v2');await p.waitForTimeout(70);
 const discrete=await p.locator('.model-memory').innerText();assert(discrete.includes('24.0 GB')&&discrete.includes('64.0 GB'),discrete);
 await p.screenshot({path:path.resolve(`.build/shared-studio-qa/${lang}-model-memory.png`)});
 await p.evaluate(()=>{window.qa.hardware={platform:'windows',memoryGB:64,backend:'rocm',acceleratorMemoryGB:16};window.qa.memoryBudget=12.8;});
 await choose('drama3');await p.waitForTimeout(70);
 const amd=await p.locator('.model-memory').innerText();assert(amd.includes('16.0 GB')&&amd.includes('64.0 GB'),amd);
 await p.evaluate(()=>{window.qa.hardware={platform:'windows',memoryGB:32,backend:'cpu',displayAdapters:[{vendorId:0x8086,name:'Intel UHD Graphics',dedicatedMemoryGB:0.5}]};window.qa.memoryBudget=24;});
 await choose('gpt-sovits-v2');await p.waitForTimeout(70);
 const integrated=await p.locator('.model-memory').innerText();assert(integrated.includes('32.0 GB')&&!integrated.includes('24.0 GB VRAM'),integrated);
 await p.evaluate(()=>{window.qa.hardware={platform:'windows',memoryGB:32,backend:'cpu',displayAdapters:[{vendorId:0x1002,name:'AMD Radeon RX 6800',dedicatedMemoryGB:16}]};window.qa.memoryBudget=24;});
 await choose('drama3');await p.waitForTimeout(70);
 const inactiveAmd=await p.locator('.model-memory').innerText();assert(inactiveAmd.includes('32.0 GB')&&inactiveAmd.includes('16.0 GB')&&inactiveAmd.includes(lang==='en'?'GPU inference unavailable':'模型推理'),inactiveAmd);
 await p.evaluate(()=>{window.qa.hardware={platform:'macos',memoryGB:64,backend:'metal'};window.qa.memoryBudget=56;});
 await choose('gpt-sovits-v2');await p.waitForTimeout(70);await choose('drama3');await p.waitForFunction(()=>!document.querySelector('[data-action=confirm-switch]').disabled);
 await p.evaluate(()=>{window.qa.drawer=document.querySelector('.drawer');window.qa.voiceList=document.querySelector('#switch-voice-list');window.qa.lag=true;window.qa.planRenders=0;new MutationObserver(()=>window.qa.planRenders++).observe(document.querySelector('#drawer-root'),{childList:true});});
 await choose('gpt-sovits-v2');assert(await p.locator('[data-action=confirm-switch]').isDisabled());
 await choose('drama3');await p.waitForTimeout(450);
 assert(await p.evaluate(()=>document.querySelector('.drawer')===window.qa.drawer));assert(await p.evaluate(()=>document.querySelector('#switch-voice-list')===window.qa.voiceList));assert.equal(await p.evaluate(()=>window.qa.planRenders),0);
 assert.equal(await p.locator('#switch-voice-list input[data-role=voice]:checked').inputValue(),voiceID('drama3'));
 // A response arriving after cancellation must not recreate any drawer.
 await choose('gpt-sovits-v2');await p.locator('.drawer [data-action=close-drawer]').last().click();await p.waitForTimeout(420);assert.equal(await p.locator('.drawer').count(),0);
 await p.evaluate(()=>window.qa.lag=false);await p.locator('[data-action=change-models]').click();await p.waitForSelector('#switch-voice-list');await p.waitForFunction(()=>!document.querySelector('[data-action=confirm-switch]').disabled);
 // Failure exposes a retry action and leaves the same controls available.
 await p.evaluate(()=>window.qa.planFailure=true);await choose('gpt-sovits-v2');await p.waitForSelector('[data-action=retry-model-plan]');await p.locator('[data-action=retry-model-plan]').click();await p.waitForFunction(()=>!document.querySelector('[data-action=confirm-switch]').disabled);
 await p.evaluate(()=>{window.qa.hardware={platform:'macos',memoryGB:32,backend:'metal'};window.qa.memoryBudget=24;});
 await choose('drama3');
 await p.waitForFunction(()=>document.querySelector('.model-memory .warning'));
 assert(await p.locator('[data-action=confirm-switch]').isEnabled(),'An over-budget model remains selectable with a warning');
 const downloadOnly=p.locator(`[data-action=download-selected-voice][data-value="${voiceID('drama3')}"]`);
 assert(await downloadOnly.isEnabled(),'Memory pressure must still permit download-only');
 await downloadOnly.click();
 assert.equal((await p.evaluate(()=>window.qa.calls.filter(c=>c.name==='studio_start').at(-1))).args.op,'maintain-model');
 assert.equal(await p.locator('.welcome').count(),0,'Downloading another voice model jumped back to Welcome');
 await p.evaluate(async()=>{window.qa.installed=true;await window.qa.listeners.get('studio-finished')({payload:{runID:'repair-run',action:'model-maintenance',code:0,paused:false}});});
 await p.waitForSelector('[data-action=change-models]:not([disabled])');
 await p.locator('[data-action=change-models]').click();await p.waitForSelector('#switch-voice-list');
 assert((await p.locator('#switch-voice-list').innerText()).includes(lang==='en'?'Downloaded':'已下載'),'Installed model shows a textual status');
 await choose('gpt-sovits-v2');await p.waitForFunction(()=>!document.querySelector('[data-action=confirm-switch]').disabled);
 await p.locator('[data-action=confirm-switch]').click();await p.waitForSelector('.studio.expert .model-maintenance');
 assert.equal(await p.locator('.welcome').count(),0,'Expert model switch jumped back to Welcome');
 assert.equal(errors.length,0,errors.join('\n'));results.push({language:lang,stableDrawer:true,modelStatusesWithoutDots:true,pinnedMemoryPanel:true,stalePlansIgnored:true,cancelStaysClosed:true,retryWorks:true,downloadWithoutSwitching:true});await p.close();
 }
 await browser.close();fs.writeFileSync('.build/model-ui-acceptance.json',JSON.stringify({nativeGPUInference:false,results},null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
