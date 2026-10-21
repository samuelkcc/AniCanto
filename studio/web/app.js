import {initialLanguage} from './interface-language.js';
import {InstallationLog} from './setup-progress.js';
import {reviewPage} from './review-page.js';
import {captureReviewViewport,restoreReviewViewport} from './review-viewport.js';
import {workerText,projectWarning} from './workflow-text.js';
import {matchingPreset,presetPlan,setupParameters,presetReasons} from './quality-presets.js';
import {icon} from './icons.js';
import {syncAssistantMotion} from './assistant-motion.js';
import {ConversionQueue,pendingVideos} from './conversion-queue.js';
import {orderControls,installQueueOrder} from './queue-order.js';
import {ENGINES,THEMES,PHASES,esc,tc,shortTime,bytes,filename,takeAt,cueAt,captionAt,themeAssets,mergeJourney,visibleMilestones,selectableEngines} from './model.js';
import {translate} from './i18n.js';
import {APP_VERSION} from './assets/app-version.js';
import {APPLICATION_LICENSE} from './assets/application-license.js';
import {chapters,searchChapters,articleHTML} from './help.js';
import {aboutCopy} from './about-copy.js';
import {COPYRIGHT,PROJECT_URL} from './product-info.js';
import {licenceCopy} from './licence-copy.js';
import {downloadSourcesSection,renderDownloadSources} from './download-sources.js';
import {USE_TERMS} from './assets/use-terms.js';

const $=(s,root=document)=>root.querySelector(s),$$=(s,root=document)=>[...root.querySelectorAll(s)];
const native=window.__TAURI__;
const invoke=(name,args={})=>native?native.core.invoke(name,args):Promise.reject(new Error('Open AniCanto desktop to use the local processing engine.'));
const rpc=(op,params={})=>invoke('studio_rpc',{op,params});
let setupSelection=null,selectedQuality=null;
const termsKey='anicanto-use-terms-'+USE_TERMS.sha256;
let localTermsAccepted=localStorage.getItem(termsKey)==='accepted';
const termsReady=()=>localTermsAccepted||state.useTermsAccepted===true;
async function syncUseTerms(){if(runtimeReady&&localTermsAccepted&&!state.useTermsAccepted){await rpc('accept-use-terms',{accepted:true,sha256:USE_TERMS.sha256,language:state.language});state.useTermsAccepted=true;}}
async function showUseTerms(){const lang=state.language==='en'?'en':'zh-HK';await showDrawer(USE_TERMS.title[lang],USE_TERMS.paragraphs[lang].map(p=>`<p>${esc(p)}</p>`).join('')+`<p><strong>Built with Fish Audio</strong> · Fish Audio Community License v1.0</p><small>${esc(USE_TERMS.revision)}</small>`);}
// A composition is selected once; changing views or production state cannot
// replace the cast underneath an active animation.
const welcomeVariant=1+Math.floor(Math.random()*4);
let pendingConfig=null,deployAfterBootstrap=false,initializing=true,modelChoices=[],pendingSwitch=null,setupReturn=null,switchRevision=0,switchSession=0,switchBusy=false,modelStartBusy=false,switchStarting=false;
let pendingStartupMode=null,welcomeThemeTouched=false,startupMessage='Preparing your studio…';
const firstLanguage=initialLanguage(localStorage.getItem('anicanto-language'),navigator.languages||[navigator.language]);
async function configure(params){if(params.language)localStorage.setItem('anicanto-language',params.language);if(!runtimeReady){pendingConfig={...pendingConfig,...params,settings:{...pendingConfig?.settings,...params.settings}};if(params.mode)state.mode=params.mode;if(params.language){state.language=params.language;if(!params.preserveProductionSettings){state.settings.dubLanguages=params.language==='en'?['yue','en']:['yue'];state.settings.subtitleModes=params.language==='en'?['yue','english','dual','original']:['yue','original'];state.settings.subtitleSelection='automatic';}}Object.assign(state.settings,params.settings||{});return state;}return rpc('configure',params)}
let state={language:firstLanguage,mode:'basic',queue:[],settings:{ttsBackend:'drama3',selectedEngines:['drama3'],dubLanguages:['yue','en'],subtitleModes:['yue','english','dual','original'],subtitleSelection:'automatic',includeOriginal:true,productionMode:'normal',roleAnalysisMode:'independent'},ui:{}},
 screen='welcome',page='edit',snapshot={},draft=null,dirty=false,selectedCue=0,language='yue',inspector='dialogue',dialogueTab='listen',
 themeKey='studio',runtimeReady=false,active=null,journey=null,runID=null,
 plan=null,inventory=[],setupEvent=null,setupFailure='',logs='',logSearch='',logSource='',logSources=[],errorsOnly=false,followLogs=true,follow=false,sourceTime=0,
 duration=0,mediaPath='',mediaKind='source',previewToken=0,pollBusy=false,closing=false,undoStack=[],redoStack=[],zoom=12,
 navVisible=true,browserVisible=true,inspectorVisible=true,removing=false,exportingLogs=false,retakeEngine=null,auditionEngine=null,captionLanguage='yue';
const rememberedTheme=localStorage.getItem('anicanto-theme');
if(rememberedTheme in THEMES)themeKey=rememberedTheme;
let timelineViewport={rowID:null,left:0,top:0};
let timelineDragging=false,timelineSuppressClickUntil=0;
function rememberTimelineViewport(){const el=$('.timeline-scroll');if(el)timelineViewport={rowID:el.dataset.rowId,left:el.scrollLeft,top:el.scrollTop};}
let previewEnabled=false,previewLoading=false,previewError='',previewProgress=null,previewFallback=false,previewOutput=false,previewTimer=null,helpQuery='',helpChapter='start',aboutSession=0;
const finishedRunIDs=new Set(),conversionQueue=new ConversionQueue(),mediaRequests=new Map();
let starting=false,startPromise=null,finishingRun=false,finishChain=Promise.resolve();
let enteringWorkspace=false;
let queueRevision=0,queueRenderPending=false,queueFocus=null;
const queueOrder=installQueueOrder({move:moveQueueRow,step:stepQueueRow,updated:()=>{if(queueRenderPending){queueRenderPending=false;render()}else refreshQueueViews();restoreQueueFocus()},error:e=>toast(e.message||e,true)});
const queueControls=i=>orderControls(state.queue,i,{t,esc,icon});
function restoreQueueFocus(){if(!queueFocus)return;const {id,action}=queueFocus;queueFocus=null;const card=$$('[data-queue-id]').find(el=>el.dataset.queueId===id);const control=action==='handle'?card?.querySelector('[data-queue-handle]'):card?.querySelector(`[data-action="${action}"]:not(:disabled)`);(control||card?.querySelector('[data-queue-handle]'))?.focus({preventScroll:true});}
function refreshQueueViews(){
 if(queueOrder.busy)return;
 const focus=document.activeElement?.closest('.queue-order-controls');
 if(focus)queueFocus={id:focus.closest('[data-queue-id]').dataset.queueId,action:document.activeElement.dataset.action||'handle'};
 const shelf=$('#shelf');if(shelf){const top=shelf.scrollTop;shelf.innerHTML=shelfCards();shelf.scrollTop=top;}
 if(['queue','projects'].includes(page)){const el=$('.main .page');if(el){const top=el.scrollTop;el.outerHTML=fullPage();$('.main .page').scrollTop=top;}}
 restoreQueueFocus();
}
async function moveQueueRow(id,beforeID){
 ++queueRevision;queueFocus={id,action:document.activeElement?.dataset.action||'handle'};
 try{state=await rpc('move-video',{id,beforeID});conversionQueue.reorder(state.queue);toast(t(active?'Order changed. The current video continues; waiting videos follow the new order.':'Video order saved'));}
 finally{++queueRevision;}
}
async function stepQueueRow(id,direction){const index=state.queue.findIndex(r=>r.id===id),target=index+direction;if(index<0||target<0||target>=state.queue.length)return;await moveQueueRow(id,direction<0?state.queue[target].id:state.queue[target+1]?.id??null);}

const startLabel=()=>starting?'Starting…':state.mode==='basic'&&state.queue.some(r=>['attention','paused'].includes(r.status))?'Resume all unfinished videos':state.mode==='basic'&&row()?.status==='complete'&&pendingVideos(state.queue).length?'Start remaining videos':row()?.status==='paused'?'Resume':row()?.output&&snapshot.issues?.some(x=>x.status!=='user-choice-saved')?'Retry AI repair':row()?.output?'Produce a new version':'Start conversion';
const t=s=>translate(s,state.language);
const row=()=>state.queue.find(r=>r.id===state.selected);
const cues=()=>draft?.segments||[];
const current=()=>cues()[selectedCue];
const requiresEnglish=()=>state.settings.dubLanguages?.includes('en')===true;
const engineBlocked=id=>id==='wsyue'&&requiresEnglish();
const engineInstalled=id=>inventory.some(r=>r.engine===id&&r.installed&&!r.retired);
const engineChoices=()=>selectableEngines(state.platform||(plan?.hardware?.platform==='windows'?'win32':plan?.hardware?.platform),plan?.hardware).map(([id,label])=>[id,label]);
const engineMenu=()=>engineChoices().map(([id,label])=>[id,label+(engineBlocked(id)?' · '+t('Cantonese only'):engineInstalled(id)?'':id===state.settings.ttsBackend&&setupFailure?' ('+t('Setup failed')+')':id===state.settings.ttsBackend&&active?.setup?' ('+t('Downloading')+')':' ('+t('Automatic download')+')'),engineBlocked(id)]);
const engineName=e=>ENGINES.find(r=>r[0]===e)?.[1]||e;
const asset=path=>native?native.core.convertFileSrc(path):path;
const button=(action,label,ico,klass='',attrs='')=>`<button data-action="${action}" class="${klass} ${['start','start-all'].includes(action)?'action-start':['pause','close-paused'].includes(action)?'action-pause':''}" ${attrs} title="${esc(t(label))}">${ico?icon(ico):''}${label?`<span>${esc(t(label))}</span>`:''}</button>`;
const ib=(action,label,ico,attrs='')=>`<button data-action="${action}" class="icon ${action==='pause'?'action-pause':''}" title="${esc(t(label))}" aria-label="${esc(t(label))}" ${attrs}>${icon(ico)}</button>`;
const check=(key,label,value,extra='')=>`<label class="check"><input type="checkbox" data-setting="${key}" ${value?'checked':''} ${extra}>${esc(t(label))}</label>`;
const field=(label,html)=>`<div class="field"><label>${esc(t(label))}</label>${html}</div>`;
const select=(key,items,value,attrs='')=>`<select data-setting="${key}" ${attrs}>${items.map(([k,label,disabled])=>`<option value="${esc(k)}" ${value===k?'selected':''} ${disabled?'disabled':''}>${esc(t(label))}</option>`).join('')}</select>`;
const statusName=s=>t(({waiting:'Waiting',paused:'Paused',running:'Processing',complete:'Complete',attention:'Needs attention'})[s]||s||'Waiting');
const empty=(title,body,ico='edit')=>`<div class="empty">${icon(ico)}<h3>${esc(t(title))}</h3>${body?`<p>${esc(t(body))}</p>`:''}</div>`;
let toastTimer,roleQuery='';
function toast(message,error=false){const el=$('#toast');el.textContent=t(String(message));el.hidden=false;el.style.background=error?'#a2373f':'';clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.hidden=true,error?9000:3500)}
async function enterWorkspace(){
 if(enteringWorkspace||!termsReady())return;
 enteringWorkspace=true;
 try{
  screen='studio';page='edit';render();
  // The ready Welcome screen has already shown startup progress. Paint the
  // workspace immediately; its themed waiting scene covers project loading.
  await new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)));
  await syncUseTerms();
  await refreshSnapshot();
  await loadMedia();
 }finally{enteringWorkspace=false;}
}
async function safely(work){try{return await work()}catch(e){toast(e.message||e,true);return undefined}}
function applyTheme(){const a=themeAssets(themeKey);document.documentElement.style.setProperty('--accent',a.color);document.documentElement.style.setProperty('--tint',`color-mix(in srgb, ${a.color} 9%, var(--surface))`);const appearance=state.settings.appearance||'system';document.documentElement.classList.toggle('dark',appearance==='dark'||appearance==='system'&&matchMedia('(prefers-color-scheme:dark)').matches);document.documentElement.lang=state.language==='en'?'en':'zh-HK'}
function brand(){return `<div class="brand"><span class="brand-mark">${icon('logo')}</span>AniCanto</div>`}
function render(){
 if(queueOrder.busy){queueRenderPending=true;return;}
 const reviewViewport=captureReviewViewport();
 rememberTimelineViewport();
 const previousScene=$('.waiting-scene');const previousTheme=previousScene?.querySelector('.busy-assistant')?.dataset.theme;
 const video=$('#video');const wasPlaying=video&&!video.paused,position=video?.currentTime||0;
 applyTheme();$('#app').innerHTML=screen==='welcome'?welcome():studio();
 if(screen==='studio'&&page==='edit'){
  if(video){$('#video').replaceWith(video);video.currentTime=position;if(wasPlaying)video.play().catch(()=>{});}
  if(previousScene&&previousTheme===(themeKey==='ensemble'?'energy':themeKey)&&previousScene.querySelectorAll('.busy-assistant').length===(themeKey==='ensemble'?3:1))$('.waiting-scene')?.replaceWith(previousScene);
  bindVideo();updatePreviewSurface();updatePlayer();renderTranscript();renderTimeline();updateProgress();updateAudition();
 }
 if(screen==='studio'&&page==='terminal')updateLogs();
 if(screen==='studio'&&page==='roles')filterRoles();
 if(screen==='welcome')updateSetup();
 restoreReviewViewport(reviewViewport);
 syncAssistantMotion();
 paintInstallation();
}
function welcome(){const a=themeAssets(themeKey,welcomeVariant);return `<div class="welcome">
 <section class="welcome-art">${brand()}<div class="welcome-heading"><h1>${esc(t('Your anime. A whole new voice.'))}</h1><p>${esc(t('Hong Kong Cantonese · English · Just for fun'))}</p></div><div class="welcome-cover"><img src="${a.cover}" data-theme="${a.key}" data-character="assistant-${a.key}" alt="AniCanto assistant ensemble" draggable="false"></div><div class="welcome-credit">SCKC / ANIME DUBBING PLAYGROUND</div></section>
 <section class="welcome-controls"><div class="welcome-inner">
 <div class="welcome-language"><label for="welcome-language">Language</label><select id="welcome-language" ${initializing?'disabled':''}><option value="en" ${state.language==='en'?'selected':''}>English</option><option value="zh-HK" ${state.language==='zh-HK'?'selected':''}>香港繁體中文</option></select></div>
 <div class="welcome-title"><h2>${esc(t('Welcome to your dubbing studio'))}</h2><p>${esc(t('Bring an episode. Pick a voice. Hear your characters in a new language.'))}</p></div>
 ${initializing?`<div class="welcome-startup" role="status" aria-live="polite"><div class="welcome-startup-assistant">${busyAssistant(themeKey)}</div><div class="welcome-startup-copy"><strong>${esc(t('Your assistant is preparing the studio'))}</strong><small>${esc(t(startupMessage))}</small><div class="download-fill indeterminate" role="progressbar" aria-label="${esc(t(startupMessage))}"><i></i></div></div></div>`:''}
 <div class="welcome-modes">${[['basic','Basic mode','Choose Cantonese, English or both. Audio and subtitles are configured automatically.','spark'],['expert','Expert mode','A timeline, individual auditions, retakes and detailed editing.','settings']].map(([key,label,body,ico])=>`<button class="mode-card ${state.mode===key?'active':''}" data-action="mode" data-value="${key}">${icon(ico)}<div class="grow"><h4>${esc(t(label))}</h4><div class="description">${esc(t(body))}</div></div><span class="mode-dot"></span></button>`).join('')}</div>
 <details id="setup-details" ${!initializing&&(!runtimeReady||active?.setup||plan&&!plan.setupReady)?'open':''}><summary>${esc(t('Local models & setup'))}</summary><div id="setup-content"></div></details>

 <div class="welcome-terms"><label class="check"><input id="use-terms-checkbox" type="checkbox" ${termsReady()?'checked':''}>${esc(t('I agree to the media, voice and model terms'))}</label>${button('use-terms','Read use conditions','info','quiet')}</div>
 ${button('enter','Enter the studio','chevron','primary welcome-enter',runtimeReady&&!initializing&&termsReady()?'':'disabled')}
 <div class="row spread">${button('guide','Help centre','help')}${button('about','About & licences','info')}</div>
 <div class="welcome-footer"><p>${esc(t('Made by SCKC'))} · ${esc(t('Hong Kong Cantonese culture'))}</p><div class="row spread" style="margin-top:12px"><div class="theme-dots">${Object.keys(THEMES).map(k=>`<button class="theme-dot ${k===themeKey?'active':''}" style="background:${THEMES[k]}" data-action="theme" data-value="${k}" aria-label="${k}" title="${k}"></button>`).join('')}</div><small>${esc(APP_VERSION)} · AniCanto · ${esc(COPYRIGHT)}</small></div></div>
 </div></section></div>`}
const installationLog=new InstallationLog();
let installationOpen=false,installationFollow=true,installationTop=0,installationFrame=0;
const installationActive=()=>!!(active?.setup||active?.action==='model-maintenance');
function beginInstallation(){installationLog.reset();installationLog.append(t('Preparing components…'));setupFailure='';}
function installationDetails(){return `<details class="installation-details" ${installationOpen?'open':''}><summary>${esc(t('Installation details'))}</summary><div class="row spread"><label class="check"><input type="checkbox" data-install-follow ${installationFollow?'checked':''}>${esc(t('Follow latest'))}</label>${button('copy-installation','Copy details','copy')}</div><pre class="installation-console" tabindex="0" aria-label="${esc(t('Installation details'))}"></pre></details>`;}
function installationProgress(){return `<div class="installation-summary"><strong data-install-summary></strong><small data-install-phase></small><div class="download-fill indeterminate"><i></i></div><div class="row spread installation-numbers"><small data-install-bytes></small><small data-install-speed></small></div></div>`;}
function paintInstallation(){
 const summary=installationLog.summary,transfer=setupEvent?.download,n=Number(transfer?.bytesReceived??transfer?.receivedBytes??0),total=Number(transfer?.totalBytes||0),percent=total?Math.min(100,Math.max(0,100*n/total)):null;
 for(const el of $$('[data-install-summary]'))el.textContent=[t(summary.category||'Processing environment'),summary.model].filter(Boolean).join(' · ');
 for(const el of $$('[data-install-phase]'))el.textContent=t(summary.phase||'Preparing components…');
 for(const el of $$('[data-install-bytes]'))el.textContent=total?`${bytes(n)} / ${bytes(total)} · ${Math.floor(percent)}%`:t('Checking and preparing local files…');
 for(const el of $$('[data-install-speed]'))el.textContent=transfer?.bytesPerSecond?`${bytes(transfer.bytesPerSecond)}/s`:'';
 for(const el of $$('.installation-summary .download-fill')){el.classList.toggle('indeterminate',percent===null);el.querySelector('i').style.width=(percent??30)+'%';}
 for(const el of $$('.installation-console')){const top=el.scrollTop;if(el.textContent!==installationLog.text)el.textContent=installationLog.text;el.scrollTop=installationFollow?el.scrollHeight:top||installationTop;}
 let badge=$('#installation-badge');
 if(screen==='studio'&&(installationActive()||setupFailure)){
  if(!badge){badge=document.createElement('button');badge.id='installation-badge';badge.dataset.action='installation-details';badge.innerHTML='<span class="loading-mark"></span><span class="installation-badge-text"></span>';document.body.append(badge);}
  badge.classList.toggle('attention',!!setupFailure&&!installationActive());
  badge.querySelector('.loading-mark').hidden=!installationActive();
  badge.querySelector('.installation-badge-text').textContent=setupFailure&&!installationActive()?t('Setup failed · view details'):t('Models downloading / preparing')+(percent===null?'':` · ${Math.floor(percent)}%`);
 }else badge?.remove();
}
function scheduleInstallation(){if(!installationFrame)installationFrame=requestAnimationFrame(()=>{installationFrame=0;paintInstallation()});}
document.addEventListener('toggle',e=>{if(e.target.matches?.('.installation-details'))installationOpen=e.target.open;},true);
document.addEventListener('scroll',e=>{if(e.target.matches?.('.installation-console'))installationTop=e.target.scrollTop;},true);
function setupStatus(){
 const phase=setupEvent?.download?.state;
 if(phase==='verifying')return 'Verifying downloaded files…';
 if(phase==='reused')return 'Using downloaded files';
 if(phase==='connecting'||phase==='resuming'||phase==='retrying')return 'Connecting / resuming…';
 if(setupEvent?.componentProgress||setupEvent?.setupStep==='verify')return 'Loading and checking models…';
 return 'Downloading & preparing…';
}
function acceptSetupPlan(next){
 plan=next;if(!next)return;if(!next.setupReady&&$('#setup-details'))$('#setup-details').open=true;
 selectedQuality=matchingPreset(next);
 // Keep an existing custom/installed combination. New installs start at the
 // highest AVAILABLE template, never at an unavailable quality target.
 if(!selectedQuality&&!next.existingInstallation&&!next.downloads?.some(r=>r.installed)&&next.recommendedPreset){selectedQuality=next.recommendedPreset;plan=presetPlan(next,selectedQuality)}
}
function qualityTemplates(){
 const presets=plan?.qualityPresets?.filter(p=>p.id!=='compact');if(!presets?.length)return '';
 const h=plan.hardware||{},ram=Number(h.memoryGB||0),vram=Number(h.acceleratorMemoryGB||0),isMac=h.platform==='macos';
 const backend=h.backend==='cuda'?'NVIDIA · CUDA':h.backend==='rocm'?'AMD · ROCm':h.backend==='metal'?'Apple Silicon · Metal':t('CPU / GPU acceleration not confirmed');
 return `<section class="quality-templates" aria-labelledby="quality-title"><div class="row spread"><h4 id="quality-title">${esc(t('Conversion quality'))}</h4><small>${esc(t('Detected hardware'))}</small></div><small>${esc(backend)} · ${ram.toFixed(0)} GB ${esc(t(isMac?'unified memory':'system RAM'))}${vram?` · ${vram.toFixed(0)} GB VRAM`:''}</small>
 <p class="quality-expectation">${esc(t('Drama 3 + Qwen 35B gave the best Cantonese listening results so far; other combinations may retain a Japanese accent.'))}</p>
 <div class="quality-options">${presets.map(p=>`<button class="quality-card ${selectedQuality===p.id?'selected':''}" data-action="quality-preset" data-value="${esc(p.id)}" ${!p.available||active?'disabled':''} aria-pressed="${selectedQuality===p.id}"><div class="row spread"><strong>${esc(t(p.id==='quality'?'Highest quality':p.id==='balanced'?'Balanced':'Memory saving'))}</strong><small class="quality-badge">${esc(t(p.id===plan.recommendedPreset?'Recommended for this computer':p.available?'Compatible':'Unavailable'))}</small></div><small class="quality-accent-note">${esc(t(p.id==='quality'?'Closer to a Hong Kong Cantonese accent':'May retain a Japanese accent'))}</small><span>${esc(p.modelSummary||'')}</span><small>${esc(t('System memory'))} ≥ ${p.minimumSystemMemoryGB} GB${p.minimumDedicatedVRAMGB?` · VRAM ≥ ${p.minimumDedicatedVRAMGB} GB`:''}</small>${presetReasons(p).map(x=>`<span class="quality-reason">${esc(t(x))}</span>`).join('')}</button>`).join('')}</div>
 <div class="row">${button('change-models','Custom setup · compare memory','settings','',active?'disabled':'')}</div>
 <details id="quality-hardware-details" class="quality-hardware-details"><summary>${esc(t('Hardware details'))}</summary><small>${esc(t('Available model budget'))}: ${Number(plan.memoryBudgetGB||0).toFixed(1)} GB · ${esc(t('System reserve'))}: ${Number(plan.systemReserveGB||0).toFixed(1)} GB</small><small>${esc(t('Memory requirements are estimates with system headroom. Models run in sequence. Setup verifies the actual runtime before use.'))}</small>${!isMac?`<small>${esc(t('CUDA is for NVIDIA. AMD acceleration depends on the supported ROCm card and driver; Intel uses CPU in this build. Video encoding support is checked separately.'))}</small>`:''}</details></section>`;
}
function packagePanel(){
 const raw=setupEvent?.download,transfer=raw?{...raw,bytesReceived:raw.bytesReceived??raw.receivedBytes??0}:null;
 const downloads=plan?.downloads||[],missing=downloads.filter(r=>!r.installed),ready=runtimeReady&&plan?.setupReady;
 const roles=plan?.roles||{};const label=r=>r.purposeKey?purpose(r.purposeKey):r.id===roles.voice?t('Voice generation'):r.id===roles.text?t('Text translation'):r.id===roles.speech?t('Speech recognition'):r.id===roles.asr?t('Language check'):purpose(r.role||r.category||r.id);
 return `<div class="package-panel stack">
 ${!active?.setup?qualityTemplates():''}
 <div class="row spread"><h3>${esc(t(initializing?'Checking your computer…':active?.setup?setupStatus():ready?'Ready to use':'One-click setup'))}</h3>${initializing||active?.setup?'<span class="loading-mark"></span>':''}</div>
 ${setupFailure&&!active?.setup?`<section class="warning setup-failure" role="alert"><strong>${esc(t('Setup did not finish'))}</strong><p>${esc(t(/127|No such file|啟動工作程序/.test(setupFailure)?'The local runtime could not start. Retry setup to repair it.':'Retry setup to continue. Existing verified downloads are kept.'))}</p><details><summary>${esc(t('Error details'))}</summary><p>${esc(setupFailure)}</p></details></section>`:''}
 ${active?.setup?`<div class="download-status">${installationProgress()}${installationDetails()}${button('pause','Pause download','pause')}</div>`:
 `<small>${esc(t(ready?'Your selected models are ready. Existing files are reused.':'The app chooses one suitable model per purpose for your computer.'))}</small>
 ${!initializing?button('setup',ready?'Check / repair files':runtimeReady?'Download & prepare':'Prepare to use','download',ready?'':'primary',active||!termsReady()||!plan?.canDeployModels||plan?.qualityPresets?.length&&!plan.qualityPresets.some(p=>p.available)?'disabled':''):''}`}
 ${!active?.setup&&installationLog.text?installationDetails():''}<details id="download-management"><summary>${esc(t('Models & storage'))}</summary><div class="stack">
 ${screen==='welcome'&&plan?.qualityPresets?.length?'':button('change-models',screen==='welcome'?'Custom setup · compare memory':'Change models','settings','',active?'disabled':'')}
 ${missing.length?`<details id="download-details"><summary>${esc(t('To download'))} · ${bytes(missing.reduce((n,r)=>n+(Number(r.bytes)||0),0))}</summary>${missing.map(r=>`<div class="package-row"><div><strong>${esc(r.title)}</strong><br><small>${esc(label(r))}</small></div><small>${bytes(r.bytes)}</small></div>`).join('')}<small>${esc(t('All files will be checked; healthy packages are reused.'))}</small></details>`:''}
 ${(plan?.blockers||[]).length?`<p class="warning">${esc(t('No compatible setup is available. Check the memory and platform requirements above.'))}</p>`:''}
 <details id="installed-models"><summary>${esc(t('Downloaded models'))} (${inventory.length})</summary>${inventory.length?modelGroups(false):`<small>${esc(t('No downloaded models'))}</small>`}</details>
 <div class="row wrap">${button('cleanup-models','Remove all downloaded models','trash','danger',!runtimeReady||active?'disabled':'')}</div>
 <details id="runtime-cleanup"><summary>${esc(t('Runtime cleanup'))}</summary><p>${esc(t('Remove downloaded models and their execution environments for a fresh setup.'))}</p>${button('cleanup-all','Remove models & runtimes','trash','danger',!runtimeReady||active?'disabled':'')}</details>
 </div></details></div>`}

function modelGroups(expert){
 const order=['text','voice','asr','speech','classifier'];
 const title={text:'Text translation',voice:'Voice generation',asr:'Source dialogue recognition',speech:'Dubbing verification',classifier:'Audio classification'};
 const groups=[...new Set([...order,...inventory.map(r=>r.category)])];
 return groups.filter(k=>inventory.some(r=>r.category===k)).map(k=>`<section class="model-group ${expert?'card':''}"><h3>${esc(t(title[k]||purpose(k)))}</h3>${inventory.filter(r=>r.category===k).sort((a,b)=>Number(b.selected)-Number(a.selected)).map(r=>`<div class="model-item"><div class="model-item-name"><strong>${esc(r.title)}</strong><small>${bytes(r.savedBytes)}${r.installed?'':' · '+esc(t('Partially downloaded'))}</small><small class="${r.selected?'model-selected':''}">${esc(t(r.selected?'Currently selected':r.removeReason==='pending-job'?'Used by a pending job':'Additional downloaded version'))}</small></div><div class="row wrap">${expert&&!r.retired?`<details class="model-actions"><summary>${esc(t('Repair / download again'))}</summary><div class="row wrap">${button('repair-model','Repair download','refresh','',`data-value="${esc(r.id)}" ${active?'disabled':''}`)}${button('redownload-model','Download again','download','',`data-value="${esc(r.id)}" ${active?'disabled':''}`)}</div></details>`:''}${button('remove-model','Remove','trash','',`data-value="${esc(r.id)}" ${active||r.canRemove===false?'disabled':''} title="${esc(t(r.removeReason==='selected-model'?'Select another model before removing this version.':r.removeReason==='pending-job'?'A waiting or paused job still uses this model.':'Remove this downloaded version'))}"`)}</div></div>`).join('')}</section>`).join('')||empty('No downloaded models','Download & prepare','model');
}
function purpose(key=''){if(/classif|audioset/.test(key))return t('Audio classification');if(/reference/.test(key))return t('Reference transcription');if(/asr|whisper|speech/.test(key))return t('Speech recognition');if(/text|qwen|translat/.test(key))return t('Text translation');if(/visual|role/.test(key))return t('Role analysis');if(/separat/.test(key))return t('Background separation');if(/runtime|worker|native-/.test(key))return t('Runtime');return t('Voice generation')}
function updateSetup(){const panel=$('#setup-content');if(panel){const signature=String(!!active?.setup);if(panel.dataset.installing!==signature||!active?.setup){const open=new Set($$('details[open]',panel).map(x=>x.id));panel.innerHTML=packagePanel();panel.dataset.installing=signature;for(const id of open)if(id&&$('#'+id))$('#'+id).open=true;}}paintInstallation();}
let packageCleaning=false,packageOperation=null;
let cacheReview=null,cacheCleaning=false,cacheSession=0;
function updateCacheSelection(){
 if(!cacheReview)return;
 const chosen=new Set($$('[data-cache-orphan]:checked').map(x=>x.dataset.cacheOrphan));
 const extra=(cacheReview.orphanWork||[]).filter(x=>chosen.has(x.id));
 const count=cacheReview.count+extra.reduce((n,x)=>n+x.files.length,0);
 const size=cacheReview.bytes+extra.reduce((n,x)=>n+x.bytes,0);
 const el=$('#cache-size');if(el)el.textContent=bytes(size);
 const confirm=$('[data-action=confirm-clear-cache]');if(confirm)confirm.disabled=!count;
}
function cacheProgressHTML(status={}){
 const phase=status.phase||'checking',known=phase==='deleting'&&status.total>0;
 const labels={checking:'Checking selected files…',deleting:'Clearing selected files…',tidying:'Finishing cleanup…'};
 const percent=known?Math.round(status.processed/status.total*100):null;
 return `<section class="cache-progress" aria-busy="true"><h3 role="status">${esc(t(labels[phase]||'Finishing cleanup…'))}</h3><div class="download-fill ${known?'':'indeterminate'}" role="progressbar" aria-label="${esc(t('Cleanup progress'))}" aria-valuemin="0" aria-valuemax="100" ${known?`aria-valuenow="${percent}"`:''}><i style="width:${known?percent:30}%"></i></div>${known?`<p class="row spread"><span>${esc(t('Files processed'))}: ${status.processed.toLocaleString()} / ${status.total.toLocaleString()}</span><strong>${percent}%</strong></p><small>${esc(t('Space freed'))}: ${bytes(status.freedBytes||0)}${status.failed?` · ${esc(t('Files not removed'))}: ${status.failed}`:''}</small>`:''}<p>${esc(t('Please keep the app open until cleanup finishes.'))}</p></section>`;
}
async function runCacheCleanup(token,orphanIDs){
 cacheCleaning=true;const operationID=crypto.randomUUID();let polling=true;
 await showDrawer('Clear temporary files',cacheProgressHTML());
 $('.drawer [data-action=close-drawer]').disabled=true;
 const poll=async()=>{while(polling){await new Promise(r=>setTimeout(r,350));if(!polling)break;try{const status=await rpc('project-cache-status',{operationID});if(polling&&status&&['checking','deleting','tidying'].includes(status.phase))$('.drawer-body').innerHTML=cacheProgressHTML(status);}catch{/* The completion RPC remains authoritative if telemetry is unavailable. */}}};
 void poll();
 try{
  const result=await rpc('clear-project-cache',{token,orphanIDs,operationID});polling=false;cacheCleaning=false;render();updatePreviewSurface();
  await showDrawer('Clear temporary files',`<section class="cache-result ${result.complete?'success':'warning'}" role="status"><h3>${icon(result.complete?'check':'info')}${esc(t(result.complete?'Cleanup complete':'Some files could not be cleared'))}</h3><dl><div><dt>${esc(t('Space freed'))}</dt><dd>${bytes(result.freedBytes)}</dd></div><div><dt>${esc(t('Files removed'))}</dt><dd>${result.removedCount??0}</dd></div>${result.failedCount?`<div><dt>${esc(t('Files not removed'))}</dt><dd>${result.failedCount}</dd></div>`:''}</dl><p>${esc(t('Downloaded models, runtimes, original videos and finished exports were kept.'))}</p>${!result.complete?`<p>${esc(t('Files in use may need another try. Scan again to review what remains.'))}</p>`:''}<div class="row">${button('close-drawer','Done',null,'primary')}${button('clear-cache','Scan again','refresh')}</div></section>`);
 }catch(error){
  polling=false;cacheCleaning=false;
  await showDrawer('Clear temporary files',`<section class="cache-result warning" role="alert"><h3>${esc(t('Cleanup did not finish'))}</h3><p>${esc(error.message||String(error))}</p><p>${esc(t('Scan again to check what remains before retrying.'))}</p><div class="row">${button('close-drawer','Close')}${button('clear-cache','Scan again','refresh','primary')}</div></section>`);
 }finally{polling=false;cacheCleaning=false;}
}
function conversionModelsReady(){return runtimeReady&&plan?.setupReady===true;}
function transportControl(){
 const control=active?button('pause','Pause & save','pause','',starting||finishingRun?'disabled':''):!conversionModelsReady()?button('setup','Download & prepare','download','primary',initializing||starting||finishingRun||!plan?.canDeployModels||!termsReady()?'disabled':''):button('start',startLabel(),'play','primary',!row()||starting||finishingRun?'disabled':'');
 return `<div class="transport-control">${control}</div>`;
}
function appbar(){const expert=state.mode==='expert';return `<header class="appbar">${brand()}<div class="grow"></div><div class="header-actions">
 ${expert?`<div class="group">${ib('undo','Undo','undo',undoStack.length?'':'disabled')}${ib('redo','Redo','redo',redoStack.length?'':'disabled')}${ib('save','Save draft','save',draft?'':'disabled')}</div><div class="group">${ib('toggle-nav','Show navigation','nav')}${ib('toggle-browser','Show video list','browser')}${ib('toggle-inspector','Show inspector','inspector')}</div>`:''}
 <div class="group"><button data-action="switch-mode" class="mode-switch" title="${esc(t('Switch to'))} ${esc(t(expert?'Basic mode':'Expert mode'))}">${icon(expert?'settings':'spark')}<span class="mode-caption"><small>${esc(t('Current mode'))}</small><span>${esc(t(expert?'Expert mode':'Basic mode'))}</span></span>${icon('chevron')}</button>${ib('guide','Help centre','help')}${ib('about','About & licences','info')}${ib('welcome','Welcome','home')}</div>
 ${expert?`<div class="group">${button('export','Export video','export','primary',draft&&!active?'':'disabled')}</div>`:''}</div></header>`}
const NAV=[['edit','Edit','edit'],['roles','Roles','roles'],['review','Review report','review'],['produce','Produce','export'],['queue','Work queue','queue'],['terminal','Terminal','terminal'],['defaults','Production defaults','settings'],['models','Model centre','model'],['projects','Projects and exports','folder'],['preferences','Preferences','settings']];
function studio(){const expert=state.mode==='expert';return `<div class="studio ${expert?'expert':'basic'}">${appbar()}${expert?`<section id="expert-progress" class="expert-progress">${progressHTML(false)}</section>`:''}
 <div class="workspace">${expert&&navVisible?`<nav class="navigation">${NAV.map(([k,label,ico],i)=>`${i===6?'<div class="rule"></div>':''}<button class="${page===k?'active':''}" data-action="page" data-value="${k}">${icon(ico)}<span>${esc(t(label))}</span></button>`).join('')}</nav>`:''}
 ${page==='edit'&&browserVisible?browser():''}<main class="main"><div class="workspace-title">${page!=='edit'&&!expert?button('back','Back to preview','back','back-prominent'):''}${page!=='edit'||!browserVisible?button('add','Add videos','plus'):''}<h3>${esc(t(NAV.find(r=>r[0]===page)?.[1]||'Edit'))}</h3><span class="filename ellipsis grow">${esc(filename(row()?.video))}</span></div>${page==='edit'?editor():fullPage()}</main></div><footer class="statusbar ${page!=='edit'||expert&&!inspectorVisible?'has-transport':''}"><span>${esc(active?t('Processing'):deliveryLabel(row()))} ${dirty?` · <span class="accent">${esc(t('Draft changed'))}</span>`:''}</span><span class="product-stamp">${esc(APP_VERSION)} · AniCanto · ${esc(COPYRIGHT)}</span>${page!=='edit'||expert&&!inspectorVisible?transportControl():''}</footer></div>`}
function browser(){return `<aside class="browser"><div class="panel-title">${esc(t('Video queue'))}<span class="row queue-actions"><span class="badge">${state.queue.length}</span>${button('add','Add videos','plus','icon-button')}</span></div><div class="shelf" id="shelf" data-queue-list>${shelfCards()}</div><div class="browser-bottom">${state.mode==='basic'?button('projects','Projects and exports','folder'):''}${esc(t('Your original videos stay in their current folder.'))}</div></aside>`}
function deliveryLabel(r){return r?.deliveryKind==='preview'&&r.status!=='running'?t('Preview saved — dubbing incomplete'):statusName(r?.status)}
function shelfCards(){return state.queue.length?state.queue.map((r,i)=>`<article class="shelf-card ${r.id===state.selected?'active':''}" data-action="select" data-value="${esc(r.id)}" data-queue-id="${esc(r.id)}" tabindex="0">${queueControls(i)}<div class="row spread"><span class="badge accent">${String(i+1).padStart(2,'0')}</span><small class="status accent">${esc(deliveryLabel(r))}</small></div><h4>${esc(filename(r.video))}</h4><small>${esc(t('Total processing'))} · ${shortTime(r.processingSeconds||0)}</small><button class="remove icon ghost" data-action="remove" data-value="${r.id}" aria-label="${esc(t('Remove'))}" ${r.status==='running'?'disabled':''}>${icon('close')}</button></article>`).join(''):empty('No videos yet','','folder')}
// The same aligned working drawing is continuously skinned at its joints.
function busyAssistant(key,index=0){const theme=key in THEMES&&key!=='ensemble'?key:'studio';return `<div class="busy-assistant" data-theme="${theme}" data-motion="skeletal-continuous" role="img" aria-label="${esc(t('Your theme assistant is organising the studio'))}"><canvas class="assistant-sprite" data-theme="${theme}" data-offset="${index*4}" width="300" height="300" aria-hidden="true"></canvas></div>`;}
function waitingScene(){const cast=themeKey==='ensemble'?['energy','studio','mint']:[themeKey];return `<div class="waiting-scene" aria-live="off"><div class="waiting-stage ${cast.length>1?'ensemble':''}">${cast.map((key,index)=>busyAssistant(key,index)).join('')}<span class="floating-note note-one" aria-hidden="true">♪</span><span class="floating-note note-two" aria-hidden="true">♫</span><div class="waiting-meter" aria-hidden="true">${'<i></i>'.repeat(7)}</div></div><div class="waiting-copy"><strong id="preview-status">${esc(t(previewError?'Preview could not be opened':previewLoading?'Preparing video preview…':'Preview is off'))}</strong><p>${esc(t(previewError?'Your project is safe. Retry preview or continue with it off.':previewLoading?'Preparing a compatible copy. Conversion continues separately.':'Open preview when you want to watch. Your assistant will keep you company.'))}</p>${previewLoading?`<div class="download-fill ${previewProgress?.progress?'':'indeterminate'}"><i style="width:${previewProgress?.progress?Math.round(previewProgress.progress*100):25}%"></i></div><small>${esc(t(previewProgress?.stage==='copying'?'Copying cloud video into local cache…':previewProgress?.stage==='remux'?'Preparing preview without re-encoding…':previewProgress?.stage==='encode'?'Preparing compatible preview…':'Reading video…'))}${previewProgress?.progress?` · ${Math.round(previewProgress.progress*100)}%`:''}</small>`:''}${button('toggle-preview',previewEnabled?'Close preview':'Open preview','edit','',row()?'':'disabled')}${previewError?button('retry-preview','Retry preview','refresh'):''}</div></div>`;}
function updatePreviewSurface(){const stage=$('.video-stage');if(!stage)return;stage.classList.toggle('preview-off',!previewEnabled||previewLoading||!!previewError);let scene=$('.waiting-scene',stage);if(scene){const holder=document.createElement('div');holder.innerHTML=waitingScene();scene.querySelector('.waiting-copy')?.replaceWith(holder.querySelector('.waiting-copy'));}else stage.insertAdjacentHTML('beforeend',waitingScene());const toggle=$('[data-action=preview-control]');if(toggle){toggle.hidden=!previewEnabled||previewLoading||!!previewError;toggle.title=t(previewEnabled?'Close preview':'Open preview');toggle.setAttribute('aria-label',toggle.title);toggle.setAttribute('aria-pressed',String(previewEnabled));}syncAssistantMotion();}
async function setPreview(enabled,output=false){previewEnabled=enabled;previewError='';if(!enabled){++previewToken;clearInterval(previewTimer);previewProgress=null;previewLoading=false;const v=$('#video');if(v){v.pause();v.removeAttribute('src');v.load();}mediaPath='';updatePreviewSurface();return;}updatePreviewSurface();await loadMedia(output);}
function editor(){const expert=state.mode==='expert';return `<div class="content-split"><section class="preview-column">
 ${expert?'':`<div class="preview-heading"><h2>${esc(t('Preview & listen'))}</h2></div>`}
 <div class="player-card"><div class="video-stage ${!previewEnabled||previewLoading||previewError?'preview-off':''}"><video id="video" playsinline preload="none" ${previewEnabled&&mediaPath?`src="${esc(asset(mediaPath))}"`:''}></video><div id="video-caption" class="video-caption"></div><div id="video-notice" class="video-notice" ${mediaPath?'style="display:none"':''}>${esc(t(row()?'Preparing video preview…':'Drop one or more episodes here'))}</div>${waitingScene()}</div>
 <div class="player-controls">${ib('preview-control',previewEnabled?'Close preview':'Open preview','edit',`aria-pressed="${previewEnabled}"`)}${ib('play','Play original','play')}<span id="play-time" class="time">00:00:00.0</span><input id="seek" type="range" min="0" max="${duration||1}" step="0.05" value="${sourceTime}" aria-label="${esc(t('Timeline'))}"><span id="play-duration" class="time">${tc(duration)}</span><label class="check"><input id="follow" type="checkbox" ${follow?'checked':''}>${esc(t('Follow processing'))}</label>${ib('captions','Preview captions','subtitles')}</div></div>
 ${expert?'<section class="transcript" id="transcript"></section>':`<section id="basic-progress" class="progress-card basic-progress">${progressHTML(true)}</section><section id="audition-card" class="card audition-card"></section><div id="output-row"></div>`}
 </section>${inspectorVisible?`<aside class="inspector"><div class="panel-title">${esc(t(expert?'Dialogue':'Production settings'))}${icon(expert?'settings':'spark')}</div>${expert?`<div class="inspector-tabs"><div class="segmented">${[['production','Production'],['dialogue','Dialogue'],['picture','Picture'],['sound','Mix']].map(([k,l])=>`<button class="${inspector===k?'active':''}" data-action="inspector" data-value="${k}">${esc(t(l))}</button>`).join('')}</div></div>`:''}<div id="inspector-content" class="inspector-content">${expert?inspectorHTML():productionSettings(false)}</div><div class="inspector-footer">${transportControl()}<small style="display:block;margin-top:8px">${esc(t(expert?'Edits and retakes create a new version. Earlier recordings and exports are retained.':'Choose Cantonese, English or both. Audio and subtitles are configured automatically.'))}</small></div></aside>`:''}</div>${expert?'<section id="timeline" class="timeline"></section>':''}`}
const FULL_AI_NOTICE='Roles and shared voice references require Full AI review. Choose Expert mode → Production defaults → More options → Full AI review before starting a new conversion. Full AI review takes approximately three times as long as Normal mode; actual time varies with hardware, video length and optional visual analysis. Existing results are kept when you change this setting.';
function productionSettings(expert){const s=expert?state.settings:{...state.settings,productionMode:'normal'},englishSource=sourceLanguage()==='en';return `
 <div class="row spread"><h4>${esc(t(s.productionMode==='fast'?'High speed':s.productionMode==='standard'?'Full AI review':'Normal mode'))}</h4><span class="pill">${esc(t(s.productionMode==='standard'?'Full AI review':'Source voice per line'))}</span></div>
 ${s.productionMode==='normal'?`<small>${esc(t('Normal mode checks missing speech, names and language, and keeps Japanese OP / ED.'))}</small>`:''}
 ${expert?`<details><summary>${esc(t('More options'))}</summary><div class="stack">${field('Production mode',select('productionMode',[['normal','Normal mode'],['fast','High speed'],...(expert||s.productionMode==='standard'?[['standard','Full AI review']]:[])],s.productionMode))}${s.productionMode==='fast'?`<p class="warning">${esc(t('High speed skips all quality review and quality-driven retakes. The video may contain dubbing defects.'))}</p>`:s.productionMode==='standard'?`<p>${esc(t(FULL_AI_NOTICE))}</p>`:''}</div></details>`:''}
 <div class="rule"></div>${check('preferFirstAudibleTake','Keep the first audible take; repair missing speech only',s.preferFirstAudibleTake!==false,active?'disabled':'')}<small>${esc(t('Language concerns are shown in the review report without replacing audible recordings.'))}</small>${check('automaticAlternateVoice','Automatically try another installed voice model for missing lines',s.automaticAlternateVoice!==false,active?'disabled':'')}<small>${esc(t('Only verified target-language recordings replace missing speech.'))}</small>${expert?field('Voice engine',select('ttsBackend',engineMenu(),s.ttsBackend,active?'disabled':'')):`<small>${esc(t('Voice engine'))}: ${esc(engineName(s.ttsBackend))}</small>`}
 ${expert?`<details class="engine-tracks"><summary>${esc(t('Additional voice engines'))} · ${(s.selectedEngines||[]).length}</summary><div class="stack"><small>${esc(t('Create a separate audio track for each selected engine and dubbing language in one conversion. Engines run in sequence to limit memory use. Extra engines need their models installed and increase processing time.'))}</small>${engineChoices().map(([k,l])=>`<label class="check"><input type="checkbox" data-engine-track="${k}" ${(s.selectedEngines||[s.ttsBackend]).includes(k)?'checked':''} ${k===s.ttsBackend||active||engineBlocked(k)?'disabled':''}>${esc(l)}${engineBlocked(k)?' · '+esc(t('Cantonese only')):''}${k===s.ttsBackend?` · ${esc(t('Default track'))}`:''}</label>`).join('')}</div></details>`:''}
 ${field('Dubbing languages',select('dubLanguages',englishSource?[['yue','Hong Kong Cantonese']]:[['yue','Hong Kong Cantonese'],['en','English'],['both','Both languages']],englishSource?'yue':s.dubLanguages?.length===2?'both':s.dubLanguages?.[0],englishSource?'disabled':''))}
 ${expert?check('includeOriginal',sourceLanguage()==='ja'?'Keep Japanese audio track':'Keep original audio track',s.includeOriginal):`<small>${esc(t('Original audio, music and sound effects are preserved automatically.'))}</small>`}<div class="rule"></div>
 ${expert?`${field('Output subtitles',`<div class="stack">${(englishSource?[['yue','Hong Kong Cantonese']]:[['yue','Hong Kong Cantonese'],['english','English'],['dual','Cantonese + English together (learning)'],['original','Original subtitles (when available)']]).map(([k,l])=>`<label class="check"><input type="checkbox" data-subtitle="${k}" ${(englishSource?k==='yue':s.subtitleModes?.includes(k))?'checked':''} ${englishSource?'disabled':''}>${esc(t(l))}</label>`).join('')}</div>`)}${s.subtitleSelection==='custom'&&!englishSource?button('automatic-subtitles','Restore automatic subtitles','refresh'):''}`:`${field('Output subtitles',`<small>${esc(t('Automatic'))}</small><div class="row wrap">${(englishSource?['Hong Kong Cantonese']:s.dubLanguages?.length===2?['Hong Kong Cantonese','English','Bilingual learning']:s.dubLanguages?.[0]==='en'?['English']:['Hong Kong Cantonese']).map(label=>`<span class="pill">${esc(t(label))}</span>`).join('')}</div>`)}${englishSource?'':`<small>${esc(t('Original text subtitles are kept when available. Burnt-in captions are not duplicated.'))}</small>`}`}
 ${expert?`<div class="rule"></div>${field('Translation source',select('translationSource',[['audio-and-subtitles','Automatic subtitles + Japanese audio'],['audio-and-ocr','Japanese audio + screen OCR'],['audio-only','Japanese audio only']],s.translationSource))}<small>${esc(t(s.translationSource==='audio-only'?'Ignores OCR and original subtitles for translation.':s.translationSource==='audio-and-ocr'?'Listen to Japanese first, detect lower-screen subtitles automatically, then combine the evidence for translation. No manual crop is required.':'Uses external or embedded text subtitles when available. Otherwise detects lower-screen OCR automatically. Japanese audio remains the primary source.'))}</small>
 ${field('Reference strategy',select('roleAnalysisMode',[['independent','Source voice per line'],['audio','Audio grouping']],s.roleAnalysisMode==='audiovisual'?'audio':s.roleAnalysisMode,active?'disabled':''))}
 ${check('visualRoleAnalysisEnabled','Visual role analysis (about 3× processing time)',s.visualRoleAnalysisEnabled,active?'disabled':'')}<small>${esc(t('Analyses frames and portraits. Allow about three times the processing time of Normal mode.'))}</small>`:''}
 ${button('change-models','Change models','model','',active?'disabled':'')}${expert?`<details><summary>${esc(t('OP / ED treatment'))}</summary><div class="stack">${select('translateOPED',[['keep','Keep original Japanese'],['translate','Translate all dialogue']],s.translateOPED?'translate':'keep')}</div></details>`:''}
 ${expert?`${field('Processing range',select('limit',[['0','Full video'],['60','60 sec'],['180','3 min']],String(s.limit||0)))}${field('Start time (seconds)',`<input type="number" min="0" step=".1" data-setting="startOffset" value="${s.startOffset||0}">`)}`:''}
 <div class="rule"></div>${field('Output folder',`<div class="row"><small class="grow ellipsis" title="${esc(s.exportFolder||state.storage)}">${esc(s.exportFolder||`${state.storage||'…'}/exports`)}</small>${ib('output-folder','Choose folder','folder')}</div>`)}`}
function inspectorHTML(){const c=current();if(inspector==='production')return productionSettings(true);
 if(inspector==='picture')return `<div class="stack"><h4>${esc(t('Preview captions'))}</h4>${select('captionLanguage',[['yue','Hong Kong Cantonese'],['en','English'],['original','Original subtitles'],['none','No captions']],captionLanguage)}${field('Caption override',`<input data-cue-field="captionText" value="${esc(c?.captionText||'')}" placeholder="${esc(t('Empty follows the dubbing script'))}" ${c?'':'disabled'}>`)}<small>${esc(t('Edits and retakes create a new version. Earlier recordings and exports are retained.'))}</small></div>`;
 if(inspector==='sound')return `<div class="stack">${field('Music / sound effects',`<input type="range" min="0" max="2" step=".05" data-setting="backgroundGain" value="${state.settings.backgroundGain??1}">`)}${check('backgroundDucking','Background separation',state.settings.backgroundDucking!==false)}${check('includeOriginal','Keep Japanese audio track',state.settings.includeOriginal)}</div>`;
 if(!c)return empty('No script yet','Translated dialogue and recordings appear here as processing progresses.');
 return `<div class="row spread"><div><h3>${esc(t('Line'))} ${selectedCue+1}</h3><small>${tc(c.start)} – ${tc(c.end)}</small></div>${ib('play-original','Play original','sound')}</div>
 <div class="row spread"><span class="pill">${esc(t(language==='en'?'English':'Hong Kong Cantonese'))}</span><div class="segmented">${(sourceLanguage()==='en'?[['yue','HK']]:[['yue','HK'],['en','EN']]).map(([k,l])=>`<button data-action="audition-language" data-value="${k}" class="${language===k?'active':''}">${l}</button>`).join('')}</div></div>
 <div class="segmented">${[['listen','Listen'],['record','Retake'],['adjust','Adjust']].map(([k,l])=>`<button data-action="dialogue-tab" data-value="${k}" class="${dialogueTab===k?'active':''}">${esc(t(l))}</button>`).join('')}</div>
 ${dialogueTab==='adjust'?`<div class="timing-grid">${[['start','Start'],['end','End'],['rate','Rate'],['take','Retake'],['trimStart','Trim start'],['trimEnd','Trim end']].map(([key,label])=>`<label>${esc(t(label))}<input type="number" data-cue-field="${key}" min="0" step="${key==='take'?'1':'.05'}" value="${c[key]??(key==='rate'?1:key==='take'?42:0)}"></label>`).join('')}</div>${checkCue('enabled','Enabled',c.enabled!==false)}`:
 `${ENGINES.filter(([k])=>state.settings.selectedEngines?.includes(k)||takeAt(snapshot.takes||[],selectedCue,k,language)).map(([k,l])=>{const take=takeAt(snapshot.takes||[],selectedCue,k,language);return `<div class="take-row ${k===state.settings.ttsBackend?'selected':''}"><div><h4>${esc(l)}</h4><small>${esc(t(take?'Available':'Waiting for recording'))}</small></div>${button('play-take','Listen','play','',`data-engine="${k}" ${take?'':'disabled'}`)}</div>`}).join('')}
 ${dialogueTab==='record'?`${field('Voice engine',select('retakeEngine',engineChoices(),retakeEngine||state.settings.ttsBackend))}${button('retake','Generate this line','refresh','primary',active?'disabled':'')}<small>${esc(t('Edits and retakes create a new version. Earlier recordings and exports are retained.'))}</small>`:''}`}
 <div class="rule"></div>${field('Role',`<select id="cue-role"><option value="">${esc(t('Unassigned'))}</option>${(draft.settings.voiceProfiles||snapshot.roles||[]).map(r=>`<option value="${esc(r.id)}" ${c.speakerId===r.id?'selected':''}>${esc(r.name||r.id)}</option>`).join('')}</select>`)}
 ${button('adopt','Use recording','check','primary',takeAt(snapshot.takes||[],selectedCue,auditionEngine||state.settings.ttsBackend,language)?'':'disabled')}<small>${esc(t('Recording to use'))}: ${esc(engineName(auditionEngine||state.settings.ttsBackend))}</small>`}
async function previewDetails(){
 const info=snapshot.report?.previewDelivery||{},entries=new Map();
 for(const item of [...(info.missing||[]),...(info.unresolvedChecks||[])])entries.set(`${item.engine}:${item.language}:${item.index}`,item);
 const reasons={'timing-overrun':'The full recording does not fit the available time.','missing-script':'A reliable translation could not be confirmed.','reference-blocked':'The original voice reference could not be used reliably.','generation-failed':'A usable voice recording could not be generated.','missing-audio':'A usable voice recording could not be generated.','verification-unresolved':'The spoken language or completeness could not be confirmed.','language-or-content-check':'The spoken language or completeness could not be confirmed.'};
 await showDrawer('Why this is a preview',`<h3>${esc(t('Preview saved — dubbing incomplete'))}</h3><p>${esc(t('Automatic repair reached its limit for these lines. The playable preview, original audio and successful recordings are retained.'))}</p><p>${esc(t('This preview is not marked as a complete dub.'))}</p>${entries.size?`<div class="preview-issues">${[...entries.values()].slice(0,100).map(item=>`<section class="card"><strong>${esc(t('Dialogue'))} ${item.index} · ${esc(t(item.language==='en'?'English':'Hong Kong Cantonese'))}</strong>${Number.isFinite(item.start)?`<small>${tc(item.start)}${Number.isFinite(item.end)?' – '+tc(item.end):''}</small>`:''}<p>${esc(t(reasons[item.reason]||'The spoken language or completeness could not be confirmed.'))}</p></section>`).join('')}</div>`:`<p>${esc(t('Detailed positions are available in the exported debug report.'))}</p>`}<div class="row">${button('close-drawer','Close')}</div>`);
}

function checkCue(key,label,value){return `<label class="check"><input type="checkbox" data-cue-field="${key}" ${value?'checked':''}>${esc(t(label))}</label>`}
function progressHTML(basic){const j=journey||row()?.journey||snapshot.journey||{};const stages=visibleMilestones(j.milestones||PHASES.map(id=>({id,state:'pending',seconds:0})),basic);const complete=row()?.status==='complete'||(row()?.deliveryKind==='preview'&&!!row()?.output&&row()?.status!=='running')||j.complete;const pct=complete?100:Math.round((j.progress||row()?.progress||0)*100);const r=row();const total=snapshot.time?.seconds||r?.processingSeconds||0;const currentSeconds=active?.seconds||0;
 return `<div class="progress-top"><div class="progress-stage">${esc(complete?t(r?.deliveryKind==='preview'?'Preview saved — dubbing incomplete':'Output saved'):workerText(r?.stage,state.language,true)||t('Ready when you are'))}</div><div class="progress-percent">${pct}%</div><div class="progress-detail ellipsis" title="${esc(r?.message||'')}">${esc(workerText(r?.message,state.language)||t('Translated dialogue and recordings appear here as processing progresses.'))}</div><div class="progress-times">${esc(t('Total processing'))}: ${shortTime(total)} · ${esc(t('This run'))}: ${shortTime(currentSeconds)}<br>${esc(estimateRemaining())}</div></div>
 <div class="progress-track"><div class="fill" style="width:${pct}%"></div>${basic?`<div class="runner ${!active?'paused':''}" style="left:${Math.min(98,Math.max(2,pct))}%;background-image:url('${themeAssets(themeKey).runner}');background-size:${themeAssets(themeKey).runnerSize}" aria-hidden="true"></div>`:''}</div>
 <div class="milestones" style="--milestone-count:${stages.length}">${stages.map(m=>`<div class="milestone ${esc(m.state)}"><span class="dot"></span><span>${esc(t(m.id==='recognition'&&sourceLanguage()!=='ja'?(sourceLanguage()==='en'?'English speech':'Source speech'):m.id))}<small>${m.state==='prepared'?t('Saved'):m.state==='pending'?'—':shortTime(m.seconds)}</small></span></div>`).join('')}</div>`}
let phaseSample=null;
function estimateRemaining(){if(!active)return '';const s=phaseSample;if(!s||s.last<=s.first||s.total<=s.last)return t('Estimating remaining time…');const elapsed=(performance.now()-s.started)/1000;return `${t('Remaining')} ≈ ${shortTime((s.total-s.last)*elapsed/(s.last-s.first))}`}
function updateProgress(){for(const [id,basic] of [['basic-progress',true],['expert-progress',false]])if($('#'+id))$('#'+id).innerHTML=progressHTML(basic)}
function renderTranscript(){const el=$('#transcript');if(!el)return;const c=current();el.innerHTML=`<div class="transcript-bar"><div class="row"><strong>${esc(t('Dialogue'))}</strong><small>${c?`${selectedCue+1} / ${cues().length}`:'—'}</small>${ib('previous','Previous line','back',selectedCue?'':'disabled')}${ib('next','Next line','chevron',selectedCue<cues().length-1?'':'disabled')}</div><div class="row"><span class="pill">${esc(t(language==='en'?'English':'Hong Kong Cantonese'))}</span>${ib('play-take','Listen','sound',c?'':'disabled')}${ib('stop-audio','Stop playback','stop')}</div></div>${c?`<div class="transcript-columns"><div class="transcript-pane"><label>${esc(sourceLabel())}</label><textarea data-cue-field="original" spellcheck="false">${esc(c.original)}</textarea><small>${esc(originalCaption(c.start))}</small></div><div class="transcript-pane"><label>${esc(t('Dubbing script'))}</label><textarea data-cue-field="${language==='en'?'english':'text'}">${esc(c[language==='en'?'english':'text'])}</textarea><input data-cue-field="captionText" value="${esc(c.captionText)}" placeholder="${esc(t('Empty follows the dubbing script'))}"></div></div>`:empty('No script yet','Translated dialogue and recordings appear here as processing progresses.')}`;
 if($('#inspector-content')&&state.mode==='expert')$('#inspector-content').innerHTML=inspectorHTML();}
function originalCaption(time){return(snapshot.originalCaptions||[]).filter(r=>r.start<=time&&time<r.end).map(r=>r.text).join('\n')}
function renderTimeline(){if(timelineDragging)return;rememberTimelineViewport();const el=$('#timeline');if(!el)return;const dur=duration||snapshot.review?.config?.duration||1;const scale=zoom;const width=Math.max(el.clientWidth-1,155+dur*scale);const takeRows=snapshot.takes||[];const engines=ENGINES.map(([k])=>k).filter(k=>state.settings.selectedEngines?.includes(k)||takeRows.some(r=>r.engine===k&&r.language===language));const tracks=[['Video','video'],[sourceLanguage()==='en'?'English original':sourceLanguage()==='ja'?'Japanese original':'Original audio','original'],['Music / sound effects','background'],['Subtitles','caption'],['Dubbing window','window'],...engines.map(k=>[engineName(k)+' · '+(language==='en'?'EN':'HK'),'voice',k])];
 el.innerHTML=`<div class="timeline-bar"><div class="row"><strong>${esc(t('Timeline'))}</strong>${button('split','Split clip','split','',draft?'':'disabled')}${button('new-dialogue','Add dialogue','plus','',draft?'':'disabled')}</div><div class="row"><small>−</small><input id="zoom" type="range" min="2" max="60" step="2" value="${zoom}" aria-label="Zoom"><small>+</small></div></div><div class="timeline-scroll" data-row-id="${esc(state.selected||'')}"><div style="width:${width}px;position:relative"><div class="timeline-ruler" title="${esc(t('Drag the ruler to browse the timeline'))}">${Array.from({length:Math.ceil(dur/10)},(_,i)=>`<span class="tick" style="left:${155+i*10*scale}px">${tc(i*10)}</span>`).join('')}</div>
 ${tracks.map(([label,key,engine])=>`<div class="track"><div class="track-label">${esc(t(label))}</div>${key==='video'?`<div class="clip video-clip" style="left:155px;width:${dur*scale}px" data-action="seek-timeline" data-start="0">${esc(filename(row()?.video))}</div>`:key==='background'||key==='original'?'':cues().map((c,i)=>{const take=key==='voice'?takeAt(takeRows,i,engine,language):null;const a=key==='caption'?(c.captionStart??c.start):c.start;const b=key==='caption'?(c.captionEnd??c.end):c.end;const missing=key==='voice'&&!take;return `<div class="clip ${i===selectedCue?'selected':''} ${missing?'missing':''}" style="left:${155+a*scale}px;width:${Math.max(4,(b-a)*scale)}px" data-action="cue" data-index="${i}" ${engine?`data-engine="${engine}"`:""} title="${esc(c.text||c.original)}">${esc(key==='caption'?c.text:c.speakerId||String(i+1))}</div>`}).join('')}</div>`).join('')}<div class="timeline-head" id="timeline-head" style="left:${155+sourceTime*scale}px"></div></div></div><div class="timeline-navigation"><div class="row">${ib('timeline-left','Scroll timeline left','back')}${button('timeline-playhead','Show playhead',null)}${ib('timeline-right','Scroll timeline right','chevron')}</div><input id="timeline-pan" type="range" min="0" max="1" step="0.01" value="0" aria-label="${esc(t('Browse timeline'))}"><small id="timeline-visible-range"></small></div>`;
 const viewport=$('.timeline-scroll',el);if(timelineViewport.rowID===state.selected){viewport.scrollLeft=timelineViewport.left;viewport.scrollTop=timelineViewport.top;}
 viewport.addEventListener('scroll',()=>{rememberTimelineViewport();updateTimelineNavigation();},{passive:true});
 viewport.addEventListener('wheel',event=>{if(event.shiftKey||event.target.closest('.timeline-ruler')){event.preventDefault();viewport.scrollLeft+=Math.abs(event.deltaX)>Math.abs(event.deltaY)?event.deltaX:event.deltaY;}},{passive:false});
 viewport.addEventListener('pointerdown',event=>{if(event.button!==0||!event.target.closest('.timeline-ruler')&&!(event.target.classList.contains('track')))return;
  const x=event.clientX,left=viewport.scrollLeft;let moved=false;timelineDragging=true;viewport.classList.add('panning');viewport.setPointerCapture(event.pointerId);
  const move=e=>{if(Math.abs(e.clientX-x)>4)moved=true;viewport.scrollLeft=left-(e.clientX-x);};
  const finish=()=>{viewport.removeEventListener('pointermove',move);viewport.removeEventListener('pointerup',finish);viewport.removeEventListener('pointercancel',finish);viewport.classList.remove('panning');timelineDragging=false;if(moved)timelineSuppressClickUntil=performance.now()+150;rememberTimelineViewport();updateTimelineNavigation();};
  viewport.addEventListener('pointermove',move);viewport.addEventListener('pointerup',finish);viewport.addEventListener('pointercancel',finish);event.preventDefault();
 });
 updateTimelineNavigation();
}
function updateTimelineNavigation(){const el=$('.timeline-scroll'),slider=$('#timeline-pan');if(!el||!slider)return;const max=Math.max(0,el.scrollWidth-el.clientWidth);slider.max=String(max/zoom);slider.value=String(el.scrollLeft/zoom);slider.disabled=max<1;const label=$('#timeline-visible-range');if(label)label.textContent=tc(el.scrollLeft/zoom)+' – '+tc(Math.min(duration||snapshot.review?.config?.duration||0,(el.scrollLeft+Math.max(0,el.clientWidth-155))/zoom));for(const [action,disabled] of [['timeline-left',el.scrollLeft<1],['timeline-right',el.scrollLeft>=max-1]]){const b=$('[data-action='+action+']');if(b)b.disabled=disabled;}}
function navigateTimeline(action){const el=$('.timeline-scroll');if(!el)return;el.scrollLeft=action==='timeline-playhead'?Math.max(0,155+sourceTime*zoom-el.clientWidth/2):el.scrollLeft+(action==='timeline-left'?-1:1)*Math.max(100,(el.clientWidth-155)*.75);rememberTimelineViewport();updateTimelineNavigation();}
function updateAudition(){const el=$('#audition-card');if(el){const index=cueAt(cues(),sourceTime);const c=cues()[index];const take=takeAt(snapshot.takes||[],index,state.settings.ttsBackend,language);el.innerHTML=`<div class="row spread"><strong class="row">${icon('sound')}${esc(t('This line'))}</strong><small>${c?`${tc(c.start)} – ${tc(c.end)}`:''}</small></div><p class="script">${esc(c?.[language==='en'?'english':'text']||t('No dialogue at this position'))}</p><div class="row wrap">${button('play-original','Play original','play','',c?`data-index="${index}"`:'disabled')}${button('play-take',engineName(state.settings.ttsBackend)+' · '+t(language==='en'?'English':'Hong Kong Cantonese'),'play','',take?`data-index="${index}"`:'disabled')}</div>`;}
 const output=$('#output-row');if(output)output.innerHTML=row()?.output?`<div class="output-row"><strong class="${row()?.deliveryKind==='preview'?'warning':'success'}">${row()?.deliveryKind==='preview'?'⚠':'✓'} ${esc(t(row()?.deliveryKind==='preview'?'Preview saved — dubbing incomplete':'Output saved'))}${snapshot.issues?.length?` · ${snapshot.issues.length} ${esc(t('Review notes'))}`:''}</strong><div class="row">${button('play-output',row()?.deliveryKind==='preview'?'Play preview':'Play output','play')}${button('reveal','Show file','folder')}${row()?.deliveryKind==='preview'?button('preview-details','Why this is a preview','info'):''}</div></div>`:'';
}
function pageHeader(title,body='',action=''){return `<div class="page-header"><div><h2>${esc(t(title))}</h2>${body?`<p>${esc(t(body))}</p>`:''}</div>${action}</div>`}
function fullPage(){let content='';
 if(page==='roles')content=rolesPage();
 else if(page==='review'){content=pageHeader('Review report','Incomplete recordings stay available for comparison.')+reviewPage({snapshot,cues:cues(),t,button,historyRow,engineName,active,sourceLanguage:sourceLanguage()});}
 else if(page==='produce'){content=pageHeader('Export a new version','Edits and retakes create a new version. Earlier recordings and exports are retained.')+(!draft?empty('No project selected','Open a processed video from the list to edit its script.'): `<div class="defaults-grid"><section class="card"><h3>${esc(t('Clips'))}</h3>${(draft.clips.length?draft.clips:[{start:0,end:duration||snapshot.review.config.duration,enabled:true,ripple:true}]).map((c,i)=>`<div class="clip-editor"><span class="badge">${i+1}</span><label>${esc(t('Start'))}<input type="number" data-clip="${i}" data-key="start" step=".1" value="${c.start}"></label><label>${esc(t('End'))}<input type="number" data-clip="${i}" data-key="end" step=".1" value="${c.end}"></label><input type="checkbox" data-clip="${i}" data-key="enabled" ${c.enabled?'checked':''}></div>`).join('')}</section><section class="card"><h3>${esc(t('Production settings'))}</h3>${productionSettings(true)}</section></div>`);}
 else if(page==='queue'||page==='projects'){content=pageHeader(page==='queue'?'Work queue':'Projects and exports','',`<div class="row wrap">${button('clear-cache','Clear temporary files','trash','',active?'disabled':'')}${button('start-all','Resume all unfinished videos','play','primary',active||starting||finishingRun?'disabled':'')}</div>`)+(state.queue.length?`<div class="queue-list" data-queue-list aria-label="${esc(t('Work queue'))}">`+state.queue.map((r,i)=>`<article class="card queue-row" data-queue-id="${esc(r.id)}"><div class="queue-rail">${queueControls(i)}<span class="queue-num">${String(i+1).padStart(2,'0')}</span></div><div><h4>${esc(filename(r.video))}</h4><small>${esc(t('Total processing'))} · ${shortTime(r.processingSeconds||0)}</small>${r.requestedExportFolder?`<small class="queue-destination" title="${esc(r.requestedExportFolder)}">${esc(t('Export destination'))}: ${esc(r.requestedExportFolder)}</small>`:''}${r.deliveryKind==='preview'?`<small class="warning preview-delivery-note">${esc(t('Automatic repair finished. This labelled preview still contains incomplete dialogue.'))}${(r.incompleteDialogue??r.missingDialogue)!=null?` ${r.incompleteDialogue??r.missingDialogue} ${esc(t('Unfinished dialogue lines'))}`:''}</small>`:''}${r.deliveryState==='not-exported'?`<small class="warning">${esc(t('Not exported. Working recordings are retained for repair.'))}</small>`:''}${r.lastError?`<div class="queue-error">${esc(projectWarning(r.lastError.message,state.language))}</div>`:''}</div><div><span class="pill">${esc(deliveryLabel(r))}</span><div class="download-fill" style="margin-top:10px"><i style="width:${100*(r.progress||0)}%"></i></div></div><div class="row wrap">${button('select-project','Edit','edit','',`data-value="${r.id}"`)}${r.output?button('reveal',r.deliveryKind==='preview'?'Show preview':'Show file','folder','',`data-path="${esc(r.output)}"`):`${button('retry','Retry','refresh','',`data-value="${r.id}" ${active?'disabled':''}`)}${r.workingOutput?button('reveal','Working files','folder','',`data-path="${esc(r.job||r.workingOutput)}"`):''}`}${ib('remove','Remove','trash',`data-value="${r.id}" ${active?'disabled':''}`)}</div></article>`).join('')+'</div>':empty('No videos yet','Drop one or more episodes here','folder'));}
 else if(page==='terminal')return `<section class="page terminal-page"><div class="row spread terminal-tools"><div class="row wrap"><select id="log-source" aria-label="${esc(t('Log source'))}">${logSources.map(r=>`<option value="${esc(r.id)}" ${logSource===r.id?'selected':''}>${esc(t(r.title))}</option>`).join('')}</select><label class="check"><input id="errors-only" type="checkbox" ${errorsOnly?'checked':''}>${esc(t('Errors only'))}</label><input id="log-search" placeholder="${esc(t('Search logs'))}" value="${esc(logSearch)}"><label class="check"><input id="follow-logs" type="checkbox" ${followLogs?'checked':''}>${esc(t('Follow latest'))}</label></div><div class="row">${button('refresh-logs','Refresh','refresh')}${button('copy-logs','Copy logs','terminal')}${button('export-logs','Export debug report','download')}</div></div><pre id="terminal-output" class="terminal-output"></pre></section>`;
 else if(page==='defaults'){content=pageHeader('Production defaults','Choose Cantonese, English or both. Audio and subtitles are configured automatically.')+`<div class="defaults-grid"><div class="card">${productionSettings(true)}</div><div class="card"><h3>${esc(t('Reference strategy'))}</h3><p class="muted">${esc(t('Select a timeline line to edit, audition or retake it. Save your draft and export a new version. Switching modes keeps the same project and settings.'))}</p><div class="warning">${esc(t('High speed skips all quality review and quality-driven retakes. The video may contain dubbing defects.'))}</div></div></div>`;}
 else if(page==='models'){const extras=modelChoices.filter(r=>r.category==='voice'&&!inventory.some(v=>v.id===r.id&&v.installed));const selected=state.settings.ttsBackend,installed=engineInstalled(selected);content=pageHeader('Model centre','One selected version per purpose. Remove other versions below.',button('change-models','Change selected models','settings','',active?'disabled':''))+`<section class="card stack selected-model-status ${!installed?'warning':''}"><h3>${esc(t('Selected voice model'))} · ${esc(engineName(selected))}</h3><p>${esc(t(installed?'Downloaded and ready':active?.setup?'Download in progress':setupFailure?'Setup failed; this model is not ready.':'Selected, but not downloaded yet.'))}</p>${setupFailure?`<small>${esc(setupFailure)}</small>`:''}${!installed&&!active?`<div class="row wrap">${button('setup','Retry setup','refresh','',!plan?.canDeployModels||!termsReady()?'disabled':'')}${setupFailure?button('installation-details','View error details','info'):''}</div>`:''}</section><div id="model-maintenance-status">${maintenanceHTML()}</div><section class="card stack"><h3>${esc(t('Download another voice model'))}</h3><small>${esc(t('Download without switching'))} · ${esc(t('Download only; deploy this voice engine before it can join automatic repair.'))}</small><div class="row wrap"><select id="extra-voice-model" aria-label="${esc(t('Download another voice model'))}">${extras.map(r=>`<option value="${esc(r.id)}">${esc(r.title)} · ${bytes(r.bytes)}</option>`).join('')}</select>${button('download-extra-voice','Download without switching','download','',active||!extras.length?'disabled':'')}</div></section>${modelGroups(true)}`;}

 else if(page==='preferences'){content=pageHeader('Preferences')+`<div class="preferences-grid"><div class="card stack">${field('Interface language',`<select id="preferences-language"><option value="en" ${state.language==='en'?'selected':''}>English</option><option value="zh-HK" ${state.language==='zh-HK'?'selected':''}>香港繁體中文</option></select>`)}<small>${esc(t('New workflow entries use this language. Earlier entries and raw model output are kept.'))}</small>${field('Appearance',select('appearance',[['system','System'],['light','Light'],['dark','Dark']],state.settings.appearance||'system'))}${field('Theme',`<div class="theme-dots">${Object.keys(THEMES).map(k=>`<button data-action="theme" data-value="${k}" class="theme-dot ${themeKey===k?'active':''}" style="background:${THEMES[k]}" title="${k}" aria-label="${k}"></button>`).join('')}</div>`)}${check('randomAnimeTheme','Random theme at startup',state.settings.randomAnimeTheme===true)}</div><div class="card stack"><h3>${esc(t('Local models & setup'))}</h3><small>${esc(state.storage)}</small><div class="row wrap">${button('welcome-models','Download management','model')}</div></div></div>`;}
 return `<section class="page" data-page="${esc(page)}" data-project="${esc(state.selected||'')}"><div class="page-inner">${content}</div></section>`}
function rolesPage(){
 const roles=draft?.settings?.voiceProfiles||snapshot.roles||[];
 const independent=roles.filter(p=>p.identityStatus==='independent').length;
 const summary=independent===roles.length&&roles.length?'These are source references for individual lines, not identified characters.':'Reference voices and character profiles for this project.';
 return pageHeader('Roles & source references')+`<div class="card role-notice"><strong>${esc(t(independent===roles.length&&roles.length?'Source voice per line':'Character analysis'))}</strong><p>${esc(t(summary))}</p><details><summary>${esc(t('About full AI character analysis'))}</summary><p>${esc(t(FULL_AI_NOTICE))}</p></details></div>`+
 (roles.length?`<div class="role-tools"><label for="role-search">${esc(t('Find a reference'))}</label><input id="role-search" type="search" value="${esc(roleQuery)}" placeholder="${esc(t('Search line number, name or transcript'))}"><small id="role-count" aria-live="polite"></small></div><div class="roles-grid">${roles.map((p,i)=>roleCard(p,i)).join('')}</div><p id="role-no-results" class="muted" hidden>${esc(t('No matching references'))}</p>`:empty('No roles yet','References appear after speech analysis.','roles'));
}
function roleCard(p,index){
 const independent=p.identityStatus==='independent';
 const n=Number.isInteger(p.sourceIndex)&&p.sourceIndex>=0?p.sourceIndex+1:index+1;
 const label=independent?(state.language==='en'?`Line ${n} · Source voice`:`第 ${n} 句原聲`):p.name||p.id||`${t('Role')} ${n}`;
 const number=independent?`#${String(n).padStart(3,'0')}`:`R${String(index+1).padStart(2,'0')}`;
 const range=p.referenceRanges?.[0];
 const duration=p.originalReferenceSeconds;
 const status=independent?'Source reference':({confirmed:'Confirmed',uncertain:'Unconfirmed',verified:'Confirmed',candidate:'Candidate'})[p.identityStatus]||'Character reference';
 const search=[n,number,label,p.name,p.id,p.promptText].join(' ').toLocaleLowerCase();
 const hidden=roleQuery&&!search.includes(roleQuery.toLocaleLowerCase().trim());
 return `<article class="card role-card" data-role-id="${esc(p.id)}" data-role-search="${esc(search)}" ${hidden?'hidden':''}><div class="role-head">${p.avatar?`<img class="role-portrait" src="${esc(asset(p.avatar))}" alt="">`:`<div class="role-number" aria-label="${esc(label)}">${esc(number)}</div>`}<div class="role-heading"><h3>${esc(label)}</h3><span class="role-kind">${esc(t(status))}</span></div></div>${!independent?`<small class="role-id">${esc(p.id||'')}</small>`:''}${range?`<div class="role-meta"><span>${esc(tc(range[0]))} – ${esc(tc(range[1]))}</span>${Number.isFinite(duration)?`<span>${Number(duration.toFixed(1))} ${esc(t('sec'))}</span>`:''}</div>`:''}<label class="role-transcript-label" for="role-text-${index}">${esc(t('Reference transcript'))}</label><textarea id="role-text-${index}" data-role-text="${esc(p.id)}" rows="3">${esc(p.promptText||'')}</textarea>${p.referenceIssue?`<small class="warning">${esc(p.referenceIssue)}</small>`:''}${button('role-audio','Reference audio','sound','',p.reference?`data-path="${esc(p.reference)}"`:'disabled')}</article>`;
}
function filterRoles(){
 const cards=$$('.role-card');let visible=0;const query=roleQuery.toLocaleLowerCase().trim();
 for(const card of cards){card.hidden=!card.dataset.roleSearch.includes(query);if(!card.hidden)visible++;}
 if($('#role-count'))$('#role-count').textContent=`${visible} / ${cards.length} · ${t('References')}`;
 if($('#role-no-results'))$('#role-no-results').hidden=visible>0;
}
function historyRow(h){return `<div class="history-row"><div><strong>${esc(engineName(h.engine))} · ${esc(h.language)}</strong><br><small>${esc(h.reason||'')} · ${shortTime(h.seconds||h.audioSeconds)} · ${esc(h.text||'')}</small></div>${button('history-audio','Listen to take','play','',`data-path="${esc(h.path)}"`)}</div>`}
function appendProcessLog(text,structured=false){if(installationActive()&&!structured){installationLog.event({message:String(text)});scheduleInstallation();}if(logSources.some(r=>r.id===logSource&&r.title==='Process output'))logs=(logs+text+'\n').slice(-262144);if(page==='terminal')updateLogs()}
async function refreshLogs(){logSources=await rpc('log-sources');if(!logSources.some(r=>r.id===logSource))logSource=logSources[0]?.id||'';logs=await rpc('logs',{source:logSource});const el=$('#log-source');if(el)el.innerHTML=logSources.map(r=>`<option value="${esc(r.id)}" ${logSource===r.id?'selected':''}>${esc(t(r.title))}</option>`).join('');updateLogs()}
function updateLogs(){const el=$('#terminal-output');if(!el)return;const lines=logs.split('\n').filter(l=>(!logSearch||l.toLowerCase().includes(logSearch.toLowerCase()))&&(!errorsOnly||/error|fail|exception|traceback|denied|錯誤|失敗|未能|缺聲/i.test(l)));el.textContent=lines.join('\n')||t('No logs yet');if(followLogs)el.scrollTop=el.scrollHeight}

function bindVideo(){const v=$('#video');if(!v)return;v.ontimeupdate=()=>{if(!previewEnabled||!v.getAttribute('src'))return;sourceTime=v.currentTime;updatePlayer();updateAudition()};v.onloadedmetadata=()=>{if(!previewEnabled||!Number.isFinite(v.duration))return;duration=v.duration;if(sourceTime>0&&sourceTime<=duration)v.currentTime=sourceTime;if($('#seek'))$('#seek').max=duration;if($('#play-duration'))$('#play-duration').textContent=tc(duration);renderTimeline()};v.onloadeddata=()=>{if(!previewEnabled)return;previewLoading=false;previewError='';if($('#video-notice'))$('#video-notice').style.display='none';updatePreviewSurface();};v.onerror=()=>{if(!previewEnabled||!v.getAttribute('src'))return;if(previewFallback){previewFallback=false;safely(()=>loadMedia(previewOutput,true));return}previewError='decode';previewLoading=false;updatePreviewSurface();};}
let lastAuditionCue=-2;
function updatePlayer(){if($('#play-time'))$('#play-time').textContent=tc(sourceTime);if($('#seek')&&document.activeElement!==$('#seek'))$('#seek').value=sourceTime;if($('#video-caption')){const text=captionLanguage==='none'?'':captionLanguage==='original'?originalCaption(sourceTime):captionAt(cues(),sourceTime,captionLanguage);$('#video-caption').innerHTML=text?`<span>${esc(text)}</span>`:''}if($('#timeline-head'))$('#timeline-head').style.left=`${155+sourceTime*zoom}px`}
async function loadMedia(output=false,compatible=false){
 const r=row();if(!previewEnabled||!r||screen!=='studio'||page!=='edit')return;
 previewLoading=true;previewError='';previewProgress=null;previewFallback=false;previewOutput=output;
 updatePreviewSurface();const token=++previewToken,id=r.id,params={id,output,compatible};
 const key=JSON.stringify(params);
 clearInterval(previewTimer);
 let checking=false;
 previewTimer=setInterval(async()=>{
  if(checking||token!==previewToken||!previewLoading)return;
  checking=true;
  try{const p=await rpc('media-status',params);if(token!==previewToken)return;previewProgress=p;if(p.duration&&!duration){duration=p.duration;if($('#play-duration'))$('#play-duration').textContent=tc(duration)}updatePreviewSurface()}
  catch(e){console.warn(e)}finally{checking=false}
 },750);
 try{
  if(!mediaRequests.has(key)){
   const request=invoke('studio_media',{params}).finally(()=>{if(mediaRequests.get(key)===request)mediaRequests.delete(key)});
   mediaRequests.set(key,request);
  }
  const m=await mediaRequests.get(key);
  if(token!==previewToken||state.selected!==id||!previewEnabled)return;
  mediaPath=m.path;duration=m.duration;mediaKind=output?'output':'source';previewFallback=!!m.fallbackAvailable;
  const v=$('#video');if(v){v.src=asset(mediaPath);v.preload='auto';v.load();renderTimeline()}
 }catch(e){if(token!==previewToken)return;previewLoading=false;previewError=String(e);updatePreviewSurface();toast(String(e),true)}
 finally{if(token===previewToken)clearInterval(previewTimer)}
}
function seek(seconds){sourceTime=Math.max(0,Math.min(duration||seconds,seconds));const v=$('#video');if(v&&previewEnabled&&v.getAttribute('src')&&v.readyState>0)v.currentTime=sourceTime;updatePlayer()}
let audioToken=0;
function playAudio(path,start=0,end=null){const a=$('#audition'),token=++audioToken;$('#video')?.pause();a.pause();a.onloadedmetadata=null;a.ontimeupdate=null;a.src=asset(path);const play=()=>{if(token!==audioToken)return;a.currentTime=Math.max(0,start);a.play().catch(e=>toast(e.message,true));};a.onloadedmetadata=play;a.ontimeupdate=()=>{if(token===audioToken&&Number.isFinite(end)&&a.currentTime>=end)a.pause();};if(a.readyState>=1)play();}
function chooseCue(index,seekTo=true){if(index<0||index>=cues().length)return;rememberTimelineViewport();selectedCue=index;auditionEngine=null;if(seekTo)seek(cues()[index].start);renderTranscript();renderTimeline();updateAudition()}
function checkpoint(){if(!draft)return;undoStack.push(structuredClone(draft));if(undoStack.length>50)undoStack.shift();redoStack=[];dirty=true}
async function save(){if(!draft)return;await rpc('save-draft',{id:state.selected,draft});dirty=false;toast(t('Saved'))}
const EXPORT_SETTINGS=['backgroundGain','backgroundDucking','includeOriginal','subtitleModes','subtitleSelection','exportFolder','selectedEngines','ttsBackend','defaultAudioEngine','dubLanguages','model','asrModel','speechModel','drama3Model','cosyModel','voxcpmModel','wsyueModel','deploymentModels'];
function updateDraftSettings(keys){if(!draft)return;const changed=keys.filter(k=>state.settings[k]!==undefined&&JSON.stringify(draft.settings[k])!==JSON.stringify(state.settings[k]));if(!changed.length)return;checkpoint();for(const k of changed)draft.settings[k]=structuredClone(state.settings[k]);}
function settingsViewport(){return ['#inspector-content','.main .page'].map(selector=>{const el=$(selector);return {selector,top:el?.scrollTop||0,details:el?$$('details',el).map(d=>d.open):[]};});}
function restoreSettingsViewport(saved){for(const item of saved){const el=$(item.selector);if(!el)continue;$$('details',el).forEach((d,i)=>{if(i<item.details.length)d.open=item.details[i]});el.scrollTop=item.top;}}
async function setSettings(patch,params={}){const viewport=settingsViewport();state=await configure({settings:patch,...params});
 updateDraftSettings(EXPORT_SETTINGS.filter(k=>k in patch||['subtitleModes','subtitleSelection'].includes(k)&&('dubLanguages' in patch||'subtitleSelection' in patch)||k==='defaultAudioEngine'&&'ttsBackend' in patch));
 applyTheme();if($('#inspector-content'))$('#inspector-content').innerHTML=state.mode==='expert'?inspectorHTML():productionSettings(false);if(page==='defaults'){const main=$('.main');main.querySelector('.page').outerHTML=fullPage()}if(page==='preferences')render();if(patch.selectedEngines)renderTimeline();restoreSettingsViewport(viewport);}

async function refreshState(){const revision=queueRevision;const next=await rpc('state');if(revision!==queueRevision)return;state=next;runtimeReady=true;refreshQueueViews();updateProgress();}
async function refreshSnapshot(){if(!row())return;const id=state.selected;const next=await rpc('snapshot',{id});if(state.selected!==id)return;const changed=JSON.stringify(next.draft?.segments)!==JSON.stringify(snapshot.draft?.segments)||next.takes?.length!==snapshot.takes?.length;const reviewChanged=JSON.stringify([next.issues,next.resolvedIssues,next.reviewState,next.draft?.segments])!==JSON.stringify([snapshot.issues,snapshot.resolvedIssues,snapshot.reviewState,snapshot.draft?.segments]);const rootChanged=snapshot.root!==next.root;snapshot=next;duration=Number(next.review?.config?.duration||next.draft?.settings?.duration||duration)||duration;if(!dirty&&!next.draft&&rootChanged){draft=null;renderTranscript();renderTimeline();updateAudition();}if(!dirty&&next.draft){draft=next.draft;if(changed){renderTranscript();renderTimeline();updateAudition()}}if(next.journey)journey=mergeJourney(journey,next.journey,runID||`saved-${id}`);updateProgress();if(page==='review'&&reviewChanged&&!document.activeElement?.matches('[data-review-choice],[data-review-recording]')){const el=$('.main .page');if(el){const saved=captureReviewViewport();el.outerHTML=fullPage();restoreReviewViewport(saved);}}}
async function selectRow(id){if(dirty)await save();state=await rpc('select',{id});snapshot={};draft=null;dirty=false;selectedCue=0;retakeEngine=null;auditionEngine=null;journey=null;sourceTime=0;duration=0;mediaPath='';undoStack=[];redoStack=[];await refreshSnapshot();if(screen==='studio'){render();await loadMedia()}}
let sourceConfirmation=null;
function sourceLanguage(){return row()?.sourceLanguage||snapshot.review?.config?.sourceLanguage||'ja'}
function sourceLabel(){const code=sourceLanguage(),known=({ja:'Japanese source',en:'English source',zh:'Chinese source',ko:'Korean source'})[code];return known?t(known):`${t(row()?.sourcePreflight?.name||code)} · ${t('Original dialogue')}`}
async function startConversion(id=state.selected,freshVersion=false){
 if(active||starting||!id)return;
 starting=true;
 startPromise=(async()=>{
  // Selection is essential; snapshot / decoder refresh is optional and must not
  // prevent the next queued conversion from starting.
  if(state.selected!==id){
   if(dirty)await save();
   state=await rpc('select',{id});
   ++previewToken;$('#video')?.pause();$('#audition').pause();
   for(const el of [$('#video'),$('#audition')])if(el){el.removeAttribute('src');el.load()}
   snapshot={};draft=null;dirty=false;selectedCue=0;sourceTime=0;duration=0;mediaPath='';journey=null;undoStack=[];redoStack=[];
   retakeEngine=null;auditionEngine=null;
  }
  render();
  let sourceConfirmed=null;
  if(state.queue.find(r=>r.id===id)?.status!=='paused'&&!state.queue.find(r=>r.id===id)?.output){
   // Automatic detection uses the existing Starting status. A drawer is
   // reserved for a decision, so normal Japanese starts never flash a panel.
   const info=await rpc('source-language',{id});
   state=await rpc('state');if(info.language==='en')language='yue';
   if(info.needsConfirmation){
    const accepted=await new Promise(resolve=>{
     sourceConfirmation=resolve;
     showDrawer('Source language',`<h3>${esc(t('Detected language'))}: ${esc(t(info.name))}</h3><p>${esc(t(info.supported?(info.language==='en'?'English source: generate Cantonese dubbing and Cantonese subtitles only.':'Translate this source into the selected Cantonese / English output. Other source languages use Normal mode with independent voice references.'):(info.reason||'This source language is not supported.')))}</p><p>${esc(t('Experimental source-language support. Accuracy and voice imitation depend on the models.'))}</p><div class="row">${button('close-drawer','Cancel')}${info.supported?button('confirm-source-language','Convert this language','play','primary'):''}</div>`);
    });
    if(!accepted){conversionQueue.stop();await rememberQueue(false);return;}
    sourceConfirmed=info.token;
   }
  }
  const spec=await invoke('studio_start',{op:'start',params:{id,sourceConfirmed,freshVersion}});
  runID=spec.id;journey=null;phaseSample=null;
  if(!finishedRunIDs.has(spec.id))active={id:spec.id,rowID:id,action:'batch',seconds:0};
  // A successful launch must never be treated as a launch failure because an
  // optional UI refresh failed (which could launch another job concurrently).
  await refreshState().catch(e=>console.warn(e));
  await refreshSnapshot().catch(e=>console.warn(e));
  render();if(!mediaPath)await loadMedia().catch(e=>console.warn(e));
 })();
 try{await startPromise}finally{starting=false;render()}
}
async function rememberQueue(enabled){state=await configure({ui:{autoQueue:enabled,autoQueueAttention:enabled&&conversionQueue.includeAttention},settings:{}})}
async function advanceQueue(){
 await queueOrder.idle();
 let id;
 while(!active&&(id=conversionQueue.next(state.queue))){
  try{await startConversion(id,conversionQueue.freshVersionID===id);return}catch(e){toast(`${filename(state.queue.find(r=>r.id===id)?.video)} · ${t(e.message||String(e))}`,true)}
  if(!conversionQueue.enabled)break;
 }
 conversionQueue.stop();await rememberQueue(false);
}
async function beginConversion(selected,all,includeAttention=false,freshVersion=false){
 if(active||starting||finishingRun)return;
 if(!conversionModelsReady()){toast(t('Prepare models before starting conversion.'));return;}
 starting=true;render();
 try{conversionQueue.begin(state.queue,{selected,all,includeAttention});conversionQueue.freshVersionID=freshVersion?selected:null;await rememberQueue(all)}
 catch(e){conversionQueue.stop();throw e}
 finally{starting=false}
 await advanceQueue();render();
}
async function pauseConversion(){
 conversionQueue.stop();
 // If the click lands while launch is being prepared, wait for the owned child
 // before pausing it, rather than allowing it to start after the pause request.
 await startPromise?.catch(()=>{});
 if(active)await invoke('studio_pause');
 await rememberQueue(false);
}
async function renderVersion(segment=null,submitted=draft){if(active||!submitted)return;const spec=await invoke('studio_start',{op:'render',params:{id:state.selected,draft:submitted,segment,engine:retakeEngine||state.settings.ttsBackend,language}});dirty=false;runID=spec.id;phaseSample=null;active={id:spec.id,rowID:state.selected,seconds:0};await refreshState();render();}
async function refreshModels(){inventory=await rpc('models');if(page==='models')modelChoices=await rpc('model-choices');updateSetup();if(page==='models'&&screen==='studio'){const el=$('.main .page');if(el){const saved=captureReviewViewport();el.outerHTML=fullPage();restoreReviewViewport(saved);}}}
let drawerReturnFocus=null;
async function closeDrawer(){
 const shade=$('.drawer-shade');if(!shade)return;
 if(shade._closing)return shade._closing;
 const panel=$('.drawer',shade),transform=getComputedStyle(panel).transform,backgroundColor=getComputedStyle(shade).backgroundColor;shade.classList.add('closing');
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 shade._closing=(async()=>{
  if(!reduced&&shade.animate){
   // Start at the current presentation position, including a partly opened panel.
   const effects=[panel.animate([{transform},{transform:'translateX(100%)'}],{duration:220,easing:'cubic-bezier(.4,0,1,1)',fill:'forwards'}),shade.animate([{backgroundColor},{backgroundColor:'transparent'}],{duration:220,fill:'forwards'})];
   await Promise.all(effects.map(a=>a.finished.catch(()=>{})));
  }
  const current=shade.parentElement===document.querySelector('#drawer-root');if(current&&!switchStarting)switchBusy=false;shade.remove();
  // A late close must never delete a newly opened replacement drawer.
  if(current&&drawerReturnFocus?.isConnected)drawerReturnFocus.focus();
 })();return shade._closing;
}
async function showDrawer(title,body){const previous=$('.drawer');if(!previous?.contains(document.activeElement))drawerReturnFocus=document.activeElement;$('#drawer-root').innerHTML=`<div class="drawer-shade" data-action="close-drawer"><aside class="drawer" role="dialog" aria-modal="true" aria-label="${esc(t(title))}"><div class="drawer-header"><span>${esc(t(title))}</span>${ib('close-drawer','Close','close')}</div><div class="drawer-body">${body}</div></aside></div>`;$('.drawer button')?.focus()}
function guide(){
 helpQuery='';helpChapter='start';
 showDrawer('Help centre',`<div class="help-layout"><div class="help-sidebar"><label for="help-search">${esc(t('Search the manual'))}</label><input id="help-search" type="search" autocomplete="off" placeholder="${esc(t('Search topics…'))}" aria-controls="help-toc help-article"><small id="help-count" role="status" aria-live="polite"></small><nav id="help-toc" aria-label="${esc(t('Chapters'))}"></nav></div><article id="help-article" tabindex="-1" aria-labelledby="help-article-title"></article></div>`);
 $('.drawer').classList.add('help-drawer');renderHelp();$('#help-search')?.focus();
}
function renderHelp(){
 const all=chapters(state.language),matches=searchChapters(all,helpQuery);
 if(!matches.some(c=>c.id===helpChapter))helpChapter=matches[0]?.id||'';
 $('#help-count').textContent=`${matches.length} / ${all.length} · ${t('Chapters')}`;
 $('#help-toc').innerHTML=matches.map(c=>`<button data-action="help-chapter" data-value="${c.id}" class="${c.id===helpChapter?'active':''}" aria-current="${c.id===helpChapter?'page':'false'}"><span>${String(c.number).padStart(2,'0')}</span><span>${esc(c.title)}</span></button>`).join('');
 const article=$('#help-article'),current=matches.find(c=>c.id===helpChapter);
 article.innerHTML=current?articleHTML(current):`<h2 id="help-article-title">${esc(t('No matching chapters'))}</h2><p>${esc(t('Try a shorter search or another word.'))}</p>`;article.scrollTop=0;
 if(current){const i=all.findIndex(c=>c.id===current.id);article.innerHTML+=`<div class="help-pagination">${i?button('help-chapter',all[i-1].title,'back','',`data-value="${all[i-1].id}"`):'<span></span>'}${i<all.length-1?button('help-chapter',all[i+1].title,'chevron','',`data-value="${all[i+1].id}"`):''}</div>`;}
}
async function about(){await showDrawer('About & licences',`<div class="row">${icon('logo')}<h1>AniCanto</h1></div><small>${esc(APP_VERSION)} · AniCanto · ${esc(COPYRIGHT)}</small><div class="about-project"><a href="${esc(PROJECT_URL)}" data-action="open-project-link" rel="noopener noreferrer">${esc(PROJECT_URL)}</a><small>${esc(t('GitHub project'))}</small></div>${aboutCopy(state.language).map(section=>`<section class="about-section"><h3>${esc(section.title)}</h3><p>${esc(section.text)}</p></section>`).join('')}<div class="rule"></div><h3>${esc(t('Application licence'))}</h3><p>AniCanto · MIT · SCKC</p><details><summary>MIT License</summary><pre id="application-license-text">${esc(APPLICATION_LICENSE)}</pre></details>${licenceCopy(state.language).map(section=>`<section class="about-section licence-guidance"><h3>${esc(section.title)}</h3><p>${esc(section.text)}</p></section>`).join('')}<div class="rule"></div><h3>Built with Fish Audio</h3><p>${esc(t('Drama 3 uses the Fish Audio Community License v1.0. Model terms are separate from the MIT application licence.'))}</p>${button('use-terms','Read use conditions','info')}${downloadSourcesSection(t)}<div class="rule"></div><h3>${esc(t('Third-party libraries & licences'))}</h3><input id="license-search" placeholder="${esc(t('Search components'))}"><p id="license-status" role="status">${esc(t('Loading licence inventory…'))}</p><div id="license-list"></div>`);
 const sources=$('#download-source-list');if(sources){const renderSources=()=>{$('#download-source-count').textContent=renderDownloadSources(sources,$('#download-source-search').value,t);};$('#download-source-search').addEventListener('input',renderSources);renderSources();}
 await loadLicenses();}
let licenseRows=[];
async function loadLicenses(){const session=++aboutSession,marker=$('#license-status');if(!marker)return;marker.textContent=t('Loading licence inventory…');
 try{const all=await rpc('licenses');if(session!==aboutSession||!marker.isConnected)return;const rows=Array.isArray(all)?all:all.components||all.packages||[];const seen=new Set();licenseRows=rows.filter(r=>{const key=JSON.stringify([r.name,r.version,r.license,r.text||r.licenseText]);if(seen.has(key))return false;seen.add(key);return true});
 if(!licenseRows.length)throw Error(t('The licence inventory is unavailable. Repair the app package and try again.'));renderLicenses($('#license-search')?.value||'');}
 catch(error){if(session!==aboutSession||!marker.isConnected)return;marker.innerHTML=`<span class="warning">${esc(t('Could not load licence information.'))} ${esc(error.message||error)}</span> ${button('retry-licenses','Try again','refresh')}`;}}
function renderLicenses(filter){const el=$('#license-list');if(!el)return;const rows=licenseRows.filter(r=>`${r.name} ${r.version} ${r.license} ${r.origin||''}`.toLowerCase().includes(filter.toLowerCase()));
 const status=$('#license-status');if(status)status.textContent=`${rows.length} / ${licenseRows.length} · ${t('Components')}`;
 const groups=new Map();for(const row of rows){const name=row.name?.includes('(optional model)')?'Model weight notices':/runtime|Application Support|Bundled wheel|CPython|pip|Python/i.test(row.origin||row.name)?'Processing runtimes':/font|icon|reference|artwork/i.test(row.name)?'Artwork, fonts and references':'Native tools and application libraries';if(!groups.has(name))groups.set(name,[]);groups.get(name).push(row);}
 const componentHTML=r=>`<details class="package-row" style="display:block"><summary><span class="grow">${esc(r.name)} <small>${esc(r.version)}</small></span><small>${esc(r.license||r.licence||'')}</small></summary><small>${esc(r.origin||r.runtimes?.join(' · ')||'')}</small><pre>${esc(r.text||r.licenseText||t('No separate notice text was supplied; see the component origin and licence identifier.'))}</pre></details>`;
 el.innerHTML=rows.length?[...groups].map(([name,items])=>`<details class="licence-group" ${filter?'open':''}><summary><strong>${esc(t(name))}</strong><small>${items.length} ${esc(t('Components'))}</small></summary>${items.map(componentHTML).join('')}</details>`).join(''):`<p>${esc(t('No matching components'))}</p>`;}
async function chooseVoiceEngine(engine){
 if(active||modelStartBusy||switchBusy){toast(t('Wait for the current task to finish before changing models.'),true);render();return;}
 if(engineBlocked(engine)){toast(t('WenetSpeech-Yue supports Cantonese only. Choose another engine for English or bilingual dubbing.'),true);render();return;}
 if(engineInstalled(engine)){await changeModels(engine);return;}
 modelStartBusy=true;
 try{
  const models={...state.settings.deploymentModels};delete models.voice;
  const proposal=await rpc('plan',{engine,models});
  if(!proposal.canDeployModels||proposal.engine!==engine||!proposal.roles?.voice)throw Error(t('This voice model is not available for this computer.'));
  const params={engine,models:{...models,...Object.fromEntries(Object.entries(proposal.roles).filter(([key])=>['voice','text','speech','asr','referenceSpeech'].includes(key)))},removeOld:false};setupReturn={screen,page};beginInstallation();
  installationLog.event({message:engineName(engine)});
  startPromise=invoke('studio_start',{op:'setup',params});const r=await startPromise;
  if(!finishedRunIDs.has(r.id)){active={id:r.id,setup:true,seconds:0};setupEvent={message:engineName(engine)};}
  render();
 }finally{modelStartBusy=false;startPromise=null;}
}
async function changeModels(engine){
 if(active){toast(t('Pause & save'),true);return;}
 const session=++switchSession;++switchRevision;switchBusy=true;
 pendingSwitch={engine:engine||state.settings.ttsBackend,models:{...state.settings.deploymentModels},removeOld:state.mode!=='expert'};
 if(engine&&engine!==state.settings.ttsBackend)delete pendingSwitch.models.voice;
 await showDrawer('Change models',`<div id="model-switch" class="stack"><p class="quality-expectation">${esc(t('Drama 3 sounds closer to Hong Kong Cantonese in our listening tests. Other models may retain a Japanese accent.'))}</p><p>${esc(t('The current model stays available until the new download is verified.'))}</p><div id="switch-controls"></div><div id="switch-plan" role="status">${esc(t('Checking model choices…'))}</div><div class="row">${button('close-drawer','Cancel',null)}${button('confirm-switch','Checking model choices…','download','primary','disabled')}</div></div>`);
 try{modelChoices=await rpc('model-choices');if(session!==switchSession||!$('#model-switch'))return;await reviewSwitch();}
 catch(error){if(session!==switchSession||!$('#switch-plan'))return;$('#switch-plan').textContent=String(error.message||error);throw error;}
}
function modelMemorySummary(proposal,selection,categories){
 const h=proposal.hardware||plan?.hardware||{},ram=Number(h.memoryGB||0),vram=Number(h.acceleratorMemoryGB||0);
 const dedicated=h.platform==='windows'&&['cuda','rocm','xpu'].includes(h.backend);
 const inactiveDiscrete=h.platform==='windows'&&!dedicated?(h.displayAdapters||[]).filter(a=>[0x10de,0x1002].includes(Number(a.vendorId))&&Number(a.dedicatedMemoryGB||0)>1).sort((a,b)=>Number(b.dedicatedMemoryGB)-Number(a.dedicatedMemoryGB))[0]:null;
 const capacity=dedicated?vram:ram,reserve=Number(proposal.systemReserveGB??plan?.systemReserveGB??Math.max(8,ram*.15)),budget=Number(proposal.memoryBudgetGB??plan?.memoryBudgetGB??0);
 const selected=categories.map(([role,,category])=>modelChoices.find(m=>m.id===(selection.models[role]||proposal.roles?.[role])&&m.category===category)).filter(Boolean);
 const peak=Math.max(0,...selected.map(m=>Number(m.estimatedMemoryGB||0)),...(proposal.downloads||[]).map(m=>Number(m.estimatedMemoryGB||0)));
 const fit=capacity>0&&budget>0&&peak<=budget;
 const label=dedicated?'Dedicated GPU VRAM':h.platform==='macos'?'Unified memory':'System RAM';
 const percent=capacity?Math.min(100,Math.round(100*peak/capacity)):0;
 return {fit,html:`<section class="model-memory" role="status"><strong>${esc(t('Estimated peak model memory'))}: ${peak.toFixed(1)} / ${capacity?capacity.toFixed(1):'—'} GB ${esc(t(label))}</strong><div class="download-fill" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}" aria-label="${esc(t('Estimated memory usage'))}"><i style="width:${percent}%"></i></div><small>${esc(t('Available model budget'))}: ${budget.toFixed(1)} GB · ${esc(t('System reserve'))}: ${reserve.toFixed(1)} GB</small>${dedicated?`<small>${esc(t('System RAM'))}: ${ram.toFixed(1)} GB · ${esc(t('Dedicated GPU VRAM'))}: ${vram?vram.toFixed(1):'—'} GB</small>`:inactiveDiscrete?`<small>${esc(t('Dedicated GPU VRAM'))}: ${Number(inactiveDiscrete.dedicatedMemoryGB).toFixed(1)} GB · ${esc(t('GPU inference unavailable; model memory is checked against system RAM.'))}</small>`:''}<small>${esc(t('Models run in sequence; the figure is the largest selected model, not the sum.'))}</small>${dedicated&&!vram?`<p class="warning">${esc(t('Dedicated GPU VRAM could not be verified. Deployment is blocked until it can be measured.'))}</p>`:!fit?`<p class="warning">${esc(t('This model combination exceeds the available memory. Choose a smaller model.'))}</p>`:''}</section>`};
}
async function reviewSwitch(){
 const revision=++switchRevision,selection=structuredClone(pendingSwitch);switchBusy=true;
 const confirm=$('[data-action=confirm-switch]');if(confirm)confirm.disabled=true;
 if($('#switch-plan'))$('#switch-plan').textContent=t('Checking download plan…');
 try{
 let proposal,planningError='';
 try{proposal=await rpc('plan',{engine:selection.engine,models:selection.models});}
 catch(error){planningError=String(error.message||error);if(!planningError.includes('incompatible-requested-model'))throw error;proposal={...(plan||{}),engine:selection.engine,roles:{...(plan?.roles||{}),...selection.models},canDeployModels:false,blockers:[planningError],downloads:[],modelDownloadBytes:0};}
 if(revision!==switchRevision||!$('#model-switch'))return;
 const roles=proposal.roles||{};
 const categories=[['text','Text translation','text'],['voice','Voice generation','voice'],['asr','Source dialogue recognition','asr'],['speech','Dubbing verification','speech']];
 if(!$('#switch-engine'))$('#switch-controls').innerHTML=field('Voice engine',select('switch-engine',engineMenu(),pendingSwitch.engine,'id="switch-engine"'))+categories.map(([role,label])=>field(label,`<select data-setting="switch-role" data-role="${role}" id="switch-${role}"></select>`)).join('')+(state.mode==='expert'?`<small>${esc(t('Expert mode keeps extra downloads. Remove unused versions in Model centre.'))}</small>`:`<label class="check"><input id="remove-old-model" type="checkbox" ${pendingSwitch.removeOld?'checked':''}>${esc(t('Remove replaced models after successful setup'))}</label><small>${esc(t('Models used by pending jobs or kept in Expert mode are retained.'))}</small>`);
 for(const [role,label,category] of categories){
  const el=$('#switch-'+role);const choices=modelChoices.filter(r=>r.category===category&&(role!=='voice'||r.engine===proposal.engine));
  const signature=choices.map(r=>r.id).join('|');
  if(el.dataset.options!==signature){el.innerHTML=choices.map(r=>`<option value="${esc(r.id)}">${esc(r.title)} · ${Number(r.estimatedMemoryGB||0).toFixed(1)} GB</option>`).join('');el.dataset.options=signature;}
  const value=roles[role]||selection.models[role]||choices[0]?.id||'';if(el.value!==value)el.value=value;
 }
 if(!planningError&&proposal.canDeployModels!==false){
  for(const [role] of categories){const value=$('#switch-'+role)?.value;if(value)pendingSwitch.models[role]=value;}
 }
 const memory=modelMemorySummary(proposal,selection,categories);
 $('#switch-plan').innerHTML=`${memory.html}<h3>${esc(t('Required download'))} · ${bytes(proposal.modelDownloadBytes)}</h3>${(proposal.downloads||[]).filter(r=>!r.installed).map(r=>`<div class="package-row"><span>${esc(r.title)}</span><small>${bytes(r.bytes)}</small></div>`).join('')}${(proposal.blockers||[]).map(x=>`<p class="warning">${esc(t(x))}</p>`).join('')}`;
 const button=$('[data-action=confirm-switch]');button.disabled=proposal.canDeployModels===false||!memory.fit||!!planningError||!termsReady();button.querySelector('span').textContent=t(proposal.modelDownloadBytes?'Download & switch':'Use selected models');switchBusy=false;
 }catch(error){if(revision!==switchRevision||!$('#switch-plan'))return;$('#switch-plan').innerHTML=`<p class="warning">${esc(String(error.message||error))}</p>${button('retry-model-plan','Retry','refresh')}`;throw error;}
}
function maintenanceHTML(){return installationActive()?`<div class="card model-maintenance" role="status">${installationProgress()}${installationDetails()}</div>`:'';}
async function startModelMaintenance(id,mode='repair'){if(active||modelStartBusy)return;modelStartBusy=true;beginInstallation();setupEvent={message:t('Checking and preparing local files…')};const status=$('#model-maintenance-status');if(status)status.innerHTML=`<div class="card model-maintenance" role="status">${installationProgress()}${installationDetails()}</div>`;paintInstallation();try{const r=await invoke('studio_start',{op:'maintain-model',params:{id,mode}});if(finishedRunIDs.has(r.id)){await closeDrawer();await refreshModels();render();return}active={id:r.id,action:'model-maintenance',modelID:id,seconds:0};setupEvent={message:t('Verifying model files…')};await closeDrawer();render();}finally{modelStartBusy=false;}}
async function maintainModel(id,mode){
 if(active||modelStartBusy)return;
 const model=inventory.find(r=>r.id===id);if(!model)return;
 await showDrawer(mode==='repair'?'Repair download':'Download again',`<h3>${esc(model.title)}</h3><p>${esc(t(mode==='repair'?'Checks every file and downloads only missing or damaged files. Current model choices and projects are kept.':'Downloads fresh copies into a staging folder. Existing model files are kept until the new files have passed checksum verification.'))}</p><small>${esc(t('Model size'))}: ${bytes(model.bytes)}${model.missingFiles?.length?` · ${esc(t('Missing files'))}: ${model.missingFiles.length} (${bytes(model.missingBytes)})`:''}</small><div class="row">${button('close-drawer','Cancel',null)}${button('start-model-maintenance',mode==='repair'?'Repair download':'Download again','download','primary',`data-value="${esc(id)}" data-mode="${mode}"`)}</div>`);
}

function packageProgressHTML(status={}){
 const known=['deleting','tidying'].includes(status.phase)&&Number.isFinite(status.total),percent=known?(status.total?Math.min(100,Math.round(100*(status.processed||0)/status.total)):100):null;
 const label=status.phase==='deleting'?'Removing downloaded files…':status.phase==='tidying'?'Finishing cleanup…':'Checking downloaded files…';
 return `<section class="package-cleanup-progress" aria-busy="true"><h3 role="status">${esc(t(label))}</h3><div class="download-fill ${known?'':'indeterminate'}" role="progressbar" aria-label="${esc(t('Removal progress'))}" aria-valuemin="0" aria-valuemax="100" ${known?`aria-valuenow="${percent}"`:''}><i style="width:${known?percent:30}%"></i></div>${known?`<p class="row spread"><span>${esc(t('Files processed'))}: ${status.processed||0} / ${status.total}</span><strong>${percent}%</strong></p><small>${esc(t('Space freed'))}: ${bytes(status.freedBytes||0)}</small>`:''}<p>${esc(t('Please keep the app open until cleanup finishes.'))}</p></section>`;
}
function onPackageProgress({payload}){if(packageCleaning&&payload.operationID===packageOperation&&$('.package-cleanup-progress'))$('.drawer-body').innerHTML=packageProgressHTML(payload)}
async function refreshAfterPackageCleanup(){
 const previous=selectedQuality;
 runtimeReady=(await invoke('studio_status')).runtimeReady;
 inventory=[];plan=null;selectedQuality=null;setupEvent=null;setupFailure='';
 if(runtimeReady){state=await rpc('state');inventory=await rpc('models');}
 acceptSetupPlan(await rpc('plan'));
 if(previous&&plan?.qualityPresets?.some(p=>p.id===previous&&p.available)){plan=presetPlan(plan,previous);selectedQuality=previous;}
 updateSetup();
}
async function cleanup(mode){
 if(packageCleaning||active)return;
 packageCleaning=true;packageOperation=crypto.randomUUID();
 await showDrawer('Download management',packageProgressHTML());$('.drawer [data-action=close-drawer]').disabled=true;
 try{
  const plan=await invoke('studio_cleanup',{mode,token:null,operation:packageOperation});
  packageCleaning=false;packageOperation=null;
  await showDrawer('Download management',`<h3>${esc(t(mode==='all'?'Remove models & runtimes':'Remove downloaded models'))}</h3><p>${bytes(plan.bytes)} · ${plan.files} ${esc(t('Files'))}</p><p>${esc(t(mode==='all'?'Downloaded models and runtimes will be removed. Projects, source videos and finished exports are kept.':'All app-managed model downloads and partial files will be removed. Projects, source videos, finished exports and runtimes are kept.'))}</p>${plan.groups.map(g=>`<div class="package-row"><span>${esc(g.path)}</span><span>${bytes(g.bytes)}</span></div>`).join('')}<div class="row">${button('close-drawer','Cancel',null)}${button('execute-cleanup','Confirm removal','trash','danger',`data-mode="${mode}" data-token="${esc(plan.token)}"`)}</div>`);
 }catch(error){packageCleaning=false;packageOperation=null;await showDrawer('Download management',`<section class="warning" role="alert"><h3>${esc(t('Cleanup did not finish'))}</h3><p>${esc(t(error.message||String(error)))}</p>${button('close-drawer','Close')}</section>`);}
}
async function executePackageCleanup(mode,token){
 if(packageCleaning||active)return;
 packageCleaning=true;packageOperation=crypto.randomUUID();let result=null;
 await showDrawer('Download management',packageProgressHTML());$('.drawer [data-action=close-drawer]').disabled=true;
 try{
  result=await invoke('studio_cleanup',{mode,token,operation:packageOperation});
  if(result.deferred){$('.drawer-body').innerHTML=`<h3>${esc(t('Finishing cleanup…'))}</h3><p>${esc(t('The app will close so Windows can remove files in use. Open it again to set up models.'))}</p>`;await native.window.getCurrentWindow().close();return;}
  packageOperation=null;
  $('.drawer-body').innerHTML=packageProgressHTML({phase:'checking'});
  await refreshAfterPackageCleanup();
  packageCleaning=false;
  await showDrawer('Download management',`<section class="cache-result ${result.complete?'success':'warning'}" role="status"><h3>${esc(t(result.complete?'Removal complete':'Some files could not be removed'))}</h3><dl><div><dt>${esc(t('Space freed'))}</dt><dd>${bytes(result.bytesFreed??result.freedBytes??0)}</dd></div><div><dt>${esc(t('Files removed'))}</dt><dd>${result.filesDeleted??0}</dd></div></dl><p>${esc(t('Projects, source videos and finished exports were kept.'))}</p><p>${esc(t('Setup is ready to use again without restarting the app.'))}</p>${button('close-drawer','Done',null,'primary')}</section>`);
 }catch(error){
  packageOperation=null;
  await refreshAfterPackageCleanup().catch(()=>{});
  packageCleaning=false;
  await showDrawer('Download management',`<section class="warning" role="alert"><h3>${esc(t(result?'Removal finished; setup status needs refreshing':'Cleanup did not finish'))}</h3><p>${esc(t(error.message||String(error)))}</p><div class="row">${button('close-drawer','Close')}${button('refresh-setup-plan','Refresh setup','refresh','primary')}</div></section>`);
 }finally{packageCleaning=false;packageOperation=null;}
}

async function removeProject(id,b){
 if(removing)return;
 if(active)throw Error(t('Pause processing before removing a project.'));
 removing=true;b.disabled=true;
 try{
  const previous=state.selected,result=await rpc('remove',{id});state=result.state;
  if(state.selected!==previous){
   ++previewToken;$('#video')?.pause();$('#audition').pause();
   for(const el of [$('#video'),$('#audition')])if(el){el.removeAttribute('src');el.load();}
   snapshot={};draft=null;dirty=false;journey=null;runID=null;selectedCue=0;sourceTime=0;duration=0;mediaPath='';mediaKind='source';follow=false;undoStack=[];redoStack=[];
  }
  await closeDrawer();render();
  if(state.selected!==previous){await refreshSnapshot();await loadMedia();}
  toast(t('Project removed. Source videos and exports were kept.'));
 }finally{removing=false;b.disabled=false;}
}
async function action(e){const b=e.target.closest('[data-action]');if(!b||b.disabled)return;const a=b.dataset.action,v=b.dataset.value;if(a==='installation-details'){await showDrawer('Installation details',(setupFailure&&!installationActive()?`<section class="warning setup-failure" role="alert"><strong>${esc(t('Setup did not finish'))}</strong><p>${esc(setupFailure)}</p></section>`:installationProgress())+installationDetails()+(installationActive()?button('pause','Pause download','pause'):setupFailure?button('setup','Retry setup','refresh'):''));const details=$('#drawer .installation-details')||$('.drawer .installation-details');if(details)details.open=true;paintInstallation();return;}if(a==='copy-installation'){await navigator.clipboard.writeText(installationLog.text);toast(t('Copied'));return;}if(a==='open-project-link')e.preventDefault();
 if(a==='confirm-source-language'){const resolve=sourceConfirmation;sourceConfirmation=null;await closeDrawer();resolve?.(true);return}
 if(a==='close-drawer'){if(switchStarting||cacheCleaning||packageCleaning)return;if(e.target.closest('.drawer')&&!e.target.closest('button'))return;++cacheSession;if(sourceConfirmation){sourceConfirmation(false);sourceConfirmation=null;}++switchSession;++switchRevision;await closeDrawer();return}
 await safely(async()=>{
 if(a==='mode'||a==='switch-mode'){const mode=a==='switch-mode'?(state.mode==='basic'?'expert':'basic'):v;state.mode=mode;if(initializing){pendingStartupMode=mode;if(!runtimeReady)pendingConfig={...pendingConfig,mode,settings:{...pendingConfig?.settings}};render();return}render();state=await configure({mode,settings:{}});render();return}
 if(a==='theme'){themeKey=v;localStorage.setItem('anicanto-theme',v);render();if(initializing){welcomeThemeTouched=true;if(!runtimeReady)pendingConfig={...pendingConfig,settings:{...pendingConfig?.settings,animeTheme:v,themeSession:v}};return}await setSettings({animeTheme:v});return}
 if(a==='open-project-link'){await invoke('studio_open_project');return}
 if(a==='use-terms'){await showUseTerms();return}
 if(a==='enter'){await enterWorkspace();return}
 if(a==='welcome'||a==='welcome-models'){screen='welcome';$('#video')?.pause();$('#audition').pause();render();if(a==='welcome-models')$('#setup-details').open=true;return}
 if(a==='page'||a==='projects'){if(dirty)await save();page=a==='projects'?'projects':v;render();if(page==='terminal'){await refreshLogs()}if(page==='models')await refreshModels();return}
 if(a==='back'){page='edit';render();await loadMedia();return}
 if(a==='copy-download-source'){await navigator.clipboard.writeText(v);toast(t('Copied'));return;}
 if(a==='guide'){guide();return}if(a==='help-chapter'){helpChapter=v;helpQuery='';if($('#help-search'))$('#help-search').value='';renderHelp();$('#help-article')?.focus();return}if(a==='retry-licenses'){await loadLicenses();return}if(a==='about'){await about();return}
 if(a==='add'){const paths=await invoke('studio_pick',{kind:'video'});if(paths.length){page='edit';state=await rpc('add',{paths});await selectRow(state.selected);render();if(screen==='studio')await loadMedia()}return}
 if(a==='queue-up'||a==='queue-down'){await queueOrder.run(()=>stepQueueRow(v,a==='queue-up'?-1:1));return}
 if(a==='select'||a==='select-project'){if(a==='select-project')page='edit';await selectRow(v);return}
 if(a==='remove'){
  if(active)throw Error(t('Pause processing before removing a project.'));
  const target=state.queue.find(r=>r.id===(v||state.selected));if(!target)return;
  await showDrawer('Remove project',`<h3>${esc(filename(target.video))}</h3><p>${esc(t('Remove processing data? Completed exports and source videos will be kept.'))}</p><div class="row">${button('close-drawer','Cancel',null)}${button('remove-project','Confirm removal','trash','danger',`data-value="${esc(target.id)}"`)}</div>`);return;
 }
 if(a==='remove-project'){await removeProject(v,b);return;}
 if(a==='change-models'){await changeModels();return;}if(a==='retry-model-plan'){await reviewSwitch();return;}
 if(a==='download-extra-voice'){const id=$('#extra-voice-model')?.value;if(id)await startModelMaintenance(id,'repair');return;}
 if(a==='repair-model'||a==='redownload-model'){await maintainModel(v,a==='repair-model'?'repair':'redownload');return}
 if(a==='start-model-maintenance'){await startModelMaintenance(v,b.dataset.mode);return}
 if(a==='confirm-switch'){if(switchBusy||!pendingSwitch||active||!termsReady())return;switchBusy=true;switchStarting=true;b.disabled=true;const label=b.querySelector('span'),before=label.textContent;label.textContent=t('Starting download…');setupReturn={screen,page};pendingSwitch.removeOld=$('#remove-old-model')?.checked||false;const params=structuredClone(pendingSwitch);let r;try{beginInstallation();if(!runtimeReady){setupSelection=params;deployAfterBootstrap=true;r=await invoke('studio_bootstrap');}else{r=await invoke('studio_start',{op:'setup',params});}}catch(error){deployAfterBootstrap=false;switchBusy=false;b.disabled=false;label.textContent=before;throw error;}finally{switchStarting=false;}if(!finishedRunIDs.has(r.id)){active={id:r.id,setup:true,seconds:0};setupEvent={message:t(runtimeReady?'Downloading & preparing…':'Prepare runtime')};if(!(screen==='studio'&&page==='models'))screen='welcome';}await closeDrawer();render();return;}
 if(a==='production-mode'){await setSettings({productionMode:v});return}
 if(a==='start'||a==='retry'){const produceNew=a==='start'&&startLabel()==='Produce a new version';await beginConversion(v||state.selected,state.mode==='basic'&&!produceNew,state.mode==='basic'&&!produceNew,produceNew);return}
 if(a==='start-all'){await beginConversion(null,true,true);return}
 if(a==='pause'){await pauseConversion();return}
 if(a==='toggle-preview'||a==='preview-control'){await setPreview(!previewEnabled);return}if(a==='retry-preview'){await setPreview(true);return}
 if(a==='play'){if(!previewEnabled||!mediaPath){await setPreview(true);return}const el=$('#video');if(el.paused)await el.play();else el.pause();return}
 if(a==='play-original'){const c=cues()[Number(b.dataset.index??selectedCue)];$('#audition').pause();if(c){if(!previewEnabled||!mediaPath)await setPreview(true);seek(c.start);await $('#video').play()}return}
 if(a==='play-take'){const i=Number(b.dataset.index??selectedCue),engine=b.dataset.engine||(state.mode==='expert'?auditionEngine:null)||state.settings.ttsBackend;const take=takeAt(snapshot.takes||[],i,engine,language);if(take){auditionEngine=engine;playAudio(take.audio);if(state.mode==='expert')renderTranscript();}return}
 if(a==='history-audio'||a==='role-audio'){playAudio(b.dataset.path);return}
 if(a==='stop-audio'){audioToken++;const player=$('#audition');player.pause();player.onloadedmetadata=null;player.ontimeupdate=null;$('#video')?.pause();return}
 if(a==='preview-details'){await previewDetails();return}
 if(a==='play-output'){await setPreview(true,true);await $('#video').play();return}
 if(a==='reveal'){await invoke('studio_reveal',{path:b.dataset.path||row()?.output||state.storage});return}
 if(a==='inspector'){inspector=v;$('#inspector-content').innerHTML=inspectorHTML();$$('[data-action=inspector]').forEach(b=>b.classList.toggle('active',b.dataset.value===v));return}
 if(a==='dialogue-tab'){dialogueTab=v;$('#inspector-content').innerHTML=inspectorHTML();return}
 if(a==='audition-language'){language=v;auditionEngine=null;renderTranscript();updatePlayer();updateAudition();return}
 if(a==='captions'){await showDrawer('Preview captions',`<div class="stack">${[['yue','Hong Kong Cantonese'],['en','English'],['original','Original subtitles'],['none','No captions']].map(([k,l])=>button('caption-choice',l,'subtitles',captionLanguage===k?'active':'',`data-value="${k}"`)).join('')}</div>`);return}
 if(a==='caption-choice'){captionLanguage=v;await closeDrawer();updatePlayer();renderTranscript();return}
 if(['timeline-left','timeline-right','timeline-playhead'].includes(a)){navigateTimeline(a);return;}
 if((a==='seek-timeline'||a==='cue')&&performance.now()<timelineSuppressClickUntil)return;
 if(a==='seek-timeline'){const rect=b.getBoundingClientRect();seek((Number(b.dataset.start)||0)+Math.max(0,e.clientX-rect.left)/zoom);updateAudition();return}
 if(a==='cue'){chooseCue(Number(b.dataset.index));if(b.dataset.engine){auditionEngine=b.dataset.engine;renderTranscript();}return}if(a==='previous'){chooseCue(selectedCue-1);return}if(a==='next'){chooseCue(selectedCue+1);return}
 if(a==='review-edit'||a==='review-retake'){language=b.dataset.language||language;retakeEngine=b.dataset.engine||null;auditionEngine=retakeEngine;page='edit';selectedCue=Math.min(cues().length-1,Number(b.dataset.index));inspector='dialogue';dialogueTab=a==='review-retake'?'record':'listen';render();await loadMedia();return}
 if(a==='review-retake-now'){if(active)return;language=b.dataset.language||language;retakeEngine=b.dataset.engine||state.settings.ttsBackend;selectedCue=Math.min(cues().length-1,Number(b.dataset.index));const segment=cues()[selectedCue];if(segment){const submitted=structuredClone(draft),target=submitted.segments.find(x=>x.id===segment.id);if(target){target.take=crypto.getRandomValues(new Uint32Array(1))[0]&0x7fffffff;target.audioTake=null;delete target.reviewDecisions?.[`${language}:${retakeEngine}`];await renderVersion(segment.id,submitted)}}return}
 if(a==='review-attempt'){const issue=[...(snapshot.issues||[]),...(snapshot.resolvedIssues||[])].find(x=>x.id===b.closest('.issue-card')?.dataset.issueId),source=issue?.attempts?.[Number(b.dataset.attemptIndex)]?.audition;if(source)playAudio(source.path,source.start,source.end);return;}
 if(a==='review-audition'){const issue=[...(snapshot.issues||[]),...(snapshot.resolvedIssues||[])].find(x=>x.id===b.closest('.issue-card')?.dataset.issueId),source=issue?.auditions?.[b.dataset.source];if(source)playAudio(source.path,source.start,source.end);return;}
 if(a==='review-listen'){
  const card=b.closest('.issue-card'),select=card?.querySelector('[data-review-recording]');if(select?.value)playAudio(select.value);return;
 }
 if(a==='review-choice'){
  if(active)return;const card=b.closest('.issue-card'),choice=card.querySelector('[data-review-choice]').value,index=Number(b.dataset.index),engine=b.dataset.engine,lang=b.dataset.language;
  const audio=card.querySelector('[data-review-recording]')?.value;
  await showDrawer('Confirm fallback choice',`<p>${esc(t(choice==='original'?'This line will keep its original source voice. The translated captions are retained.':choice==='recording'?'This recording may contain wrong pronunciation, a different language or missing words. Accepting it is your explicit editorial choice, not an AI quality pass.':'The saved override will be removed.'))}</p><p>${esc(t('Earlier exports and recordings are retained. Export a new version to apply this choice.'))}</p><div class="row">${button('close-drawer','Cancel',null)}${button('confirm-review-choice','Save choice','check','primary',`data-index="${index}" data-engine="${esc(engine)}" data-language="${esc(lang)}" data-choice="${esc(choice)}" data-audio="${esc(audio||'')}"`)}</div>`);return;
 }
 if(a==='confirm-review-choice'){
  if(active)return;b.disabled=true;if(dirty)await save();
  const result=await rpc('review-resolution',{id:state.selected,baseFingerprint:draft.baseFingerprint,index:Number(b.dataset.index),engine:b.dataset.engine,language:b.dataset.language,action:b.dataset.choice,audio:b.dataset.audio,confirmDefect:b.dataset.choice==='recording'});
  draft=result.draft;snapshot=result.snapshot;dirty=false;await closeDrawer();render();toast(t('Fallback choice saved. Export a new version to apply it.'));return;
 }
 if(a==='save'){await save();return}
 if(a==='undo'||a==='redo'){const stack=a==='undo'?undoStack:redoStack,other=a==='undo'?redoStack:undoStack;if(stack.length){other.push(structuredClone(draft));draft=stack.pop();dirty=true;renderTranscript();renderTimeline()}return}
 if(a==='retry-review'){if(active||starting||finishingRun)return;if(dirty){toast(t('Save or export your edits before retrying automatic review.'));return;}const spec=await invoke('studio_start',{op:'retry-review',params:{id:state.selected,mode:'pending'}});runID=spec.id;phaseSample=null;active={id:spec.id,rowID:state.selected,seconds:0};await refreshState();render();return}
 if(a==='retake'){await renderVersion(current()?.id);return}if(a==='export'){await renderVersion();return}
 if(a==='adopt'){const take=takeAt(snapshot.takes||[],selectedCue,auditionEngine||state.settings.ttsBackend,language);if(take&&current()){checkpoint();current().audioTake=take.audio;toast(t('Chosen recording'));}return}
 if(a==='split'){if(!draft)return;checkpoint();const clips=draft.clips.length?draft.clips:[{start:0,end:duration,enabled:true,ripple:true}];for(let i=0;i<clips.length;i++){const c=clips[i];if(c.start+.04<sourceTime&&sourceTime<c.end-.04){clips.splice(i,1,{...c,end:sourceTime},{...c,start:sourceTime});break}}draft.clips=clips;renderTimeline();return}
 if(a==='new-dialogue'){if(!draft)return;checkpoint();const c={id:crypto.randomUUID(),sources:[],manual:true,start:sourceTime,end:Math.min(duration,sourceTime+2),captionStart:sourceTime,captionEnd:Math.min(duration,sourceTime+2),original:'',text:'',english:'',speakerId:'',enabled:true,rate:1,take:42};draft.segments.push(c);draft.segments.sort((a,b)=>a.start-b.start);chooseCue(draft.segments.indexOf(c));return}
 if(a==='toggle-nav'){navVisible=!navVisible;render();return}if(a==='toggle-browser'){browserVisible=!browserVisible;render();return}if(a==='toggle-inspector'){inspectorVisible=!inspectorVisible;render();return}
 if(a==='output-folder'){const paths=await invoke('studio_pick',{kind:'folder'});if(paths[0])await setSettings({exportFolder:paths[0]});return}
 if(a==='plan'){acceptSetupPlan(await rpc('plan'));updateSetup();return}if(a==='inventory'){await refreshModels();return}
 if(a==='bootstrap'){beginInstallation();const r=await invoke('studio_bootstrap');active={id:r.id,setup:true,seconds:0};setupEvent={message:t('Prepare runtime')};updateSetup();return}
 if(a==='clear-cache'){
  if(active||cacheCleaning)return;const session=++cacheSession;
  await showDrawer('Clear temporary files',`<section class="cache-progress" aria-busy="true"><h3 role="status">${esc(t('Scanning application storage…'))}</h3><div class="download-fill indeterminate" role="progressbar" aria-label="${esc(t('Scanning application storage…'))}"><i></i></div><p>${esc(t('Counting temporary files. Nothing is removed during this scan.'))}</p></section>`);
  let p;try{p=await rpc('project-cache-plan');}catch(error){if(session===cacheSession)await showDrawer('Clear temporary files',`<p role="alert">${esc(error.message||String(error))}</p>${button('clear-cache','Scan again','refresh')}`);return;}if(session!==cacheSession)return;cacheReview=p;
  const labels={'ocr-frames':'OCR images','video-preview':'Video previews','package-cache':'Package download cache','compiler-cache':'Compiled cache'};
  await showDrawer('Clear temporary files',`<h3>${esc(t('Estimated space to free'))}: <span id="cache-size">${bytes(p.bytes)}</span></h3><p>${esc(t('Scans the app storage folders directly, including old previews and interrupted work that is no longer in the list.'))}</p><h4>${esc(t('Rebuildable temporary files'))}</h4>${Object.entries(p.groups||{}).map(([k,n])=>`<div class="package-row"><span>${esc(t(labels[k]||k))}</span><small>${bytes(n)}</small></div>`).join('')||`<p>${esc(t('No rebuildable cache found.'))}</p>`}<small>${esc(t('Shared files may free less space. Downloaded models, runtimes, source videos and final movies are kept.'))}</small>
  <div class="rule"></div><h4>${esc(t('Unlinked working data'))} (${(p.orphanWork||[]).length})</h4><p>${esc(t('These folders are not linked to the current queue or saved projects. They may contain recordings from an interrupted conversion. Select only if you no longer need to resume or edit them.'))}</p>
  ${(p.orphanWork||[]).map(x=>`<label class="check cache-work"><input type="checkbox" data-cache-orphan="${esc(x.id)}" ${x.canRemove?'':'disabled'}><span>${esc(x.title||x.id)}<small>${bytes(x.bytes)} · ${esc(t('Recordings and working data'))}</small></span></label>`).join('')}
  ${(p.warnings||[]).length?`<p class="warning">${esc(t('Saved project references could not be checked. Working data is protected; only rebuildable caches can be cleaned.'))}</p>`:''}
  <div class="row"><button data-action="close-drawer">${esc(t('Cancel'))}</button>${button('confirm-clear-cache','Clear selected files','trash','danger',`data-token="${esc(p.token)}"`)}</div>`);updateCacheSelection();return;
 }
 if(a==='confirm-clear-cache'){
  if(active||cacheCleaning)return;
  const token=b.dataset.token,orphanIDs=$$('[data-cache-orphan]:checked').map(x=>x.dataset.cacheOrphan);b.disabled=true;
  previewEnabled=false;previewLoading=false;$('#video')?.pause();$('#video')?.removeAttribute('src');$('#video')?.load();
  await runCacheCleanup(token,orphanIDs);return;
 }
 if(a==='remove-model'){
  if(active)return;
  const p=await rpc('model-removal-plan',{id:v});
  if(!p.canRemove){toast(t(p.reason==='selected-model'?'Select another model before removing this version.':'A waiting or paused job still uses this model.'),true);return;}
  await showDrawer('Remove downloaded model',`<h3>${esc(p.title)}</h3><p>${esc(t('Only this downloaded model is removed. Source videos, projects, exports and runtimes are kept.'))}</p><p>${esc(t('Storage to free'))}: ${bytes(p.bytes)}</p>${p.sharedBytesRetained?`<p>${esc(t('Shared files retained for other models'))}: ${bytes(p.sharedBytesRetained)}</p><small>${esc((p.sharedModels||[]).map(m=>m.title).join(' · '))}</small>`:''}<div class="row">${button('close-drawer','Cancel',null)}${button('confirm-remove-model','Remove','trash','danger',`data-value="${esc(v)}"`)}</div>`);return;
 }
 if(a==='confirm-remove-model'){if(active)return;b.disabled=true;try{const result=await rpc('remove-model',{id:v});await closeDrawer();await refreshModels();acceptSetupPlan(await rpc('plan'));updateSetup();toast(t('Model removed')+' · '+t('Space freed')+': '+bytes(result.freedBytes)+(result.sharedBytesRetained?' · '+t('Shared files retained for other models')+': '+bytes(result.sharedBytesRetained):''));}finally{if(b.isConnected)b.disabled=false;}return;}
 if(a==='remove-retired-model'){if(active)return;await rpc('remove-retired-model',{id:v});await refreshModels();acceptSetupPlan(await rpc('plan'));updateSetup();return}
 if(a==='quality-preset'){if(active)return;plan=presetPlan(plan,b.dataset.value);selectedQuality=b.dataset.value;updateSetup();return}
 if(a==='setup'){if(active||packageCleaning||!plan?.canDeployModels||!termsReady())return;if($('.drawer'))await closeDrawer();beginInstallation();await syncUseTerms();setupSelection=setupParameters(plan);if(!runtimeReady){deployAfterBootstrap=true;const r=await invoke('studio_bootstrap');active={id:r.id,setup:true,seconds:0};setupEvent={message:t('Prepare runtime')};updateSetup();return;}const r=await invoke('studio_start',{op:'setup',params:setupSelection});active={id:r.id,setup:true,seconds:0};setupEvent={message:t('Download missing components')};updateSetup();return}
 if(a==='cleanup-models'||a==='cleanup-all'){await cleanup(a==='cleanup-all'?'all':'models');return}
 if(a==='execute-cleanup'){await executePackageCleanup(b.dataset.mode,b.dataset.token);return}
 if(a==='refresh-setup-plan'){b.disabled=true;try{await refreshAfterPackageCleanup();await closeDrawer()}finally{if(b.isConnected)b.disabled=false}return}
 if(a==='export-logs'){if(exportingLogs)return;exportingLogs=true;b.disabled=true;try{const report=await invoke('studio_export_logs',{language:state.language});if(!report.cancelled)toast(t('Debug report saved')+' · '+filename(report.path));}finally{exportingLogs=false;b.disabled=false;}return}
 if(a==='refresh-logs'){await refreshLogs();return}if(a==='copy-logs'){await navigator.clipboard.writeText(logs);toast(t('Copied'));return}
 if(a==='automatic-subtitles'){await setSettings({subtitleSelection:'automatic'});return}
 if(a==='close-paused'){closing=true;await pauseConversion();return}
 });}
document.addEventListener('click',action);
document.addEventListener('keydown',async e=>{if(e.key==='Escape'&&!switchStarting&&!cacheCleaning&&!packageCleaning){++cacheSession;if(sourceConfirmation){sourceConfirmation(false);sourceConfirmation=null;}++switchSession;++switchRevision;await closeDrawer();}if((e.metaKey||e.ctrlKey)&&e.key==='s'){e.preventDefault();safely(save)}if(e.key==='Enter'&&e.target.matches('.shelf-card'))e.target.click()});
document.addEventListener('input',e=>{if(e.target.id==='role-search'){roleQuery=e.target.value;filterRoles()}if(e.target.id==='seek')seek(Number(e.target.value));if(e.target.id==='zoom'){rememberTimelineViewport();const leftTime=timelineViewport.left/zoom;zoom=Number(e.target.value);renderTimeline();const el=$('.timeline-scroll');if(el)el.scrollLeft=leftTime*zoom;rememberTimelineViewport();updateTimelineNavigation()}if(e.target.id==='timeline-pan'){const el=$('.timeline-scroll');if(el){el.scrollLeft=Number(e.target.value)*zoom;rememberTimelineViewport();updateTimelineNavigation();}}if(e.target.id==='log-search'){logSearch=e.target.value;updateLogs()}if(e.target.id==='license-search')renderLicenses(e.target.value);if(e.target.id==='help-search'){helpQuery=e.target.value;renderHelp()}});
document.addEventListener('change',e=>safely(async()=>{const el=e.target;
 if(el.hasAttribute('data-install-follow')){installationFollow=el.checked;paintInstallation();return;}
 if(el.dataset.cacheOrphan){updateCacheSelection();return;}
 if(el.id==='use-terms-checkbox'){localTermsAccepted=el.checked;if(localTermsAccepted)localStorage.setItem(termsKey,'accepted');else localStorage.removeItem(termsKey);if(!localTermsAccepted){state.useTermsAccepted=false;if(runtimeReady)await rpc('revoke-use-terms');}await syncUseTerms();render();return}
 if(el.id==='welcome-language'||el.id==='preferences-language'){state=await configure({language:el.value,settings:{},preserveProductionSettings:el.id==='preferences-language'});render();if(page==='terminal')await refreshLogs();return}
 if(el.id==='follow'){follow=el.checked;if(follow){$('#audition').pause();if(row()?.sourceTime!=null)seek(row().sourceTime)}return}
 if(el.id==='log-source'){logSource=el.value;await refreshLogs();return}
 if(el.id==='errors-only'){errorsOnly=el.checked;updateLogs();return}
 if(el.id==='remove-old-model'&&pendingSwitch){pendingSwitch.removeOld=el.checked;return}
 if(el.id==='follow-logs'){followLogs=el.checked;return}
 if(el.dataset.setting){const k=el.dataset.setting;if(k==='captionLanguage'){captionLanguage=el.value;updatePlayer();return}if(k==='retakeEngine'){retakeEngine=el.value;return}let value=el.type==='checkbox'?el.checked:el.type==='number'||el.type==='range'?Number(el.value):el.value;
 if(k==='roleAnalysisMode'||k==='visualRoleAnalysisEnabled'){const patch={[k]:value};if(k==='roleAnalysisMode')patch.visualRoleAnalysisEnabled=false;if(value===true||value==='audio')patch.productionMode='standard';await setSettings(patch);return;}
 if(k==='translationSource'){await setSettings({translationSource:value,...(value==='audio-and-subtitles'?{batchAutoSubtitles:true,subtitleSource:'embedded',subtitle:null,ocr:false,ocrRect:null}:{})});return;}
 if(k==='ttsBackend'){await chooseVoiceEngine(value);return;}if(k==='switch-role'){if(!pendingSwitch)return;pendingSwitch.models[el.dataset.role]=value;await reviewSwitch();return;}if(k==='switch-engine'){if(!pendingSwitch)return;pendingSwitch.engine=value;delete pendingSwitch.models.voice;await reviewSwitch();return;}if(k==='dubLanguages'){value=value==='both'?['yue','en']:[value];if(value.includes('en')&&state.settings.ttsBackend==='wsyue'){toast(t('WenetSpeech-Yue supports Cantonese only. Choose another engine for English or bilingual dubbing.'),true);el.value='yue';return;}if(value.includes('en')){await setSettings({dubLanguages:value,selectedEngines:(state.settings.selectedEngines||[state.settings.ttsBackend]).filter(id=>id!=='wsyue')});return;}}if(k==='translateOPED')value=value==='translate';if(k==='limit')value=Number(value);await setSettings({[k]:value});return}
 if(el.dataset.engineTrack){if(engineBlocked(el.dataset.engineTrack)){el.checked=false;toast(t('Cantonese only'),true);return;}const engines=new Set(state.settings.selectedEngines||[state.settings.ttsBackend]);el.checked?engines.add(el.dataset.engineTrack):engines.delete(el.dataset.engineTrack);engines.add(state.settings.ttsBackend);await setSettings({selectedEngines:ENGINES.map(([k])=>k).filter(k=>engines.has(k))});return}
 if(el.dataset.subtitle){const modes=new Set(state.settings.subtitleModes);el.checked?modes.add(el.dataset.subtitle):modes.delete(el.dataset.subtitle);await setSettings({subtitleModes:[...modes],subtitleSelection:'custom'});return}
 if(el.dataset.cueField&&current()){checkpoint();const k=el.dataset.cueField;current()[k]=el.type==='checkbox'?el.checked:el.type==='number'?Number(el.value):el.value;current().audioTake=null;delete current().reviewDecisions;renderTimeline();updatePlayer();return}
 if(el.id==='cue-role'&&current()){checkpoint();current().speakerId=el.value;delete current().audioTake;renderTimeline();return}
 if(el.dataset.roleText&&draft){checkpoint();const role=draft.settings.voiceProfiles.find(r=>r.id===el.dataset.roleText);if(role)role.promptText=el.value;return}
 if(el.dataset.clip!=null&&draft){checkpoint();if(!draft.clips.length)draft.clips=[{start:0,end:duration,enabled:true,ripple:true}];draft.clips[Number(el.dataset.clip)][el.dataset.key]=el.type==='checkbox'?el.checked:Number(el.value);return}
}));
async function onEvent({payload}){const event=payload.event;if(active&&payload.runID!==active.id)return;if(payload.rowID){const r=state.queue.find(r=>r.id===payload.rowID);if(r){r.stage=event.stage;r.message=event.message;if(event.journey){journey=mergeJourney(journey,event.journey,payload.runID);r.journey=journey}if(event.output)r.output=event.output;if(event.deliveryKind){r.deliveryKind=event.deliveryKind;if(event.deliveryKind==='complete'){delete r.previewOutput;delete r.missingDialogue;delete r.incompleteDialogue;}}if(event.previewOutput)r.previewOutput=event.previewOutput;if(event.missingDialogue!=null)r.missingDialogue=event.missingDialogue;if(event.incompleteDialogue!=null)r.incompleteDialogue=event.incompleteDialogue;if(event.job)r.job=event.job;if(event.review)r.review=event.review;if(event.cueIndex!=null){const c=cues()[event.cueIndex];if(c)r.sourceTime=c.start;}if(follow&&$('#audition').paused&&r.sourceTime!=null&&Math.abs(sourceTime-r.sourceTime)>.4)seek(r.sourceTime);}}
 if(event.workTotal>0){const key=`${event.workID}-${event.workTotal}`;if(!phaseSample||phaseSample.key!==key)phaseSample={key,first:event.workCompleted,last:event.workCompleted,total:event.workTotal,started:performance.now()};else phaseSample.last=event.workCompleted;}
 if(installationActive())installationLog.event(event);
 if(installationActive()){const message=event.message||'';if(/^ERROR:/i.test(message)||!setupFailure&&(event.stage==='錯誤'||/error|failed/i.test(event.stage||'')))setupFailure=message;setupEvent=event;if(active?.setup)updateSetup();const el=$('#model-maintenance-status');if(el&&!el.querySelector('.installation-summary'))el.innerHTML=maintenanceHTML();scheduleInstallation();}appendProcessLog(JSON.stringify(event),true);updateProgress();}
async function onFinished({payload}){
 if(finishedRunIDs.has(payload.runID))return;
 finishedRunIDs.add(payload.runID);if(finishedRunIDs.size>100)finishedRunIDs.delete(finishedRunIDs.values().next().value);
 // Native completion may arrive before the launch RPC returns for a short job.
 await startPromise?.catch(()=>{});
 if(active&&payload.runID!==active.id)return;
 finishingRun=true;
 const wasSetup=active?.setup,wasMaintenance=(active?.action||payload.action)==='model-maintenance';
 const conversionFinished=!!payload.rowID&&(active?.action||payload.action)==='batch';
 const failedRow=payload.rowID;
 if((wasSetup||wasMaintenance)&&payload.code&&!payload.paused)setupFailure=setupFailure||setupEvent?.message||t('Setup did not finish');
 if(wasSetup||wasMaintenance)installationLog.append(t(payload.paused?'Download paused':payload.code?'Setup did not finish':'Model files verified'));
 active=null;setupEvent=null;for(const b of $$('#drawer-root [data-action=pause]'))b.disabled=true;
 try{
  runtimeReady=(await invoke('studio_status')).runtimeReady;
  if(runtimeReady){
   await queueOrder.idle();
   if(pendingConfig){state=await rpc('configure',pendingConfig);pendingConfig=null}
   await refreshState();await syncUseTerms();
   if(wasSetup&&!payload.code&&!payload.paused)setupFailure='';
   if(wasSetup&&!payload.code&&!payload.paused)updateDraftSettings(EXPORT_SETTINGS);
   await refreshSnapshot().catch(e=>console.warn(e));
  }
  if(wasSetup&&runtimeReady){await refreshModels();acceptSetupPlan(await rpc('plan').catch(()=>null));if(!payload.code&&!payload.paused&&setupReturn){screen=setupReturn.screen;page=setupReturn.page;setupReturn=null;pendingSwitch=null}}
  if(wasMaintenance&&runtimeReady){logSource='logs/studio/process.log';await refreshModels();toast(t(payload.paused?'Download paused':payload.code?'Model repair failed. See Terminal for details.':'Model files verified'),!!payload.code&&!payload.paused)}
  if(closing){await native.window.getCurrentWindow().close();return}
  render();
  if(deployAfterBootstrap&&!payload.code&&!payload.paused){deployAfterBootstrap=false;const r=await invoke('studio_start',{op:'setup',params:setupSelection||setupParameters(plan)});active={id:r.id,setup:true,seconds:0};updateSetup();return}
  if(payload.code||payload.paused)deployAfterBootstrap=false;
  if(payload.finalizationError){conversionQueue.stop();await rememberQueue(false);toast(t('The task ended, but its queue status could not be saved. Reopen the app to recover saved work. See Terminal for details.'),true);return;}
  if(payload.paused){conversionQueue.stop();await rememberQueue(false)}
  else if(conversionFinished&&conversionQueue.enabled)await advanceQueue();
  if(payload.code&&!payload.paused)toast(wasSetup?t('Setup did not finish'):state.queue.find(r=>r.id===failedRow)?.lastError?.message||`Task exited (${payload.code}). See Terminal.`,true);
 }catch(e){conversionQueue.stop();await rememberQueue(false).catch(()=>{});throw e}
 finally{finishingRun=false;render()}
}
async function poll(){if(pollBusy)return;pollBusy=true;try{const status=await invoke('studio_status');runtimeReady=status.runtimeReady;if(status.running&&!finishedRunIDs.has(status.running.id))active={...active,...status.running};if(runtimeReady&&screen==='studio'&&row()){await refreshState();await refreshSnapshot();if(page==='terminal'){await refreshLogs()}}updateProgress();paintInstallation();}catch(e){console.warn(e)}finally{pollBusy=false}}
function startupProgress(message){startupMessage=message;const label=$('.welcome-startup-copy small'),bar=$('.welcome-startup [role=progressbar]');if(label)label.textContent=t(message);if(bar)bar.setAttribute('aria-label',t(message));}
async function boot(){
 render();
 if(!native){initializing=false;render();return;}
 // Give Welcome and its assistant a frame before starting local services.
 await new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)));
 await native.event.listen('studio-event',event=>safely(()=>onEvent(event)));
 await native.event.listen('studio-cleanup-progress',onPackageProgress);
 await native.event.listen('studio-cleanup-close-requested',()=>toast(t('Please keep the app open until cleanup finishes.')));
 await native.event.listen('studio-log',({payload})=>{appendProcessLog(payload)});
 await native.event.listen('studio-finished',event=>{finishChain=finishChain.then(()=>safely(()=>onFinished(event)));return finishChain});
 await native.event.listen('studio-close-requested',()=>showDrawer('Pause & save',`<p>${esc(t('A task is running. Pause and save before closing?'))}</p><div class="row">${button('close-drawer','Cancel',null)}${button('close-paused','Pause and close','pause','primary')}</div>`));
 await native.event.listen('tauri://drag-drop',({payload})=>safely(async()=>{if(payload.paths?.length){state=await rpc('add',{paths:payload.paths});await selectRow(state.selected)}}));
 startupProgress('Checking your computer…');
 const status=await invoke('studio_status');
 runtimeReady=status.runtimeReady;
 if(status.running)active=status.running;
 if(runtimeReady){
  startupProgress('Loading your projects…');
  state=await rpc('state');
  if(state.ui?.interfaceLanguageInitialized===false)state=await configure({language:firstLanguage,settings:{},preserveProductionSettings:true});
  else localStorage.setItem('anicanto-language',state.language);
  await syncUseTerms().catch(e=>toast(e.message||e,true));
  if(active?.action==='batch'&&(state.ui.autoQueue||state.mode==='basic'))conversionQueue.restore(active.rowID,{includeAttention:state.ui.autoQueueAttention===true});
  const stored=state.settings.animeTheme;
  if(!welcomeThemeTouched){if(state.settings.randomAnimeTheme===true){const keys=Object.keys(THEMES);themeKey=keys[Math.floor(Math.random()*keys.length)];}else if(stored in THEMES)themeKey=stored;}
  localStorage.setItem('anicanto-theme',themeKey);
  await rpc('configure',{settings:{themeSession:themeKey,...(welcomeThemeTouched?{animeTheme:themeKey}:{})}});
  startupProgress('Preparing your projects…');
  await refreshSnapshot().catch(e=>console.warn(e));
  while(pendingStartupMode){const mode=pendingStartupMode;pendingStartupMode=null;state=await rpc('configure',{mode,settings:{}});if(pendingStartupMode)state.mode=pendingStartupMode;}
 }else{
  await configure({language:firstLanguage,settings:{},preserveProductionSettings:true});
 }
 initializing=false;
 render();
 setInterval(poll,2500);
 if(runtimeReady){await Promise.allSettled([refreshModels(),rpc('plan').then(p=>{acceptSetupPlan(p);updateSetup()})]);}
 else{acceptSetupPlan(await rpc('plan').catch(()=>null));updateSetup();}
}
safely(boot);
