import assert from 'node:assert/strict';
import {reviewPage} from '../studio/web/review-page.js';
import {translate} from '../studio/web/i18n.js';
import {controlCopy} from '../studio/web/workflow-guide.js';
const groups=['reportMissing','reportAdvisory','reportAvailable','reportPreserved'];
const cues=groups.map((g,n)=>({start:n,end:n+1,cantonese:`台詞${n}`}));
const rows=groups.map((g,n)=>({index:n+1,language:'yue',engine:'gpt-sovits',reportGroup:g,selectedAudio:g==='reportAvailable'?'/current.wav':null,repaired:g==='reportAvailable'}));
const issues=groups.slice(0,2).map((g,n)=>({id:'test'+n,index:n+1,language:'yue',engine:'gpt-sovits',reportGroup:g,kind:n?'verification-unresolved':'missing-audio',repairEligible:!n,evidence:[],triage:'pending'}));
const snapshot={review:{config:{selectedEngines:['gpt-sovits'],dubLanguages:['yue']},cues},issues,reportRows:rows,reviewState:{reportCounts:Object.fromEntries(groups.map(g=>[g,1])),repaired:1},workbench:{categories:{},pending:1}};
const button=(a,title,icon='',cl='',attrs='')=>`<button data-action="${a}" ${attrs}>${title}</button>`;
for(const language of ['en','zh-HK','zh-CN','ja']){
 for(const filter of [...groups.slice(0,3),'all']){
  const html=reviewPage({snapshot,t:s=>translate(s,language),language,button,engineName:s=>s,active:false,sourceLanguage:'ja',filter});
  const visible=[...html.matchAll(/class="review-result" data-report-group="([^"]+)"/g)].map(m=>m[1]);
  assert.deepEqual(visible,filter==='all'?groups:[filter]);
  for(const g of groups.slice(0,3))assert(html.includes(controlCopy(g,language,'title')));
  assert(html.includes(controlCopy('reportClassification',language)));
  if(filter==='reportAvailable'||filter==='all')assert(html.includes('data-path="/current.wav"'));
  assert(!html.includes('undefined'));assert(!html.includes('data-value="issues"'));
 }
}
console.log('PASS four canonical language labels, four primary filters, current selected playback and preserved rows');
