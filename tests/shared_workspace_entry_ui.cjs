const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');

const root=path.resolve(__dirname,'../studio/web');
const mime={'.js':'text/javascript','.css':'text/css','.html':'text/html','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.otf':'font/otf'};
const server=http.createServer((req,res)=>{
 const file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://local').pathname));
 if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
 fs.readFile(file,(error,data)=>{if(error){res.writeHead(404).end();return;}res.writeHead(200,{'content-type':mime[path.extname(file)]||'application/octet-stream'}).end(data);});
});

(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,executablePath:process.env.CANTOSYNC_QA_BROWSER||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  for(const language of ['en','zh-HK']){
   const page=await browser.newPage({viewport:{width:1280,height:850}}),errors=[];
   page.on('pageerror',error=>errors.push(error.message));
   await page.addInitScript(()=>{
    const state={language:'en',mode:'basic',queue:[{id:'entry-test',video:'test.mp4',status:'waiting'}],selected:'entry-test',settings:{ttsBackend:'drama3',selectedEngines:['drama3'],dubLanguages:['yue'],subtitleModes:['yue'],appearance:'light'},ui:{},useTermsAccepted:true};
    let snapshots=0,releaseStatus,releaseSnapshot;
    window.entryFixture={get snapshots(){return snapshots;},get mode(){return state.mode;},get theme(){return state.settings.animeTheme;},releaseStatus:()=>releaseStatus?.({runtimeReady:true,running:null}),releaseSnapshot:()=>releaseSnapshot?.({})};
    window.__TAURI__={core:{convertFileSrc:p=>p,invoke:async(name,args={})=>{
     if(name==='studio_status')return new Promise(resolve=>{releaseStatus=resolve});
     if(name==='studio_rpc'){
      if(args.op==='state')return state;
      if(args.op==='configure'){const settings={...state.settings,...args.params.settings};Object.assign(state,args.params);state.settings=settings;return state;}
      if(args.op==='snapshot'){snapshots++;return new Promise(resolve=>{releaseSnapshot=resolve});}
      if(args.op==='models')return [];
      if(args.op==='plan')return {setupReady:true,canDeployModels:true,qualityPresets:[]};
      return {};
     }
     throw Error('Unexpected operation: '+name);
    }},event:{listen:async()=>()=>{}}};
   });
   await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
   await page.locator('.welcome-startup [role=progressbar]').waitFor();
   assert.equal(await page.locator('[data-action=enter]').isDisabled(),true);
   await page.locator('[data-action=mode][data-value=expert]').click();
   assert((await page.locator('[data-action=mode][data-value=expert]').getAttribute('class')).includes('active'));
   await page.locator('[data-action=theme][data-value=ocean]').click();
   assert.equal(await page.locator('.welcome-startup canvas.assistant-sprite').getAttribute('data-theme'),'ocean');
   await page.waitForFunction(()=>Number(document.querySelector('.welcome-startup canvas.assistant-sprite')?.dataset.draws)>1);
   const firstPose=await page.locator('.welcome-startup canvas.assistant-sprite').evaluate(el=>({pixels:el.toDataURL(),draws:Number(el.dataset.draws)}));
   await page.waitForFunction(draws=>Number(document.querySelector('.welcome-startup canvas.assistant-sprite')?.dataset.draws)>draws+4,firstPose.draws);
   assert.notEqual(await page.locator('.welcome-startup canvas.assistant-sprite').evaluate(el=>el.toDataURL()),firstPose.pixels);
   if(language==='en'&&process.env.CANTOSYNC_QA_SCREENSHOT){await page.waitForFunction(()=>document.querySelector('.welcome-cover img')?.naturalWidth>0&&document.querySelector('.welcome-startup canvas.assistant-sprite')?.dataset.renderer);await page.screenshot({path:process.env.CANTOSYNC_QA_SCREENSHOT});}
   await page.evaluate(()=>window.entryFixture.releaseStatus());
   await page.waitForFunction(()=>window.entryFixture.snapshots===1);
   assert.equal(await page.locator('.welcome-startup').count(),1);
   assert.equal(await page.locator('[data-action=enter]').isDisabled(),true);
   await page.evaluate(()=>window.entryFixture.releaseSnapshot());
   await page.waitForFunction(()=>document.querySelector('.welcome-startup')===null);
   assert.equal(await page.evaluate(()=>window.entryFixture.mode),'expert');
   assert.equal(await page.evaluate(()=>window.entryFixture.theme),'ocean');
   assert.equal(await page.locator('[data-action=enter]').isEnabled(),true);
   await page.selectOption('#welcome-language',language);
   await page.locator('[data-action=enter]').click();
   await page.waitForFunction(()=>window.entryFixture.snapshots===2);
   assert.equal(await page.locator('.studio').count(),1);
   assert.equal(await page.locator('#entry-loader').count(),0);
   await page.evaluate(()=>window.entryFixture.releaseSnapshot());
   assert.equal(errors.length,0,errors.join('\n'));
   await page.close();
  }
  console.log('Welcome startup assistant, responsive mode/theme, and direct workspace entry passed');
 }finally{await browser.close();server.close();}
})().catch(error=>{console.error(error);server.close();process.exitCode=1;});
