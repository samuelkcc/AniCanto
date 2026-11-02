// Build 282 desktop review card: one recording list carries every saved take once.
// The take the export uses keeps one mark, and no second block repeats that audio.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {reviewPage} from '../studio/web/review-page.js';
import {translate} from '../studio/web/i18n.js';

const button=(a,label,ico='',klass='',attrs='')=>`<button data-action="${a}" class="${klass}" ${attrs}>${label}</button>`;
const one='/job/takes/one.wav',two='/job/takes/two.wav';
const base=()=>({review:{config:{ttsBackend:'drama3',selectedEngines:['drama3'],dubLanguages:['yue']},cues:[{start:0,end:2,cantonese:'你好'}]},
 draft:{segments:[{id:'s1',sources:[0],start:0,end:2,text:'你好'}]},
 takes:[{audio:one,index:1,language:'yue',engine:'drama3',created:1},{audio:two,index:1,language:'yue',engine:'drama3',created:2}],
 history:[],recordingCandidates:[],resolvedIssues:[],
 voiceReferences:{[one]:{state:'first',reference:'voice.wav',seed:2145860346},[two]:{state:'same',reference:'voice.wav',seed:2145860346}},
 issues:[{id:'issue-1',index:1,language:'yue',engine:'drama3',kind:'verification-unresolved',reportGroup:'reportAdvisory',evidence:[],triage:'pending',triageFingerprint:'fp'}],
 issues:[{id:'issue-1',index:1,language:'yue',engine:'drama3',kind:'verification-unresolved',reportGroup:'reportAdvisory',evidence:[],triage:'pending',triageFingerprint:'fp',
  attempts:[{action:'initial-voice-attempt',status:'generated',audition:{path:one},recordedAt:1},{action:'initial-voice-attempt',status:'generated',audition:{path:two},recordedAt:2}]}],
 reportRows:[{index:1,language:'yue',engine:'drama3',reportGroup:'reportAdvisory',selectedAudio:two,triage:'pending',triageFingerprint:'fp'}]});

const languages=['en','zh-HK','zh-CN','ja'];
const render=snapshot=>{const out={};for(const language of languages)out[language]=reviewPage({snapshot,t:s=>translate(s,language),language,button,engineName:e=>e,active:false,sourceLanguage:'ja',engineOptions:[],filter:'reportAdvisory'});return out};
const count=(text,html,language)=>(html.match(new RegExp(translate(text,language).replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'g'))||[]).length;
// A take name can sit inside a longer label in some locales, so the label count is
// tied to the place it is rendered: the row heading, or one option in the pick menu.
const inList=(text,html,language)=>count(`<strong>${translate(text,language)}</strong>`,html,language);
const inMenu=(text,html,language)=>count(`. ${translate(text,language)} · drama3</option>`,html,language);
// Some locales word the state mark inside the export note, so the mark is counted in its own pill.
const inPill=(text,html,language)=>count(`<span class="pill review-take-state">${translate(text,language)}</span>`,html,language);
const steps=html=>(html.match(/class="review-sound-step"/g)||[]).length;

// Case 1: the export uses a saved take. The mark sits on that row; no export block returns.
for(const [language,html] of Object.entries(render(base()))){
 assert.equal(steps(html),3,`${language}: listening steps ${steps(html)}`);
 assert.equal(inPill('Used in current export',html,language),1,`${language}: export mark count`);
 assert.equal(count('Voice used in the current export',html,language),0,`${language}: repeated export block`);
 assert.equal((html.match(/class="review-take-row"/g)||[]).length,2,`${language}: one row per saved take`);
 assert.equal((html.match(/class="pill review-take-state"/g)||[]).length,1,`${language}: one state mark in the list`);
 assert.equal(inList('First generated recording',html,language),1,`${language}: first take named once in the list`);
 assert.equal(inMenu('First generated recording',html,language),1,`${language}: first take offered once in the menu`);
 assert.equal(inList('Generated recording',html,language),1,`${language}: second take named once in the list`);
 assert.equal(inMenu('Generated recording',html,language),1,`${language}: second take offered once in the menu`);
 assert(html.includes(`data-path="${one}"`)&&html.includes(`data-path="${two}"`),`${language}: both takes keep one listen control`);
 assert(!html.includes('undefined'),language);
}

// Case 2: the line keeps its original voice. One export line names it, and it can be heard.
const original=base();original.draft.segments[0].reviewDecisions={'yue:drama3':{action:'original'}};original.reviewState={userChoicesApplied:true};
for(const [language,html] of Object.entries(render(original))){
 assert.equal(steps(html),3,`${language}: listening steps`);
 assert.equal(count('Voice used in the current export',html,language),1,`${language}: export line`);
 assert.equal((html.match(/class="pill review-take-state"/g)||[]).length,0,`${language}: no take carries the export mark`);
 assert(html.includes(translate('Original Japanese voice',language)),`${language}: original voice named`);
 assert((html.match(/data-source="original"/g)||[]).length>=2,`${language}: original voice is listenable`);
}

// Case 3: a saved recording choice waits for a new export. The pick and the export take read apart.
const pending=base();pending.draft.segments[0].reviewDecisions={'yue:drama3':{action:'recording',audio:one}};pending.reviewState={userChoicesApplied:false};
for(const [language,html] of Object.entries(render(pending))){
 assert.equal(count('Your selected recording',html,language),1,`${language}: saved pick mark`);
 assert.equal(inPill('Used in current export',html,language),1,`${language}: export take mark`);
 assert.equal(count('Saved choice pending a new video export.',html,language),1,`${language}: pending note`);
 assert.equal(count('Voice used in the current export',html,language),0,`${language}: no repeated export block`);
}

// Case 4: nothing was retained. The card says so once, with no empty export block.
const empty=base();empty.takes=[];empty.voiceReferences={};empty.reportRows=[];empty.issues[0].attempts=[];
for(const [language,html] of Object.entries(render(empty))){
 assert.equal(count('No TTS recording was retained for this line.',html,language),1,`${language}: empty list note`);
 assert.equal(count('Voice used in the current export',html,language),1,`${language}: export line states no selection`);
 assert.equal(count('No dubbed recording selected',html,language),1,`${language}: selection state`);
 assert.equal((html.match(/class="pill review-take-state"/g)||[]).length,0,`${language}: no phantom mark`);
}

// An older snapshot with no recording report still renders three listening steps.
const legacy=base();delete legacy.voiceReferences;
for(const [language,html] of Object.entries(render(legacy)))assert.equal(steps(html),3,`${language}: legacy listening steps`);

// Case 5: the export uses a completed take that the list no longer holds. The note names it once
// and keeps one Listen control, so no export audio becomes unhearable.
const outside=base();outside.takes=[];outside.voiceReferences={};outside.issues[0].attempts=[];
outside.reportRows=[{index:1,language:'yue',engine:'drama3',reportGroup:'reportAdvisory',selectedAudio:'/job/older.wav',triage:'pending',triageFingerprint:'fp'}];
for(const [language,html] of Object.entries(render(outside))){
 assert(html.includes(`${translate('Voice used in the current export',language)} · ${translate('Used in current export',language)}`),`${language}: export audio outside the list is named once`);
 assert.equal(count('Voice used in the current export',html,language),1,`${language}: one export line`);
 assert.equal((html.match(/data-path="\/job\/older\.wav"/g)||[]).length,1,`${language}: that audio keeps one Listen control`);
 assert.equal(count('No TTS recording was retained for this line.',html,language),1,`${language}: the list still says it holds nothing`);
}

// A retake reuses the seed the engine recorded for that line, so the edited words keep the
// same voice character instead of falling back to the default seed.
const app=fs.readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
const handler=app.split('\n').filter(row=>row.includes("review-retake-now"));
assert.equal(handler.length,1,`retake handler lines: ${handler.length}`);
assert(handler[0].includes('voiceReferences'),handler[0].slice(0,300));
assert(handler[0].includes('Number.isInteger(target.take)'),handler[0].slice(0,300));

console.log('PASS one recording list: one export mark, no repeated export block, retake reads the recorded seed');
