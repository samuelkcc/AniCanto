const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const out=path.resolve('.build/package-cleanup-qa/0.24.30');fs.mkdirSync(out,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'}),results=[];
try{for(const language of ['en','zh-HK'])for(const mode of ['models','all']){
 const page=await browser.newPage({viewport:{width:1500,height:1000},reducedMotion:'reduce'}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(({language,mode})=>{
  const f=window.fixture={listeners:new Map(),runtime:true,removed:false,executes:0,bootstraps:0,starts:0,planCalls:0};
  const state={language,mode:'basic',queue:[],selected:null,settings:{ttsBackend:'drama3',selectedEngines:['drama3'],dubLanguages:['yue'],subtitleModes:['yue'],animeTheme:'studio'},ui:{},useTermsAccepted:true,storage:'/fixture',platform:'darwin'};
  window.__TAURI__={core:{invoke:async(name,args={})=>{
   if(name==='studio_status')return {runtimeReady:f.runtime,running:null};
   if(name==='studio_cleanup'){
    const operationID=args.operation;
    if(!args.token){await new Promise(r=>setTimeout(r,150));return {token:'reviewed',bytes:3072,files:3,groups:[{path:'models',bytes:3072}]};}
    f.executes++;await f.listeners.get('studio-cleanup-progress')({payload:{operationID,phase:'deleting',total:3,processed:1,freedBytes:1024}});
    await new Promise(r=>setTimeout(r,1000));f.removed=true;if(mode==='all')f.runtime=false;return {bytesFreed:3072,filesDeleted:3,complete:true,failures:[]};
   }
   if(name==='studio_bootstrap'){f.bootstraps++;f.runtime=true;return {id:'bootstrap'};}
   if(name==='studio_start'){f.starts++;return {id:'models'};}
   if(name==='studio_rpc'){
    if(args.op==='state')return structuredClone(state);
    if(args.op==='configure'){if(args.params.language)state.language=args.params.language;return structuredClone(state);}
    if(args.op==='plan'){f.planCalls++;return {setupReady:!f.removed,canDeployModels:true,engine:'drama3',downloads:[{id:'text',title:'Qwen 9B',bytes:3072,installed:!f.removed}],roles:{text:'text'},modelDownloadBytes:f.removed?3072:0};}
    if(args.op==='models')return f.removed?[]:[{id:'text',title:'Qwen 9B',category:'text',savedBytes:3072,installed:true,selected:true}];
   }
   throw Error('Unexpected fixture call '+name+' '+args.op);
  }},event:{listen:async(name,fn)=>{f.listeners.set(name,fn);return()=>f.listeners.delete(name)}},window:{getCurrentWindow:()=>({close:async()=>{f.closed=true}})}};
 },{language,mode});
 await page.goto('http://127.0.0.1:18732');await page.waitForSelector('[data-action=cleanup-models]',{state:'attached'});
 await page.locator('#setup-details').evaluate(e=>e.open=true);await page.locator('#download-management').evaluate(e=>e.open=true);
 if(mode==='all')await page.locator('#runtime-cleanup').evaluate(e=>e.open=true);
 await page.locator(`[data-action=${mode==='all'?'cleanup-all':'cleanup-models'}]`).click();await page.waitForSelector('[data-action=execute-cleanup]');
 await page.locator('[data-action=execute-cleanup]').click();await page.waitForFunction(()=>document.querySelector('.package-cleanup-progress [role=progressbar]')?.getAttribute('aria-valuenow')==='33');
 await page.keyboard.press('Escape');assert(await page.locator('.package-cleanup-progress').isVisible());assert(await page.locator('.drawer-header [data-action=close-drawer]').isDisabled());
 await page.screenshot({path:path.join(out,`${language}-${mode}-progress.png`)});
 await page.waitForSelector('.cache-result');assert((await page.locator('.cache-result').innerText()).includes('4 KB'));
 assert.equal(await page.evaluate(()=>window.fixture.executes),1);
 await page.locator('.cache-result [data-action=close-drawer]').click();assert(await page.locator('[data-action=setup]').isEnabled());
 assert.equal(await page.evaluate(()=>window.fixture.runtime),mode==='models');
 await page.locator('[data-action=setup]').click();
 if(mode==='all')assert.equal(await page.evaluate(()=>window.fixture.bootstraps),1);else assert.equal(await page.evaluate(()=>window.fixture.starts),1);
 if(mode==='all'){
  await page.evaluate(async()=>{const f=window.fixture;f.runtime=false;await f.listeners.get('studio-event')({payload:{runID:'bootstrap',event:{stage:'錯誤',message:'Cannot start runtime: No such file or directory'}}});await f.listeners.get('studio-finished')({payload:{runID:'bootstrap',action:'runtime',code:1,paused:false}});});
  assert(await page.locator('.setup-failure').isVisible());
  assert((await page.locator('.setup-failure').innerText()).includes(language==='en'?'The local runtime could not start':'本機執行環境啟動唔到'));
  assert(await page.locator('[data-action=setup]').isEnabled());
  await page.locator('[data-action=setup]').click();assert.equal(await page.evaluate(()=>window.fixture.bootstraps),2);
 }
 await page.screenshot({path:path.join(out,`${language}-${mode}-setup.png`)});
 assert.deepEqual(errors,[]);results.push({language,mode,liveProgress:true,accurateFreedBytes:true,setupRestoredWithoutRestart:true,nextSetupStarts:true,errors});await page.close();
}
fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({fixtureOnly:true,results},null,2));console.log(JSON.stringify(results));}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
