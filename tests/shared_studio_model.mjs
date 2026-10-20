import assert from 'node:assert/strict';
import {mergeJourney,themeAssets,THEMES,captionAt,takeAt,esc,visibleMilestones,PHASES} from '../studio/web/model.js';
let journey=mergeJourney(null,{progress:.8},'attempt-A');
journey=mergeJourney(journey,{progress:.5},'attempt-A');assert.equal(journey.progress,.8);
journey=mergeJourney(journey,{progress:.1},'attempt-B');assert.equal(journey.progress,.1);
for(const key of Object.keys(THEMES))for(const variant of [1,2,3,4]){const assets=themeAssets(key,variant);assert.equal(assets.key,key);assert(assets.cover.endsWith(`welcome-${key}-${variant}.png`));assert.equal(assets.color,THEMES[key]);assert.match(assets.runner,new RegExp(`pet-${key}\\.png\\?v=[a-f0-9]{12}$`));}
const cues=[{start:1,end:2,text:'係我呀。',english:'It is me.'},{start:2,end:3,text:'再見。',english:'Goodbye.'}];
assert.equal(captionAt(cues,2,'yue'),'再見。');assert.equal(captionAt(cues,2,'en'),'Goodbye.');assert.equal(captionAt(cues,3,'en'),'');
assert.equal(takeAt([{index:2,engine:'drama3',language:'yue',audio:'old'},{index:2,engine:'drama3',language:'yue',audio:'new'}],1,'drama3','yue').audio,'new');
assert.equal(takeAt([{index:1,engine:'cosyvoice3',language:'yue'}],0,'drama3','yue'),undefined);
assert.equal(esc('<img src=x onerror="x">'),'&lt;img src=x onerror=&quot;x&quot;&gt;');
console.log('Shared progress, bilingual captions, exact-engine takes and nine theme contracts passed.');

assert.deepEqual(visibleMilestones(PHASES.map(id=>({id})),true).map(r=>r.id),['prepare','recognition','translation','voice','export']);
