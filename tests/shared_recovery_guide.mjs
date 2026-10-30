import assert from 'node:assert/strict';
import {chapters,articleHTML,resolveChapter} from '../studio/web/help.js';
import {WORKFLOW_GUIDE} from '../studio/web/workflow-guide.js';
import {esc} from '../studio/web/model.js';
for(const lang of ['en','zh-HK','zh-CN','ja']){
 const pages=chapters(lang);for(const page of pages)assert(articleHTML(page).includes('<h1'));
 const recovery=pages.find(p=>p.id===resolveChapter('automatic-recovery')),html=articleHTML(recovery);
 for(const id of ['failedVoiceFallback','missingAudio','autoRepair','durationLimit','resume']){
  const item=WORKFLOW_GUIDE.items.find(i=>i.id===id);assert(item,id);assert(pages.some(p=>articleHTML(p).includes(esc(item.body[lang]))),`${lang}: ${id}`);
 }
 assert(recovery.sections.every(s=>s.body.every(p=>typeof p==='string'&&p.trim())),lang);
}
console.log('Recovery Help uses the exact shared fallback, missing, repair, duration and resume rules in four languages.');
