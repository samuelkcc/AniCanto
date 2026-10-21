import {esc,tc} from './model.js';

const kinds={'first-audible-take-retained':'First audible take retained','name-language-unconfirmed':'Name pronunciation needs checking','timing-overrun':'Recording too long','missing-script':'Translation missing','missing-audio':'Voice missing','fast-generation-failed':'Voice generation failed','tts-generation':'Voice generation failed','reference':'Reference voice problem','reference-blocked':'Reference voice problem','normal-unresolved':'Language or completeness needs checking','targeted-language-or-integrity':'Language or completeness needs checking','verification-unresolved':'Language or completeness needs checking','automatic-recovery':'Automatic recovery','target-reference-recovery':'Target-language voice fallback','preview-original-fallback':'Original source voice used'};
const methods={'trim-padding':'Remove silent edges','adapt-source':'Shorten while preserving meaning','retry-clauses':'Regenerate complete dialogue','condition-reference':'Condition the source reference','retain':'Keep the best available take','target-language-reference':'Try a target-language voice reference','initial-voice-attempt':'First generated recording','alternate-engine':'Try another installed voice model','retained-rejected-recording':'Retained rejected recording'};
const outcomes={'adopted':'Adopted','adopted-after-interruption':'Recovered saved recording','selected-unverified':'Selected; verification pending','timing-not-fit':'Recording too long','not-verified':'Not verified','generation-failed':'Generation failed','meaning-not-verified':'Meaning not verified','reserved':'Queued','generating':'Generating','generated':'Awaiting verification','not-applicable':'Not applicable'};
const key=(index,language,engine)=>`${index}:${language}:${engine}`;
const time=n=>Number.isFinite(Number(n))?`${Number(n).toFixed(2)} s`:'';
const audible=x=>typeof x==='string'&&x.length>0;

function candidates(snapshot,line,language,engine,issue){
 const attempts=[...(issue?.attempts||[])],history=(snapshot.history||[]).filter(x=>x.index===line&&x.language===language),takes=(snapshot.takes||[]).filter(x=>x.index===line&&x.language===language);
 const published=takes.filter(x=>x.versionStatus==='complete'&&x.versionOutput===snapshot.currentOutput);
 const current=(published.length?published:takes.filter(x=>!x.versionOutput)).find(x=>x.engine===engine),found=new Map();
 function add(path,sourceEngine,kind,when=0,reason=''){
  if(!audible(path))return;
  const previous=found.get(path);
  if(previous){if(kind==='current')previous.current=true;return;}
  found.set(path,{path,engine:sourceEngine||engine,kind,when:Number(when)||0,reason,current:kind==='current'});
 }
 attempts.forEach((x,n)=>add(x.audition?.path,x.engine||engine,x.action==='initial-voice-attempt'?'first':'attempt',x.recordedAt||n,x.reason||x.status||''));
 add(issue?.auditions?.generated?.path,engine,'generated');
 add(issue?.auditions?.lastFailed?.path,engine,'rejected',0,issue?.diagnostic?.lastFailedHeard||'');
 history.forEach(x=>add(x.path,x.engine,'rejected',x.created,x.reason));
 takes.forEach(x=>add(x.audio,x.engine,x.audio===current?.audio?'current':'generated',x.created,x.reason));
 const items=[...found.values()].sort((a,b)=>(a.kind==='first'?-1:b.kind==='first'?1:a.when-b.when));
 return {items,current:current?.audio||null,failures:attempts.filter(x=>!x.audition?.path&&['generation-failed','not-verified','timing-not-fit','meaning-not-verified'].includes(x.status)).length};
}

function diagnostic(issue,t,button){
 const d=issue?.diagnostic;if(!d)return '';
 const fields=[['Source dialogue',d.sourceText],['Translated script',d.translatedText],['Heard in selected recording',d.heard],['Heard in last failed recording',d.lastFailedHeard]];
 const measures=[['Original speech length',d.sourceSeconds],['Voice reference length',d.referenceSeconds],['Generated recording length',d.recordingSeconds],['Available speaking time',d.availableSeconds],['Excess duration',d.overrunSeconds]];
 return `<details class="review-diagnostics"><summary>${esc(t('Why this line was flagged'))}</summary><div class="issue-diagnostic">${d.voiceSource==='target-language-fallback'?`<p class="warning">${esc(t('This recording uses a bundled Cantonese / English voice, not the original character voice. Language repair does not confirm voice similarity.'))}</p>`:''}${fields.map(([label,value])=>`<div><small>${esc(t(label))}</small><p>${esc(value||t('Not available yet'))}</p></div>`).join('')}<dl class="issue-measurements">${measures.map(([label,value])=>`<div><dt>${esc(t(label))}</dt><dd>${value==null?esc(t('Not measured yet')):time(value)}</dd></div>`).join('')}</dl>${issue.attempts?.length?`<ol class="repair-attempts">${issue.attempts.map((a,n)=>`<li><strong>${esc(t(methods[a.action]||'Automatic recovery'))}</strong> · ${esc(t(outcomes[a.status]||a.status||'Pending'))}${a.check?.heard?`<p>${esc(t('Heard in this attempt'))}: ${esc(a.check.heard)}</p>`:''}${a.reason?`<small>${esc(a.reason)}</small>`:''}${a.audition?button('review-attempt','Listen to take','play','',`data-attempt-index="${n}"`):''}</li>`).join('')}</ol>`:''}</div></details>`;
}

function lineCard(snapshot,cue,index,language,engine,issue,{t,button,engineName,active,sourceLanguage}){
 const attrs=`data-index="${index-1}" data-engine="${esc(engine)}" data-language="${esc(language)}"`;
 const sourceStart=Number(cue.speechStart??cue.start??0),sourceEnd=Number(cue.speechEnd??cue.end??sourceStart);
 const sources=snapshot.reviewSources||{},auditions=issue?.auditions||{};
 const source=(kind)=>auditions[kind]||(sources[kind]?{path:sources[kind],start:sourceStart,end:sourceEnd}:null);
 const {items,current,failures}=candidates(snapshot,index,language,engine,issue);
 const segment=(snapshot.draft?.segments||[]).find(x=>x.sources?.length===1&&x.sources[0]===index-1);
 const choice=segment?.reviewDecisions?.[`${language}:${engine}`];
 const choiceApplied=Boolean(snapshot.reviewState?.userChoicesApplied),pendingChoice=choice&&!choiceApplied;
 const selected=choiceApplied&&choice?.action==='original'?null:choiceApplied&&choice?.action==='recording'?choice.audio:current;
 const sourceFallback=issue?.evidence?.some(x=>x.originalFallback);
 const identity=issue?.id||`line-${index}-${language}-${engine}`;
 const clip=(kind,label)=>{const file=source(kind);return `<div class="review-source"><span>${esc(t(label))}</span>${button('review-audition','Listen','play','',`${attrs} data-source="${kind}" ${file?'':'disabled'}`)}</div>`};
 const name=x=>x.kind==='first'?'First generated recording':x.current?'Used in current export':x.kind==='rejected'?'Retained failed recording':'Generated recording';
 const recordingList=items.length?`<div class="review-take-list">${items.map((x,n)=>`<div class="review-take-row"><span class="review-take-index">${n+1}</span><span class="grow"><strong>${esc(t(name(x)))}</strong> · ${esc(engineName(x.engine))}${x.reason?`<small>${esc(t(x.reason))}</small>`:''}</span>${button('review-listen-candidate','Listen','play','',`data-path="${esc(x.path)}"`)}</div>`).join('')}</div>`:`<p class="muted">${esc(t('No TTS recording was retained for this line.'))}</p>`;
 const selectedLabel=choiceApplied&&choice?.action==='original'?t(sourceLanguage==='ja'?'Original Japanese voice':'Original source voice'):choiceApplied&&choice?.action==='recording'?t('Your selected recording'):selected?t('Used in current export'):sourceFallback?t('Original source voice used'):t('No dubbed recording selected');
 return `<article class="card issue-card review-line" data-issue-id="${esc(identity)}" data-review-key="${esc(key(index,language,engine))}"><div class="issue-body"><div class="row wrap"><h4>${esc(t('Line'))} ${index} · ${esc(t(language==='en'?'English':'Hong Kong Cantonese'))}</h4><span class="pill">${esc(t(issue?kinds[issue.kind]||'Review note':'No reported issue'))}</span></div><small>${tc(sourceStart)}–${tc(sourceEnd)} · ${esc(engineName(engine))}</small><p>${esc(cue[language==='en'?'english':'cantonese']||issue?.text||'')}</p>
 <div class="review-sound-step"><strong>1 · ${esc(t(sourceLanguage==='ja'?'Original Japanese voice':'Original source voice'))}</strong>${clip('original','Original mix')}</div>
 <div class="review-sound-step"><strong>2 · ${esc(t('Separated source voice'))}</strong>${clip('separated','Separated voice')}</div>
 <div class="review-sound-step"><strong>3 · ${esc(t('TTS recordings and failed attempts'))}</strong>${recordingList}${failures?`<small>${failures} ${esc(t('attempts have no playable audio file'))}</small>`:''}</div>
 <div class="review-sound-step"><strong>4 · ${esc(t('Voice used in the current export'))}</strong><div class="review-source"><span>${esc(selectedLabel)}</span>${selected?button('review-listen-candidate','Listen','play','',`data-path="${esc(selected)}"`):choiceApplied&&choice?.action==='original'||sourceFallback?button('review-audition','Listen','play','',`${attrs} data-source="original"`):''}</div>${pendingChoice?`<small>${esc(t('Saved choice pending a new video export.'))}</small>`:''}</div>
 ${diagnostic(issue,t,button)}${issue?.evidence?.length?`<details><summary>${esc(t('Original diagnostic evidence'))}</summary><pre>${esc(JSON.stringify(issue.evidence,null,2))}</pre></details>`:''}</div>
 <div class="issue-actions">${button('review-retake-now','Generate a new take for this line','refresh','',`${attrs} ${active||!segment?'disabled':''}`)}${items.length?`<label>${esc(t('Choose a saved TTS recording'))}<select data-review-recording="${index-1}" ${active||!segment?'disabled':''}>${items.map((x,n)=>`<option value="${esc(x.path)}" ${choice?.action==='recording'&&choice.audio===x.path?'selected':''}>${n+1}. ${esc(t(name(x)))} · ${esc(engineName(x.engine))}</option>`).join('')}</select></label>${button('review-choice','Use selected recording','check','',`${attrs} data-choice="recording" ${active||!segment?'disabled':''}`)}`:''}${source('original')?button('review-choice','Use original voice for this line','check','',`${attrs} data-choice="original" ${active||!segment?'disabled':''}`):''}${choice?button('review-choice','Remove my override','close','',`${attrs} data-choice="automatic" ${active?'disabled':''}`):''}</div></article>`;
}

export function reviewPage({snapshot,t,button,engineName,active,sourceLanguage,retryReviewStarting=false,retryReviewError='',filter='issues',listPage=0}){
 const state=snapshot.reviewState||{},issues=Array.isArray(snapshot.issues)?snapshot.issues:[],resolved=snapshot.resolvedIssues||[],review=snapshot.review||{},cues=review.cues||[];
 const config=review.config||{},engines=config.selectedEngines||[config.ttsBackend||'drama3'],languages=config.dubLanguages||[config.targetLanguage||'yue'];
 const issueMap=new Map([...resolved,...issues].map(x=>[key(x.index,x.language||'yue',x.engine||''),x]));
 const choices=(snapshot.draft?.segments||[]).some(x=>Object.keys(x.reviewDecisions||{}).length);
 let html=`<div class="review-summary card"><div class="row spread wrap"><div><h3>${esc(t('Review report'))}</h3><p>${esc(t('The finished video is in the output folder. Review and replace individual voices here when needed.'))}</p></div><div class="row wrap">${button('review-export','Apply choices and export new video','export','primary',active||!choices||state.userChoicesApplied?'disabled':'')}</div></div><div class="row wrap"><span class="pill">${state.pending??issues.length} ${esc(t('Review notes'))}</span><span class="pill">${state.repaired||0} ${esc(t('Repaired'))}</span><span class="pill">${state.userChoices||0} ${esc(t('User choices'))}</span>${issues.length&&!active?button('retry-review',retryReviewStarting?'Starting AI repair…':'Retry AI repair','refresh','',retryReviewStarting?'disabled':''):''}</div>${active?`<small>${esc(t('Pause and save before changing a review choice.'))}</small>`:''}${retryReviewError?`<p class="warning" role="alert">${esc(retryReviewError)}</p>`:''}</div>`;
 const all=[];for(let i=1;i<=cues.length;i++)for(const language of languages)for(const engine of engines){const issue=issueMap.get(key(i,language,engine));all.push({cue:cues[i-1],index:i,language,engine,issue});}
 const visible=filter==='all'?all:all.filter(x=>issues.includes(x.issue));
 const totalPages=Math.max(1,Math.ceil(visible.length/25)),page=Math.min(Math.max(0,listPage),totalPages-1),slice=visible.slice(page*25,(page+1)*25);
 html+=`<div class="review-list-tools row spread wrap"><div class="row">${button('review-filter','Needs attention','review',filter==='issues'?'active':'',`data-value="issues"`)}${button('review-filter','All dialogue','list',filter==='all'?'active':'',`data-value="all"`)}</div><small>${esc(t('Showing'))} ${visible.length?`${page*25+1}–${Math.min((page+1)*25,visible.length)}`:'0'} / ${visible.length}</small></div>`;
 if(!slice.length)html+=`<div class="empty">${esc(t('No unresolved review issues'))}<p>${esc(t('Open All dialogue to listen to every saved recording.'))}</p></div>`;
 html+=slice.map(x=>lineCard(snapshot,x.cue,x.index,x.language,x.engine,x.issue,{t,button,engineName,active,sourceLanguage})).join('');
 if(totalPages>1)html+=`<div class="row spread review-pages">${button('review-page','Previous','back','',`data-value="${page-1}" ${page?'':'disabled'}`)}<small>${page+1} / ${totalPages}</small>${button('review-page','Next','next','',`data-value="${page+1}" ${page+1<totalPages?'':'disabled'}`)}</div>`;
 return html;
}
