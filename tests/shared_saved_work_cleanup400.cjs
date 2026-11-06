// Exercise the real cleanup drawer with isolated, synthetic RPC data.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const web=path.resolve('studio/web');
const server=http.createServer((req,res)=>{const file=path.resolve(web,'.'+decodeURIComponent(req.url.split('?')[0]==='/'?'/index.html':req.url.split('?')[0]));if(!file.startsWith(web+path.sep)){res.writeHead(403);res.end();return;}fs.readFile(file,(err,data)=>{if(err){res.writeHead(404);res.end();return;}res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html');res.end(data);});});
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER});const results=[];
try{for(const language of ['en','zh-HK','zh-CN','ja']){
 const page=await browser.newPage({viewport:{width:1440,height:960}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(({language})=>{
  const state={language,mode:'basic',queue:[],selected:null,settings:{ttsBackend:'drama3',selectedEngines:['drama3'],dubLanguages:['yue'],subtitleModes:['yue'],animeTheme:'studio'},ui:{},useTermsAccepted:true,storage:'/fixture',platform:'darwin'};
  const f=window.fixture={calls:[],removed:false};
  window.__TAURI__={core:{invoke:async(name,args={})=>{
   if(name==='studio_status')return {runtimeReady:true,running:null};
   if(name==='studio_rpc'){
    if(args.op==='state')return structuredClone(state);
    if(args.op==='configure'){Object.assign(state,args.params);return structuredClone(state);}
    if(args.op==='plan')return {setupReady:true,canDeployModels:true,engine:'drama3',downloads:[],roles:{},modelDownloadBytes:0};
    if(args.op==='models')return [];
    if(args.op==='speech-library')return {clips:[],projects:[],draft:{},defaultTextModel:null};
    if(args.op==='project-cache-plan')return {token:'cache400',bytes:10,count:1,files:[{path:'cache/uv/a',bytes:10}],groups:{'package-cache':10},orphanWork:[{id:'orphan',title:'Interrupted fixture',bytes:30,files:[{}],canRemove:true}],savedWorkCleanup:{token:'saved400',canRemove:true,count:3,bytes:1000,jobCount:1,separationCount:1}};
    if(args.op==='clear-project-cache'){f.calls.push(args.params);f.removed=true;return {complete:true,freedBytes:1010,removedCount:4,failedCount:0};}
    if(args.op==='project-cache-status')return null;
   }
   throw Error('Unexpected fixture operation '+name+' '+args.op);
  }},event:{listen:async()=>()=>{}},window:{getCurrentWindow:()=>({close:async()=>{}})}};
 },{language});
 await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForSelector('[data-action=enter]');await page.locator('[data-action=enter]').click();await page.locator('[data-action=projects]').click();await page.locator('[data-action=clear-cache]').click();await page.waitForSelector('#cache-saved-work');
 const bulk=page.locator('#cache-saved-work');assert.equal(await bulk.isChecked(),false);assert.equal((await page.evaluate(()=>window.fixture.calls)).length,0);
 assert(await page.locator('[data-action=storage-health]').isVisible());
 const expected={en:'Saved desktop work and separation cache','zh-HK':'已儲存工作與分離音軌','zh-CN':'已保存工作与分离音轨',ja:'保存した作業と分離音声'}[language];assert((await page.locator('.drawer').innerText()).includes(expected));
 await bulk.check();assert(await page.locator('[data-cache-orphan]').isDisabled());
 assert((await page.locator('#cache-size').innerText()).includes('KB'));
 await page.locator('[data-action=confirm-clear-cache]').click();await page.waitForSelector('.cache-result');
 const calls=await page.evaluate(()=>window.fixture.calls);assert.equal(calls.length,1);assert.equal(calls[0].savedWorkToken,'saved400');assert.equal(calls[0].token,'cache400');assert.deepEqual(errors,[]);
 results.push({language,explicitOptIn:true,completeStorageLink:true,savedWorkTokenPassed:true,pageErrors:errors});await page.close();
}console.log(JSON.stringify({fixtureOnly:true,results},null,2));}finally{await browser.close();server.close();}})().catch(e=>{console.error(e);server.close();process.exit(1)});
