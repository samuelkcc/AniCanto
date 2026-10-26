// First-paint regression: saved appearance beats stale cache before delayed state RPC.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),http=require('node:http'),path=require('node:path');
const web=path.resolve(__dirname,'../studio/web');
const server=http.createServer((req,res)=>{
 const file=path.resolve(web,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/\/$/,'/index.html'));
 if(!file.startsWith(web+path.sep)){res.writeHead(403).end();return;}
 fs.readFile(file,(error,data)=>{if(error){res.writeHead(404).end();return;}res.setHeader('Content-Type',({'.js':'text/javascript','.html':'text/html','.css':'text/css','.png':'image/png','.otf':'font/otf'})[path.extname(file)]||'application/octet-stream');res.end(data);});
});
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const url='http://127.0.0.1:'+server.address().port;const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'}),results=[];
try{for(const pref of ['light','dark','system'])for(const os of ['light','dark']){
 const page=await browser.newPage({colorScheme:os,viewport:{width:1500,height:960}}),errors=[],calls=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.exposeBinding('fixture',async(_,name,args={})=>{
  calls.push({name,args});
  if(name==='studio_appearance')return null;
  if(name==='studio_status'){await new Promise(r=>setTimeout(r,800));return {runtimeReady:true,running:null};}
  if(name==='studio_rpc'){
   if(args.op==='state'){await new Promise(r=>setTimeout(r,800));return {language:'en',mode:'basic',queue:[],settings:{appearance:pref,animeTheme:'studio',ttsBackend:'drama3'},ui:{}};}
   if(args.op==='configure')return {};
   if(args.op==='models')return [];
   if(args.op==='plan')return {setupReady:true,downloads:[],runtimeInventory:[],hardware:{memoryGB:64},blockers:[]};
   if(args.op==='snapshot')return {};
   throw Error('Unexpected RPC '+args.op);
  }
  throw Error('Unexpected native call '+name);
 });
 await page.addInitScript(({pref})=>{
  window.__ANICANTO_APPEARANCE__=pref;
  localStorage.setItem('anicanto-appearance',pref==='dark'?'light':'dark');
  window.__TAURI__={core:{invoke:(n,a)=>window.fixture(n,a),convertFileSrc:p=>p},event:{listen:async()=>()=>{}},window:{getCurrentWindow:()=>({close:async()=>{}})}};
  window.framesObserved=[];
  const sample=()=>{if(document.querySelector('#app')?.childElementCount)window.framesObserved.push({dark:document.documentElement.classList.contains('dark'),bg:getComputedStyle(document.documentElement).backgroundColor});requestAnimationFrame(sample);};requestAnimationFrame(sample);
 },{pref});
 await page.goto(url);
 await page.waitForFunction(()=>document.querySelector('#app').childElementCount>0);
 const expected=pref==='dark'||pref==='system'&&os==='dark';
 assert.equal(await page.evaluate(()=>document.documentElement.classList.contains('dark')),expected);
 await page.waitForFunction(()=>!document.querySelector('#welcome-language')?.disabled);
 const frames=await page.evaluate(()=>framesObserved);assert(frames.length>0);assert(frames.every(f=>f.dark===expected),JSON.stringify({pref,os,frames}));
 assert(frames.every(f=>f.bg===(expected?'rgb(28, 26, 34)':'rgb(246, 245, 248)')));
 assert.equal(await page.evaluate(()=>localStorage.getItem('anicanto-appearance')),pref);
 assert.equal(calls.filter(c=>c.name==='studio_appearance').length,1);
 await page.emulateMedia({colorScheme:os==='dark'?'light':'dark'});
 const switched=pref==='system'?!expected:expected;
 await page.waitForFunction(v=>document.documentElement.classList.contains('dark')===v,switched);
 if(pref==='system')assert.equal(calls.filter(c=>c.name==='studio_appearance').length,2);
 assert.deepEqual(errors,[]);results.push({pref,system:os,frames:frames.length,firstPaintMatches:true,delayedBackendNoFlash:true,staleCacheIgnored:true,systemChangeRespected:true});await page.close();
}
// Browser / fresh profile fallback must also follow the OS, never default dark.
for(const os of ['light','dark']){
 const p=await browser.newPage({colorScheme:os});await p.goto(url);await p.waitForSelector('#app .welcome');assert.equal(await p.evaluate(()=>document.documentElement.classList.contains('dark')),os==='dark');await p.reload();assert.equal(await p.evaluate(()=>anicantoAppearance.initial),'system');await p.close();
}
fs.mkdirSync('.build/appearance75',{recursive:true});fs.writeFileSync('.build/appearance75/browser-appearance.json',JSON.stringify({cases:results,newProfileFollowsSystem:true,jsErrors:0},null,2));console.log(JSON.stringify(results));
}finally{await browser.close();await new Promise(r=>server.close(r));}})().catch(e=>{console.error(e);server.close();process.exit(1)});
