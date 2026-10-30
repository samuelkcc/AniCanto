import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {CHAPTERS,chapters,manualChapters,resolveChapter,searchChapters,articleHTML,APPLICATION_USER_GUIDE_SHA} from '../studio/web/help.js';
const src=fs.readFileSync(new URL('../docs/APPLICATION-USER-GUIDE.json',import.meta.url));
const guide=JSON.parse(src),controls=JSON.parse(fs.readFileSync(new URL('../docs/WORKFLOW-CONTROLS-GUIDE.json',import.meta.url)));
assert.equal(APPLICATION_USER_GUIDE_SHA,crypto.createHash('sha256').update(src).digest('hex'));
assert.equal(fs.readFileSync(new URL('../studio/web/assets/application-user-guide.json',import.meta.url)).compare(src),0);
const ids=new Set();let sections=0,paragraphs=0,refs=0;
for(const c of guide.chapters){assert(!ids.has(c.id));ids.add(c.id);for(const lang of guide.locales){assert(c.title[lang]);assert(c.summary[lang]);}for(const s of c.sections){sections++;for(const lang of guide.locales)assert(s.title[lang]);for(const p of s.body){paragraphs++;for(const lang of guide.locales)assert.equal(typeof p[lang],'string');}for(const id of s.controlRefs){assert(controls.items.some(i=>i.id===id));refs++;}}}
for(const locale of guide.locales){const rows=chapters(locale);assert.equal(rows.length,CHAPTERS.length);for(const c of rows){assert(c.title&&c.summary&&c.sections.length);assert(!articleHTML(c).includes('undefined'));for(const s of c.sections)assert(s.body.every(x=>typeof x==='string'&&x.length));}assert(searchChapters(rows,locale==='en'?'fallback':locale==='ja'?'字幕':'字幕').length);}
for(const id of ['work85','automatic-recovery','safe-capacity89','report90','subtitle84','workflow80'])assert(CHAPTERS.some(c=>c.id===resolveChapter(id)));
const desktopText=JSON.stringify(manualChapters('desktop'));assert(!desktopText.includes('Purchase and free features'));assert(!desktopText.includes('Translate and record one line'));assert(!desktopText.includes('reading-mobile'));
console.log(JSON.stringify({chapters:guide.chapters.length,desktopChapters:CHAPTERS.length,sections,paragraphs,controlRefs:refs,locales:guide.locales,exactSourceHash:APPLICATION_USER_GUIDE_SHA,aliases:true,platformFilter:true}));
