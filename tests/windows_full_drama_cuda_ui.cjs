// Exercise the Windows setup controls against actual shared-core plans.
// The browser fixture does not execute a Windows program or GPU inference.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
const root=path.resolve('.'),out=path.join(root,'.build/drama-cuda-full62/ui');fs.mkdirSync(out,{recursive:true});
const fixtures=JSON.parse(execFileSync('python3',['-B','-c',`import sys,json,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=['Resources','windows']
import native_setup
out={}
with tempfile.TemporaryDirectory() as d,patch.object(native_setup,'data_root',return_value=Path(d)):
 for machine,backend,vram in [('nvidia','cuda',16),('amd','rocm',16),('igpu','cpu',0)]:
  h=dict(platform='windows',architecture='x86_64',memoryGB=32,backend=backend,acceleratorMemoryGB=vram,nativeWorkflowVersion=1,acceleratorName='NVIDIA GeForce RTX 4080 Laptop GPU' if machine=='nvidia' else machine)
  out[machine]={p:native_setup.plan('drama3',hardware=h,drama_backend=p) for p in ('auto','cpu')}
  if machine=='nvidia':out[machine]['cuda']=native_setup.plan('drama3',hardware=h,drama_backend='cuda')
 out['models']=[r for r in native_setup.catalog() if r.get('category') in ('voice','text','asr','speech') and not r.get('retired')]
print(json.dumps(out))`],{maxBuffer:5_000_000}));
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'}),results=[];
 for(const machine of ['nvidia','amd','igpu'])for(const language of ['en','zh-HK','zh-CN','ja']){
  const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[],started=[];let preference='auto';
  page.on('pageerror',e=>errors.push(e.message));
  await page.exposeBinding('nativeFixture',async(_ctx,name,args)=>{
   if(name==='studio_status')return {runtimeReady:true,running:null};
   if(name==='studio_rpc'&&args.op==='plan'){preference=args.params?.dramaBackend||preference;return structuredClone(fixtures[machine][preference]);}
   if(name==='studio_rpc'&&args.op==='model-choices')return fixtures.models;
   if(name==='studio_rpc'&&args.op==='models')return [];
   if(name==='studio_start'){started.push(args.params);return {id:'windows-setup-fixture'};}
   const r=await fetch('http://127.0.0.1:18732/api',{method:'POST',body:JSON.stringify({name,args})}).then(r=>r.json());
   if(r.error)throw Error(r.error);
   if(name==='studio_rpc'&&args.op==='state'){r.result.platform='win32';r.result.language=language;r.result.settings.ttsBackend='drama3';r.result.settings.selectedEngines=['drama3'];r.result.settings.deploymentModels={};}
   return r.result;
  });
  await page.addInitScript(()=>{window.__TAURI__={core:{invoke:(name,args={})=>window.nativeFixture(name,args)},event:{listen:async()=>()=>{}},window:{getCurrentWindow:()=>({close:async()=>{}})}};});
  await page.goto('http://127.0.0.1:18732/');await page.waitForSelector('.quality-card',{state:'attached'});
  await page.locator('#setup-details').evaluate(el=>el.open=true);
  const control=page.locator('[data-setting=drama-deployment-backend][data-scope=setup]');await control.waitFor();
  assert.equal(await control.inputValue(),'auto');
  assert.equal(await control.locator('option[value=cuda]').evaluate(e=>e.disabled),machine!=='nvidia',machine+' '+language+' '+JSON.stringify(fixtures[machine].auto.hardware)+' '+await control.evaluate(e=>e.outerHTML));
  const bars=page.locator('#setup-content .model-memory-pool');assert.equal(await bars.count(),machine==='igpu'?1:2);
  assert.match(await bars.first().innerText(),/22\.0 \/ 32\.0 GB/);
  if(machine==='nvidia'){
   assert.match(await bars.last().innerText(),/12\.0 \/ 16\.0 GB/);
   assert.equal(await page.locator('#setup-content .cuda-download-summary').count(),1);
   await page.screenshot({path:path.join(out,machine+'-'+language+'.png'),fullPage:true});
   await control.selectOption('cpu');await page.waitForFunction(()=>!document.querySelector('#setup-content .cuda-download-summary'));
   assert.match(await bars.last().innerText(),/9\.1 \/ 16\.0 GB|9\.0 \/ 16\.0 GB/);
   await control.selectOption('cuda');await page.waitForSelector('#setup-content .cuda-download-summary');
   // The custom model drawer must preserve the same backend and pools.
   await page.locator('[data-action=change-models]').first().click();
   const switchControl=page.locator('#switch-drama-backend select');await switchControl.waitFor();
   assert.equal(await switchControl.inputValue(),'cuda');
   await switchControl.selectOption('cpu');await page.waitForFunction(()=>!document.querySelector('#switch-plan .cuda-download-summary'));
   assert.equal(await switchControl.inputValue(),'cpu');
   await switchControl.selectOption('cuda');await page.waitForSelector('#switch-plan .cuda-download-summary');
   assert.match(await page.locator('#switch-memory .model-memory-pool').first().innerText(),/22\.0 \/ 32\.0 GB/);
   if(!await page.locator('#use-terms-checkbox').isChecked())await page.locator('#use-terms-checkbox').check();
   await page.locator('[data-action=confirm-switch]').click();
   assert.equal(started.length,1);assert.equal(started[0].dramaBackend,'cuda');assert.equal(started[0].models.voice,'drama3-native-q2');
  }else{
   assert.equal(await page.locator('#setup-content .cuda-download-summary').count(),0);
   await control.selectOption('cpu');await page.waitForTimeout(200);
   assert.equal(await control.inputValue(),'cpu');
   assert.equal(await page.locator('#setup-content .cuda-download-summary').count(),0);
   await page.screenshot({path:path.join(out,machine+'-'+language+'.png'),fullPage:true});
  }
  assert.deepEqual(errors,[]);results.push({machine,language,dualMemoryPools:machine!=='igpu',backendChoiceRetained:true});await page.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify({simulatedUI:true,windowsInferenceTested:false,cases:results},null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
