const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=path.resolve('.build/shared-studio-qa');fs.mkdirSync(out,{recursive:true});
async function uniqueCommands(page,expert){
 for(const action of ['add','guide','about','switch-mode'])assert.equal(await page.locator(`[data-action=${action}]`).count(),1,`Duplicate or missing ${action}`);
 for(const action of ['export','save','undo','redo'])assert.equal(await page.locator(`[data-action=${action}]`).count(),expert?1:0,`Duplicate ${action}`);
 for(const action of ['pause','start','change-models'])assert((await page.locator(`[data-action=${action}]`).count())<=1,`Duplicate ${action}`);
 assert((await page.locator('[data-action=projects], [data-action=page][data-value=projects]').count())<=1,'Duplicate project management navigation');
 assert(await page.locator('[data-action=add]').isVisible(),'Import is not accessible');
 const add=await page.evaluate(()=>[...document.querySelectorAll('[data-action=add]')].filter(el=>el.getClientRects().length).map(el=>el.getBoundingClientRect().x)[0]);assert(Number.isFinite(add)&&add<400,'Import should be on the left');
}
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CANTOSYNC_QA_BROWSER?{executablePath:process.env.CANTOSYNC_QA_BROWSER}:{})});const results=[];
 for(const lang of ['en','zh-HK']){
  const page=await browser.newPage({viewport:{width:1500,height:960},reducedMotion:'reduce'});const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{
   const listeners=new Map();window.studioFixture={rpc:0,listeners};
   window.__TAURI__={core:{convertFileSrc:p=>'/media?path='+encodeURIComponent(p),invoke:async(name,args={})=>{
    window.studioFixture.rpc++;if(name==='studio_pick'){window.studioFixture.picks=(window.studioFixture.picks||0)+1;return window.studioFixture.pickPaths||[];}const r=await fetch('/api',{method:'POST',body:JSON.stringify({name,args})});const x=await r.json();if(x.error)throw Error(x.error);if(name==='studio_start'&&!window.studioFixture.holdSetup)setTimeout(()=>listeners.get('studio-finished')?.({payload:{runID:'fixture-setup',code:0,paused:false}}),150);return x.result;
   }},event:{listen:async(name,fn)=>{listeners.set(name,fn);return ()=>listeners.delete(name)}},window:{getCurrentWindow:()=>({close:async()=>{}})}};
  });
  await page.goto('http://127.0.0.1:18732');await page.waitForSelector('#welcome-language');
  await page.selectOption('#welcome-language',lang);await page.waitForTimeout(150);
  for(const theme of ['studio','ocean','energy']){
   await page.locator(`[data-action=theme][data-value=${theme}]`).first().click();await page.waitForTimeout(120);
   const cover=page.locator('.welcome-cover img');await cover.evaluate(img=>img.decode());
   assert((await cover.getAttribute('src')).match(new RegExp(`welcome-${theme}-[1-4]\\.png$`)));
   await page.screenshot({path:path.join(out,`${lang}-welcome-${theme}.png`)});
  }
  // Keep the public interface gallery on the app's primary purple theme.
  await page.locator('[data-action=theme][data-value=studio]').first().click();
  await page.locator('[data-action=guide]').click();assert(!(await page.locator('.drawer').innerText()).includes(lang==='en'?'使用教學':'Prepare your studio'));
  await page.locator('.drawer [data-action=close-drawer]').click();
  await page.locator('[data-action=about]').click();await page.waitForSelector('#license-list details');assert.equal(await page.locator('.drawer .welcome-art').count(),0);await page.locator('.drawer [data-action=close-drawer]').click();
  await page.locator('[data-action=mode][data-value=basic]').click();await page.locator('[data-action=enter]').click();await page.waitForSelector('#video');await page.waitForTimeout(400);
  await uniqueCommands(page,false);await page.locator('[data-action=add]').click();assert.equal(await page.evaluate(()=>window.studioFixture.picks),1,'One click opened more than one file picker');
  assert.equal(await page.locator('#basic-progress .milestone').count(),5);const progress=await page.locator('#basic-progress').boundingBox();assert(progress.height<190,`Basic progress wastes vertical space: ${progress.height}`);
  const card=await page.locator('.player-card').boundingBox(),controls=await page.locator('.player-controls').boundingBox();assert(controls.y+controls.height<=card.y+card.height+1,'Playback controls were clipped');
  assert.equal(await page.locator('[data-subtitle]').count(),0);assert.equal(await page.locator('[data-setting=includeOriginal]').count(),0);await page.locator('[data-action=change-models]').click();await page.waitForSelector('[data-setting=switch-engine]');await page.locator('[data-setting=switch-engine]').selectOption('gpt-sovits-v2');await page.waitForSelector('[data-action=confirm-switch]');assert(await page.locator('#remove-old-model').isChecked());await page.evaluate(()=>window.studioFixture.holdSetup=true);await page.locator('[data-action=confirm-switch]').click();await page.waitForSelector('.download-status');await page.evaluate(()=>window.studioFixture.listeners.get('studio-event')({payload:{runID:'fixture-setup',event:{stage:'下載中',message:'Drama3-small · model.gguf',download:{bytesReceived:1000000000,totalBytes:3000000000,bytesPerSecond:25000000}}}}));await page.screenshot({path:path.join(out,`${lang}-downloading.png`)});assert((await page.locator('.download-status').innerText()).includes('1.0 GB'));await page.locator('[data-action=enter]').click();await page.waitForSelector('.studio.basic');await uniqueCommands(page,false);assert.equal(await page.locator('[data-action=pause]').count(),1,'Duplicate pause during processing');await page.evaluate(()=>{window.studioFixture.holdSetup=false;window.studioFixture.listeners.get('studio-finished')({payload:{runID:'fixture-setup',code:0,paused:false}})});await page.waitForSelector('#video');await page.waitForTimeout(300);
  await page.locator('#follow').check();await page.waitForTimeout(100);assert(await page.locator('#follow').isChecked());
  const playback=await page.evaluate(()=>{const v=document.querySelector('#video'),before=window.studioFixture.rpc,start=performance.now();for(let i=0;i<2000;i++)v.dispatchEvent(new Event('timeupdate'));return {sameNode:document.querySelector('#video')===v,rpc:window.studioFixture.rpc-before,ms:performance.now()-start}});assert(playback.sameNode);assert.equal(playback.rpc,0,'Playback callbacks performed RPC');assert(playback.ms<2000,'Playback callbacks are unexpectedly slow');
  await page.locator('[data-action=projects]').click();await page.waitForSelector('[data-action=back]');assert(await page.locator('[data-action=back]').isVisible());assert(await page.locator('[data-action=back]').evaluate(el=>el.classList.contains('back-prominent')&&getComputedStyle(el).color==='rgb(255, 255, 255)'));assert((await page.locator('[data-action=back]').boundingBox()).x<(await page.locator('[data-action=add]').boundingBox()).x);await page.locator('[data-action=back]').click();await page.waitForSelector('#video');
  await page.waitForFunction(()=>document.querySelector('#toast')?.hidden);await page.screenshot({path:path.join(out,`${lang}-basic.png`)});
  await page.locator('[data-action=switch-mode]').click();await page.waitForSelector('.studio.expert');assert.equal(await page.locator('.mode-switch').count(),1);
  await uniqueCommands(page,true);
  for(const panel of ['nav','browser','inspector']){await page.locator(`[data-action=toggle-${panel}]`).click();await uniqueCommands(page,true);}
  await page.screenshot({path:path.join(out,`${lang}-expert-panels-hidden.png`)});
  for(const panel of ['inspector','browser','nav']){await page.locator(`[data-action=toggle-${panel}]`).click();await uniqueCommands(page,true);}
  assert.equal(await page.locator('[data-setting=ttsBackend]').count(),0); // Dialogue inspector, not a second production selector.
  await page.locator('[data-action=inspector][data-value=production]').click();assert.equal(await page.locator('[data-setting=ttsBackend]').inputValue(),'gpt-sovits-v2');
  assert(await page.locator('[data-setting=visualRoleAnalysisEnabled]').isVisible());await page.locator('[data-action=inspector][data-value=dialogue]').click();
  const ep=await page.locator('#expert-progress').boundingBox();assert(ep.height<120,`Expert progress too tall: ${ep.height}`);
  await page.waitForFunction(()=>document.querySelector('#toast')?.hidden);await page.screenshot({path:path.join(out,`${lang}-expert.png`)});
  for(const key of ['roles','review','produce','queue','terminal','defaults','models','preferences','projects']){
   await page.locator(`[data-action=page][data-value=${key}]`).click();await page.waitForTimeout(150);await page.waitForFunction(()=>document.querySelector('#toast')?.hidden);await page.screenshot({path:path.join(out,`${lang}-${key}.png`)});
   await uniqueCommands(page,true);
   assert(await page.locator(key==='terminal'?'.terminal-tools':'.page-inner > *').count()>0,`${key}: page content is missing`);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${key}: horizontal window overflow`);
  }
  await page.evaluate(movie=>window.studioFixture.pickPaths=[movie],path.resolve('.build/windows/desktop-qa/日本語 episode 01.mp4'));await page.locator('[data-action=add]').click();await page.waitForSelector('.studio.expert [data-cue-field=text]');assert.equal(await page.locator('.studio.expert [data-cue-field=text]').count(),1,'Import from another page did not return to the editor');
  await page.locator('[data-action=page][data-value=edit]').click();await page.waitForSelector('[data-cue-field=text]');
  await page.locator('[data-cue-field=text]').fill(lang==='en'?'你好呀，再見啦。':'你好呀，香港。');await page.locator('[data-cue-field=text]').blur();
  await page.locator('[data-action=save]').click();await page.waitForTimeout(100);
  assert.equal(errors.length,0,errors.join('\n'));results.push({language:lang,pages:10,geometry:true,sharedEngine:true,basicReturn:true,bilingualGuide:true,draftSaved:true,singleImportControl:true,uniqueGlobalCommands:true,hiddenPanelsImport:true,errors});await page.close();
 }
 const cold=await browser.newPage({viewport:{width:1280,height:800}});let badRPC=0;
 await cold.addInitScript(()=>{window.__TAURI__={core:{invoke:async(name,args)=>{if(name==='studio_status')return {runtimeReady:false,running:null};if(name==='studio_rpc')throw Error('Python is deliberately absent');return {};},convertFileSrc:p=>p},event:{listen:async()=>()=>{}}}});
 cold.on('pageerror',()=>badRPC++);await cold.goto('http://127.0.0.1:18732');await cold.waitForTimeout(100);await cold.selectOption('#welcome-language','zh-HK');await cold.locator('[data-action=mode][data-value=expert]').click();assert(await cold.locator('[data-action=enter]').isDisabled());assert((await cold.locator('[data-action=guide]').innerText()).includes('使用手冊'));assert.equal(badRPC,0);await cold.screenshot({path:path.join(out,'cold-welcome.png')});await cold.close();
 const removal=await browser.newPage({viewport:{width:1500,height:960}});
 await removal.addInitScript(()=>{
  window.confirm=()=>{throw Error('Browser confirmation is unavailable in the native host')};
  window.__TAURI__={core:{convertFileSrc:p=>'/media?path='+encodeURIComponent(p),invoke:async(name,args={})=>{const response=await fetch('/api',{method:'POST',body:JSON.stringify({name,args})});const data=await response.json();if(data.error)throw Error(data.error);return data.result;}},event:{listen:async()=>()=>{}}};
 });
 const removalErrors=[];removal.on('pageerror',e=>removalErrors.push(e.message));
 await removal.goto('http://127.0.0.1:18732');await removal.waitForSelector('[data-action=enter]');
 await removal.locator('[data-action=mode][data-value=basic]').click();await removal.locator('[data-action=enter]').click();await removal.waitForSelector('.shelf-card');
 const fixture=path.join(out,'SamCantoSync/jobs/fixture'),movie=path.resolve('.build/windows/desktop-qa/日本語 episode 01.mp4');
 const exportName='removal-proof-'+Date.now()+'.mp4';fs.copyFileSync(movie,path.join(fixture,exportName));fs.writeFileSync(path.join(fixture,'working.tmp'),'temporary project data');fs.writeFileSync(path.join(fixture,'report.json'),JSON.stringify({output:path.join(fixture,exportName)}));
 for(const language of ['en','zh-HK']){
  await removal.evaluate(async language=>window.__TAURI__.core.invoke('studio_rpc',{op:'configure',params:{language}}),language);await removal.reload();await removal.waitForSelector('[data-action=enter]');await removal.locator('[data-action=enter]').click();await removal.waitForSelector('.shelf-card');
  // Both entry points must open an in-app confirmation and cancellation must do no RPC removal.
  await removal.locator('.shelf-card [data-action=remove]').click();await removal.waitForSelector('.drawer [data-action=remove-project]');
  await removal.locator('.drawer [data-action=close-drawer]').last().click();assert.equal(await removal.locator('.shelf-card').count(),1);
  assert(fs.existsSync(path.join(fixture,'working.tmp')));
  await removal.locator('[data-action=projects]').click();await removal.locator('.queue-row [data-action=remove]').click();await removal.waitForSelector('.drawer [data-action=remove-project]');
  await removal.locator('.drawer [data-action=close-drawer]').last().click();assert.equal(await removal.locator('.queue-row').count(),1);
  await removal.locator('[data-action=back]').click();
 }
 // Confirm from Projects, then re-add and confirm from the shelf in the other language.
 await removal.locator('[data-action=projects]').click();await removal.locator('.queue-row [data-action=remove]').click();await removal.locator('[data-action=remove-project]').click();await removal.waitForSelector('.empty');
 assert(!fs.existsSync(fixture));assert(fs.existsSync(movie));assert(fs.readFileSync(path.join(out,'SamCantoSync/exports',exportName)).equals(fs.readFileSync(movie)));
 await removal.locator('[data-action=back]').click();assert.equal(await removal.locator('#video').getAttribute('src'),null);
 await removal.evaluate(async movie=>{await window.__TAURI__.core.invoke('studio_rpc',{op:'configure',params:{language:'en'}});await window.__TAURI__.core.invoke('studio_rpc',{op:'add',params:{paths:[movie]}});},movie);
 await removal.reload();await removal.waitForSelector('[data-action=enter]');await removal.locator('[data-action=enter]').click();await removal.waitForSelector('.shelf-card');await removal.locator('.shelf-card [data-action=remove]').click();await removal.locator('[data-action=remove-project]').click();await removal.waitForSelector('.shelf .empty');
 await uniqueCommands(removal,false);await removal.screenshot({path:path.join(out,'empty-basic-single-import.png')});await removal.locator('[data-action=switch-mode]').click();await removal.waitForSelector('.studio.expert');await uniqueCommands(removal,true);await removal.screenshot({path:path.join(out,'empty-expert-single-import.png')});
 assert(fs.existsSync(movie));assert.equal(removalErrors.length,0,removalErrors.join('\n'));
 const persisted=JSON.parse(fs.readFileSync(path.join(out,'SamCantoSync/studio/desktop-state.json')));assert.equal(persisted.queue.length,0);assert.equal(persisted.selected,null);
 await removal.screenshot({path:path.join(out,'removal-complete.png')});await removal.close();
 await browser.close();fs.writeFileSync(path.join(out,'ui-acceptance.json'),JSON.stringify({fixtureOnly:true,nativeGPUInference:false,coldWelcomeWithoutPython:true,removal:{bothEntryPoints:true,bilingual:true,cancelPreserved:true,sourceAndExportsPreserved:true,persistedEmpty:true,noBrowserConfirm:true},results},null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
