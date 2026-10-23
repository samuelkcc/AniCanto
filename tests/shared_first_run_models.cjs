const {chromium}=require('playwright');
const assert=require('node:assert/strict');

(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER});
 const page=await browser.newPage({viewport:{width:1440,height:960},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.addInitScript(()=>{
  const listeners=new Map(),choices=[
   {id:'mlx:qwen3.5-9b:4bit',title:'Qwen 9B',category:'text',engine:'mlx-text',estimatedMemoryGB:9},
   {id:'mlx:qwen3.5-35b-a3b:4bit',title:'Qwen 35B',category:'text',engine:'mlx-text',estimatedMemoryGB:22},
   {id:'drama3-35b-4bit',title:'Drama 3',category:'voice',engine:'drama3',estimatedMemoryGB:23},
   {id:'v2ProPlus',title:'GPT V2 Pro+',category:'voice',engine:'gpt-sovits-v2',estimatedMemoryGB:7},
   {id:'asr-1.7b-8bit',title:'Qwen ASR',category:'asr',engine:'qwen3-asr',estimatedMemoryGB:3},
   {id:'whisper-large-v3',title:'Whisper',category:'speech',engine:'whisper',estimatedMemoryGB:5},
  ];
  window.qa={calls:[],listeners,ready:false};
  window.__TAURI__={core:{convertFileSrc:path=>path,invoke:async(name,args={})=>{
   window.qa.calls.push({name,args});
   if(name==='studio_status')return {runtimeReady:window.qa.ready,running:null};
   if(name==='studio_bootstrap'){window.qa.ready=true;return {id:'bootstrap-run'};}
   if(name==='studio_start')return {id:'setup-run'};
   if(name==='studio_rpc'&&args.op==='model-choices')return choices;
   if(name==='studio_rpc'&&args.op==='plan'){
    const requested=args.params?.models||{},engine=args.params?.engine||'drama3';
    const roles={text:requested.text||'mlx:qwen3.5-9b:4bit',voice:requested.voice||(engine==='drama3'?'drama3-35b-4bit':'v2ProPlus'),
                 asr:requested.asr||'asr-1.7b-8bit',speech:requested.speech||'whisper-large-v3'};
    return {engine,hardware:{platform:'macos',memoryGB:64,backend:'metal'},memoryBudgetGB:56,systemReserveGB:8,
     canDeployModels:true,roles,downloads:[],modelDownloadBytes:0,qualityPresets:[{id:'balanced',available:true,modelSummary:'Drama 3 + Qwen 9B',
      minimumSystemMemoryGB:16,requestedModels:{text:'mlx:qwen3.5-9b:4bit',voice:'drama3-35b-4bit'},plan:{canDeployModels:true}}]};
   }
   const response=await fetch('/api',{method:'POST',body:JSON.stringify({name,args})});const data=await response.json();if(data.error)throw Error(data.error);return data.result;
  }},event:{listen:async(name,fn)=>{listeners.set(name,fn);return ()=>{}}}};
 });
 await page.goto('http://127.0.0.1:18732');await page.waitForSelector('#use-terms-checkbox');
 await page.locator('#use-terms-checkbox').check();
 await page.locator('[data-action=change-models]').first().click();
 await page.waitForSelector('#switch-voice-list input[data-role=voice]');
 assert((await page.locator('.model-memory').innerText()).includes('64.0 GB'));
 await page.locator('.switch-voice-group:has(h4:has-text("GPT V2 Pro+")) input[data-role=voice]').first().check();
 await page.waitForFunction(()=>!document.querySelector('[data-action=confirm-switch]').disabled);
 await page.locator('[data-action=confirm-switch]').click();
 assert.equal(await page.evaluate(()=>window.qa.calls.filter(c=>c.name==='studio_bootstrap').length),1);
 assert.equal(await page.evaluate(()=>window.qa.calls.filter(c=>c.name==='studio_start').length),0);
 await page.evaluate(()=>window.qa.listeners.get('studio-finished')({payload:{runID:'bootstrap-run',action:'bootstrap',code:0,paused:false}}));
 await page.waitForFunction(()=>window.qa.calls.some(c=>c.name==='studio_start'&&c.args.op==='setup'));
 const params=await page.evaluate(()=>window.qa.calls.find(c=>c.name==='studio_start'&&c.args.op==='setup').args.params);
 assert.equal(params.engine,'gpt-sovits-v2');assert.equal(params.models.voice,'v2ProPlus');
 assert.equal(errors.length,0,errors.join('\n'));
 await browser.close();console.log('First-run custom selection and bootstrap handoff passed.');
})().catch(error=>{console.error(error);process.exit(1)});
