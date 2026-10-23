const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process');
const root=path.resolve('.'),out=path.join(root,'.build/maintenance/ui');fs.mkdirSync(out,{recursive:true});
const licences=JSON.parse(execFileSync('python3',[path.join(root,'studio/backend.py'),'--root',path.join(out,'data'),'--shared',process.env.CANTOSYNC_QA_SHARED_RESOURCES||path.join(root,'dist/AniCanto.app/Contents/Resources')],{input:JSON.stringify({op:'licenses'}),maxBuffer:100*1024*1024}).toString()).result;
assert(licences.length>20,'Packaged third-party inventory is missing');
const CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' asset: http://asset.localhost data:; media-src 'self' asset: http://asset.localhost blob:; connect-src ipc: http://ipc.localhost; object-src 'none'; base-uri 'none'; frame-src 'none'";
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CANTOSYNC_QA_BROWSER?{executablePath:process.env.CANTOSYNC_QA_BROWSER}:{})});let reports=[];
 for(const lang of ['en','zh-HK']){
  const p=await browser.newPage({viewport:{width:1500,height:960}}),errors=[];p.on('pageerror',e=>errors.push(e.message));let media=0,failLicences=false,subtitleUpdateDone=null;
  await p.route('http://127.0.0.1:18732/',async route=>{const response=await route.fetch();await route.fulfill({response,headers:{...response.headers(),'Content-Security-Policy':CSP}})});
  await p.exposeBinding('nativeFixture',async(_ctx,name,args)=>{
   if(name==='studio_media'){media++;}
   if(name==='studio_rpc'&&args.op==='licenses'){if(failLicences)throw Error('Simulated disconnected runtime');return licences;}
   const r=await fetch('http://127.0.0.1:18732/api',{method:'POST',body:JSON.stringify({name,args})}),data=await r.json();if(data.error)throw Error(data.error);if(args.op==='configure'&&args.params?.settings?.subtitleSelection==='custom'){subtitleUpdateDone?.();subtitleUpdateDone=null;}return data.result;
  });
  await p.addInitScript(()=>{const listeners=new Map();window.__TAURI__={core:{invoke:(name,args={})=>window.nativeFixture(name,args),convertFileSrc:p=>'/media?path='+encodeURIComponent(p)},event:{listen:async(name,fn)=>{listeners.set(name,fn);return()=>listeners.delete(name)}},window:{getCurrentWindow:()=>({close:async()=>{}})}};});
  await p.goto('http://127.0.0.1:18732/');await p.waitForSelector('#welcome-language');await p.selectOption('#welcome-language',lang);await p.waitForTimeout(100);
  await p.locator('[data-action=use-terms]').click();
  assert.equal(await p.locator('.drawer-header > span').innerText(),lang==='en'?'Media, voices and model terms':'影片、聲音及模型使用條款');
  assert((await p.locator('.drawer-body').innerText()).includes(lang==='en'?'AniCanto is a local learning and creative tool.':'AniCanto 是本機學習及創作工具。'));
  await p.locator('.drawer [data-action=close-drawer]').click();
  await p.locator('#use-terms-checkbox').uncheck();await p.waitForFunction(()=>document.querySelector('[data-action=enter]').disabled);
  await p.locator('#use-terms-checkbox').check();await p.waitForFunction(()=>!document.querySelector('[data-action=enter]').disabled);
  await p.locator('#setup-details').evaluate(el=>el.open=true);await p.locator('#download-management > summary').click();
  assert(await p.locator('[data-action=cleanup-downloads]').isVisible(),'Model storage cleanup is inaccessible');assert.equal(await p.locator('[data-action=cleanup-downloads]').count(),1);
  await p.locator('[data-action=about]').click();await p.waitForSelector('#license-list details');assert((await p.locator('#license-list details').count())>20);assert((await p.locator('.about-project + .about-section').first().innerText()).length>0);assert((await p.locator('.drawer-body').innerText()).includes(lang==='en'?'Local AI, offline after setup':'本機 AI，部署後可離線使用'));assert.equal(await p.locator('#privacy-policy > summary').innerText(),lang==='en'?'Privacy policy':'私隱政策');await p.locator('#privacy-policy').evaluate(el=>el.open=true);const privacy=await p.locator('#privacy-policy').innerText();assert(privacy.includes(lang==='en'?'does not upload your videos':'不會將你的影片'));assert(privacy.includes(lang==='en'?'IP address':'IP 位址'));await p.locator('#application-license-text').evaluate(el=>el.parentElement.open=true);assert((await p.locator('#application-license-text').innerText()).includes('Permission is hereby granted'));
  const sample=licences.find(r=>r.text&&r.text.length>100);await p.fill('#license-search',sample.name);await p.locator('#license-list details').first().evaluate(el=>el.open=true);assert((await p.locator('#license-list').innerText()).length>100);
  await p.screenshot({path:path.join(out,lang+'-licences.png')});await p.locator('.drawer [data-action=close-drawer]').click();failLicences=true;await p.locator('[data-action=about]').click();await p.waitForSelector('[data-action=retry-licenses]');assert((await p.locator('#application-license-text').textContent()).includes('Permission is hereby granted'));failLicences=false;await p.locator('[data-action=retry-licenses]').click();await p.waitForSelector('#license-list details');await p.locator('.drawer [data-action=close-drawer]').click();
  await p.locator('[data-action=guide]').click();assert.equal(await p.locator('#help-toc button').count(),17);
  assert.equal(await p.locator('.drawer-header > span').innerText(),lang==='en'?'Help centre':'使用手冊');
  if(lang==='en')assert(!/[\u3400-\u9fff]/.test(await p.locator('#help-article').innerText()),'English help shows Chinese content');
  for(let i=0;i<17;i++){await p.locator('#help-toc button').nth(i).click();assert((await p.locator('#help-article').innerText()).length>200);}
  await p.fill('#help-search',lang==='en'?'generation-limit':'解碼達上限');assert.equal(await p.locator('#help-toc button').count(),1);assert(await p.locator('#help-search').evaluate(el=>el===document.activeElement));assert((await p.locator('#help-article').innerText()).toLowerCase().includes('generation-limit'));
  await p.fill('#help-search','qzxnoresult');assert.equal(await p.locator('#help-toc button').count(),0);assert((await p.locator('#help-article').innerText()).includes(lang==='en'?'No matching chapters':'找不到相符章節'));
  await p.fill('#help-search',lang==='en'?'Ollama':'Ollama');assert((await p.locator('#help-toc button').count())>=1);await p.screenshot({path:path.join(out,lang+'-help-search.png')});await p.fill('#help-search','');await p.locator('#help-toc button').first().click();await p.screenshot({path:path.join(out,lang+'-help.png')});await p.locator('.drawer [data-action=close-drawer]').click();
  await p.locator('[data-action=mode][data-value=basic]').click();await p.locator('[data-action=enter]').click();await p.waitForSelector('#video');await p.waitForTimeout(150);assert.equal(media,0,'Default-off preview invoked expensive media RPC');assert.equal(await p.locator('#video').getAttribute('src'),null);assert(await p.locator('.waiting-scene').isVisible());
  assert.equal(await p.locator('[data-subtitle]').count(),0,'Basic subtitles must be automatic');
  await p.screenshot({path:path.join(out,lang+'-preview-off.png')});const sprite=p.locator('.assistant-sprite').first();await p.waitForFunction(()=>document.querySelector('.assistant-sprite')?.dataset.draws>1);const before=await sprite.evaluate(el=>el.toDataURL());await p.waitForTimeout(300);assert.notEqual(before,await sprite.evaluate(el=>el.toDataURL()),'Assistant joints do not animate');
  await p.locator('.waiting-scene [data-action=toggle-preview]').click();await p.waitForFunction(()=>document.querySelector('#video')?.readyState>=2);assert.equal(media,1);assert(!(await p.locator('.waiting-scene').isVisible()));await p.locator('[data-action=preview-control]').click();assert.equal(await p.locator('#video').getAttribute('src'),null);assert(await p.locator('.waiting-scene').isVisible());
  await p.locator('.appbar [data-action=mode][data-value=expert]').click();await p.waitForSelector('.studio.expert');assert.equal(media,1,'Mode change reloaded preview while off');assert(await p.locator('.waiting-scene').isVisible());
  await p.locator('[data-action=inspector][data-value=production]').click();const learning=p.locator('[data-subtitle=dual]');assert(await learning.isVisible());
  const subtitleUpdate=()=>new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Subtitle configuration did not finish')),10000);subtitleUpdateDone=()=>{clearTimeout(timer);resolve();};});
  const learningWasChecked=await learning.isChecked();await Promise.all([subtitleUpdate(),learning.setChecked(!learningWasChecked)]);await p.waitForSelector('[data-action=automatic-subtitles]');
  assert.equal(await learning.isChecked(),!learningWasChecked);
  await p.locator('[data-action=automatic-subtitles]').click();
  await p.locator('[data-action=page][data-value=terminal]').click();await p.waitForSelector('#log-source option',{state:'attached'});const sources=await p.locator('#log-source').innerText();for(const name of lang==='en'?['Workflow summary','Process output','MLX translation','Ollama translation']:['流程摘要','程序詳細紀錄','MLX 翻譯紀錄','Ollama 翻譯紀錄'])assert(sources.includes(name));
  assert.deepEqual(errors,[]);reports.push({language:lang,chapters:17,packagedLicenceRows:licences.length,nativeCSP:true,licenceFailureRetry:true,previewDefaultOff:true,previewReleased:true,assistantAnimated:true,logCategories:true,learningSubtitleControl:true});await p.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'acceptance.json'),JSON.stringify(reports,null,2));console.log(JSON.stringify(reports));
})().catch(e=>{console.error(e);process.exit(1)});
