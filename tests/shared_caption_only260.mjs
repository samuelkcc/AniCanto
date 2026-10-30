import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {chapters,searchChapters,articleHTML,manualChapters} from '../studio/web/help.js';
const guide=JSON.parse(fs.readFileSync('docs/APPLICATION-USER-GUIDE.json')),controls=JSON.parse(fs.readFileSync('docs/WORKFLOW-CONTROLS-GUIDE.json')),receipt=JSON.parse(fs.readFileSync('.build/timing260/canonical-copy.json'));
assert.equal(guide.revision,'application-user-guide-13-caption-only-hk');assert.equal(controls.revision,'workflow-controls-guide-19-caption-only-hk');
const ids=new Set(controls.items.map(x=>x.id));for(const c of guide.chapters)for(const s of c.sections)for(const ref of s.controlRefs)assert(ids.has(ref),ref);
for(const platform of ['desktop','ipad','iphone']){const chapter=manualChapters(platform).find(c=>c.id==='subtitles');assert(chapter.sections.some(s=>s.id==='caption-only-no-dialogue-captionOnlyNoDialogue'));assert(chapter.sections.some(s=>s.id==='hong-kong-contextual-wording-hongKongContextualWording'));}
for(const locale of guide.locales){const chapter=chapters(locale).find(c=>c.id==='subtitles'),caption=chapter.sections.find(s=>s.id==='caption-only-no-dialogue-captionOnlyNoDialogue'),wording=chapter.sections.find(s=>s.id==='hong-kong-contextual-wording-hongKongContextualWording');assert(caption.body[0].includes('iPad'));assert(wording.body[0].includes('小說'));assert(wording.body[0].includes('分分鐘'));assert(searchChapters(chapters(locale),'小說').some(c=>c.id==='subtitles'));assert(articleHTML(chapter).includes('caption')||locale!=='en');}
for(const [name,key] of [['docs/APPLICATION-USER-GUIDE.json','manualSHA256'],['docs/WORKFLOW-CONTROLS-GUIDE.json','controlSHA256']])assert.equal(crypto.createHash('sha256').update(fs.readFileSync(name)).digest('hex'),receipt[key]);
const app=fs.readFileSync('studio/web/app.js','utf8');assert(app.includes("settingSwitch('skipNonDialogueCaptions','Non-dialogue captions only',s.skipNonDialogueCaptions!==false"));assert(!app.includes("settingSwitch('skipNonDialogueCaptions','Non-dialogue captions only',Boolean"));
console.log('PASS guide13/control19 references, four-language Help/search, mobile-pending scope and default-on production control.');
