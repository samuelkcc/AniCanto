// Build 291 desktop notice: the source-language badge states the evidence the app actually had.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {esc} from '../studio/web/model.js';
import {icon} from '../studio/web/icons.js';
import {translate} from '../studio/web/i18n.js';
import {projectWarning} from '../studio/web/workflow-text.js';

const source=fs.readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
// Each template is one top-level function: it ends at its own closing brace or at the next top-level declaration.
const body=name=>{const start=source.indexOf(`function ${name}(`);assert(start>=0,`${name}: missing`);const rest=source.slice(start);
 const closes=[...rest.matchAll(/^\}/gm)].filter(match=>match.index>0).map(match=>match.index+1);
 const next=[...rest.matchAll(/^(?=function |const |let )/gm)].filter(match=>match.index>0).map(match=>match.index);
 const stops=[...closes,...next];
 assert(stops.length,`${name}: unterminated`);return rest.slice(0,Math.min(...stops))};
const names=['previewNotices','previewNoticeBadge','queueNoticeChip'];
const literal=source.match(/const SOURCE_LANGUAGE_NAMES=(\{[^}]*\});/);
assert(literal,'app.js: SOURCE_LANGUAGE_NAMES is missing');
const SOURCE_LANGUAGE_NAMES=new Function(`return ${literal[1]}`)();
const shell=row=>new Function('d',`const {esc,icon,t,projectWarning,SOURCE_LANGUAGE_NAMES,row}=d;
${names.map(body).join('\n')}
return {previewNotices,previewNoticeBadge,queueNoticeChip}`)({
 esc,icon,t:text=>translate(text,row.language),projectWarning,SOURCE_LANGUAGE_NAMES,row:()=>row});

const LISTEN='Speech recognition could not run on this computer, so this app used Japanese. Install the speech model in Model centre, then check the language again.';
const CAPTION='Speech recognition could not confirm the spoken language, so it uses Japanese for timing. The dialogue words come from the subtitles inside this file.';
const BLANK='No source language was found, so this app is working in Japanese. Check it before export.';
const cases=[
 // A speech model that could not run must not read as "nothing was found".
 {id:'listen',language:'zh-HK',sourcePreflight:{assumedSourceLanguage:true,listenFailure:'Speech model folder is empty'},key:LISTEN,extra:''},
 // Readable captions inside the file carry the dialogue words, so the badge says so and names that language.
 {id:'caption',language:'zh-HK',sourcePreflight:{assumedSourceLanguage:true,listenFailure:'',subtitleLanguage:'zh',subtitleMethod:'subtitle-track-tag'},key:CAPTION,extra:' · '},
 // With no audio evidence and no captions, the older sentence still applies.
 {id:'blank',language:'zh-HK',sourcePreflight:{assumedSourceLanguage:true},key:BLANK,extra:''}];

for(const language of ['en','zh-HK','zh-CN','ja']){
 for(const item of cases){
  const row={id:`row-${item.id}`,video:`/queue/${item.id}.mkv`,status:'completed',deliveryState:'exported',sourcePreflight:item.sourcePreflight,language};
  const api=shell(row);
  const notes=api.previewNotices(row);
  assert.equal(notes.length,1,`${language}/${item.id}: ${JSON.stringify(notes)}`);
  assert.equal(notes[0].kind,'info',`${language}/${item.id}: the language note is information, not a fault`);
  const text=translate(item.key,language);
  assert.equal(notes[0].text,text+item.extra+(item.id==='caption'?translate('Chinese',language):''),`${language}/${item.id}: ${notes[0].text}`);
  if(language!=='en')assert.notEqual(text,item.key,`${language}/${item.id}: copy is not translated`);
  // The badge is a wide information band, and the video card keeps no chip for it.
  const badge=api.previewNoticeBadge(row);
  assert(badge.includes('class="preview-notice info-only"'),`${language}/${item.id}: ${badge}`);
  assert(badge.includes(text)&&badge.includes('preview-notice-line info'),`${language}/${item.id}: ${badge}`);
  assert.equal(api.queueNoticeChip(row),'',`${language}/${item.id}: an information line never raises a card chip`);
 }
 // Every written-language name the caption note can show is a translated copy key.
 for(const name of ['Chinese','Cantonese','Japanese','English','Korean'])assert(Object.values(SOURCE_LANGUAGE_NAMES).includes(name),`${language}: ${name}`);
 if(language!=='en')assert.notEqual(translate('Chinese',language),'Chinese',`${language}: the caption language name is not translated`);
}
// A video with a real detection carries no language note at all.
const detected={id:'row-ok',video:'/queue/ok.mkv',status:'completed',deliveryState:'exported',sourcePreflight:{assumedSourceLanguage:false,languageEvidence:'audio-samples-majority'},language:'zh-HK'};
assert.equal(shell(detected).previewNotices(detected).length,0,'a majority reading is not a fallback notice');
console.log('Three source-language notice states passed in four interface languages.');
