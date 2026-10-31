// Review status tabs for desktop build 278: the user's own listening state filters the report.
import assert from 'node:assert/strict';
import {reviewPage} from '../studio/web/review-page.js';
import {translate} from '../studio/web/i18n.js';
import {controlCopy} from '../studio/web/workflow-guide.js';

const button=(a,label,ico='',klass='',attrs='')=>`<button data-action="${a}" class="${klass}" ${attrs} title="${label}">${label}</button>`;
const render=(snapshot,language,over={})=>reviewPage({snapshot,t:s=>translate(s,language),language,button,engineName:e=>e,active:false,sourceLanguage:'ja',engineOptions:[],...over});
const rows=html=>[...html.matchAll(/data-report-group="([^"]+)"/g)].map(match=>match[1]);
const marks=html=>[...html.matchAll(/data-action="review-triage"[^>]*data-fingerprint="([^"]*)"/g)].map(match=>match[1]);

const snapshot=()=>({review:{config:{ttsBackend:'drama3',selectedEngines:['drama3'],dubLanguages:['yue']},
 cues:[{start:0,end:2,cantonese:'第一句'},{start:3,end:5,cantonese:'第二句'},{start:6,end:8,cantonese:'第三句'}]},
 draft:{segments:[]},takes:[],history:[],recordingCandidates:[],resolvedIssues:[],issues:[],
 reportRows:[{index:1,language:'yue',engine:'drama3',reportGroup:'reportAvailable',triage:'checked',triageFingerprint:'fp-1',triageID:'line-1-yue-drama3'},
             {index:2,language:'yue',engine:'drama3',reportGroup:'reportAdvisory',triage:'deferred',triageFingerprint:'fp-2',triageID:'line-2-yue-drama3'},
             {index:3,language:'yue',engine:'drama3',reportGroup:'reportMissing',triage:'pending',triageFingerprint:'fp-3',triageID:'line-3-yue-drama3'}],
 reviewState:{reportCounts:{reportMissing:1,reportAdvisory:1,reportAvailable:1},repaired:0,userChoices:0},
 reviewTriage:{pending:1,checked:1,deferred:1,total:3}});

for(const language of ['en','zh-HK','zh-CN','ja']){
 const html=render(snapshot(),language,{filter:'all'});
 for(const id of ['reviewChecked','reviewPending'])
  assert(html.includes(`>${controlCopy(id,language,'title')}</button>`),`${language} ${id}`);
 // A flagged or unflagged line can carry the human mark.
 // Three lines carry the marks: two buttons when unreviewed, three once marked.
 assert.deepEqual([...new Set(marks(html))].filter(Boolean),['fp-1','fp-2','fp-3'],`${language}: ${marks(html).join(',')}`);
 assert(!html.includes('undefined'),language);
}
assert.deepEqual(rows(render(snapshot(),'en',{filter:'reviewChecked'})),['reportAvailable']);
assert.deepEqual(rows(render(snapshot(),'en',{filter:'reviewPending'})),['reportAdvisory','reportMissing']);
// The tabs combine with the search field.
assert.deepEqual(rows(render(snapshot(),'en',{filter:'reviewPending',search:'第三句'})),['reportMissing']);
assert.deepEqual(rows(render(snapshot(),'en',{filter:'reviewPending',search:'第一句'})),[]);
// The summary counts the human states beside the AI categories.
{
 const html=render(snapshot(),'en');
 assert(html.includes(`>1 ${controlCopy('reviewChecked','en','title')}</span>`),html.slice(0,1200));
 assert(html.includes(`>2 ${controlCopy('reviewPending','en','title')}</span>`),html.slice(0,1200));
}
// A snapshot without the projection keeps the report working.
{
 const quiet=snapshot();delete quiet.reviewTriage;for(const row of quiet.reportRows)delete row.triage;
 const html=render(quiet,'en',{filter:'reviewPending'});
 assert.equal(rows(html).length,3);
}
console.log('PASS review status tabs, four languages, per-line marks, search combination, summary counts');
