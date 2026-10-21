const {chromium}=require('playwright');
const assert=require('node:assert/strict');

(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER});
 try{
  for(const language of ['en','zh-HK']){
   const page=await browser.newPage({viewport:{width:1440,height:960},reducedMotion:'reduce'});
   await page.addInitScript(()=>{
    const listeners=new Map();window.retryQA={calls:[],fail:true};
    window.__TAURI__={core:{convertFileSrc:path=>'/media?path='+encodeURIComponent(path),invoke:async(name,args={})=>{
     if(name==='studio_start'&&args.op==='retry-review'){
      window.retryQA.calls.push(args);
      await new Promise(resolve=>setTimeout(resolve,120));
      if(window.retryQA.fail)throw Error('Repair setup failed for test');
      return {id:'review-retry-fixture'};
     }
     if(name==='studio_start')return {id:'fixture-setup'};
     const response=await fetch('/api',{method:'POST',body:JSON.stringify({name,args})});
     const data=await response.json();if(data.error)throw Error(data.error);return data.result;
    }},event:{listen:async(name,callback)=>{listeners.set(name,callback);return ()=>{}}}};
   });
   await page.goto('http://127.0.0.1:18732/');
   await page.locator('#welcome-language').selectOption(language);
   await page.locator('[data-action=mode][data-value=expert]').click();
   await page.locator('[data-action=enter]').click();
   await page.locator('[data-action=page][data-value=review]').click();
   const retry=page.locator('[data-action=retry-review]');await retry.waitFor();
   await retry.click();
   await page.locator('[data-action=retry-review]:disabled').waitFor();
   await page.locator('.review-summary [role=alert]').getByText('Repair setup failed for test').waitFor();
   assert.equal(await page.evaluate(()=>window.retryQA.calls.length),1);
   await page.evaluate(()=>{window.retryQA.fail=false});
   await page.locator('[data-action=retry-review]').click();
   await page.waitForFunction(()=>window.retryQA.calls.length===2);
   assert.equal(await page.locator('.review-summary [role=alert]').count(),0);
   assert.equal((await page.evaluate(()=>window.retryQA.calls[1].params.mode)),'pending');
   await page.close();
  }
  console.log('Review retry gives feedback, keeps errors visible, and starts only reported-line repair in both languages.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
