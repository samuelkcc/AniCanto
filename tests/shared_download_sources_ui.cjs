const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER});const out='.build/management/0.24.30/ui';fs.mkdirSync(out,{recursive:true});
try{for(const language of ['en','zh-HK']){
 const page=await browser.newPage({viewport:{width:1500,height:960}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(language=>{window.__TAURI__={core:{convertFileSrc:p=>p,invoke:async(name,args={})=>{
  if(name==='studio_open_project'){window.projectLinkOpened=true;return;}
  if(name==='studio_status')return {runtimeReady:false,running:null};
  if(name==='studio_rpc'&&args.op==='plan')return {};
  if(name==='studio_rpc'&&args.op==='licenses')return [{name:'Fixture library',license:'MIT',text:'TEST NOTICE'}];
  if(name==='studio_rpc'&&args.op==='model-removal-plan')throw Error('Pause processing before removing a model.');return {};
 }},event:{listen:async()=>()=>{}}};localStorage.setItem('anicanto-language',language);},language);
 await page.goto('http://127.0.0.1:18732');await page.waitForSelector('[data-action=about]');
 // Welcome language control works before runtime deployment.
 await page.locator('#welcome-language').count().then(async n=>{if(n)await page.locator('#welcome-language').selectOption(language);else await page.locator('select[data-setting=language]').selectOption(language)});
 assert((await page.locator('.welcome-footer').textContent()).includes('© 2026 SCKC'));
 await page.locator('[data-action=about]').click();await page.waitForSelector('#download-source-search');
 const projectLink=page.locator('[data-action=open-project-link]');assert.equal(await projectLink.getAttribute('href'),'https://github.com/samuelkcc/AniCanto');
 await projectLink.click();assert.equal(await page.evaluate(()=>window.projectLinkOpened),true);
 assert((await page.locator('.drawer-body').innerText()).includes('© 2026 SCKC'));

 assert.equal(await page.locator('.download-source-group[open]').count(),0);
 assert.equal(await page.locator('.download-source-group').count(),4);
 const translation=page.locator('.download-source-group').first();
 assert.equal(await translation.locator('summary > strong').first().innerText(),language==='en'?'Text translation models':'文字翻譯模型');
 for(const size of ['9B','35B'])assert((await translation.textContent()).toUpperCase().includes(size));
 // The Windows title has a space after Qwen3.5, not the hyphen of the MLX repositories.
 assert(!(await translation.textContent()).includes('4B'));
 assert(!(await page.locator('.download-source-group > summary').allTextContents()).some(s=>/Qwen 3.5 ·/.test(s)));
 await translation.locator('summary').first().click();await page.screenshot({path:`${out}/${language}-translation-group.png`});
 await page.locator('#download-source-search').fill('qwen3.5:4b');
 assert.equal(await page.locator('.download-source-model').count(),0);

 await page.locator('#download-source-search').fill('Fun-CosyVoice3-0.5B-2512-8bit');assert.equal(await page.locator('.download-source-model').count(),0);
 await page.locator('#download-source-search').fill('Fun-CosyVoice3-0.5B-2512');
 const row=page.locator('.download-source-model').first();await row.locator('summary').click();
 assert.match(await row.textContent(),/FunAudioLLM\/Fun-CosyVoice3-0.5B-2512/);
 assert.match(await row.textContent(),/29e01c4e8d000f4bcd70751be16fa94bf3d85a18/);
 assert.match(await row.textContent(),/[a-f0-9]{64}/);
 assert.match(await row.textContent(),/Windows · NVIDIA/);
 assert.match(await page.locator('.download-sources').textContent(),language==='en'?/do not mean your installed files were just checked/:/唔代表剛剛校驗過/);
 assert.match(await row.locator('[data-action=copy-download-source]').first().getAttribute('data-value'),/^https:\/\/huggingface.co\/FunAudioLLM\/Fun-CosyVoice3-0.5B-2512\/resolve\/29e01c4e8d000f4bcd70751be16fa94bf3d85a18\//);
 await page.screenshot({path:`${out}/${language}-sources.png`});
 await page.locator('#download-source-search').fill('registry.ollama.ai');assert.match(await page.locator('#download-source-list').textContent(),/qwen3.5/);
 await page.locator('#download-source-search').fill('no-such-model-unique');assert.equal(await page.locator('.download-source-model').count(),0);
 assert.deepEqual(errors,[]);await page.close();
}console.log(JSON.stringify({languages:['en','zh-HK'],sources:true,pinnedRevision:true,expectedSHA256:true,blockedCosyHidden:true,officialCosyNvidiaOnly:true,groupsCollapsed:true,ollama:true,coldAbout:true,search:true}));}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
