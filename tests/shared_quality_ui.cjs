const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
const root=path.resolve('.'),out=path.join(root,'.build/maintenance/quality-ui');fs.mkdirSync(out,{recursive:true});
const plans=JSON.parse(execFileSync('python3',['-c',`import sys,json
sys.path[:0]=['Resources','windows']
import studio_core,native_setup
rows=json.load(open('Resources/model-options.json'))
out={}
for key,ram,plat,vram in [('mac64',64,'macos',0),('mac16',16,'macos',0),('win16',32,'windows',16),('win8',32,'windows',8)]:
 h=dict(platform=plat,architecture='aarch64' if plat=='macos' else 'x86_64',memoryGB=ram,backend='metal' if plat=='macos' else 'cuda',acceleratorBudgetGB=ram*.75,acceleratorMemoryGB=vram,nativeWorkflowVersion=1)
 out[key]=studio_core.call('deployment',hardware=h,models=rows if plat=='macos' else native_setup.catalog())
out['windowsModels']=native_setup.catalog()
print(json.dumps(out))`],{maxBuffer:4000000}));
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CANTOSYNC_QA_BROWSER?{executablePath:process.env.CANTOSYNC_QA_BROWSER}:{})}),results=[];
 for(const lang of ['en','zh-HK'])for(const key of ['mac64','mac16','win16','win8']){
  const p=await browser.newPage({viewport:{width:1500,height:1000}}),errors=[],started=[];let ready=key!=='win16';p.on('pageerror',e=>errors.push(e.message));
  await p.exposeBinding('nativeFixture',async(_ctx,name,args)=>{
   if(name==='studio_status')return {runtimeReady:ready,running:null};
   if(name==='studio_bootstrap'){ready=true;return {id:'fixture-bootstrap'};}
   if(name==='studio_start'){started.push(args.params);return {id:'fixture-models'};}
   if(name==='studio_rpc'&&args.op==='plan')return plans[key];
   if(name==='studio_rpc'&&args.op==='model-choices'&&key.startsWith('win'))return plans.windowsModels;
   if(name==='studio_rpc'&&args.op==='state'){
    const data=await fetch('http://127.0.0.1:18732/api',{method:'POST',body:JSON.stringify({name,args})}).then(r=>r.json());data.result.language=lang;return data.result;
   }
   const response=await fetch('http://127.0.0.1:18732/api',{method:'POST',body:JSON.stringify({name,args})}).then(r=>r.json());if(response.error)throw Error(response.error);return response.result;
  });
  await p.addInitScript(()=>{const listeners=new Map();window._qualityEmit=(name,payload)=>listeners.get(name)?.({payload});window.__TAURI__={core:{invoke:(name,args={})=>window.nativeFixture(name,args)},event:{listen:async(name,fn)=>{listeners.set(name,fn);return()=>listeners.delete(name)}},window:{getCurrentWindow:()=>({close:async()=>{}})}};});
  await p.goto('http://127.0.0.1:18732/');await p.waitForSelector('.quality-card',{state:'attached'});await p.selectOption('#welcome-language',lang);await p.locator('#setup-details').evaluate(el=>el.open=true);await p.waitForTimeout(100);
  await p.waitForSelector('.quality-card');assert.equal(await p.locator('.quality-card').count(),2);assert(!(await p.locator('#setup-content').innerText()).includes('drama3-small'));
  if(key==='mac64'){await p.evaluate(()=>scrollTo(0,0));await p.screenshot({path:path.join(out,'mac64-setup-'+lang+'.png'),fullPage:true});}
  assert(!(await p.locator('.quality-options').innerText()).includes('Qwen 2B'));assert.equal(await p.locator('.quality-accent-note').count(),2);assert.match(await p.locator('.quality-accent-note').first().innerText(),lang==='en'?/Hong Kong Cantonese accent/:/香港廣東話口音/);assert.equal(await p.locator('.quality-accent-note').first().evaluate(e=>getComputedStyle(e).fontSize),'12px');
  assert(!/[（()）]/.test(await p.locator('.quality-accent-note').allTextContents().then(x=>x.join(''))));
  assert.equal(await p.locator('.quality-expectation').count(),1);
  assert((await p.locator('.quality-expectation').innerText()).length<(lang==='en'?160:60));
  assert.equal(await p.locator('.quality-card').first().locator('small').count(),3,'No repeated quality blurb or empty recognition label');
  await p.locator('#quality-hardware-details > summary').click();
  assert(await p.locator('#quality-hardware-details').evaluate(e=>e.open));
  await p.locator('#download-management > summary').click();
  assert.equal(await p.locator('[data-action=cleanup-models]').count(),1);
  assert(await p.locator('[data-action=cleanup-models]').isVisible());
  assert(!(await p.locator('#download-management > summary').innerText()).includes('0 MB'));
  assert(!(await p.locator('#download-details > summary').allTextContents()).some(s=>s.includes('0 MB')));
  assert(!await p.locator('[data-action=cleanup-all]').isVisible(),'Runtime cleanup should be collapsed');
  const high=p.locator('[data-action=quality-preset][data-value=quality]');assert.equal(await high.isDisabled(),!['mac64','win16'].includes(key));
  if(!await p.locator('#use-terms-checkbox').isChecked())await p.locator('#use-terms-checkbox').check();await p.waitForTimeout(100);const setup=p.locator('[data-action=setup]');assert.equal(await setup.isDisabled(),['mac16','win8'].includes(key),key+' '+lang+' '+await p.locator('#setup-content').innerText());
  if(key==='win16'){
   await p.locator('[data-action=change-models]').first().click();await p.waitForSelector('.model-memory-pool');
   assert.equal(await p.locator('.model-memory-pool').count(),2,'Dedicated GPU must show separate RAM and VRAM bars');
   assert.match(await p.locator('.model-memory-pool').first().innerText(),/22\.0 \/ 32\.0 GB/);
   assert.match(await p.locator('.model-memory-pool').last().innerText(),/16\.0 GB/);
   await p.waitForTimeout(400);await p.screenshot({path:path.join(out,'win16-model-switch-'+lang+'.png')});
   await p.locator('[data-action=close-drawer]').first().click();await p.waitForTimeout(400);
   // Screenshot capture can leave Chromium's Web Animation unfinished in the
   // fixture; clear that overlay before testing the independent setup action.
   await p.evaluate(()=>document.querySelector('#drawer-root').replaceChildren());await setup.click();
   await p.evaluate(()=>window._qualityEmit('studio-finished',{runID:'fixture-bootstrap',code:0,paused:false}));
   await p.waitForFunction(()=>document.querySelector('.download-status'));
   assert.equal(started.length,1);assert.equal(started[0].engine,'drama3');assert.equal(started[0].models.text,'qwen3.5:9b');assert.equal(started[0].models.voice,'drama3-native-q2');
  }
  assert.deepEqual(errors,[]);await p.screenshot({path:path.join(out,key+'-'+lang+'.png'),fullPage:true});
  results.push({hardware:key,language:lang,cards:2,memoryGuard:true,bootstrapChoiceRetained:key==='win16'});await p.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
