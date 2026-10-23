import assert from 'node:assert/strict';
import {chapters,articleHTML} from '../studio/web/help.js';
for(const [lang,needle] of [['en','same first-audible retention'],['zh-HK','保留首輪有聲錄音'],['zh-CN','保留首轮有声录音'],['ja','最初の有声音声']]){
 const pages=chapters(lang);for(const page of pages)assert(articleHTML(page).includes('<h1'));
 const recovery=pages.find(p=>p.id==='automatic-recovery');
 assert(articleHTML(recovery).includes(needle),lang);
 assert(recovery.sections.at(-1).body.every(p=>typeof p==='string'&&p.length>150));
}
console.log('Recovery guidance renders in all four interface languages.');
