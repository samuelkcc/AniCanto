import {controlCopy} from './workflow-guide.js';
import {languageTitle} from './model.js';
import {esc,tc,scriptField} from './model.js';

const kinds={'subtitle-continuation':'Subtitle allocation review','generation-input':'Generation input error','source-clock-target-missing':'Target voice skipped for uncertain timing','subtitle-allocation-unconfirmed':'Subtitle alignment needs checking','source-primary-fallback':'Auxiliary source used','failed-voice-choice':'Saved voice fallback','source-clock-unconfirmed':'Source speech timing needs checking','first-audible-take-retained':'First audible take retained','name-term-mismatch':'Locked name or technique needs checking','name-language-unconfirmed':'Name pronunciation needs checking','timing-overrun':'Recording too long','missing-script':'Translation missing','missing-audio':'Voice missing','fast-generation-failed':'Voice generation failed','tts-generation':'Voice generation failed','reference':'Reference voice problem','reference-blocked':'Reference voice problem','normal-unresolved':'Language or completeness needs checking','targeted-language-or-integrity':'Language or completeness needs checking','verification-unresolved':'Language or completeness needs checking','automatic-recovery':'Automatic recovery','target-reference-recovery':'Target-language voice fallback','preview-original-fallback':'Original source voice used'};
const methods={'trim-padding':'Remove silent edges','adapt-source':'Shorten while preserving meaning','retry-clauses':'Regenerate complete dialogue','condition-reference':'Condition the source reference','retain':'Keep the best available take','target-language-reference':'Try a target-language voice reference','initial-voice-attempt':'First generated recording','alternate-engine':'Try another installed voice model','retained-rejected-recording':'Retained rejected recording'};
const outcomes={'adopted':'Adopted','adopted-after-interruption':'Recovered saved recording','selected-unverified':'Selected; verification pending','timing-not-fit':'Recording too long','not-verified':'Not verified','generation-failed':'Generation failed','meaning-not-verified':'Meaning not verified','reserved':'Queued','generating':'Generating','generated':'Awaiting verification','not-applicable':'Not applicable'};
const key=(index,language,engine)=>`${index}:${language}:${engine}`;
const time=n=>Number.isFinite(Number(n))?`${Number(n).toFixed(2)} s`:'';
const audible=x=>typeof x==='string'&&x.length>0;

// The review report edits the saved words for one track, then regenerates that line.
const captionKey=language=>language==='en'?'english':language==='zh'?'mandarin':'cantonese';

function wordsEditor({cue,segment,index,language,active,t}){
 const value=segment?.[scriptField(language)]??cue?.[captionKey(language)]??'';
 return `<label class="review-words-field">${esc(t('Dubbing words for this line'))}<textarea data-review-words="${index-1}" rows="2" ${active||!segment?'disabled':''}>${esc(value)}</textarea></label>`;
}

function enginePicker(options,engine,index,active,t){
 if(!Array.isArray(options)||options.length<2)return '';
 return `<label class="review-engine-field">${esc(t('Voice engine for a new recording'))}<select data-review-engine="${index-1}">${options.map(([id,label])=>`<option value="${esc(id)}" ${id===engine?'selected':''}>${esc(label)}</option>`).join('')}</select></label>`;
}

function candidates(snapshot,line,language,engine,issue,removed=new Set()){
 const attempts=[...(issue?.attempts||[])],history=(snapshot.history||[]).filter(x=>x.index===line&&x.language===language),takes=(snapshot.takes||[]).filter(x=>x.index===line&&x.language===language),catalog=(snapshot.recordingCandidates||[]).filter(x=>x.index===line&&x.language===language);
 const references=snapshot.voiceReferences||{};
 const published=takes.filter(x=>x.versionStatus==='complete'&&x.versionOutput===snapshot.currentOutput);
 const current=(published.length?published:takes.filter(x=>!x.versionOutput)).find(x=>x.engine===engine),found=new Map();
 function add(path,sourceEngine,kind,when=0,reason=''){
  if(!audible(path)||removed.has(path))return;
  const previous=found.get(path);
  if(previous){if(kind==='current')previous.current=true;return;}
  // A retake reuses the first-voice action, so only the earliest take keeps the
  // "first generated recording" label. Later takes read as generated recordings.
  if(kind==='first'&&[...found.values()].some(x=>x.kind==='first'))kind='attempt';
 found.set(path,{path,engine:sourceEngine||engine,kind,when:Number(when)||0,reason,current:kind==='current',reference:references[path]?.state||''});
 }
 attempts.forEach((x,n)=>add(x.audition?.path,x.engine||engine,x.action==='initial-voice-attempt'?'first':'attempt',x.recordedAt||n,x.reason||x.status||''));
 add(issue?.auditions?.generated?.path,engine,'generated');
 add(issue?.auditions?.lastFailed?.path,engine,'rejected',0,issue?.diagnostic?.lastFailedHeard||'');
 history.forEach(x=>add(x.path,x.engine,'rejected',x.created,x.reason));
 catalog.forEach(x=>add(x.path,x.engine,x.kind||'generated',x.created,x.reason));
 takes.forEach(x=>add(x.audio,x.engine,x.audio===current?.audio?'current':'generated',x.created,x.reason));
 // The first generated recording stays first; later takes follow in creation order.
 const rank=x=>x.kind==='first'?0:1;
 const items=[...found.values()].sort((a,b)=>rank(a)-rank(b)||a.when-b.when);
 return {items,current:current?.audio||null,failures:attempts.filter(x=>!x.audition?.path&&['generation-failed','not-verified','timing-not-fit','meaning-not-verified'].includes(x.status)).length};
}

function diagnostic(issue,t,button){
 const d=issue?.diagnostic;if(!d)return '';
 const fields=[['Source dialogue',d.sourceText],['Translated script',d.translatedText],['Heard in selected recording',d.heard],['Heard in last failed recording',d.lastFailedHeard]];
 const measures=[['Original speech length',d.sourceSeconds],['Voice reference length',d.referenceSeconds],['Generated recording length',d.recordingSeconds],['Available speaking time',d.availableSeconds],['Excess duration',d.overrunSeconds]];
 return `<details class="review-diagnostics"><summary>${esc(t('Why this line was flagged'))}</summary><div class="issue-diagnostic">${d.voiceSource==='target-language-fallback'?`<p class="warning">${esc(t('This recording uses a bundled Cantonese / English voice, not the original character voice. Language repair does not confirm voice similarity.'))}</p>`:''}${fields.map(([label,value])=>`<div><small>${esc(t(label))}</small><p>${esc(value||t('Not available yet'))}</p></div>`).join('')}<dl class="issue-measurements">${measures.map(([label,value])=>`<div><dt>${esc(t(label))}</dt><dd>${value==null?esc(t('Not measured yet')):time(value)}</dd></div>`).join('')}</dl>${d.generationBudget?.length?`<p>${esc(t('Exact-input generation attempts'))}: ${d.generationBudget.map(x=>`${x.attempts}/${x.maximumAttempts}${x.permanent?' · '+esc(t('Change script or reference before retrying')):''}`).join(' · ')}</p>`:''}${issue.attempts?.length?`<ol class="repair-attempts">${issue.attempts.map((a,n)=>`<li><strong>${esc(t(methods[a.action]||'Automatic recovery'))}</strong> · ${esc(t(outcomes[a.status]||a.status||'Pending'))}${a.check?.heard?`<p>${esc(t('Heard in this attempt'))}: ${esc(a.check.heard)}</p>`:''}${a.reason?`<small>${esc(a.reason)}</small>`:''}${a.audition?button('review-attempt','Listen to take','play','',`data-attempt-index="${n}"`):''}</li>`).join('')}</ol>`:''}</div></details>`;
}

function lineCard(snapshot,cue,index,language,engine,issue,options){
 const {t,button,engineName,active,sourceLanguage}=options;
 const attrs=`data-index="${index-1}" data-engine="${esc(engine)}" data-language="${esc(language)}"`;
 const sourceStart=Number(cue.speechStart??cue.start??0),sourceEnd=Number(cue.speechEnd??cue.end??sourceStart);
 const sources=snapshot.reviewSources||{},auditions=issue?.auditions||{};
 const source=(kind)=>auditions[kind]||(sources[kind]?{path:sources[kind],start:sourceStart,end:sourceEnd}:null);
 const removed=new Set((snapshot.removedTakes||[]).map(x=>x.path));const {items,current:storedCurrent,failures}=candidates(snapshot,index,language,engine,issue,removed);
 const record=(snapshot.reportRows||[]).find(x=>x.index===index&&x.language===language&&x.engine===engine),current=record?record.selectedAudio:storedCurrent;
 const segment=(snapshot.draft?.segments||[]).find(x=>x.sources?.length===1&&x.sources[0]===index-1);
  // The server publishes the in-use list, so the report and the removal guard
  // compare the same normalised paths. An older snapshot falls back locally.
  const kept=new Set((snapshot.protectedTakes||[]).map(x=>x.path).filter(audible));
  if(!kept.size)for(const path of [...(snapshot.reportRows||[]).filter(x=>x.index===index&&x.language===language).flatMap(x=>[x.selectedAudio,x.audio]),segment?.audioTake,...Object.values(segment?.reviewDecisions||{}).map(x=>x?.audio),...(snapshot.takes||[]).filter(x=>x.versionStatus==='complete'&&x.index===index&&x.language===language).map(x=>x.audio)].filter(audible))kept.add(path);
 const choice=segment?.reviewDecisions?.[`${language}:${engine}`];
 const choiceApplied=Boolean(snapshot.reviewState?.userChoicesApplied),pendingChoice=choice&&!choiceApplied;
 const selected=choiceApplied&&choice?.action==='original'?null:choiceApplied&&choice?.action==='recording'?choice.audio:current;
 const sourceFallback=issue?.evidence?.some(x=>x.originalFallback);
 const identity=issue?.id||`line-${index}-${language}-${engine}`;
  // The server projects one human review state per dialogue line, flagged or not.
  const triageState=record?.triage||issue?.triage||'pending';
  const triageFingerprint=record?.triageFingerprint||issue?.triageFingerprint||'';
  const triageMark=value=>button('review-triage',value==='checked'?'Checked by me':value==='deferred'?'Review later':'Reopen review',value==='checked'?'check':value==='deferred'?'next':'refresh','',`data-value="${value}" data-fingerprint="${esc(triageFingerprint)}" ${active?'disabled':''}`);
 const clip=(kind,label)=>{const file=source(kind);return `<div class="review-source"><span>${esc(t(label))}</span>${button('review-audition','Listen','play','',`${attrs} data-source="${kind}" ${file?'':'disabled'}`)}</div>`};
 const name=x=>x.kind==='first'?'First generated recording':x.kind==='rejected'?'Retained failed recording':'Generated recording';
 // One state mark per recording. The name says what the take is; the mark says whether the
 // current export uses it, or the user saved it and a new export has not applied it yet.
 // A saved choice wins over the older export take, so one line never carries two marks.
 // An applied "use original voice" override means no take is in the export, so the export
 // note has to name the original voice instead of falling back to the older take.
 const usedPath=choiceApplied&&choice?(choice.action==='recording'?choice.audio:null):current;
 const stateOf=x=>x.path===usedPath?'Used in current export':pendingChoice&&x.path===choice?.audio?'Your selected recording':'';
 const removeButton=x=>kept.has(x.path)?button('review-remove-take','Remove this recording','trash','',`disabled data-path="${esc(x.path)}"`):button('review-remove-take','Remove this recording','trash','',`data-path="${esc(x.path)}" data-index="${index-1}" data-language="${esc(language)}" data-engine="${esc(x.engine)}" ${active?'disabled':''}`);
  // The engine records the separated voice behind every take, so a retake that
  // used another reference reads differently from a take that used the same one.
  const referenceNote=x=>x.reference==='different'?`<small class="warning">${esc(t('Used a different separated voice than the first recording of this line.'))}</small>`:'';
 const statePill=x=>{const state=stateOf(x);return state?` <span class="pill review-take-state">${esc(t(state))}</span>`:''};
 const recordingList=items.length?`<div class="review-take-list">${items.map((x,n)=>`<div class="review-take-row"><span class="review-take-index">${n+1}</span><span class="grow"><strong>${esc(t(name(x)))}</strong> · ${esc(engineName(x.engine))}${statePill(x)}${x.reason?`<small>${esc(t(x.reason))}</small>`:''}${referenceNote(x)}</span>${button('review-listen-candidate','Listen','play','',`data-path="${esc(x.path)}"`)}${removeButton(x)}</div>`).join('')}</div>`:`<p class="muted">${esc(t('No TTS recording was retained for this line.'))}</p>`;
 const sourceVoiceLabel=sourceLanguage==='ja'?'Original Japanese voice':sourceLanguage==='en'?'Original English voice':'Original source voice';
 const selectedLabel=choiceApplied&&choice?.action==='original'?t(sourceVoiceLabel):choiceApplied&&choice?.action==='recording'?t('Your selected recording'):selected?t('Used in current export'):sourceFallback?t('Original source voice used'):t('No dubbed recording selected');
 // The list already marks the recording the export uses. This line only appears when that
 // audio is not one of the listed recordings, so no take ever reads in two places.
 // An export take outside the list still has to be listenable, so this line carries its own
 // Listen control. The original-voice control only appears when no take is in use.
 const usedListen=usedPath?button('review-listen-candidate','Listen','play','',`data-path="${esc(usedPath)}"`):choiceApplied&&choice?.action==='original'||sourceFallback?button('review-audition','Listen','play','',`${attrs} data-source="original"`):'';
 const usedNote=usedPath&&items.some(x=>x.path===usedPath)?'':`<p class="review-used-note">${esc(t('Voice used in the current export'))} · ${esc(selectedLabel)}${usedListen}</p>`;
 return `<article class="card issue-card review-line" data-issue-id="${esc(identity)}" data-review-key="${esc(key(index,language,engine))}"><div class="issue-body"><div class="row wrap"><h4>${esc(t('Line'))} ${index} · ${esc(t(languageTitle(language)))}</h4><span class="pill">${esc(t(issue?.status==='repaired'?'Repaired':issue?kinds[issue.kind]||'Review note':'No reported issue'))}</span></div>${issue?.repairEligible===false?`<p class="muted">${esc(t('Optional listening note; not included in automatic delivery repair.'))}</p>`:''}<small>${tc(sourceStart)}–${tc(sourceEnd)} · ${esc(engineName(engine))}</small>${wordsEditor({cue,segment,index,language,active,t})}
 <div class="review-sound-step"><strong>1 · ${esc(t(sourceVoiceLabel))}</strong>${clip('original','Original mix')}</div>
 <div class="review-sound-step"><strong>2 · ${esc(t('Separated source voice'))}</strong>${clip('separated','Separated voice')}</div>
 <div class="review-sound-step"><strong>3 · ${esc(t('TTS recordings and failed attempts'))}</strong>${recordingList}${usedNote}${failures?`<small>${failures} ${esc(t('attempts have no playable audio file'))}</small>`:''}${pendingChoice?`<small>${esc(t('Saved choice pending a new video export.'))}</small>`:''}</div>
 ${triageFingerprint?`<div class="review-triage row wrap"><span class="pill">${esc(t(triageState==='checked'?'Checked by you':triageState==='deferred'?'Review later':'Not reviewed yet'))}</span>${triageMark('checked')}${triageMark('deferred')}${triageState!=='pending'?triageMark('pending'):''}</div><small>${esc(t('Your review status is not an automatic quality pass and does not change the exported audio.'))}</small>`:''}
 ${diagnostic(issue,t,button)}${issue?.evidence?.length?`<details><summary>${esc(t('Original diagnostic evidence'))}</summary><pre>${esc(JSON.stringify(issue.evidence,null,2))}</pre></details>`:''}</div>
 <div class="issue-actions">${enginePicker(options.engineOptions||[],engine,index,active,t)}${button('review-save-words','Save words','save','',`${attrs} ${active||!segment?'disabled':''}`)}${button('review-retake-now','Generate a new take for this line','refresh','',`${attrs} ${active||!segment?'disabled':''}`)}${items.length?`<label>${esc(t('Choose a saved TTS recording'))}<select data-review-recording="${index-1}" ${active||!segment?'disabled':''}>${items.map((x,n)=>`<option value="${esc(x.path)}" ${choice?.action==='recording'&&choice.audio===x.path?'selected':''}>${n+1}. ${esc(t(name(x)))} · ${esc(engineName(x.engine))}</option>`).join('')}</select></label>${button('review-choice','Use selected recording','check','',`${attrs} data-choice="recording" ${active||!segment?'disabled':''}`)}`:''}${source('original')?button('review-choice','Use original voice for this line','check','',`${attrs} data-choice="original" ${active||!segment?'disabled':''}`):''}${choice?button('review-choice','Remove my override','close','',`${attrs} data-choice="automatic" ${active?'disabled':''}`):''}</div></article>`;
}

export function reviewPage({snapshot,t,button,engineName,active,sourceLanguage,language='en',retryReviewStarting=false,retryReviewError='',filter='reportMissing',search='',listPage=0,engineOptions=[]}){
 const state=snapshot.reviewState||{},issues=Array.isArray(snapshot.issues)?snapshot.issues:[],resolved=snapshot.resolvedIssues||[],review=snapshot.review||{},cues=review.cues||[];
 const config=review.config||{},engines=config.selectedEngines||[config.ttsBackend||'drama3'],languages=config.dubLanguages||[config.targetLanguage||'yue'];
 const issueMap=new Map([...resolved,...issues].map(x=>[key(x.index,x.language||'yue',x.engine||''),x]));
 const choices=(snapshot.draft?.segments||[]).some(x=>Object.keys(x.reviewDecisions||{}).length);
 const label=id=>controlCopy(id,language,'title');const counts=state.reportCounts||{};
 const lineTriage=snapshot.reviewTriage||{};
 // One short summary and one category filter sit on top. Everything below is one card per dialogue line.
 let html=`<div class="review-summary card"><div class="row spread wrap"><div><h3>${esc(t('Review report'))}</h3><p>${esc(t(snapshot.currentOutput?'The finished video is in the output folder. Review and replace individual voices here when needed.':'No video has been exported yet. Review available evidence here; resume processing from the queue.'))}</p></div><div class="row wrap">${button('review-export','Apply choices and export new video','export','primary',active||!choices||state.userChoicesApplied?'disabled':'')}</div></div><div class="row wrap"><span class="pill">${counts.reportMissing??state.repairEligible??0} ${esc(label('reportMissing'))}</span><span class="pill">${counts.reportAdvisory??state.advisory??0} ${esc(label('reportAdvisory'))}</span><span class="pill">${counts.reportAvailable??0} ${esc(label('reportAvailable'))}</span>${state.workflowNotices?`<span class="pill warning">${state.workflowNotices} ${esc(t('Workflow notices'))}</span>`:''}<span class="pill">${state.repaired||0} ${esc(t('Repaired'))}</span><span class="pill">${state.userChoices||0} ${esc(t('User choices'))}</span>${lineTriage.total?`<span class="pill">${lineTriage.checked||0} ${esc(label('reviewChecked'))}</span><span class="pill warning">${(lineTriage.pending||0)+(lineTriage.deferred||0)} ${esc(label('reviewPending'))}</span>`:''}${issues.some(x=>(!x.reportGroup||x.reportGroup==='reportMissing')&&x.repairEligible!==false&&x.triage!=='checked'&&x.triage!=='deferred'&&x.status!=='user-choice-saved')&&!active?button('retry-review',retryReviewStarting?'Starting AI repair…':'Repair delivery issues','refresh','',retryReviewStarting?'disabled':''):''}</div>${active?`<small>${esc(t('Pause and save before changing a review choice.'))}</small>`:''}${retryReviewError?`<p class="warning" role="alert">${esc(retryReviewError)}</p>`:''}</div>`;
 const all=[];for(let i=1;i<=cues.length;i++)for(const track of languages)for(const engine of engines){const issue=issueMap.get(key(i,track,engine));const record=(snapshot.reportRows||[]).find(x=>x.index===i&&x.language===track&&x.engine===engine);all.push({cue:cues[i-1],index:i,language:track,engine,issue,...record,reportGroup:record?.reportGroup||issue?.reportGroup||(issue?(issue.repairEligible===false?'reportAdvisory':'reportMissing'):'reportAvailable')});}
 const query=(search||'').trim().toLowerCase();
 const matched=(x)=>!query||String(x.index)===query||[x.cue?.cantonese,x.cue?.mandarin,x.cue?.english,x.cue?.japanese,x.cue?.text,x.cue?.captionText].some(v=>typeof v==='string'&&v.toLowerCase().includes(query));
 // The last two tabs follow the user's own listening state, not the AI category.
 const triageOf=(x)=>x.triage||x.issue?.triage||'pending';
 const visible=all.filter(x=>filter==='reviewChecked'?triageOf(x)==='checked':filter==='reviewPending'?triageOf(x)!=='checked':filter==='all'||x.reportGroup===filter).filter(matched);
 const totalPages=Math.max(1,Math.ceil(visible.length/25)),page=Math.min(Math.max(0,listPage),totalPages-1),slice=visible.slice(page*25,(page+1)*25);
 html+=`<div class="review-list-tools row spread wrap"><div class="row">${['reportMissing','reportAdvisory','reportAvailable','all','reviewChecked','reviewPending'].map(value=>button('review-filter',value==='all'?t('All dialogue'):label(value),null,filter===value?'active':'',`data-value="${value}"`)).join('')}</div><label class="review-search">${esc(controlCopy('reportSearch',language,'title'))}<input id="review-search" type="search" value="${esc(search)}" placeholder="${esc(t('Line number or dialogue words'))}" autocomplete="off" spellcheck="false"></label><small>${esc(t('Showing'))} ${visible.length?`${page*25+1}–${Math.min((page+1)*25,visible.length)}`:'0'} / ${visible.length}</small></div>`;
 if(!slice.length)html+=`<div class="empty">${esc(t(query?'No dialogue matches this search':filter==='reportMissing'?'No dialogue needs dubbing':filter==='reportAdvisory'?'No review notes here':'No dialogue in this category'))}<p>${esc(t('Open All dialogue to listen to every saved recording.'))}</p></div>`;
 html+=slice.map(x=>`<div class="review-result" data-report-group="${esc(x.reportGroup)}"><span class="pill">${esc(x.captionCovered?t('Subtitle voiced by neighbouring turn'):x.captionOnly?t('Caption only · no dialogue'):x.reportGroup==='checking'?t('Checking recordings'):label(x.reportGroup))}</span>${x.repaired?`<span class="pill">${esc(t('Repaired'))}</span>`:''}${lineCard(snapshot,x.cue,x.index,x.language,x.engine,x.issue,{t,button,engineName,active,sourceLanguage,engineOptions})}</div>`).join('');
 if(totalPages>1)html+=`<div class="row spread review-pages">${button('review-page','Previous','back','',`data-value="${page-1}" ${page?'':'disabled'}`)}<small>${page+1} / ${totalPages}</small>${button('review-page','Next','next','',`data-value="${page+1}" ${page+1<totalPages?'disabled':''}`)}</div>`;
 return `<div class="review-report">${html}</div>`;
}
