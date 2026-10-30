import {APPLICATION_USER_GUIDE,APPLICATION_USER_GUIDE_SHA} from './assets/application-user-guide.js';
import {WORKFLOW_GUIDE} from './workflow-guide.js';
import {esc} from './model.js';
export {APPLICATION_USER_GUIDE_SHA};
const applies=(row,platform)=>!row.platforms||row.platforms.includes(platform);
export function manualChapters(platform='desktop'){
 return APPLICATION_USER_GUIDE.chapters.filter(c=>applies(c,platform)).map(c=>({...c,sections:c.sections.filter(s=>applies(s,platform)).flatMap(s=>[
  ...(s.body?.length?[{...s,body:s.body}]:[]),
  ...(s.controlRefs||[]).map(id=>{const item=WORKFLOW_GUIDE.items.find(x=>x.id===id);if(!item)throw Error('Unknown shared control '+id);return {id:s.id+'-'+id,title:item.title,body:[item.body],steps:false};})
 ])}));
}
export const CHAPTERS=manualChapters();
export function resolveChapter(id){return CHAPTERS.find(c=>c.id===id||c.aliases?.includes(id))?.id||id;}
export function chapters(language){const text=v=>v?.[language]??v?.en??'';return CHAPTERS.map((c,i)=>({...c,number:i+1,title:text(c.title),summary:text(c.summary),sections:c.sections.map(s=>({...s,title:text(s.title),body:s.body.map(text)}))}));}
export function searchChapters(rows,query){const words=String(query).normalize('NFKC').toLocaleLowerCase().trim().split(/\s+/u).filter(Boolean);return rows.filter(c=>{const text=[c.title,c.summary,...c.sections.flatMap(s=>[s.title,...s.body])].join(' ').normalize('NFKC').toLocaleLowerCase();return words.every(w=>text.includes(w));});}
export function articleHTML(c){return `<div class="help-eyebrow">ANICANTO / ${String(c.number).padStart(2,'0')}</div><h1 id="help-article-title">${esc(c.title)}</h1><p class="help-lead">${esc(c.summary)}</p>${c.sections.map(s=>`<section class="help-section"><h2>${esc(s.title)}</h2>${s.steps?`<ol>${s.body.map(p=>`<li>${esc(p)}</li>`).join('')}</ol>`:s.body.map(p=>`<p>${esc(p)}</p>`).join('')}</section>`).join('')}`;}
