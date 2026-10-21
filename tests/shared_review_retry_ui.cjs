const {chromium}=require('playwright');
const assert=require('node:assert/strict');

(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER});
 try{
  for(const language of ['en','zh-HK']){
   const page=await browser.newPage({viewport:{width:1440,height:960},reducedMotion:'reduce'});
   await page.addInitScript(()=>{
    const listeners=new Map();window.retryQA={calls:[],otherStarts:[],fail:true,finish:()=>listeners.get('studio-finished')?.({payload:{runID:'review-retry-fixture',action:'render-project',code:0}})};
    window.__TAURI__={core:{convertFileSrc:path=>'/media?path='+encodeURIComponent(path),invoke:async(name,args={})=>{
     if(name==='studio_start'&&args.op==='retry-review'){
      window.retryQA.calls.push(args);
      await new Promise(resolve=>setTimeout(resolve,120));
      if(window.retryQA.fail)throw Error('Repair setup failed for test');
      return {id:'review-retry-fixture'};
     }
     if(name==='studio_start'){window.retryQA.otherStarts.push(args);return {id:'fixture-setup'};}
     const response=await fetch('/api',{method:'POST',body:JSON.stringify({name,args})});
     const data=await response.json();if(data.error)throw Error(data.error);
     const result=data.result;
     if(name==='studio_rpc'&&args.op==='plan')result.setupReady=true;
     if(name==='studio_rpc'&&['state','configure','select'].includes(args.op)&&result?.queue?.[0]){
      result.queue[0].status='complete';result.queue[0].output='/fixture-output.mp4';result.queue[0].progress=1;
     }
     if(name==='studio_rpc'&&args.op==='snapshot'&&!window.retryQA.clearIssues&&!location.search.includes('saved-choice')){
      result.issues=[{status:'unresolved',kind:'automatic-recovery',index:1,engine:'drama3',language:'yue'}];
      result.reviewState={...result.reviewState,pending:1};
     }
     if(name==='studio_rpc'&&args.op==='snapshot'&&window.retryQA.clearIssues)result.issues=[];
     if(name==='studio_rpc'&&args.op==='snapshot'&&location.search.includes('saved-choice')){
      result.issues=[{status:'user-choice-saved',index:1,engine:'drama3',language:'yue'}];
      result.reviewState={...result.reviewState,userChoicesApplied:false};
     }
     return result;
    }},event:{listen:async(name,callback)=>{listeners.set(name,callback);return ()=>{}}}};
   });
   await page.goto('http://127.0.0.1:18732/');
   await page.locator('#welcome-language').selectOption(language);
   await page.locator('[data-action=mode][data-value=expert]').click();
   await page.locator('[data-action=enter]').click();
   await page.locator('[data-action=page][data-value=review]').click();
   const retry=page.locator('[data-action=retry-review]');
   await retry.waitFor();
   const footer=page.locator('[data-action=start]');await footer.waitFor();
   assert.equal((await footer.innerText()).trim(),language==='en'?'Done':'完成');
   assert(await footer.isDisabled());
   await retry.click();
   await page.locator('.review-summary [role=alert]').getByText('Repair setup failed for test').waitFor();
   assert.equal(await page.evaluate(()=>window.retryQA.calls.length),1);
   assert.equal(await page.evaluate(()=>window.retryQA.otherStarts.length),0);
   await page.evaluate(()=>{window.retryQA.fail=false;window.retryQA.clearIssues=true});
   await retry.click();
   await page.waitForFunction(()=>window.retryQA.calls.length===2);
   assert.equal(await page.locator('.review-summary [role=alert]').count(),0);
   assert.equal((await page.evaluate(()=>window.retryQA.calls[1].params.mode)),'pending');
   await page.evaluate(()=>window.retryQA.finish());
   await page.locator('[data-action=start]:disabled').getByText(language==='en'?'Done':'完成').waitFor();
   await page.close();
  }
  const choice=await browser.newPage({viewport:{width:1440,height:960},reducedMotion:'reduce'});
  await choice.addInitScript(()=>{
   window.retryQA={otherStarts:[]};
   window.__TAURI__={core:{convertFileSrc:path=>'/media?path='+encodeURIComponent(path),invoke:async(name,args={})=>{
    if(name==='studio_start'){window.retryQA.otherStarts.push(args);return {id:'saved-choice-render'};}
    const response=await fetch('/api',{method:'POST',body:JSON.stringify({name,args})});
    const data=await response.json();if(data.error)throw Error(data.error);
    const result=data.result;
    if(name==='studio_rpc'&&args.op==='plan')result.setupReady=true;
    if(name==='studio_rpc'&&['state','configure','select'].includes(args.op)&&result?.queue?.[0]){
     result.queue[0].status='complete';result.queue[0].output='/fixture-output.mp4';result.queue[0].progress=1;
    }
    if(name==='studio_rpc'&&args.op==='snapshot'){
     result.issues=[{status:'user-choice-saved',index:1,engine:'drama3',language:'yue'}];
     result.reviewState={...result.reviewState,userChoicesApplied:false};
     result.draft=result.draft||{segments:[],settings:{}};
    }
    return result;
   }},event:{listen:async()=>()=>{}}};
  });
  await choice.goto('http://127.0.0.1:18732/?saved-choice');
  await choice.locator('#welcome-language').selectOption('en');
  await choice.locator('[data-action=mode][data-value=expert]').click();
  await choice.locator('[data-action=enter]').click();
  await choice.locator('[data-action=start]').getByText('Export a new version').click();
  await choice.waitForFunction(()=>window.retryQA.otherStarts.some(x=>x.op==='render'));
  await choice.close();
  console.log('Completed footer remains Done; optional review repair starts with visible feedback in both languages.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
