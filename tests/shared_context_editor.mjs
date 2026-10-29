import assert from 'node:assert/strict';
import {editCueField,effectiveMix,mixerHTML} from '../studio/web/context-editor.js';
import {translate} from '../studio/web/i18n.js';
import {panelCopy} from '../studio/web/workflow-guide.js';
assert.deepEqual(effectiveMix({}),{backgroundGain:.8,backgroundDucking:false});
assert.deepEqual(effectiveMix({backgroundGain:2,backgroundDucking:true}),{backgroundGain:1.5,backgroundDucking:true});
const cue={text:'完整台詞',captionText:'原顯示',audioTake:'/selected.wav',reviewDecisions:{'yue:drama3':{action:'recording',audio:'/selected.wav'}},audioAcceptedHistoryID:'accepted'};
const old=structuredClone(cue);assert(editCueField(cue,'captionText','新顯示'));assert.equal(cue.audioTake,old.audioTake);assert.deepEqual(cue.reviewDecisions,old.reviewDecisions);assert.equal(cue.audioAcceptedHistoryID,'accepted');assert.equal(cue.text,old.text);
assert(!editCueField(cue,'captionText','新顯示'));assert(editCueField(cue,'text','不同配音台詞'));assert.equal(cue.audioTake,null);assert(!cue.reviewDecisions);
const role={...old};editCueField(role,'speakerId','different-role');assert.equal(role.audioTake,null);assert(!role.reviewDecisions);
for(const language of ['en','zh-HK','zh-CN','ja']){
 const t=s=>translate(s,language),html=mixerHTML({settings:{backgroundGain:.35,backgroundDucking:false},t,field:(label,body)=>`<label>${t(label)}${body}</label>`,settingSwitch:(key,label,value)=>`<input data-setting="${key}" ${value?'checked':''}>${t(label)}`});
 assert(html.includes('35%'));assert(html.includes('max="1.5"'));assert(!html.includes('includeOriginal'));assert(!html.includes('Background separation'));assert(panelCopy('title',language));assert(panelCopy('warning',language).includes('2'));
 if(language!=='en')for(const key of ['Edit dialogue','Save and close','Export mix','Export background level','Lower background while speaking'])assert.notEqual(t(key),key);
}
console.log('PASS caption-only recording preservation, changed script/role invalidation, mixer bounds and four-language controls');
