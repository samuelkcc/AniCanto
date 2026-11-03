// Recording list labels for desktop build 278: one first take, later retakes read as generated takes.
import assert from 'node:assert/strict';
import {reviewPage} from '../studio/web/review-page.js';
import {translate} from '../studio/web/i18n.js';

const button=(a,label,ico='',klass='',attrs='')=>`<button data-action="${a}" class="${klass}" ${attrs}>${label}</button>`;
const snapshot={review:{config:{ttsBackend:'drama3',selectedEngines:['drama3'],dubLanguages:['yue']},cues:[{start:0,end:2,cantonese:'你好'}]},
 draft:{segments:[{id:'s1',sources:[0],start:0,end:2,text:'你好'}]},takes:[],history:[],recordingCandidates:[],resolvedIssues:[],
 issues:[{id:'issue-1',index:1,language:'yue',engine:'drama3',kind:'verification-unresolved',reportGroup:'reportAdvisory',evidence:[],triage:'pending',triageFingerprint:'fp',
  attempts:[{action:'initial-voice-attempt',status:'generated',audition:{path:'/job/takes/one.wav'},recordedAt:1},
            {action:'initial-voice-attempt',status:'generated',audition:{path:'/job/takes/two.wav'},recordedAt:2},
            {action:'initial-voice-attempt',status:'generated',audition:{path:'/job/takes/three.wav'},recordedAt:3}]}],
 reportRows:[{index:1,language:'yue',engine:'drama3',reportGroup:'reportAdvisory',selectedAudio:'/job/takes/one.wav',triage:'pending',triageFingerprint:'fp'}]};
for(const language of ['en','zh-HK','zh-CN','ja']){
 const html=reviewPage({snapshot,t:s=>translate(s,language),language,button,engineName:e=>e,active:false,sourceLanguage:'ja',engineOptions:[],filter:'reportAdvisory'});
 // The recording list and the choice dropdown repeat each label once.
 const list=html.split('data-review-recording')[0];
 const count=(text,where)=>(where.match(new RegExp(translate(text,language),'g'))||[]).length;
 assert.equal(count('First generated recording',list),2,`${language}: ${count('First generated recording',list)} first-take labels`);
 assert.equal(count('First generated recording',html),3,`${language}: dropdown repeat`);
 assert(count('Generated recording',list)>=2,language);
 assert(html.includes('/job/takes/two.wav')&&html.includes('/job/takes/three.wav'),language);
 assert(!html.includes('undefined'),language);
}
console.log('PASS one first-take label, later retakes keep their files and read as generated recordings');
