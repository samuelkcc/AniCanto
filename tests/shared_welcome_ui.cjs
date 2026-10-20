// A failed consent sync must not leave English chrome over Chinese app state.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
(async()=>{
 const out=path.resolve('.build/compliance/welcome-02415');fs.mkdirSync(out,{recursive:true});
 const terms=fs.readFileSync('Resources/USE-TERMS.json'),sha=crypto.createHash('sha256').update(terms).digest('hex');
 const request=async(name,args)=>{const r=await fetch('http://127.0.0.1:18732/api',{method:'POST',body:JSON.stringify({name,args})}),data=await r.json();if(data.error)throw Error(data.error);return data.result};
 await request('studio_rpc',{op:'configure',params:{language:'zh-HK',settings:{}}});
 const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER});
 try{
  const p=await browser.newPage({viewport:{width:1500,height:960}});let failConsent=true,initialState=true;
  await p.exposeBinding('welcomeFixture',async(_ctx,name,args)=>{
   if(name==='studio_rpc'&&args.op==='accept-use-terms'&&failConsent){failConsent=false;throw Error('Simulated consent bridge error');}
   const value=await request(name,args);
   if(name==='studio_rpc'&&args.op==='state'&&initialState){initialState=false;value.useTermsAccepted=false;}
   return value;
  });
  await p.addInitScript(sha=>{localStorage.setItem('anicanto-use-terms-'+sha,'accepted');window.__TAURI__={core:{invoke:(name,args={})=>window.welcomeFixture(name,args),convertFileSrc:p=>'/media?path='+encodeURIComponent(p)},event:{listen:async()=>()=>{}},window:{getCurrentWindow:()=>({close:async()=>{}})}}},sha);
  await p.goto('http://127.0.0.1:18732/');
  await p.waitForFunction(()=>document.documentElement.lang==='zh-HK'&&!document.querySelector('#welcome-language').disabled);
  await p.waitForFunction(()=>document.querySelector('#toast').textContent.includes('Simulated consent'));
  assert.equal(await p.locator('#welcome-language').inputValue(),'zh-HK');
  assert((await p.locator('.welcome-title h2').innerText()).includes('歡迎'));
  for(const language of ['zh-HK','en']){
   await p.selectOption('#welcome-language',language);await p.waitForFunction(lang=>document.documentElement.lang===lang,language);
   await p.locator('[data-action=use-terms]').click();
   assert.equal(await p.locator('.drawer-header > span').innerText(),JSON.parse(terms).title[language]);
   assert((await p.locator('.drawer-body').innerText()).includes(JSON.parse(terms).paragraphs[language][0]));
   await p.screenshot({path:path.join(out,'terms-'+language+'.png'),animations:'disabled'});await p.locator('.drawer [data-action=close-drawer]').click();
   await p.locator('[data-action=guide]').click();assert.equal(await p.locator('#help-toc button').count(),17);
   assert.equal(await p.locator('#help-article-title').innerText(),language==='en'?'Getting started':'開始使用');
   await p.fill('#help-search',language==='en'?'generation-limit':'解碼達上限');assert.equal(await p.locator('#help-toc button').count(),1);
   await p.screenshot({path:path.join(out,'help-'+language+'.png'),animations:'disabled'});await p.locator('.drawer [data-action=close-drawer]').click();
  }
  await p.locator('#use-terms-checkbox').uncheck();await p.waitForFunction(()=>document.querySelector('[data-action=enter]').disabled);
  await p.locator('#use-terms-checkbox').check();await p.waitForFunction(()=>!document.querySelector('[data-action=enter]').disabled);
  await p.locator('[data-action=enter]').click();await p.waitForSelector('#video');
  assert(!(await p.locator('#toast').innerText()).includes('Unsupported desktop operation'));
  // Returning home must allow either card, including clicks on its nested
  // title, description, icon and selection indicator, to select the next mode.
  for(const language of ['zh-HK','en']){
   await p.locator('[data-action=welcome]').click();
   await p.selectOption('#welcome-language',language);
   await p.waitForFunction(lang=>document.documentElement.lang===lang,language);
   for(const [mode,child] of [['expert','h4'],['basic','.description'],['expert','svg'],['basic','.mode-dot']]){
    await p.locator(`[data-action=mode][data-value=${mode}] ${child}`).click();
    await p.waitForFunction(mode=>document.querySelector('.mode-card.active')?.dataset.value===mode,mode);
    await p.locator('[data-action=enter]').click();
    await p.waitForSelector(mode==='expert'?'.studio.expert':'.studio.basic');
    await p.locator('[data-action=switch-mode]').click();
    await p.waitForSelector(mode==='expert'?'.studio.basic':'.studio.expert');
    await p.locator('[data-action=welcome]').click();
   }
   await p.locator('[data-action=enter]').click();await p.waitForSelector('#video');
  }
  console.log(JSON.stringify({welcomeModeRoundTrips:true,startupFailureKeepsLanguageConsistent:true,termsLanguages:['en','zh-HK'],helpChapters:17,helpSearchBothLanguages:true,consentRevokeAccept:true,enterStudio:true}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
