// Preserve the item being read while live evidence changes, including playback.
// Anchor by stable issue ID; array positions change as automatic repairs finish.
export function captureReviewViewport(root=document){
 const page=root.querySelector('.page[data-page="review"]');if(!page)return null;
 const top=page.getBoundingClientRect().top,cards=[...page.querySelectorAll('[data-issue-id]')];
 const visible=cards.filter(el=>el.getBoundingClientRect().bottom>top);
 const active=document.activeElement,card=active?.closest('[data-issue-id]');
 const control=active?.matches('select')?(active.hasAttribute('data-review-choice')?'[data-review-choice]':'[data-review-recording]'):active?.dataset.action?`[data-action="${active.dataset.action}"]${active.dataset.source?`[data-source="${active.dataset.source}"]`:''}`:null;
 return {project:page.dataset.project,top:page.scrollTop,left:page.scrollLeft,
  anchors:visible.map(el=>({id:el.dataset.issueId,offset:el.getBoundingClientRect().top-top})),
  cards:cards.map(el=>({id:el.dataset.issueId,details:[...el.querySelectorAll('details')].map(d=>d.open),values:[...el.querySelectorAll('select')].map(s=>s.value)})),
  focus:card&&control?{id:card.dataset.issueId,control}:null};
}
export function restoreReviewViewport(saved,root=document){
 const page=root.querySelector('.page[data-page="review"]');if(!saved||!page||saved.project!==page.dataset.project)return;
 const cards=new Map([...page.querySelectorAll('[data-issue-id]')].map(el=>[el.dataset.issueId,el]));
 for(const old of saved.cards){const el=cards.get(old.id);if(!el)continue;
  [...el.querySelectorAll('details')].forEach((d,i)=>{d.open=old.details[i]===true;});
  [...el.querySelectorAll('select')].forEach((s,i)=>{if([...s.options].some(o=>o.value===old.values[i]))s.value=old.values[i];});
 }
 const focus=saved.focus&&cards.get(saved.focus.id)?.querySelector(saved.focus.control);if(focus&&!focus.disabled)focus.focus({preventScroll:true});
 page.scrollLeft=saved.left;page.scrollTop=saved.top;
 const anchor=saved.anchors.find(a=>cards.has(a.id));
 if(anchor)page.scrollTop+=cards.get(anchor.id).getBoundingClientRect().top-page.getBoundingClientRect().top-anchor.offset;
}
