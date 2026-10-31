// Build 278 desktop notices: one wide badge in the preview column, a short chip on the video card.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {esc} from '../studio/web/model.js';
import {icon} from '../studio/web/icons.js';
import {translate} from '../studio/web/i18n.js';
import {controlCopy} from '../studio/web/workflow-guide.js';
import {projectWarning} from '../studio/web/workflow-text.js';

const source=fs.readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
// Each template is one top-level function: it ends at its own closing brace or at the next top-level declaration.
const body=name=>{const start=source.indexOf(`function ${name}(`);assert(start>=0,`${name}: missing`);const rest=source.slice(start);
 const closes=[...rest.matchAll(/^\}/gm)].filter(match=>match.index>0).map(match=>match.index+1);
 const next=[...rest.matchAll(/^(?=function |const |let )/gm)].filter(match=>match.index>0).map(match=>match.index);
 const stops=[...closes,...next];
 assert(stops.length,`${name}: unterminated`);return rest.slice(0,Math.min(...stops))};
const names=['previewNotices','previewNoticeBadge','queueNoticeChip','sourceLanguageApprovalControl','productionScopeControl'];
// The desktop shell owns these templates; the stub mirrors the browser globals.
const shell=(row,language,settings={})=>new Function('d',`const {esc,icon,t,controlCopy,projectWarning,settingSwitch,productionConfig,individualProduction,row,state,active}=d;
${names.map(body).join('\n')}
return {previewNotices,previewNoticeBadge,queueNoticeChip,sourceLanguageApprovalControl,productionScopeControl}`)({
 esc,icon,t:text=>translate(text,language),controlCopy,projectWarning,
 settingSwitch:(key,label,value,extra='')=>`<label class="setting-switch"><span class="switch-copy">${esc(translate(label,language))}</span><input type="checkbox" role="switch" data-setting="${key}" ${value?'checked':''} ${extra}></label>`,
 productionConfig:()=>settings,individualProduction:()=>row?.useGlobalSettings===false,row:()=>row,state:{language},active:false});

const failing={id:'row-1',video:'/queue/one.mkv',status:'attention',lastError:{message:'對白覆蓋：第一句 · 語音不完整 — 有錄音 4/6；缺聲 2'}};
const noticed={id:'row-2',video:'/queue/two.mkv',status:'paused',queueNotice:'Confirm this video’s source language before starting it.'};
const preview={id:'row-3',video:'/queue/three.mkv',status:'completed',deliveryKind:'preview',incompleteDialogue:3,deliveryState:'not-exported'};
const clean={id:'row-4',video:'/queue/four.mkv',status:'completed',deliveryState:'exported'};

for(const language of ['en','zh-HK','zh-CN','ja']){
 // A failed video shows the wide error band, and the card keeps only a short chip.
 const failed=shell(failing,language);
 const errorBadge=failed.previewNoticeBadge(failing);
 assert(errorBadge.includes('class="preview-notice has-error"')&&errorBadge.includes('role="alert"'),`${language}: ${errorBadge}`);
 assert(errorBadge.includes(projectWarning(failing.lastError.message,language)),`${language}: ${errorBadge}`);
 assert(errorBadge.includes('preview-notice-line error'),language);
 assert(failed.queueNoticeChip(failing).includes('queue-notice-chip error'),language);
 // A queue notice reads as a warning, not an error.
 const stopped=shell(noticed,language);
 const warningBadge=stopped.previewNoticeBadge(noticed);
 assert(warningBadge.includes('class="preview-notice "')&&warningBadge.includes('role="status"'),`${language}: ${warningBadge}`);
 const noticeText=translate(noticed.queueNotice,language);
 assert(warningBadge.includes(noticeText)&&warningBadge.includes('preview-notice-line warning'),`${language}: ${warningBadge}`);
 // The card chip keeps the short label and puts the full message in the tooltip.
 const chip=stopped.queueNoticeChip(noticed);
 assert(chip.includes(translate('Needs attention',language))&&chip.includes(noticeText),`${language}: ${chip}`);
 // An incomplete preview and an unexported delivery each add one readable line.
 const part=shell(preview,language);
 assert.equal(part.previewNotices(preview).length,2,`${language}: ${JSON.stringify(part.previewNotices(preview))}`);
 assert(part.previewNoticeBadge(preview).includes(String(preview.incompleteDialogue)),language);
 // A healthy video carries no notice at all.
 assert.equal(shell(clean,language).previewNoticeBadge(clean),'',language);
 assert.equal(shell(clean,language).queueNoticeChip(clean),'',language);
 // The auto-approve switch sits under the Global scope switch in both inspectors.
 for(const settings of [{},{autoApproveSourceLanguage:true}]){
  const scope=shell(clean,language,settings).productionScopeControl();
  const approval=scope.indexOf('data-setting="autoApproveSourceLanguage"');
  assert(approval>scope.indexOf('data-setting="productionScopeGlobal"'),`${language}: ${scope}`);
  assert(/data-setting="autoApproveSourceLanguage" checked/.test(scope),`${language}: ${scope}`);
  assert(scope.includes(controlCopy('autoApproveSourceLanguage',language,'title')),language);
 }
 // The switch reads as off only when the stored setting is false.
 const off=shell(clean,language,{autoApproveSourceLanguage:false}).sourceLanguageApprovalControl();
 assert(!/data-setting="autoApproveSourceLanguage" checked/.test(off),`${language}: ${off}`);
 assert(off.includes(controlCopy('autoApproveSourceLanguage',language)),`${language}: tooltip`);
 assert(!shell(clean,language).productionScopeControl().includes('undefined'),language);
}

// Text from a worker or the queue can never inject markup.
const hostile=shell({...clean,lastError:{message:'<script>alert(1)</script>'}},'en');
const badge=hostile.previewNoticeBadge({...clean,lastError:{message:'<script>alert(1)</script>'}});
assert(badge.includes('&lt;script&gt;')&&!badge.includes('<script>'),badge);

// The badge belongs to the preview column, after the player controls, not inside a card.
const editor=body('editor');
assert(editor.includes('${previewNoticeBadge()}'),'preview column call');
assert(editor.indexOf('${previewNoticeBadge()}')>editor.indexOf('class="player-controls"'),'badge after the player');
assert(editor.indexOf('${previewNoticeBadge()}')<editor.indexOf('id="basic-progress"'),'badge above the working panels');
// The video card no longer prints a long notice line.
const shelf=body('shelfCards');
assert(shelf.includes('${queueNoticeChip(r)}'),'chip on the card');
assert(!shelf.includes('queueNotice?`<small class="warning">'),'no long notice text on the card');
// Both interface modes and the queue pages keep the same notice rules.
const css=fs.readFileSync(new URL('../studio/web/styles.css',import.meta.url),'utf8');
for(const rule of ['.preview-notice{','.preview-notice.has-error{','.queue-notice-chip{','.production-scope .source-approval-switch{'])
 assert(css.includes(rule),rule);

console.log('PASS wide preview notice badge, short card chip, four languages, escaped text, switch under Global scope');
