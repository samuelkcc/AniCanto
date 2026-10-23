const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=path.resolve('.build/shared-queue-qa');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CANTOSYNC_QA_BROWSER?{executablePath:process.env.CANTOSYNC_QA_BROWSER}:{})});
 const results=[];
 async function fixture(options={}){
  const page=await browser.newPage({viewport:{width:1500,height:960},reducedMotion:'reduce'}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(options=>{
   const f=window.queueFixture={listeners:new Map(),starts:[],media:0,drawers:0,options};
   new MutationObserver(records=>{for(const r of records)for(const n of r.addedNodes)if(n.nodeType===1&&(n.matches('.drawer-shade')||n.querySelector('.drawer-shade')))f.drawers++;}).observe(document,{childList:true,subtree:true});
   const source=id=>`/fixtures/episode-${id}.mkv`;
   f.state={useTermsAccepted:true,language:options.language||'en',mode:options.mode||'basic',selected:options.selected||'a',settings:{ttsBackend:'drama3',selectedEngines:['drama3'],dubLanguages:['yue'],subtitleModes:['yue'],includeOriginal:true,productionMode:'normal',appearance:'light'},ui:{autoQueue:!!options.restore,autoQueueAttention:!!options.restoreAttention},queue:(options.rows||[['a','waiting'],['b','waiting']]).map(([id,status])=>({id,video:source(id),status,progress:status==='complete'?1:0,...(status==='complete'?{output:`/exports/${id}.mp4`}:{})})),storage:'/fixture'};
   f.running=options.restore?{id:'restored-run',rowID:'a',action:'batch'}:null;
   f.finish=async({code=0,paused=false,duplicate=false,preview=false}={})=>{
    let payload;
    if(duplicate)payload=f.last;
    else{if(!f.running)throw Error('No active fixture run');const r=f.running;payload={runID:r.id,rowID:r.rowID,action:'batch',code,paused};const row=f.state.queue.find(x=>x.id===r.rowID);row.status=paused?'paused':code||preview?'attention':'complete';if(preview){row.deliveryKind='preview';row.incompleteDialogue=2;}if(!code&&!paused){row.output=`/exports/${row.id}.mp4`;row.progress=1;}f.running=null;f.last=payload;}
    await f.listeners.get('studio-finished')({payload});
   };
   window.__TAURI__={core:{convertFileSrc:p=>p,invoke:async(name,args={})=>{
    if(name==='studio_status')return {runtimeReady:true,running:structuredClone(f.running)};
    if(name==='studio_pick')return ['/fixtures/episode-c.mkv'];
    if(name==='studio_pause'){f.pauses=(f.pauses||0)+1;setTimeout(()=>f.finish({paused:true}),0);return;}
    if(name==='studio_media'){f.media++;throw Error('Preview must stay off');}
    if(name==='studio_start'){
     if(args.op!=='start')throw Error('Unexpected task '+args.op);
     if(f.running)throw Error('Concurrent native conversion');
     const id=args.params.id;f.starts.push(id);
     if(options.launchFailure===id)throw Error('Missing source file');
     const row=f.state.queue.find(r=>r.id===id);row.status='running';row.progress=0;
     const run={id:'run-'+f.starts.length,rowID:id,action:'batch'};f.running=run;
     if(options.fast===id)setTimeout(()=>f.finish(),0);
     await new Promise(resolve=>setTimeout(resolve,60));return {id:run.id};
    }
    if(name==='studio_rpc'){
     const p=args.params||{};
     if(args.op==='configure'){Object.assign(f.state.settings,p.settings||{});Object.assign(f.state.ui,p.ui||{});if(p.mode)f.state.mode=p.mode;if(p.language)f.state.language=p.language;return structuredClone(f.state);}
     if(args.op==='source-language'){if(options.sourceDelay)await new Promise(resolve=>setTimeout(resolve,options.sourceDelay));const language=options.sourceLanguage||'ja';f.state.queue.find(r=>r.id===p.id).sourceLanguage=language;return {language,name:language==='en'?'English':language==='fr'?'French':'Japanese',needsConfirmation:!!options.sourceLanguage,supported:options.sourceSupported!==false,token:'fixture-source',reason:'The detected source language is not supported by the selected voice engine.'};}
     if(args.op==='move-video'){
      if(options.moveDelay)await new Promise(r=>setTimeout(r,options.moveDelay));
      const row=f.state.queue.find(r=>r.id===p.id);f.state.queue=f.state.queue.filter(r=>r.id!==p.id);
      const index=p.beforeID==null?f.state.queue.length:f.state.queue.findIndex(r=>r.id===p.beforeID);
      if(!row||index<0)throw Error('The video list changed. Try moving the video again.');
      f.state.queue.splice(index,0,row);f.moves=(f.moves||0)+1;return structuredClone(f.state);
     }
     if(args.op==='state')return structuredClone(f.state);
     if(args.op==='add'){
      for(const video of p.paths||[])if(!f.state.queue.some(r=>r.video===video))f.state.queue.push({id:'c',video,status:'waiting',progress:0});
      return structuredClone(f.state);
     }
     if(args.op==='select'){f.state.selected=p.id;return structuredClone(f.state);}
     if(args.op==='snapshot'){
      if(options.badSnapshot===p.id)throw Error('Fixture snapshot unavailable');
      return {root:'/jobs/'+p.id,takes:[],review:{config:{duration:6}},issues:p.id==='a'?(options.reviewIssues||[]):[],reviewState:{pending:p.id==='a'?(options.reviewIssues||[]).length:0}};
     }
     if(args.op==='models'||args.op==='model-choices'||args.op==='licenses')return [];
     if(args.op==='plan')return {setupReady:true,downloads:[],roles:{}};
     if(args.op==='save-draft')return {};
    }
    throw Error('Unexpected fixture IPC '+name+' '+args.op);
   }},event:{listen:async(name,fn)=>{f.listeners.set(name,fn);return ()=>f.listeners.delete(name)}},window:{getCurrentWindow:()=>({close:async()=>{f.closed=true}})}};
  },options);
  await page.goto(process.env.ANICANTO_QA_URL||'http://127.0.0.1:18732');await page.waitForSelector('#welcome-language');await page.locator('[data-action=enter]').click();await page.waitForSelector('#video');
  async function count(n){await page.waitForFunction(n=>window.queueFixture.starts.length===n,n);await page.waitForFunction(()=>!document.querySelector('[data-action=start]')?.textContent.includes('Starting'));const pause=page.locator('button[data-action=pause]').first();if(await pause.count()){const color=await pause.evaluate(e=>getComputedStyle(e).backgroundColor);assert(['rgb(189, 48, 61)','rgb(159, 35, 48)'].includes(color),'Pause & save must be red on the shared Mac/Windows UI: '+color);}}
  async function finish(opts){await page.evaluate(opts=>window.queueFixture.finish(opts),opts);}
  async function end(name){assert.deepEqual(errors,[],name);if(!options.sourceLanguage)assert.equal(await page.evaluate(()=>window.queueFixture.drawers),0,'Automatic Japanese detection flashed a drawer');assert.equal(await page.evaluate(()=>window.queueFixture.media),0,'Preview decoder was started');console.log('PASS '+name);results.push({name,starts:await page.evaluate(()=>window.queueFixture.starts),errors});await page.close();}
  return {page,count,finish,end};
 }
 {
  const {page,count,finish,end}=await fixture({selected:'b'});
  await page.locator('[data-action=start]').evaluate(b=>{b.click();b.click()});await count(1);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a']);
  await finish();await count(2);assert.equal(await page.evaluate(()=>window.queueFixture.state.selected),'b');
  assert((await page.locator('.workspace-title .filename').innerText()).includes('episode-b'));
  await finish({duplicate:true});assert.equal(await page.evaluate(()=>window.queueFixture.starts.length),2);
  await finish();await page.waitForSelector('[data-action=start]');assert.equal(await page.locator('[data-action=start]').innerText(),'Done');
  assert(await page.locator('[data-action=start]').isDisabled());
  assert.equal(await page.evaluate(()=>window.queueFixture.state.ui.autoQueue),false);await page.screenshot({path:path.join(out,'two-videos-complete.png')});await end('Basic Start, queue order, double click, duplicate finish and selected item');
 }
 {
  const {page,count,finish,end}=await fixture({rows:[['a','waiting']]});
  await page.locator('[data-action=start]').click();await count(1);
  await page.locator('[data-action=add]').click();
  await page.waitForFunction(()=>window.queueFixture.state.queue.some(r=>r.id==='c'));
  assert.equal(await page.evaluate(()=>window.queueFixture.state.queue.find(r=>r.id==='c').status),'waiting');
  await finish();await count(2);
  assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a','c']);
  await finish();await end('Basic queue includes video imported during active conversion');
 }
 for(const language of ['en','zh-HK']){
  const {page,count,finish,end}=await fixture({language,rows:[['a','complete'],['b','waiting']]});
  assert.equal(await page.locator('[data-action=start]').innerText(),language==='en'?'Start remaining videos':'開始餘下影片');
  await page.locator('[data-action=start]').click();await count(1);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['b']);await finish();await end('Completed first skipped: '+language);
 }
 for(const language of ['en','zh-HK']){
  const reviewIssues=[{index:1,status:'unresolved',kind:'automatic-recovery',language:'yue',engine:'drama3'}];
  const {page,count,finish,end}=await fixture({language,rows:[['a','complete'],['b','waiting']],reviewIssues});
  assert.equal(await page.locator('[data-action=start]').innerText(),language==='en'?'Start remaining videos':'開始餘下影片');
  await page.locator('[data-action=open-review]').click();
  assert.equal(await page.locator('[data-action=retry-review]').count(),1,'Optional report repair must remain reachable from Basic mode');
  await page.locator('[data-action=back]').click();
  await page.locator('[data-action=start]').click();await count(1);await finish();
  await page.locator('[data-action=select][data-value=a]').click();
  await page.waitForFunction(()=>document.querySelector('[data-action=start]')?.textContent.includes(document.documentElement.lang==='en'?'Done':'完成'));
  assert(await page.locator('[data-action=start]').isDisabled());
  await end('Completed export with optional report does not mask next video or completion: '+language);
 }
 {
  const {page,count,finish,end}=await fixture();await page.locator('[data-action=start]').click();await count(1);
  await page.locator('[data-action=pause]').click();await page.waitForSelector('[data-action=start]');await page.waitForTimeout(120);assert.equal(await page.evaluate(()=>window.queueFixture.starts.length),1);
  assert.equal(await page.locator('[data-action=start]').innerText(),'Resume all unfinished videos');await page.locator('[data-action=start]').click();await count(2);await finish();await count(3);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a','a','b']);await finish();await end('Pause stops queue; Resume continues current then next');
 }
 for(const variant of ['failed-conversion','launchFailure','badSnapshot','fast']){
  const {page,count,finish,end}=await fixture(variant==='failed-conversion'?{}:{[variant]:'a'});
  await page.locator('[data-action=start]').click();
  if(['launchFailure','fast'].includes(variant))await count(2);
  else{await count(1);await finish(variant==='failed-conversion'?{code:1}:{});await count(2);}
  assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a','b']);await finish();await end('Next starts once after '+variant);
 }
 {
  const {page,count,finish,end}=await fixture();await page.locator('[data-action=start]').click();await count(1);await page.locator('[data-action=mode][data-value=expert]').click();await page.waitForSelector('.studio.expert');await finish();await count(2);await finish();await end('Switch to Expert preserves active Basic queue');
 }
 {
  const {page,count,finish,end}=await fixture({mode:'expert',selected:'b'});await page.locator('[data-action=start]').click();await count(1);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a']);await finish();await count(2);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a','b']);await finish();await end('Expert Start follows the full queue, matching Basic');
 }
 {
  const {page,count,finish,end}=await fixture({mode:'expert',rows:[['a','waiting']]});
  await page.locator('[data-action=inspector][data-value=production]').click();
  const mode=page.locator('[data-setting=productionMode]');
  await mode.locator('xpath=ancestor::details').evaluate(el=>el.open=true);
  assert.equal(await mode.isDisabled(),false);
  await page.locator('[data-action=start]').click();await count(1);
  await mode.locator('xpath=ancestor::details').evaluate(el=>el.open=true);
  assert.equal(await mode.isDisabled(),true,'Production mode must lock while conversion runs');
  await mode.evaluate(el=>{el.value='fast';el.dispatchEvent(new Event('change',{bubbles:true}))});
  assert.equal(await page.evaluate(()=>window.queueFixture.state.settings.productionMode),'normal','Synthetic change must not bypass the lock');
  await finish();await page.waitForFunction(()=>!document.querySelector('[data-setting=productionMode]')?.disabled);
  await end('Production mode unlocks only after conversion finishes');
 }
 {
  const {page,count,finish,end}=await fixture({mode:'expert',rows:[['a','running'],['b','waiting']],restore:true});await finish();await count(1);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['b']);await finish();await end('Restore live batch intent after UI reload');
 }
 {
  const {page,count,finish,end}=await fixture({rows:[['a','paused'],['b','attention'],['c','attention'],['d','attention']]});
  assert.equal(await page.locator('[data-action=start]').innerText(),'Resume all unfinished videos');
  await page.locator('[data-action=start]').click();await count(1);await finish({preview:true});await count(2);
  await finish();await count(3);await finish();await count(4);await finish();
  assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a','b','c','d']);
  assert.equal(await page.evaluate(()=>window.queueFixture.state.ui.autoQueue),false);
  await end('Basic resume includes all attention items; preview continues once to each remaining video');
 }
 {
  const {page,count,finish,end}=await fixture({mode:'expert',rows:[['a','running'],['b','attention']],restore:true,restoreAttention:true});
  await finish({preview:true});await count(1);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['b']);await finish();
  await end('UI reload preserves repair-all intent across incomplete preview');
 }
 for(const language of ['en','zh-HK']){
  const {page,count,finish,end}=await fixture({language,sourceDelay:650,rows:[['a','attention'],['b','paused'],['c','attention']]});
  await page.locator('[data-action=start]').click();
  await page.waitForTimeout(100);assert.equal(await page.locator('.drawer-shade').count(),0);
  assert.equal(await page.locator('[data-action=start]').innerText(),language==='en'?'Starting…':'正在啟動…');
  await count(1);await finish({preview:true});await count(2);await finish();await count(3);await finish();
  assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a','b','c']);
  await end('Resume repairs attention and paused rows without a source-language drawer: '+language);
 }
 for(const sourceLanguage of ['en','fr']){
  const {page,count,end}=await fixture({sourceLanguage,rows:[['a','waiting']]});
  await page.locator('[data-action=start]').click();await page.waitForSelector('[data-action=confirm-source-language]');
  assert.equal(await page.evaluate(()=>window.queueFixture.starts.length),0,'Source started before confirmation');
  assert((await page.locator('.drawer').innerText()).includes(sourceLanguage==='en'?'English':'French'));
  await page.locator('.drawer button[data-action=close-drawer]').first().click();await page.waitForTimeout(100);
  assert.equal(await page.evaluate(()=>window.queueFixture.starts.length),0);assert.equal(await page.evaluate(()=>window.queueFixture.state.ui.autoQueue),false);
  await page.locator('[data-action=start]').click();await page.waitForSelector('[data-action=confirm-source-language]');await page.locator('[data-action=confirm-source-language]').click();await count(1);
  if(sourceLanguage==='en'){assert.equal(await page.locator('[data-setting=dubLanguages] option').count(),1);assert.equal(await page.locator('[data-setting=dubLanguages]').inputValue(),'yue');assert(await page.locator('[data-setting=dubLanguages]').isDisabled());}
  await end('Detected '+sourceLanguage+' requires confirmation; Cancel starts nothing');
 }
 {
  const {page,end}=await fixture({sourceLanguage:'fr',sourceSupported:false,rows:[['a','waiting']]});
  await page.locator('[data-action=start]').click();await page.waitForSelector('.drawer');await page.waitForTimeout(100);
  assert.equal(await page.locator('[data-action=confirm-source-language]').count(),0);assert.equal(await page.evaluate(()=>window.queueFixture.starts.length),0);
  await page.locator('.drawer button[data-action=close-drawer]').first().click();await end('Unsupported source shows explanation and cannot start');
 }

 for(const language of ['en','zh-HK']){
  const {page,count,finish,end}=await fixture({language,moveDelay:150,rows:[['a','waiting'],['b','waiting'],['c','waiting']]});
  await page.locator('[data-action=start]').click();await count(1);
  const ids=()=>page.locator('#shelf > [data-queue-id]').evaluateAll(es=>es.map(e=>e.dataset.queueId));
  const handle=page.locator('[data-queue-handle=c]'),start=await handle.boundingBox(),target=await page.locator('#shelf [data-queue-id=b]').boundingBox();
  await page.mouse.move(start.x+start.width/2,start.y+start.height/2);await page.mouse.down();
  await page.mouse.move(start.x+start.width/2,target.y+5,{steps:10});
  await page.waitForTimeout(2700); // A real poll cannot destroy the dragged row.
  assert(await page.locator('.queue-drop-marker').isVisible());await page.mouse.up();
  await page.waitForFunction(()=>window.queueFixture.moves===1);
  assert.deepEqual(await ids(),['a','c','b']);assert.equal(await page.evaluate(()=>window.queueFixture.state.selected),'a');
  assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a']);
  await page.locator('[data-action=projects]').click();assert.deepEqual(await page.locator('.queue-row').evaluateAll(es=>es.map(e=>e.dataset.queueId)),['a','c','b']);
  await page.locator('[data-queue-id=b] [data-action=queue-up]').click();await page.waitForFunction(()=>window.queueFixture.moves===2);
  assert.deepEqual(await page.locator('.queue-row').evaluateAll(es=>es.map(e=>e.dataset.queueId)),['a','b','c']);
  await page.locator('[data-queue-handle=c]').focus();await page.keyboard.press('ArrowUp');await page.waitForFunction(()=>window.queueFixture.moves===3);
  assert.deepEqual(await page.locator('.queue-row').evaluateAll(es=>es.map(e=>e.dataset.queueId)),['a','c','b']);
  assert.equal(await page.evaluate(()=>document.activeElement?.dataset.queueHandle),'c');
  await page.screenshot({path:path.join(out,'reorder-'+language+'.png')});
  await finish();await count(2);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a','c']);
  await finish();await count(3);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a','c','b']);await finish();
  await end('Live drag, polling, synchronized projects, arrow/keyboard moves and new batch order: '+language);
 }
 {
  const {page,end}=await fixture({rows:[['a','waiting'],['b','waiting'],['c','waiting']]});
  const box=await page.locator('[data-queue-handle=c]').boundingBox(),top=await page.locator('[data-queue-id=a]').boundingBox();
  await page.mouse.move(box.x+8,box.y+8);await page.mouse.down();await page.mouse.move(box.x+8,top.y+5,{steps:10});await page.keyboard.press('Escape');await page.mouse.up();
  assert.equal(await page.locator('.queue-drop-marker').count(),0);assert.equal(await page.evaluate(()=>window.queueFixture.moves||0),0);
  assert.equal(await page.evaluate(()=>window.queueFixture.state.selected),'a');await end('Escape cancels reorder without selecting or changing any video');
 }

 {
  const {page,end}=await fixture({rows:'abcdefghijkl'.split('').map(id=>[id,'waiting'])});
  const box=await page.locator('[data-queue-handle=a]').boundingBox(),shelf=await page.locator('#shelf').boundingBox();
  await page.mouse.move(box.x+8,box.y+8);await page.mouse.down();await page.mouse.move(box.x+8,shelf.y+shelf.height-4,{steps:12});
  await page.waitForFunction(()=>{const s=document.querySelector('#shelf');return s.scrollTop>s.scrollHeight-s.clientHeight-10});
  await page.mouse.up();await page.waitForFunction(()=>window.queueFixture.moves===1);
  assert.equal(await page.evaluate(()=>window.queueFixture.state.queue.at(-1).id),'a');
  await end('Long queue auto-scrolls while dragging to the bottom');
 }
 {
  const {page,count,finish,end}=await fixture({rows:[['a','waiting'],['b','waiting'],['c','waiting']]});
  await page.locator('[data-action=start]').click();await count(1);
  const box=await page.locator('[data-queue-handle=c]').boundingBox(),target=await page.locator('[data-queue-id=b]').boundingBox();
  await page.mouse.move(box.x+8,box.y+8);await page.mouse.down();await page.mouse.move(box.x+8,target.y+5,{steps:10});
  // Worker completion during the gesture waits for the move to be persisted.
  await page.evaluate(()=>{window.queueFixture.finish();});await page.waitForTimeout(150);
  assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a']);
  await page.mouse.up();await count(2);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['a','c']);
  await finish();await count(3);await finish();await end('Worker finishes during drag: next movie waits for saved order');
 }
 for(const language of ['en','zh-HK']){
  const {page,count,end}=await fixture({language,mode:'expert',rows:[['a','waiting']]});
  await page.locator('[data-action=start]').click();await count(1);
  await page.locator('.inspector-footer [data-action=pause]').waitFor();
  assert.equal(await page.locator('.inspector-footer [data-action=pause]').count(),1);
  await page.locator('[data-action=toggle-inspector]').click();
  assert.equal(await page.locator('.workspace-title [data-action=pause]').count(),1,'Hidden inspector keeps Pause in the Edit header');
  assert.equal(await page.locator('.statusbar.has-transport').count(),0);
  for(const destination of ['review','produce','queue','models','preferences']){
   await page.locator(`[data-action=page][data-value=${destination}]`).click();
   assert.equal(await page.locator('[data-action=pause]').count(),0,'Pause must only appear in Edit');
   assert.equal(await page.locator('.statusbar .transport-control').count(),0,'No global transport footer');
  }
  await page.locator('[data-action=page][data-value=edit]').click();assert.equal(await page.locator('.workspace-title [data-action=pause]').count(),1);
  await page.locator('[data-action=toggle-inspector]').click();assert.equal(await page.locator('.inspector-footer [data-action=pause]').count(),1);assert.equal(await page.locator('[data-action=pause]').count(),1);
  await page.locator('[data-action=pause]').click();await page.waitForSelector('[data-action=start]');
  await end('Pause only in Edit, including hidden inspector; no full-width transport footer: '+language);
 }
 await browser.close();fs.writeFileSync(path.join(out,'acceptance.json'),JSON.stringify({fixtureOnly:true,realUIActions:true,previewOff:true,results},null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
