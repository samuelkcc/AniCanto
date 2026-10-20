// Real local RPC/data fixture; native file-dialog and model execution are separate.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=path.resolve('.build/shared-studio-qa'),job=path.join(out,'SamCantoSync/jobs/fixture');
const other=path.join(job,'tracks/voxcpm2-yue');fs.mkdirSync(other,{recursive:true});
fs.copyFileSync(path.join(job,'voice.wav'),path.join(other,'cosy-voice.wav'));
fs.writeFileSync(path.join(other,'audio-preview.json'),JSON.stringify({engine:'voxcpm2',language:'yue'}));
fs.writeFileSync(path.join(other,'timing.json'),JSON.stringify([{index:1,start:.25,end:2,audio:path.join(other,'cosy-voice.wav')}]));
fs.writeFileSync(path.join(job,'drama3-request.log'),'model details\nWinError 5 Access is denied\n');
fs.writeFileSync(path.join(out,'SamCantoSync/mlx-text.log'),'translation details\n');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER});const results=[];
 for(const lang of ['en','zh-HK']){
  const page=await browser.newPage({viewport:{width:1500,height:960},reducedMotion:'reduce'});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{
   const listeners=new Map();window.audit={listeners,calls:[],cancelExport:false,exports:0};
   window.__TAURI__={core:{convertFileSrc:p=>'/media?path='+encodeURIComponent(p),invoke:async(name,args={})=>{
    window.audit.calls.push({name,args});
    if(name==='studio_start')return {id:'audit-render'};
    if(name==='studio_export_logs'){
     if(window.audit.cancelExport)return {cancelled:true};
     const r=await fetch('/api',{method:'POST',body:JSON.stringify({name:'studio_rpc',args:{op:'export-logs',params:{}}})});const d=await r.json();if(d.error)throw Error(d.error);window.audit.report=d.result;window.audit.exports++;return {cancelled:false,path:'/chosen/AniCanto-debug.txt'};
    }
    if(name==='studio_pick')return [];
    const r=await fetch('/api',{method:'POST',body:JSON.stringify({name,args})});const d=await r.json();if(d.error)throw Error(d.error);return d.result;
   }},event:{listen:async(name,fn)=>{listeners.set(name,fn);return ()=>{}}}};
  });
  await page.goto('http://127.0.0.1:18732');await page.waitForSelector('#welcome-language');await page.selectOption('#welcome-language',lang);await page.waitForTimeout(100);
  await page.locator('[data-action=guide]').click();const guide=await page.locator('.drawer').innerText();
  for(const word of lang==='en'?['Basic mode:','Expert mode:','multiple voice engines','three times','Pause, resume']:['基本模式：','專家模式：','多引擎配音','三倍','暫停、繼續'])assert(guide.includes(word),word);
  if(lang==='en')assert(!/使用教學|一般模式|專家模式/.test(guide));
  await page.locator('.drawer [data-action=close-drawer]').last().click();
  await page.locator('[data-action=mode][data-value=expert]').click();await page.locator('[data-action=enter]').click();await page.waitForSelector('[data-cue-field=text]');
  await page.locator('[data-action=page][data-value=roles]').click();assert((await page.locator('.role-notice').innerText()).includes(lang==='en'?'three times':'三倍'));
  await page.locator('[data-action=page][data-value=edit]').click();await page.waitForSelector('[data-cue-field=text]');
  await page.locator('[data-action=inspector][data-value=production]').click();await page.locator('.engine-tracks>summary').click();
  const extra=page.locator('[data-engine-track=voxcpm2]');if(!(await extra.isChecked()))await extra.check();
  const stored=await page.evaluate(()=>window.__TAURI__.core.invoke('studio_rpc',{op:'state',params:{}}));assert(stored.settings.selectedEngines.includes('voxcpm2'));
  await page.locator('[data-action=inspector][data-value=dialogue]').click();
  await page.locator('[data-action=dialogue-tab][data-value=record]').click();await page.selectOption('[data-setting=retakeEngine]','voxcpm2');
  await page.locator('[data-action=dialogue-tab][data-value=adjust]').click();await page.locator('[data-action=dialogue-tab][data-value=record]').click();assert.equal(await page.locator('[data-setting=retakeEngine]').inputValue(),'voxcpm2');
  await page.locator('[data-action=retake]').click();const retake=await page.evaluate(()=>window.audit.calls.filter(c=>c.name==='studio_start').at(-1));assert.equal(retake.args.params.engine,'voxcpm2');assert(retake.args.params.segment);
  await page.evaluate(()=>window.audit.listeners.get('studio-finished')({payload:{runID:'audit-render',code:0,paused:false}}));await page.waitForTimeout(150);
  await page.locator('[data-action=play-take][data-engine=voxcpm2]').click();await page.locator('[data-action=adopt]').click();await page.locator('[data-action=save]').click();await page.waitForTimeout(100);
  let saved=JSON.parse(fs.readFileSync(path.join(job,'editor-draft-studio.json')));assert.equal(saved.segments[0].audioTake,path.join(other,'cosy-voice.wav'));
  await page.waitForTimeout(2700);saved=JSON.parse(fs.readFileSync(path.join(job,'editor-draft-studio.json')));assert.equal(saved.segments[0].audioTake,path.join(other,'cosy-voice.wav'));
  await page.locator('[data-action=inspector][data-value=sound]').click();await page.locator('[data-setting=backgroundGain]').fill('0.35');await page.locator('[data-setting=backgroundGain]').dispatchEvent('change');await page.locator('[data-action=save]').click();await page.waitForTimeout(100);
  saved=JSON.parse(fs.readFileSync(path.join(job,'editor-draft-studio.json')));assert.equal(saved.settings.backgroundGain,.35);
  // Timeline video bar must seek instead of being an inert control.
  await page.locator('.video-clip').click({position:{x:18,y:8}});assert(Math.abs(await page.locator('#video').evaluate(v=>v.currentTime)-1.5)<.3);
  await page.locator('[data-action=export]').click();const render=await page.evaluate(()=>window.audit.calls.filter(c=>c.name==='studio_start').at(-1));assert.equal(render.args.params.draft.settings.backgroundGain,.35);assert(render.args.params.draft.settings.selectedEngines.includes('voxcpm2'));
  await page.evaluate(()=>window.audit.listeners.get('studio-finished')({payload:{runID:'audit-render',code:0,paused:false}}));await page.waitForTimeout(150);
  await page.locator('[data-action=page][data-value=terminal]').click();await page.waitForFunction(()=>document.querySelector('#log-source').options.length>=2);
  await page.selectOption('#log-source','mlx-text.log');await page.waitForFunction(()=>document.querySelector('#terminal-output').textContent.includes('translation details'));
  await page.evaluate(()=>window.audit.listeners.get('studio-log')({payload:'process event belongs to another source'}));assert(!(await page.locator('#terminal-output').innerText()).includes('process event belongs to another source'));
  await page.locator('[data-action=export-logs]').click();await page.waitForFunction(()=>!!window.audit.report);assert((await page.evaluate(()=>window.audit.report)).includes('WinError 5'));assert((await page.locator('#toast').innerText()).includes('AniCanto-debug.txt'));
  await page.evaluate(()=>window.audit.cancelExport=true);await page.locator('[data-action=export-logs]').click();assert.equal(await page.evaluate(()=>window.audit.exports),1);
  await page.screenshot({path:path.join(out,`${lang}-terminal-debug.png`)});
  for(const key of ['edit','roles','review','produce','queue','terminal','defaults','models','preferences','projects']){
   await page.locator(`[data-action=page][data-value=${key}]`).click();await page.waitForTimeout(60);
   for(const action of ['add','guide','about','switch-mode','save','export'])assert.equal(await page.locator(`[data-action=${action}]`).count(),1,`${key}: duplicate ${action}`);
   for(const action of ['pause','start','change-models'])assert(await page.locator(`[data-action=${action}]`).count()<=1,`${key}: duplicate ${action}`);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${key}: overflow`);
  }
  // Cancellation from the project list and shelf must leave data intact.
  await page.locator('.queue-row [data-action=remove]').click();await page.locator('.drawer [data-action=close-drawer]').last().click();assert(fs.existsSync(job));
  await page.locator('[data-action=page][data-value=edit]').click();await page.locator('[data-action=switch-mode]').click();await page.waitForSelector('.studio.basic');
  assert.equal(await page.locator('[data-engine-track]').count(),0);
  await page.locator('[data-action=captions]').click();await page.locator('[data-action=caption-choice][data-value=en]').click();assert((await page.locator('#audition-card').innerText()).includes(lang==='en'?'Hong Kong Cantonese':'香港廣東話'));
  const cols=await page.locator('.milestones').evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length);assert.equal(cols,5);
  await page.locator('.shelf-card [data-action=remove]').click();await page.locator('.drawer [data-action=close-drawer]').last().click();assert.equal(await page.locator('.shelf-card').count(),1);
  assert.equal(errors.length,0,errors.join('\n'));results.push({language:lang,pages:10,multiEngine:true,retakeChoicePersisted:true,adoptedExactEngine:true,persistedAfterPoll:true,mixInExport:true,timelineSeek:true,debugExportAndCancel:true,duplicateCommands:false,removalCancel:true});await page.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'action-audit.json'),JSON.stringify({nativeWindowsExecution:false,nativeSaveDialog:false,results},null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
