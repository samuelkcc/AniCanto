import assert from 'node:assert/strict';
import {reviewPage} from '../studio/web/review-page.js';
import {translate} from '../studio/web/i18n.js';

const button=(a,label,ico='',klass='',attrs='')=>`<button data-action="${a}" class="${klass}" ${attrs} title="${label}">${label}</button>`;
// The desktop shell translates every button label; the stub mirrors app.js.
const translated=(t2,a,label,ico='',klass='',attrs='')=>`<button data-action="${a}" class="${klass}" ${attrs} title="${t2(label)}">${t2(label)}</button>`;
const engines=[['drama3','Drama3'],['gpt-sovits','GPT-SoVITS']];
const tags=(html,action)=>[...html.matchAll(new RegExp(`<button data-action="${action}"[^>]*>`,'g'))].map(match=>match[0]);
const base=()=>({review:{config:{ttsBackend:'drama3',selectedEngines:['drama3','gpt-sovits'],dubLanguages:['yue'],productionMode:'normal'},cues:[{start:1,end:2,speechStart:1,speechEnd:2,cantonese:'你好呀'}]},
 draft:{segments:[{id:'seg-1',sources:[0],start:1,end:2,text:'你好呀'}]},
 takes:[{index:1,language:'yue',engine:'drama3',audio:'/job/takes/first.wav'}],
 history:[{index:1,language:'yue',engine:'gpt-sovits',path:'/job/history/failed.wav'}],
 recordingCandidates:[{index:1,language:'yue',engine:'drama3',path:'/job/takes/first.wav',kind:'first'},{index:1,language:'yue',engine:'gpt-sovits',path:'/job/history/failed.wav',kind:'rejected'}],
 reportRows:[{index:1,language:'yue',engine:'drama3',reportGroup:'reportMissing',selectedAudio:'/job/takes/first.wav'}],
 issues:[],resolvedIssues:[],reviewState:{reportCounts:{reportMissing:1,reportAdvisory:0,reportAvailable:0},repaired:0,userChoices:0},workbench:{categories:{},canUndo:false}});
const render=(snapshot,over={})=>reviewPage({snapshot,t:s=>translate(s,'en'),language:'en',button:(a,label,ico,klass,attrs)=>translated(t=>translate(t,'en'),a,label,ico,klass,attrs),engineName:e=>e,active:false,sourceLanguage:'ja',filter:'all',engineOptions:engines,...over});

// One card per audio track offers the words box, the engine menu and a single-line retake.
{
 const html=render(base());
 assert.match(html,/<textarea data-review-words="0" rows="3"\s*>/);
 assert.match(html,/<select data-review-engine="0"\s*>/);
 for(const [id] of engines)assert(html.includes(`value="${id}"`),id);
 for(const action of ['review-save-words','review-retake-now','review-choice']){
  const rows=tags(html,action);
  assert(rows.length,action);
  // The report numbers a line from one; every per-line action uses the editor position.
  for(const tag of rows)assert(tag.includes('data-index="0"')&&tag.includes('data-language="yue"')&&!tag.includes('disabled'),`${action}: ${tag}`);
  assert.deepEqual(new Set(rows.map(tag=>tag.match(/data-engine="([^"]+)"/)[1])),new Set(['drama3','gpt-sovits']),action);
 }
}
// Audio used by the export or a saved choice stays protected; spare takes can be removed.
{
 const rows=tags(render(base()),'review-remove-take');
 const used=rows.filter(tag=>tag.includes('data-path="/job/takes/first.wav"'));
 assert.equal(used.length,0,'First recordings have no Remove control');
 assert(used.every(tag=>tag.includes('disabled')&&!tag.includes('data-index')),used.join(' | '));
 const spare=rows.filter(tag=>tag.includes('data-path="/job/history/failed.wav"'));
 assert(spare.length&&spare.every(tag=>tag.includes('data-index="0"')&&!tag.includes('disabled')),rows.join(' | '));
 const chosen=base();chosen.draft.segments[0].audioTake='/job/history/failed.wav';
 const blocked=tags(render(chosen),'review-remove-take').filter(tag=>tag.includes('data-path="/job/history/failed.wav"'));
 assert(blocked.length&&blocked.every(tag=>tag.includes('disabled')),blocked.join(' | '));
}
// A removed recording disappears from every list, and processing locks the editor.
{
 const snapshot=base();snapshot.removedTakes=[{path:'/job/history/failed.wav'}];
 const hidden=render(snapshot);
 assert(!hidden.includes('/job/history/failed.wav'),hidden.slice(0,200));
 assert.equal(tags(hidden,'review-remove-take').length,0,'Only the protected first recording remains');
 const busy=render(base(),{active:true});
 assert.match(busy,/<textarea data-review-words="0" rows="3" disabled>/);
 assert.match(busy,/<select data-review-engine="0" disabled>/);
 for(const action of ['review-save-words','review-retake-now'])for(const tag of tags(busy,action))assert(tag.includes('disabled'),`${action}: ${tag}`);
 for(const tag of tags(busy,'review-remove-take'))assert(tag.includes('disabled'),tag);
}
// One installed engine offers no engine menu; every interface language renders clean copy.
{
 const single=render(base(),{engineOptions:[['drama3','Drama3']]});
 assert(single.includes('data-review-engine='),'The model control stays visible with one engine');
 const copies=['Dubbing words for this line','Voice engine for a new recording','Save words','Remove this recording','Words saved. Generate a new take to record them.','Recording removed. It stays in the discarded-recordings folder.'];
 for(const language of ['en','zh-HK','zh-CN','ja']){
  const localized=reviewPage({snapshot:base(),t:s=>translate(s,language),language,button:(a,label,ico,klass,attrs)=>translated(t2=>translate(t2,language),a,label,ico,klass,attrs),engineName:e=>e,active:false,sourceLanguage:'ja',filter:'all',engineOptions:engines});
  assert(!localized.includes('undefined'),language);
  for(const copy of copies){
   const value=translate(copy,language);
   if(language!=='en')assert.notEqual(value,copy,`${language} needs a translation for: ${copy}`);
   if(copies.indexOf(copy)<4)assert(localized.includes(value),`${language}: ${copy}`);
  }
 }
}
console.log('PASS review report edits words, offers engine choice, regenerates one line and removes only unused recordings');
