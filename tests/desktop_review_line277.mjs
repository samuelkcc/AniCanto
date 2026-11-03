// Review report shape for desktop build 277: one summary, one filter row, one search, one card per line.
import assert from 'node:assert/strict';
import {reviewPage} from '../studio/web/review-page.js';
import {translate} from '../studio/web/i18n.js';
import {controlCopy} from '../studio/web/workflow-guide.js';

const translated=(t2,a,label,ico='',klass='',attrs='')=>`<button data-action="${a}" class="${klass}" ${attrs} title="${t2(label)}">${t2(label)}</button>`;
const tags=(html,action)=>[...html.matchAll(new RegExp(`<button data-action="${action}"[^>]*>`,'g'))].map(match=>match[0]);
const cues=n=>Array.from({length:n},(_,i)=>({start:i*3,end:i*3+2,speechStart:i*3,speechEnd:i*3+2,cantonese:`第 ${i+1} 句`}));
const base=(lines=3)=>({review:{config:{ttsBackend:'drama3',selectedEngines:['drama3'],dubLanguages:['yue'],productionMode:'normal'},cues:cues(lines)},
 draft:{segments:cues(lines).map((c,i)=>({id:`seg-${i}`,sources:[i],start:c.start,end:c.end,text:c.cantonese}))},
 takes:[],history:[],recordingCandidates:[],reportRows:[],issues:[],resolvedIssues:[],
 reviewState:{reportCounts:{reportMissing:1,reportAdvisory:1,reportAvailable:lines-2},repaired:0,userChoices:0}});
const render=(snapshot,over={})=>reviewPage({snapshot,t:s=>translate(s,'en'),language:'en',button:(a,label,ico,klass,attrs)=>translated(t=>translate(t,'en'),a,label,ico,klass,attrs),engineName:e=>e,active:false,sourceLanguage:'ja',engineOptions:[['drama3','Drama3']],...over});
const rows=html=>[...html.matchAll(/data-report-group="([^"]+)"/g)].map(match=>match[1]);

// The report keeps one summary card and one filter row. The old section blocks are gone.
{
 const html=render(base());
 assert.equal((html.match(/class="review-summary card"/g)||[]).length,1,html.slice(0,300));
 for(const dropped of ['coverage-summary','workflow-notice','performance-review','review-category','issue-classification','review-undo-triage'])
  assert(!html.includes(dropped),dropped);
 const filters=tags(html,'review-filter');
 // Build 278 adds the two human review tabs after the four AI categories.
 assert.deepEqual(filters.map(tag=>tag.match(/data-value="([^"]+)"/)[1]),['reportMissing','reportAdvisory','reportAvailable','all','reviewChecked','reviewPending'],filters.join(' | '));
 for(const id of ['reportMissing','reportAdvisory','reportAvailable'])
  assert(filters.some(tag=>tag.includes(`title="${controlCopy(id,'en','title')}"`)&&controlCopy(id,'en','title')),id);
 assert.equal((html.match(/id="review-search"/g)||[]).length,1,html.slice(0,300));
 // The search field keeps the shared guide label in all four interface languages.
  for(const language of ['en','zh-HK','zh-CN','ja']){
   const page=reviewPage({snapshot:base(),t:s=>translate(s,language),language,
    button:(a,label,ico,klass,attrs)=>translated(t2=>translate(t2,language),a,label,ico,klass,attrs),
    engineName:e=>e,active:false,sourceLanguage:'ja',engineOptions:[],filter:'all'});
   assert(page.includes(controlCopy('reportSearch',language,'title')+'<input id="review-search"'),language);
  }
}
// The filter and the search field select the same list, and one card is one dialogue line.
{
 const snapshot=base();
 snapshot.reportRows=[{index:1,language:'yue',engine:'drama3',reportGroup:'reportMissing',selectedAudio:'/job/one.wav'},
                      {index:2,language:'yue',engine:'drama3',reportGroup:'reportAdvisory'},
                      {index:3,language:'yue',engine:'drama3',reportGroup:'reportAvailable'}];
 assert.deepEqual(rows(render(snapshot,{filter:'reportMissing'})),['reportMissing']);
 assert.deepEqual(rows(render(snapshot,{filter:'reportAdvisory'})),['reportAdvisory']);
 assert.deepEqual(rows(render(snapshot,{filter:'reportAvailable'})),['reportAvailable']);
 assert.equal(rows(render(snapshot,{filter:'all'})).length,3);
 assert.deepEqual(rows(render(snapshot,{filter:'all',search:'第 2 句'})),['reportAdvisory']);
 assert.deepEqual(rows(render(snapshot,{filter:'all',search:'3'})),['reportAvailable']);
 assert(rows(render(snapshot,{filter:'all',search:'没有这句'})).length===0);
}
// Long reports page at 25 lines, so the report never becomes one endless column.
{
 const snapshot=base(30);
 const first=render(snapshot,{filter:'all'});
 assert.equal(rows(first).length,25,`${rows(first).length} cards`);
 assert(first.includes('1 / 2'),first.slice(-400));
 const second=render(snapshot,{filter:'all',listPage:1});
 assert.equal(rows(second).length,5);
 assert(second.includes('2 / 2'),second.slice(-400));
}
// The server list decides which recordings are in use, and the first take stays first.
{
 const snapshot=base();
 snapshot.recordingCandidates=[{index:1,language:'yue',engine:'drama3',path:'/job/first.wav',kind:'first',created:10},
                               {index:1,language:'yue',engine:'drama3',path:'/job/second.wav',kind:'generated',created:20},
                               {index:1,language:'yue',engine:'drama3',path:'/job/third.wav',kind:'generated',created:30}];
 snapshot.protectedTakes=[{path:'/job/second.wav',reason:'saved review choice'}];
 const html=render(snapshot,{filter:'all',listPage:0});
 const order=[...html.matchAll(/class="review-take-index">\d+<\/span><span class="grow"><strong>([^<]+)/g)].map(match=>match[1]);
 assert.deepEqual(order,['First generated recording','Generated recording','Generated recording'],order.join(' | '));
 const removes=tags(html,'review-remove-take');
 const disabled=removes.filter(tag=>tag.includes('disabled')).map(tag=>tag.match(/data-path="([^"]+)"/)[1]);
 assert.deepEqual(disabled,['/job/second.wav'],removes.join(' | '));
 assert(!removes.some(tag=>tag.includes('data-path="/job/first.wav"')),removes.join(' | '));
}
// The list copy is translated in every interface language.
{
 const copies=['Line number or dialogue words','All dialogue','No dialogue matches this search','Showing','No dialogue needs dubbing','No review notes here','No dialogue in this category','Open All dialogue to listen to every saved recording.'];
 for(const language of ['en','zh-HK','zh-CN','ja']){
  const view=(over,fixture=base())=>reviewPage({snapshot:fixture,t:s=>translate(s,language),language,button:(a,label,ico,klass,attrs)=>translated(t2=>translate(t2,language),a,label,ico,klass,attrs),engineName:e=>e,active:false,sourceLanguage:'ja',engineOptions:[['drama3','Drama3']],filter:'all',...over});
  const html=[view({}),view({filter:'reportMissing'}),view({filter:'reportAdvisory'}),view({filter:'reportAvailable'},base(0)),view({search:'no such words'})];
  assert(!html.join('').includes('undefined'),language);
  for(const copy of copies){
   const value=translate(copy,language);
   if(language!=='en')assert.notEqual(value,copy,`${language} needs a translation for: ${copy}`);
   if(copy!=='Showing')assert(html.some(page=>page.includes(value)),`${language}: ${copy}`);
  }
  assert(html.every(page=>page.includes(`placeholder="${translate('Line number or dialogue words',language)}"`)),language);
 }
}
console.log('PASS build277 review report: one summary, one filter row, one search, paged cards and a server-side protection list');
