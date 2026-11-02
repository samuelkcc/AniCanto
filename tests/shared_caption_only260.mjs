import assert from 'node:assert/strict';
import fs from 'node:fs';
import {chapters,searchChapters,articleHTML,manualChapters} from '../studio/web/help.js';
const guide=JSON.parse(fs.readFileSync('docs/APPLICATION-USER-GUIDE.json')),controls=JSON.parse(fs.readFileSync('docs/WORKFLOW-CONTROLS-GUIDE.json')),contract=JSON.parse(fs.readFileSync('docs/RECOVERY-WORKFLOW-CONTRACT.json'));
// The build 260 receipt pinned one guide and control revision pair. Those documents move with every later copy change, so
// the durable check is the mirror in the shared contract plus the copy that ships inside the app.
const mirror=contract.applicationUserGuide;assert(mirror,'the shared contract needs an applicationUserGuide entry');
assert.equal(mirror.revision,guide.revision,'docs/RECOVERY-WORKFLOW-CONTRACT.json must name the current manual revision');
assert.equal(mirror.controlGuideRevision,controls.revision,'docs/RECOVERY-WORKFLOW-CONTRACT.json must name the current control guide revision');
assert(fs.readFileSync('studio/web/assets/application-user-guide.json').compare(fs.readFileSync('docs/APPLICATION-USER-GUIDE.json'))===0,'the shipped manual copy must match the canonical manual');
assert(fs.readFileSync('studio/web/assets/workflow-controls-guide.js','utf8').includes(`"revision": "${controls.revision}"`),'the shipped control guide copy must carry the canonical revision');
const ids=new Set(controls.items.map(x=>x.id));for(const c of guide.chapters)for(const s of c.sections)for(const ref of s.controlRefs)assert(ids.has(ref),ref);
for(const platform of ['desktop','ipad','iphone']){const chapter=manualChapters(platform).find(c=>c.id==='subtitles');assert(chapter.sections.some(s=>s.id==='caption-only-no-dialogue-captionOnlyNoDialogue'));assert(chapter.sections.some(s=>s.id==='hong-kong-contextual-wording-hongKongContextualWording'));}
for(const locale of guide.locales){const chapter=chapters(locale).find(c=>c.id==='subtitles'),caption=chapter.sections.find(s=>s.id==='caption-only-no-dialogue-captionOnlyNoDialogue'),wording=chapter.sections.find(s=>s.id==='hong-kong-contextual-wording-hongKongContextualWording');assert(caption.body[0].includes('iPad'));assert(wording.body[0].includes('小說'));assert(wording.body[0].includes('分分鐘'));assert(searchChapters(chapters(locale),'小說').some(c=>c.id==='subtitles'));assert(articleHTML(chapter).includes('caption')||locale!=='en');}
const app=fs.readFileSync('studio/web/app.js','utf8');assert(app.includes("settingSwitch('skipNonDialogueCaptions',controlCopy('captionOnlyNoDialogue',state.language,'title'),s.skipNonDialogueCaptions===true"));
console.log(`PASS ${guide.revision}/${controls.revision} mirror alignment, shipped copy, four-language Help/search and default-off opt-in caption control.`);
