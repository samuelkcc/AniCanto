import assert from 'node:assert/strict';
import {translate} from '../studio/web/i18n.js';
import {workflowNoticesHTML,performanceLabel} from '../studio/web/review-notices.js';
import {performanceHTML} from '../studio/web/workflow-dialogs.js';
import {reviewPage} from '../studio/web/review-page.js';
for(const language of ['en','zh-HK','zh-CN','ja']){
 const t=x=>translate(x,language);
 const n={title:'Subtitle source alignment',message:'Shared subtitle content is assigned to a main spoken turn. Continuation fragments avoid repeating the same translation; this alone is not missing dubbing.',detail:"{'suspectSegments':35,'unconfirmedSegments':34}",metrics:[{label:'Continuation fragments',value:18}]};
 const html=workflowNoticesHTML([n],t);assert(!html.includes('suspectSegments'));assert(!html.includes('<pre>'));assert(html.includes('18'));
 if(language!=='en'){assert(!html.includes('Subtitle source alignment'));assert(!html.includes('Continuation fragments'));}
 const button=()=>'<button>play</button>',snapshot={performance:{keptRanges:2,notes:[{start:1,end:2,label:'sigh',reason:'',id:'x'}]}};
 const p=performanceHTML(snapshot,t,button,false);assert(!p.includes('· sigh'));assert(p.includes('<details class="performance-list">'));assert(!p.includes('details open'));
 const full=reviewPage({snapshot:{...snapshot,workflowNotices:[n],review:{cues:[]},reviewState:{workflowNotices:1}},t,button,engineName:x=>x,active:false,sourceLanguage:'ja'});assert(!full.includes('suspectSegments'));assert(!full.includes('<pre>'));
 assert.equal(performanceLabel('screaming'),'Scream');assert.equal(performanceLabel('unknown-model-code'),'Uncertain reaction');
}
console.log('PASS four-language review notices, collapsed reactions, no raw diagnostics in main report');
