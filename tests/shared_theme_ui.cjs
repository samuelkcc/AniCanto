const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER});const p=await browser.newPage({viewport:{width:1500,height:960},reducedMotion:'reduce'}),errors=[];p.on('pageerror',e=>errors.push(e.message));
try{
 await p.addInitScript(()=>{window.__TAURI__={core:{convertFileSrc:p=>'/media?path='+encodeURIComponent(p),invoke:async(name,args={})=>{const x=await fetch('/api',{method:'POST',body:JSON.stringify({name,args})}).then(r=>r.json());if(x.error)throw Error(x.error);return x.result}},event:{listen:async()=>()=>{}},window:{getCurrentWindow:()=>({close:async()=>{}})}}});
 await p.goto('http://127.0.0.1:18732');await p.waitForSelector('#welcome-language');await p.selectOption('#welcome-language','en');await p.locator('[data-action=mode][data-value=expert]').click();await p.locator('[data-action=enter]').click();await p.locator('[data-action=page][data-value=preferences]').click();
 const out=path.resolve('.build/management/next-patch/ui');fs.mkdirSync(out,{recursive:true});
 const themes=['studio','ocean','energy','ninja','retro','forest','future','mint','moonflower'];
 for(const appearance of ['light','dark']){
  await p.selectOption('[data-setting=appearance]',appearance);await p.waitForFunction(dark=>document.documentElement.classList.contains('dark')===dark,appearance==='dark');
  const colours=new Set();
  for(const theme of themes){await p.locator(`[data-action=theme][data-value=${theme}]`).click();await p.waitForFunction(theme=>document.querySelector(`[data-action=theme][data-value=${theme}]`)?.classList.contains('active'),theme);
   const result=await p.locator('.navigation').evaluate(el=>{const c=e=>getComputedStyle(e);const selected=el.querySelector('button.active');return {header:c(document.querySelector('.workspace-title')).backgroundColor,nav:c(el).backgroundImage,active:c(selected).backgroundColor,ink:c(selected).color,drawer:c(document.querySelector('.appbar')).backgroundColor};});
   assert.notEqual(result.header,'rgb(255, 255, 255)');assert.notEqual(result.nav,'none');assert.equal(result.ink,'rgb(255, 255, 255)');colours.add(result.header);
   if(['studio','ocean','energy'].includes(theme))await p.screenshot({path:path.join(out,`theme-${theme}-${appearance}.png`)});
  }
  assert.equal(colours.size,9,'Every theme must colour the operation chrome distinctly');
 }
 await p.selectOption('[data-setting=appearance]','light');await p.locator('[data-action=theme][data-value=studio]').click();await p.locator('[data-action=switch-mode]').click();await p.waitForSelector('.basic');const colour=await p.locator('.workspace-title').evaluate(e=>getComputedStyle(e).backgroundColor);assert.notEqual(colour,'rgb(255, 255, 255)');assert.deepEqual(errors,[]);
 console.log('Nine themes apply to operation menus in light/dark appearance and both modes; no page errors.');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
