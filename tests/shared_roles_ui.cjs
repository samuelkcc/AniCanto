const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
(async()=>{
 const out=path.resolve('.build/compliance/roles-ui');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER});
 const results=[];
 for(const language of ['en','zh-HK']){
  const page=await browser.newPage({viewport:{width:1500,height:960}});const errors=[];
  page.on('pageerror',e=>{errors.push(e.message);console.error(e.message)});
  await page.addInitScript(()=>{window.__TAURI__={core:{convertFileSrc:p=>p,invoke:async(name,args={})=>{
   const response=await fetch('/api',{method:'POST',body:JSON.stringify({name,args})});const data=await response.json();if(data.error)throw Error(data.error);
   if(name==='studio_rpc'&&args.op==='snapshot'&&data.result.draft){
    const roles=Array.from({length:32},(_,i)=>({id:'line-fixture-'+(i+25),sourceIndex:i===31?9999:i+24,name:`第 ${i+25} 句原聲`,identityStatus:'independent',reference:'/fixture.wav',referenceRanges:[[100+i,103+i]],originalReferenceSeconds:3,promptText:'これは画面の幅が狭い場合でも読める参考録音の文章です。'}));
    roles.push({id:'R100-long-identifier-with-details',name:'A character with a deliberately long name / 完整角色名稱測試',identityStatus:'uncertain',promptText:'Reference transcript',avatar:'assets/pet-studio.png'});
    data.result.roles=roles;data.result.draft.settings.voiceProfiles=roles;
   }return data.result;
  }},event:{listen:async()=>()=>{}},window:{getCurrentWindow:()=>({close:async()=>{}})}}});
  await page.goto('http://127.0.0.1:18732');await page.waitForSelector('#welcome-language');await page.selectOption('#welcome-language',language);
  await page.locator('[data-action=mode][data-value=expert]').click();await page.locator('[data-action=enter]').click();await page.waitForSelector('#video');await page.locator('[data-action=page][data-value=roles]').click();
  await page.waitForSelector('.role-card');assert.equal(await page.locator('.role-card').count(),33);
  assert.equal(await page.locator('.role-number').first().innerText(),'#025');assert.equal(await page.locator('.role-number').nth(5).innerText(),'#030');assert.equal(await page.locator('.role-number').nth(31).innerText(),'#10000');
  assert((await page.locator('.role-card h3').first().innerText()).includes('25'));
  assert(!(await page.locator('.roles-grid').innerText()).includes('independent'));
  await page.fill('#role-search','30');assert.equal(await page.locator('.role-card:visible').count(),1);assert((await page.locator('.role-card:visible').innerText()).includes('30'));
  await page.fill('#role-search','not-a-real-reference');assert.equal(await page.locator('.role-card:visible').count(),0);assert(await page.locator('#role-no-results').isVisible());
  await page.fill('#role-search','');await page.locator('.role-card').first().locator('textarea').fill('Edited reference text');await page.locator('.role-card').first().locator('textarea').blur();
  await page.fill('#role-search','25');assert.equal(await page.locator('.role-card:visible textarea').inputValue(),'Edited reference text');await page.fill('#role-search','');
  for(const width of [1500,1050]){
   await page.setViewportSize({width,height:960});
   const geometry=await page.locator('.role-card').evaluateAll(cards=>cards.map(card=>({card:card.getBoundingClientRect().toJSON(),elements:[...card.querySelectorAll('.role-number,h3,textarea,button')].map(el=>({rect:el.getBoundingClientRect().toJSON(),client:el.clientWidth,scroll:el.scrollWidth}))})));
   for(const g of geometry){for(const e of g.elements){assert(e.rect.x>=g.card.x-1&&e.rect.right<=g.card.right+1,'Reference content overflows its card');assert(e.scroll<=e.client+2,'Role number or heading is clipped');}}
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Window overflows horizontally');
   await page.screenshot({path:path.join(out,`${language}-${width}.png`)});
  }
  assert.deepEqual(errors,[]);results.push({language,completeNumbers:true,search:true,editable:true,widths:[1500,1050],errors});await page.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
