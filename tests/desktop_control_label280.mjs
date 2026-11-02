// Build 280 desktop control label: the auto-approve switch shows its own name, with no platform prefix and no hover hint.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {esc} from '../studio/web/model.js';

const guide=JSON.parse(fs.readFileSync(new URL('../docs/WORKFLOW-CONTROLS-GUIDE.json',import.meta.url),'utf8'));
const item=guide.items.find(entry=>entry.id==='autoApproveSourceLanguage');
assert(item,'control guide needs the autoApproveSourceLanguage item');

// The label comes from the guide title, so the prefix must be gone in every locale and no locale may gain one.
const expected={'zh-HK':'接納偵測語言','zh-CN':'接受检测语言',en:'Accept detected language',ja:'検出した言語を使う'};
for(const [locale,text] of Object.entries(expected))assert.equal(item.title[locale],text,`${locale}: ${item.title[locale]}`);
for(const locale of Object.keys(item.title))assert(!/^(桌面|デスクトップ|Desktop)[:：]/.test(item.title[locale]),`${locale}: platform prefix must not return`);
// The guide gains a new revision with every copy change, so this receipt checks that the label
// fix revision is still in force instead of pinning one number that later copy changes break.
assert(/^workflow-controls-guide-(\d+)-/.test(guide.revision),guide.revision);
assert(Number(/^workflow-controls-guide-(\d+)-/.exec(guide.revision)[1])>=36,`${guide.revision}: build 280 label copy must stay in the guide`);
// The Help explanation stays, so the switch keeps a full definition in the Help centre.
for(const locale of Object.keys(expected)){assert(item.body[locale].length>80,`${locale}: body copy intact`);assert.notEqual(item.body[locale],item.title[locale],`${locale}: body stays separate from the label`);}
assert(!JSON.stringify(item.title).includes('桌面'), 'no locale keeps the Chinese prefix');

// Render the real template from app.js, with the guide copy and the same switch markup the panel uses.
const source=fs.readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
const body=name=>{const start=source.indexOf(`function ${name}(`);assert(start>=0,`${name}: missing`);const rest=source.slice(start);
 const closes=[...rest.matchAll(/^\}/gm)].filter(match=>match.index>0).map(match=>match.index+1);
 const next=[...rest.matchAll(/^(?=function |const |let )/gm)].filter(match=>match.index>0).map(match=>match.index);
 const stops=[...closes,...next];assert(stops.length,`${name}: unterminated`);return rest.slice(0,Math.min(...stops))};
const names=['settingsText','sourceLanguageApprovalControl','productionScopeControl'];
const controlCopy=(id,language,part='body')=>{const found=guide.items.find(entry=>entry.id===id);return found?.[part]?.[language]||found?.[part]?.en||''};
const groupStub="const switchGroup=(label,html,extraClass='')=>`<section class=\"switch-group${extraClass?' '+extraClass:''}\"><h4 class=\"switch-group-label\">${label}</h4><div class=\"switch-list\">${html}</div></section>`;";
const shell=(language,settings={},individual=false)=>new Function('d',`const {esc,t,controlCopy,panelCopy,settingSwitch,productionConfig,individualProduction,state,active,row}=d;
${groupStub}
${names.map(body).join('\n')}
return {sourceLanguageApprovalControl,productionScopeControl}`)({
 esc,
 t:text=>text,
 controlCopy,
 panelCopy:(key,language)=>guide.presentation[key]?.[language]||key,
 settingSwitch:(key,label,value,extra='')=>`<label class="setting-switch"><span class="switch-copy">${esc(label)}</span><span class="switch-control"><input type="checkbox" role="switch" data-setting="${key}" ${value?'checked':''} ${extra}></label>`,
 productionConfig:()=>settings,individualProduction:()=>individual,state:{language},active:false,row:()=>({id:'row-1'})});

for(const language of Object.keys(expected)){
 const switchHtml=shell(language).sourceLanguageApprovalControl();
 assert(switchHtml.includes(`<span class="switch-copy">${esc(expected[language])}</span>`),`${language}: label: ${switchHtml}`);
 assert(!switchHtml.includes('title="'),`${language}: hover hint must be gone: ${switchHtml}`);
 assert(switchHtml.includes(`aria-label="${esc(expected[language])}"`),`${language}: accessible name`);
 assert(!switchHtml.includes(expected[language].slice(0,2)+':')&&!switchHtml.includes('：'),`${language}: no prefix in the rendered label`);
 // Scope selection and source-language approval now belong to separate named groups.
 const panel=shell(language,{},true).productionScopeControl();
 assert(panel.includes('<select data-setting="productionScopeGlobal"'),`${language}: named scope menu`);
 assert(!panel.includes('data-setting="autoApproveSourceLanguage"'),`${language}: source control belongs to source group`);
 assert(!panel.includes('title="'),`${language}: no hover hint in the scope panel: ${panel}`);
}

// The guide copy that ships inside the app must be the canonical file, byte for byte.
assert(fs.readFileSync(new URL('../studio/web/assets/workflow-controls-guide.json',import.meta.url)).compare(fs.readFileSync(new URL('../docs/WORKFLOW-CONTROLS-GUIDE.json',import.meta.url)))===0,'shipped control guide copy must match the canonical file');

console.log('PASS build280 auto-approve switch: unprefixed label in four locales, no hover hint, accessible name kept, with a named scope menu');
