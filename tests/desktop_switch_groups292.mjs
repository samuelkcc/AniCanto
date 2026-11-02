// Production settings share readable collapsible groups and canonical copy.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {esc} from '../studio/web/model.js';
const js=fs.readFileSync('studio/web/app.js','utf8'),css=fs.readFileSync('studio/web/styles.css','utf8'),guide=JSON.parse(fs.readFileSync('docs/WORKFLOW-CONTROLS-GUIDE.json'));
const fn=js.split('\n').find(x=>x.startsWith('function settingsGroup('));
const build=new Function('esc','settingsText',`${fn};return settingsGroup;`);
for(const locale of ['en','zh-HK','zh-CN','ja']){
 const group=build(esc,k=>guide.presentation[k][locale]);
 for(const [id,key] of [['voice','settingsVoice'],['subtitles','settingsSubtitles'],['opening','settingsOpening'],['advanced','settingsAdvanced']]){
  const open=false,html=group(id,key,'summary','<input data-fixture="retained">',open);
  assert(html.includes(`data-settings-group="${id}" ${open?'open':''}`));
  assert(html.includes(esc(guide.presentation[key][locale]))&&html.includes('data-fixture="retained"'));
  assert(js.includes(`settingsGroup('${id}','${key}'`));
 }
}
assert(!js.includes('class="settings-help"')&&!js.includes("function settingsHelp("));
assert(css.includes('.settings-section strong{font-size:14px;'));
assert(css.includes('.settings-section-body .switch-copy{font-size:14px;'));
assert(css.includes('summary:focus-visible'));
assert(js.includes('<details class="subtitle-catalog">'));
assert(js.includes('data-subtitle="${k}"')&&js.includes('data-engine-track="${k}"'));
console.log('PASS four canonical groups, initial disclosure states, retained menus/switches and readable labels in four languages');
