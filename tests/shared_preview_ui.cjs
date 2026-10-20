const {chromium}=require('playwright');const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const out=path.resolve('.build/shared-preview-qa');fs.mkdirSync(out,{recursive:true});
(async()=>{const browser=await chromium.launch({headless:true,...(process.env.CANTOSYNC_QA_BROWSER?{executablePath:process.env.CANTOSYNC_QA_BROWSER}:{})}),results=[];
 for(const language of ['en','zh-HK']){
  const page=await browser.newPage({viewport:{width:1500,height:960},reducedMotion:'reduce'}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{
   const f=window.previewFixture={calls:[],status:0};
   window.__TAURI__={core:{convertFileSrc:p=>'/media?path='+encodeURIComponent(p),invoke:async(name,args={})=>{
    if(name==='studio_media'){f.calls.push(args.params);await new Promise(resolve=>setTimeout(resolve,1900));return {path:f.source,duration:6,fallbackAvailable:!args.params.compatible};}
    if(name==='studio_rpc'&&args.op==='media-status'){f.status++;return {stage:'remux',progress:.35,duration:6};}
    const response=await fetch('/api',{method:'POST',body:JSON.stringify({name,args})});const data=await response.json();if(data.error)throw Error(data.error);
    if(name==='studio_rpc'&&args.op==='state')f.source=data.result.queue[0].video;
    return data.result;
   }},event:{listen:async()=>()=>{}},window:{getCurrentWindow:()=>({close:async()=>{}})}};
  });
  await page.goto('http://127.0.0.1:18732');await page.waitForSelector('#welcome-language');await page.selectOption('#welcome-language',language);await page.locator('[data-action=mode][data-value=basic]').click();await page.locator('[data-action=enter]').click();await page.waitForSelector('#video');
  assert.equal(await page.evaluate(()=>window.previewFixture.calls.length),0);
  await page.locator('.waiting-scene [data-action=toggle-preview]').click();
  // Closing/reopening and repeated Play while preparation is in flight must
  // share one native process; stale responses must not revive a disabled preview.
  await page.locator('.waiting-scene [data-action=toggle-preview]').click();await page.locator('.waiting-scene [data-action=toggle-preview]').click();
  await page.locator('[data-action=play]').evaluate(b=>{b.click();b.click()});
  await page.waitForFunction(()=>document.querySelector('.waiting-copy')?.innerText.includes('35%'));
  assert.equal(await page.evaluate(()=>window.previewFixture.calls.length),1);await page.screenshot({path:path.join(out,language+'-progress.png')});
  await page.waitForFunction(()=>document.querySelector('#video')?.readyState>=2);await page.waitForFunction(()=>!document.querySelector('.video-stage').classList.contains('preview-off'));
  assert.equal(await page.evaluate(()=>window.previewFixture.calls.length),1);
  // A native decoder that cannot play a remux gets one explicit H.264 fallback.
  await page.locator('#video').evaluate(v=>v.dispatchEvent(new Event('error')));
  await page.waitForFunction(()=>window.previewFixture.calls.length===2);assert.equal(await page.evaluate(()=>window.previewFixture.calls[1].compatible),true);
  await page.waitForFunction(()=>!document.querySelector('.video-stage').classList.contains('preview-off'));
  await page.locator('[data-action=preview-control]').click();assert.equal(await page.locator('#video').getAttribute('src'),null);assert(await page.locator('.waiting-scene').isVisible());
  assert.deepEqual(errors,[]);results.push({language,preparationDeduplicated:true,visibleProgress:true,decoderFallback:true,defaultOff:true,errors});await page.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'acceptance.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
