// Build 280 desktop source-language dialog: auto-approve is on by default, so a dialog
// that still appears must name the reason it appeared.
import assert from 'node:assert/strict';
import {translate} from '../studio/web/i18n.js';
import {sourceHTML,sourceConfirmReasons,sourceListenFaultHTML} from '../studio/web/workflow-dialogs.js';

const t=language=>text=>translate(text,language);
const button=(id,label)=>`<button data-action="${id}">${label}</button>`;
const listenCopy='Speech recognition did not run on this computer, so the language label inside the file was used. Install the speech model in Model centre, then check the language again.';
const info=(over={})=>({name:'English',language:'en',streams:[{index:1,language:'eng'}],stream:1,supported:true,...over});

// The rule has exactly four reasons. A new reason needs product copy in four languages.
assert.deepEqual(Object.keys(sourceConfirmReasons).sort(),['engine-language-mismatch','language-undetected','listen-failed','switch-off']);
for(const [reason,sentence] of Object.entries(sourceConfirmReasons)){
  assert.equal(translate(sentence,'en'),sentence);
  for(const language of ['zh-HK','zh-CN','ja'])assert.notEqual(translate(sentence,language),sentence,`${reason}: ${language} copy is missing`);
  const html=sourceHTML(info({confirmReason:reason}),t('zh-HK'),button);
  assert(html.includes(translate(sentence,'zh-HK')),`${reason}: the dialog does not state this reason`);
}

// With the switch on and a usable detection there is no reason line and no fault hint.
const quiet=sourceHTML(info({confirmReason:'',detection:{confirmationSkipped:true}}),t('zh-HK'),button);
for(const sentence of Object.values(sourceConfirmReasons))assert(!quiet.includes(translate(sentence,'zh-HK')),'the dialog claimed a reason that did not happen');
assert(!quiet.includes(translate(listenCopy,'zh-HK')),'the dialog claimed a speech fault that did not happen');
assert.equal(sourceListenFaultHTML(info({}),t('zh-HK')),'');

// A listen step that could not run says which language was used and how to fix it.
const fault=sourceHTML(info({confirmReason:'language-undetected',listenFailure:'Speech model folder is empty'}),t('zh-HK'),button);
assert(fault.includes(translate(listenCopy,'zh-HK')),'the listen fault hint is missing');
for(const language of ['zh-CN','ja'])assert(sourceHTML(info({confirmReason:'language-undetected',listenFailure:'x'}),t(language),button).includes(translate(listenCopy,language)),`listen fault: ${language} copy is missing`);

console.log('OK desktop source-language reason copy');
