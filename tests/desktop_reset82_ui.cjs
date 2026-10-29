const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=path.resolve('.build/desktop-reset82-qa');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CANTOSYNC_QA_BROWSER?{executablePath:process.env.CANTOSYNC_QA_BROWSER}:{})});
 const results=[];
 async function fixture(options={}){
  const page=await browser.newPage({viewport:{width:1500,height:960},reducedMotion:'reduce'}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(options=>{
   const f=window.queueFixture={listeners:new Map(),starts:[],media:0,drawers:0,options};
   new MutationObserver(records=>{for(const r of records)for(const n of r.addedNodes)if(n.nodeType===1&&(n.matches('.drawer-shade')||n.querySelector('.drawer-shade')))f.drawers++;}).observe(document,{childList:true,subtree:true});
   const source=id=>options.videoNames?.[id]||`/fixtures/episode-${id}.mkv`;
   f.state={useTermsAccepted:true,language:options.language||'en',mode:options.mode||'basic',selected:options.selected||'a',settings:{ttsBackend:'drama3',selectedEngines:['drama3'],dubLanguages:['yue'],subtitleModes:['yue'],includeOriginal:true,productionMode:'normal',appearance:'light'},ui:{autoQueue:!!options.restore,autoQueueAttention:!!options.restoreAttention},queue:(options.rows||[['a','waiting'],['b','waiting']]).map(([id,status])=>({id,video:source(id),status,progress:status==='complete'?1:0,...(status==='complete'?{output:`/exports/${id}.mp4`}:{})})),storage:'/fixture'};
   f.running=options.restore?{id:'restored-run',rowID:'a',action:'batch'}:null;
   if(options.completed){f.running=null;f.state.ui.autoQueue=options.autoQueue!==false;f.state.queue[0].status='complete';f.state.queue[0].output='/exports/a.mp4';f.last={runID:'completed-before-reload',rowID:'a',action:'batch',code:0,paused:!!options.completedPaused};if(options.completedPaused)f.state.queue[0].status='paused';}
   f.finish=async({code=0,paused=false,duplicate=false,preview=false,dropEvent=false}={})=>{
    let payload;
    if(duplicate)payload=f.last;
    else{if(!f.running)throw Error('No active fixture run');const r=f.running;payload={runID:r.id,rowID:r.rowID,action:'batch',code,paused};const row=f.state.queue.find(x=>x.id===r.rowID);row.status=paused?'paused':code||preview?'attention':'complete';if(preview){row.deliveryKind='preview';row.incompleteDialogue=2;}if(!code&&!paused){row.output=`/exports/${row.id}.mp4`;row.progress=1;}f.running=null;f.last=payload;if(options.nativeOwned){payload.nativeQueue=1;if(!paused){const next=f.state.queue.find(x=>x.status==='waiting');if(next){f.nativeStarts??=[];f.nativeStarts.push(next.id);next.status='running';f.state.selected=next.id;f.running={id:'native-'+next.id,rowID:next.id,action:'batch'};}}}}
    if(!dropEvent)await f.listeners.get('studio-finished')({payload});
   };
   window.__TAURI__={core:{convertFileSrc:p=>p,invoke:async(name,args={})=>{
    if(name==='studio_status'){f.statusCalls=(f.statusCalls||0)+1;return {runtimeReady:true,nativeQueue:!!options.nativeOwned&&!!f.running,running:structuredClone(f.running),lastFinished:structuredClone(f.last)};}
    if(name==='studio_appearance')return null;
    if(name==='studio_ack_finished'){f.acks=(f.acks||0)+1;return true;}
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
      if(options.moveDelay)await new Promise(r=>setTimeout(r,options.moveDelay));if(options.moveFailure)throw Error('Fixture order save failed');
      const row=f.state.queue.find(r=>r.id===p.id);f.state.queue=f.state.queue.filter(r=>r.id!==p.id);
      const index=p.beforeID==null?f.state.queue.length:f.state.queue.findIndex(r=>r.id===p.beforeID);
      if(!row||index<0)throw Error('The video list changed. Try moving the video again.');
      f.state.queue.splice(index,0,row);f.moves=(f.moves||0)+1;return structuredClone(f.state);
     }
     if(args.op==='reset-video-plan'){(f.resetPlans??=[]).push(p.id);if(options.resetPlanDelay)await new Promise(r=>setTimeout(r,options.resetPlanDelay));if(options.resetPlanFailure)throw Error('Fixture reset plan failed');return {id:p.id,video:f.state.queue.find(r=>r.id===p.id).video,token:'fixture-'+p.id};}
     if(args.op==='reset-video'){f.resetAttempts=(f.resetAttempts||0)+1;if(options.resetCommitDelay)await new Promise(r=>setTimeout(r,options.resetCommitDelay));if(options.resetCommitErrorOnce&&f.resetAttempts===1)throw Error('The video state changed. Review the reset again.');if(p.token!=='fixture-'+p.id)throw Error('Bad reset token');const i=f.state.queue.findIndex(r=>r.id===p.id),old=f.state.queue[i];f.state.queue[i]={id:old.id,video:old.video,status:'waiting',progress:0};(f.resetIDs??=[]).push(p.id);return {state:structuredClone(f.state),reset:true};}
     if(args.op==='state')return structuredClone(f.state);
     if(args.op==='add'){
      for(const video of p.paths||[])if(!f.state.queue.some(r=>r.video===video))f.state.queue.push({id:'c',video,status:'waiting',progress:0});
      return structuredClone(f.state);
     }
     if(args.op==='select'){if(options.selectDelay)await new Promise(r=>setTimeout(r,options.selectDelay));f.state.selected=p.id;return structuredClone(f.state);}
     if(args.op==='snapshot'){
      (f.snapshotCalls??=[]).push(p.id);if(f.resetIDs?.includes(p.id))return {};if(options.badSnapshot===p.id)throw Error('Fixture snapshot unavailable');
      return {root:'/jobs/'+p.id,takes:[],review:{config:{duration:6}},issues:p.id==='a'?(options.reviewIssues||[]):[],reviewState:{pending:p.id==='a'?(options.reviewIssues||[]).length:0}};
     }
     if(args.op==='speech-library')return {folder:{id:'speech-studio',name:'Dubbing studio'},clips:[],projects:[],engines:[],textModels:[],parameters:{},draft:{}};
     if(args.op==='models'||args.op==='model-choices'||args.op==='licenses')return [];
     if(args.op==='plan'){(f.planRequests??=[]).push(structuredClone(p));if(options.failedPlan&&!p.engine)throw Error('Previously selected models do not fit this computer');return {setupReady:true,canDeployModels:true,downloads:[],roles:{}};}
     if(args.op==='save-draft')return {};
    }
    throw Error('Unexpected fixture IPC '+name+' '+args.op);
   }},event:{listen:async(name,fn)=>{f.listeners.set(name,fn);return ()=>f.listeners.delete(name)}},window:{getCurrentWindow:()=>({close:async()=>{f.closed=true}})}};
  },options);
  await page.goto(process.env.ANICANTO_QA_URL||'http://127.0.0.1:18732');await page.waitForSelector('#welcome-language');if(!options.stayWelcome){await page.locator('[data-action=enter]').click();await page.waitForSelector('#video');}
  async function count(n){await page.waitForFunction(n=>window.queueFixture.starts.length===n,n);await page.waitForFunction(()=>!document.querySelector('[data-action=start]')?.textContent.includes('Starting'));const pause=page.locator('button[data-action=pause]').first();if(await pause.count()){const color=await pause.evaluate(e=>getComputedStyle(e).backgroundColor);assert(['rgb(189, 48, 61)','rgb(159, 35, 48)'].includes(color),'Pause & save must be red on the shared Mac/Windows UI: '+color);}}
  async function finish(opts){await page.evaluate(opts=>window.queueFixture.finish(opts),opts);}
  async function end(name){assert.deepEqual(errors,[],name);if(!options.allowDrawers&&!options.sourceLanguage)assert.equal(await page.evaluate(()=>window.queueFixture.drawers),0,'Automatic Japanese detection flashed a drawer');assert.equal(await page.evaluate(()=>window.queueFixture.media),0,'Preview decoder was started');console.log('PASS '+name);results.push({name,starts:await page.evaluate(()=>window.queueFixture.starts),errors});await page.close();}
  return {page,count,finish,end};
 }

 async function drift(page,id){await page.evaluate(id=>{window.queueFixture.state.selected=id;window.dispatchEvent(new Event('focus'))},id);await page.waitForFunction(id=>document.querySelector('.shelf-card.active')?.dataset.queueId===id,id);}
 {
  const {page,count,end}=await fixture({language:'zh-HK',allowDrawers:true,rows:[['a','paused'],['b','waiting']],videoNames:{a:'/fixtures/忍者貓小隊.mp4',b:'/fixtures/《One Piece》-0820.mkv'}});
  await page.locator('[data-action=queue-up][data-value=b]').click();await page.waitForFunction(()=>window.queueFixture.state.queue[0].id==='b');
  await page.locator('[data-action=restart-video][data-value=b]').click();await page.waitForSelector('.restart-menu');await drift(page,'a');
  await page.locator('[data-action=restart-choice][data-value=reset]').click();await page.waitForSelector('.reset-video-confirm');
  assert.match(await page.locator('.reset-video-confirm .filename').textContent(),/0820/);await page.screenshot({path:path.join(out,'pinned-target-confirmation.png')});
  await page.locator('[data-action=confirm-reset-video]').click();await page.waitForSelector('.drawer',{state:'detached'});
  assert.deepEqual(await page.evaluate(()=>window.queueFixture.resetIDs),['b']);assert.equal(await page.evaluate(()=>window.queueFixture.state.selected),'b');assert.equal(await page.evaluate(()=>window.queueFixture.state.queue.find(x=>x.id==='a').status),'paused');
  await page.locator('[data-action=start]').first().click();await count(1);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['b']);
  await end('820 first, pinned reset survives selection drift, closes on confirmation and starts 820');
 }
 for(const status of ['paused','attention']){
  const {page,count,end}=await fixture({rows:[['a',status],['b','waiting']]});await page.locator('[data-action=queue-up][data-value=b]').click();await page.waitForFunction(()=>window.queueFixture.state.queue[0].id==='b');
  assert.equal(await page.locator('.shelf-card.active').getAttribute('data-queue-id'),'a');await page.locator('[data-action=start]').first().click();await count(1);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['b']);await end('Batch start follows visible order instead of selected '+status+' item');
 }
 {
  const {page,end}=await fixture({allowDrawers:true,resetPlanFailure:true});await page.locator('[data-action=restart-video][data-value=b]').click();await page.locator('[data-action=restart-choice][data-value=reset]').click();await page.waitForSelector('.drawer [role=alert]');
  assert.match(await page.locator('.drawer [role=alert]').textContent(),/Fixture reset plan failed/);assert.equal(await page.locator('[data-action=restart-choice][data-value=reset]').isDisabled(),false);assert.equal(await page.evaluate(()=>window.queueFixture.resetIDs?.length||0),0);await end('Reset planning error is visible and retry remains available');
 }
 {
  const {page,end}=await fixture({allowDrawers:true});await page.locator('[data-action=restart-video][data-value=b]').click();
  const before=await page.evaluate(()=>window.queueFixture.statusCalls||0);await page.evaluate(()=>{const f=window.queueFixture;f.running={id:'guard-run',rowID:'a',action:'batch'};f.state.queue.find(r=>r.id==='a').status='running';window.dispatchEvent(new Event('focus'))});await page.waitForFunction(n=>window.queueFixture.statusCalls>n,before);
  await page.locator('[data-action=restart-choice][data-value=reset]').click();await page.waitForSelector('.drawer [role=alert]');assert.match(await page.locator('.drawer [role=alert]').textContent(),/Pause processing/);assert.equal(await page.evaluate(()=>window.queueFixture.resetPlans?.length||0),0);await end('A task starting after the menu opens gives an explicit pause message');
 }
 {
  const {page,end}=await fixture({allowDrawers:true,resetPlanDelay:700});await page.locator('[data-action=restart-video][data-value=b]').click();await page.locator('[data-action=restart-choice][data-value=reset]').click();
  await page.waitForSelector('.restart-menu[aria-busy=true]');assert.match(await page.locator('.restart-menu [role=status]').textContent(),/Preparing/);assert.equal(await page.locator('[data-action=restart-choice][data-value=reset]').isDisabled(),true);
  await page.locator('.drawer-header [data-action=close-drawer]').click();await page.waitForSelector('.drawer',{state:'detached'});await page.waitForTimeout(900);assert.equal(await page.locator('.drawer').count(),0);assert.equal(await page.evaluate(()=>window.queueFixture.resetIDs?.length||0),0);await end('Cancel during preparation ignores a late response and never resets');
 }
 {
  const {page,end}=await fixture({allowDrawers:true,resetCommitDelay:700});await page.locator('[data-action=restart-video][data-value=b]').click();await page.locator('[data-action=restart-choice][data-value=reset]').click();await page.waitForSelector('.reset-video-confirm');await page.locator('[data-action=confirm-reset-video]').click();
  await page.waitForSelector('.reset-video-confirm[aria-busy=true]');assert.match(await page.locator('.reset-video-confirm [role=status]').textContent(),/Resetting/);assert.equal(await page.locator('[data-action=confirm-reset-video]').isDisabled(),true);assert.equal(await page.locator('.drawer-header [data-action=close-drawer]').isDisabled(),true);
  await page.waitForSelector('.drawer',{state:'detached'});assert.equal(await page.evaluate(()=>window.queueFixture.resetAttempts),1);await end('Reset commit shows progress and prevents duplicate submissions');
 }
 {
  const {page,end}=await fixture({allowDrawers:true,resetCommitErrorOnce:true});await page.locator('[data-action=restart-video][data-value=b]').click();await page.locator('[data-action=restart-choice][data-value=reset]').click();await page.waitForSelector('.reset-video-confirm');await page.locator('[data-action=confirm-reset-video]').click();await page.waitForSelector('[data-action=reset-retry-plan]');
  assert.equal(await page.locator('[data-action=confirm-reset-video]').isDisabled(),true);assert.match(await page.locator('.drawer [role=alert]').textContent(),/state changed/);
  await page.locator('[data-action=reset-retry-plan]').click();await page.waitForSelector('[data-action=confirm-reset-video]:enabled');await page.locator('[data-action=confirm-reset-video]').click();await page.waitForSelector('.drawer',{state:'detached'});assert.deepEqual(await page.evaluate(()=>window.queueFixture.resetIDs),['b']);assert.deepEqual(await page.evaluate(()=>window.queueFixture.resetPlans),['b','b']);await end('Stale confirmation is visible and requires a fresh reviewed plan');
 }
 {
  const {page,end}=await fixture({allowDrawers:true});await page.locator('[data-action=restart-video][data-value=b]').click();await page.locator('[data-action=restart-choice][data-value=reset]').click();await page.waitForSelector('.reset-video-confirm');await drift(page,'a');
  await page.locator('[data-action=start]').first().evaluate(e=>e.click());await page.waitForSelector('.drawer [role=alert]');assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),[]);
  await page.locator('[data-action=confirm-reset-video]').click();await page.waitForSelector('.drawer',{state:'detached'});assert.deepEqual(await page.evaluate(()=>window.queueFixture.resetIDs),['b']);assert.equal(await page.evaluate(()=>window.queueFixture.state.selected),'b');await end('Pending confirmation blocks Start and keeps its original target');
 }
 {
  const {page,count,end}=await fixture({allowDrawers:true,rows:[['a','paused'],['b','waiting']]});await page.locator('[data-action=restart-video][data-value=b]').click();await page.locator('[data-action=restart-choice][data-value=analysis]').click();await count(1);assert.deepEqual(await page.evaluate(()=>window.queueFixture.starts),['b']);await end('Explicit single-video restart still targets its own video');
 }
 await browser.close();fs.writeFileSync(path.join(out,'acceptance82.json'),JSON.stringify({fixtureOnly:true,realUIActions:true,results},null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
