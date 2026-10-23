const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
const base=process.env.ANICANTO_QA_URL||'http://127.0.0.1:18737',out=process.env.ANICANTO_QA_ROOT||'.build/workbench-qa';
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER});const receipts=[];
try{for(const language of ['en','zh-HK','zh-CN','ja']){
 const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{window.__TAURI__={core:{invoke:async(name,args={})=>{const r=await fetch('/api',{method:'POST',body:JSON.stringify({name,args})});const d=await r.json();if(d.error)throw Error(d.error);return d.result;},convertFileSrc:p=>'/media?path='+encodeURIComponent(p)},event:{listen:async()=>()=>{}}};});
 await page.goto(base);await page.waitForSelector('#welcome-language');await page.selectOption('#welcome-language',language);await page.locator('[data-action=mode][data-value=expert]').click();await page.locator('[data-action=enter]').click();await page.locator('[data-action=page][data-value=review]').click();await page.waitForSelector('.review-summary');
 // Restore the previous language run's review decision through the real persistent RPC.
 await page.evaluate(async()=>{const invoke=window.__TAURI__.core.invoke;const state=await invoke('studio_rpc',{op:'state'});const snap=await invoke('studio_rpc',{op:'snapshot',params:{id:state.selected}});for(const i of snap.issues)if(i.triage!=='pending')await invoke('studio_rpc',{op:'review-triage',params:{id:state.selected,issueID:i.id,fingerprint:i.triageFingerprint,state:'pending'}});});
 await page.reload();await page.locator('[data-action=enter]').click();await page.locator('[data-action=page][data-value=review]').click();await page.waitForSelector('.review-line');
 const before=await page.locator('.review-line').count();assert(before>0);
 const id=await page.locator('.review-line').first().getAttribute('data-issue-id');
 await page.locator('.review-line').first().locator('[data-action=review-triage][data-value=deferred]').click();
 await page.locator('[data-action=review-filter][data-value=deferred]').click();await page.locator(`[data-issue-id="${id}"]`).waitFor();
 await page.locator('[data-action=review-triage][data-value=undo]').click();await page.locator('[data-action=review-filter][data-value=issues]').click();await page.locator(`[data-issue-id="${id}"]`).waitFor();
 await page.locator(`[data-issue-id="${id}"] [data-action=review-triage][data-value=checked]`).click();await page.locator('[data-action=review-filter][data-value=checked]').click();await page.locator(`[data-issue-id="${id}"]`).waitFor();
 const persisted=await page.evaluate(async()=>{const call=window.__TAURI__.core.invoke;const s=await call('studio_rpc',{op:'state'});return call('studio_rpc',{op:'snapshot',params:{id:s.selected}});});
 assert(persisted.workbench.checked>0);assert.equal(persisted.reviewState.qualityChecked,false);assert(persisted.issues.some(i=>i.id===id),'Acknowledgement must not erase diagnostic evidence');
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Review toolbar overflow');
 await page.screenshot({path:`${out}/workbench-${language}.png`});receipts.push({language,persisted:true,undo:true,checkedIsNotQualityPass:true,layoutFits:true});
 await page.locator('[data-action=page][data-value=edit]').click();await page.locator('[data-action=subtitle-source]').click();await page.locator('[data-action=import-subtitle]').waitFor();assert(await page.locator('[data-action=import-subtitle]').isDisabled(),'A paused frozen submission must retain its subtitle lock');assert.equal(await page.locator('[data-action=import-subtitle]').count(),1,'Only the shared drawer contains import controls');await page.locator('button[data-action=close-drawer]').click();
 assert.deepEqual(errors,[]);await page.close();
 }fs.writeFileSync(`${out}/browser-receipt.json`,JSON.stringify(receipts,null,2));console.log(JSON.stringify(receipts));}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
