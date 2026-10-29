const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=path.resolve('.build/desktop-source83-qa');fs.mkdirSync(out,{recursive:true});
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
     if(args.op==='media-subtitles')return {tracks:[{id:'embedded:2',title:'Chinese',supported:true},{id:'embedded:3',title:'Japanese',supported:true},{id:'embedded:4',title:'Bitmap',supported:false}]};if(args.op==='set-subtitle-source'){f.state.queue.find(r=>r.id===p.id).conversionSubtitleChoice=p.choice;return structuredClone(f.state);}if(args.op==='state')return structuredClone(f.state);
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


 for(const language of ['en','zh-HK','zh-CN','ja']){
  const {page,end}=await fixture({language,mode:'expert',allowDrawers:true});await page.locator('[data-action=subtitle-source]').click();await page.waitForSelector('#conversion-subtitle-source');
  if(language==='zh-HK')await page.screenshot({path:path.join(out,'subtitle-source-zh-HK.png')});const values=await page.locator('#conversion-subtitle-source option').evaluateAll(items=>items.map(x=>x.value));assert(values.includes('embedded:2'));assert(values.includes('embedded:3'));assert(!values.includes('embedded:4'));assert(values.includes('ocr'));
  await page.locator('#conversion-subtitle-source').selectOption('embedded:3');await page.locator('[data-action=save-subtitle-source]').click();await page.waitForSelector('.drawer',{state:'detached'});assert.equal(await page.evaluate(()=>window.queueFixture.state.queue[0].conversionSubtitleChoice),'embedded:3');await end('Explicit conversion subtitle selector saves exact supported track: '+language);
 }
 {
  const {page,end}=await fixture({mode:'basic',allowDrawers:true});await page.locator('[data-action=subtitle-source]').click();await page.waitForSelector('#conversion-subtitle-source');const values=await page.locator('#conversion-subtitle-source option').evaluateAll(items=>items.map(x=>x.value));assert(!values.includes('ocr'));assert(values.includes('audio-only'));await end('Basic exposes ASR fallback without automatic OCR');
 }
 {
  const {page,end}=await fixture({mode:'expert',allowDrawers:true,rows:[['a','paused']]});await page.locator('[data-action=subtitle-source]').click();await page.waitForSelector('#conversion-subtitle-source');assert(await page.locator('#conversion-subtitle-source').isDisabled());assert.equal(await page.locator('[data-action=save-subtitle-source]').count(),0);await end('Paused saved job keeps its frozen source selection');
 }
 await browser.close();fs.writeFileSync(path.join(out,'acceptance83.json'),JSON.stringify({fixtureOnly:true,results},null,2));
})().catch(e=>{console.error(e);process.exit(1)});
