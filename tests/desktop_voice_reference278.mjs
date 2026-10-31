// Build 278 desktop retake continuity: the line keeps its recording seed, and the
// review card names a recording whose separated voice reference differs.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {reviewPage} from '../studio/web/review-page.js';
import {translate} from '../studio/web/i18n.js';

const button=(a,label,ico='',klass='',attrs='')=>`<button data-action="${a}" class="${klass}" ${attrs}>${label}</button>`;
const first='/job/takes/one.wav',again='/job/takes/two.wav',other='/job/takes/three.wav';
const snapshot={review:{config:{ttsBackend:'drama3',selectedEngines:['drama3'],dubLanguages:['yue']},cues:[{start:0,end:2,cantonese:'你好'}]},
 draft:{segments:[{id:'s1',sources:[0],start:0,end:2,text:'你好',take:42}]},takes:[],history:[],recordingCandidates:[],resolvedIssues:[],
 voiceReferences:{[first]:{state:'first',reference:'reference.wav',seed:42},[again]:{state:'same',reference:'reference.wav',seed:42},
  [other]:{state:'different',reference:'reference.wav',seed:42}},
 issues:[{id:'issue-1',index:1,language:'yue',engine:'drama3',kind:'verification-unresolved',reportGroup:'reportAdvisory',evidence:[],triage:'pending',triageFingerprint:'fp',
  attempts:[{action:'initial-voice-attempt',status:'generated',audition:{path:first},recordedAt:1},
            {action:'initial-voice-attempt',status:'generated',audition:{path:again},recordedAt:2},
            {action:'initial-voice-attempt',status:'generated',audition:{path:other},recordedAt:3}]}],
 reportRows:[{index:1,language:'yue',engine:'drama3',reportGroup:'reportAdvisory',selectedAudio:first,triage:'pending',triageFingerprint:'fp'}]};
const note='Used a different separated voice than the first recording of this line.';

for(const language of ['en','zh-HK','zh-CN','ja']){
 const html=reviewPage({snapshot,t:s=>translate(s,language),language,button,engineName:e=>e,active:false,sourceLanguage:'ja',engineOptions:[],filter:'reportAdvisory'});
 assert.equal((html.match(new RegExp(translate(note,language),'g'))||[]).length,1,`${language}: ${translate(note,language)}`);
 assert(html.includes(translate('First generated recording',language)),language);
 assert(!html.includes('undefined'),language);
 // Only the flagged recording carries a reference warning; the matching retake stays quiet.
 const rows=html.split('class="review-take-row"');
 assert.equal(rows.filter(row=>row.includes(translate(note,language))).length,1,`${language}: ${JSON.stringify(rows.length)}`);
}

// A snapshot from an older build carries no reference report and adds no warning.
const {voiceReferences,...legacy}=snapshot;
const quiet=reviewPage({snapshot:legacy,t:s=>translate(s,'en'),language:'en',button,engineName:e=>e,active:false,sourceLanguage:'ja',engineOptions:[],filter:'reportAdvisory'});
assert(!quiet.includes(note),quiet.slice(0,200));

// A manual retake must not draw a new recording seed at random.
const source=fs.readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
const line=source.split('\n').filter(row=>row.includes("review-retake-now"));
assert.equal(line.length,1,`retake handler lines: ${line.length}`);
assert(line[0].includes('Number.isInteger(target.take)'),line[0].slice(0,400));
assert(!line[0].includes('getRandomValues'),line[0].slice(0,400));

console.log('PASS retake keeps the line recording seed; a differing voice reference reads once in four languages');
