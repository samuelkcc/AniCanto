// Pointer-based sorting avoids the native desktop file-drop bridge. Only the
// handle starts a move; clicking a title still selects the project as before.
export function orderControls(rows,index,{t,esc,icon}){
 const id=esc(rows[index].id),control=(action,label,name,disabled=false)=>`<button class="queue-order-button" data-action="${action}" data-value="${id}" aria-label="${esc(t(label))}" title="${esc(t(label))}" ${disabled?'disabled':''}>${icon(name)}</button>`;
 return `<div class="queue-order-controls"><button class="queue-drag-handle" data-queue-handle="${id}" aria-label="${esc(t('Drag to reorder'))}" title="${esc(t('Drag to reorder'))}">${icon('grip')}</button>${control('queue-up','Move up','up',index===0)}${control('queue-down','Move down','down',index===rows.length-1)}</div>`;
}
export function installQueueOrder({move,step,updated,error}){
 let drag=null,saving=false,blockedUntil=0,frame=0,resolveIdle=null;
 let idle=Promise.resolve();
 const startBusy=()=>{idle=new Promise(resolve=>resolveIdle=resolve)};
 const endBusy=()=>{saving=false;const resolve=resolveIdle;resolveIdle=null;try{updated()}finally{resolve?.()}};
 const save=async(work)=>{saving=true;try{await work()}catch(e){error(e)}finally{endBusy()}};
 const marker=document.createElement('div');marker.className='queue-drop-marker';marker.hidden=true;marker.setAttribute('aria-hidden','true');
 function mark(){
  if(!drag?.moved)return;
  const {list,row,y}=drag;
  const rows=[...list.querySelectorAll('[data-queue-id]')].filter(r=>r!==row);
  const target=rows.find(r=>y<r.getBoundingClientRect().top+r.getBoundingClientRect().height/2);
  drag.beforeID=target?.dataset.queueId??null;
  const bounds=list.getBoundingClientRect(),rect=(target||rows.at(-1)||row).getBoundingClientRect();
  const edge=target?rect.top:rect.bottom;
  Object.assign(marker.style,{left:`${rect.left}px`,width:`${rect.width}px`,top:`${Math.max(bounds.top,Math.min(bounds.bottom,edge))}px`});
  marker.hidden=false;
 }
 function animate(){
  if(!drag)return;
  if(drag.moved){const rect=drag.scroller.getBoundingClientRect(),margin=45;
   const speed=drag.y<rect.top+margin?-Math.min(14,(rect.top+margin-drag.y)/3):drag.y>rect.bottom-margin?Math.min(14,(drag.y-rect.bottom+margin)/3):0;
   if(speed)drag.scroller.scrollTop+=speed;mark();
  }
  frame=requestAnimationFrame(animate);
 }
 function finish(cancelled=false){
  if(!drag)return;
  const d=drag;drag=null;cancelAnimationFrame(frame);marker.remove();marker.hidden=true;
  d.row.classList.remove('queue-dragging');document.body.classList.remove('queue-reordering');
  if(d.handle.hasPointerCapture(d.pointerId))d.handle.releasePointerCapture(d.pointerId);
  if(d.moved)blockedUntil=performance.now()+300;
  const next=d.row.nextElementSibling?.dataset.queueId??null;
  if(!cancelled&&d.moved&&d.beforeID!==next)save(()=>move(d.id,d.beforeID));
  else endBusy();
 }
 document.addEventListener('pointerdown',e=>{
  const handle=e.target.closest('[data-queue-handle]');if(!handle||e.button!==0||saving||drag)return;
  const row=handle.closest('[data-queue-id]'),list=row?.closest('[data-queue-list]');if(!list||list.querySelectorAll('[data-queue-id]').length<2)return;
  startBusy();drag={handle,row,list,id:row.dataset.queueId,pointerId:e.pointerId,x:e.clientX,y:e.clientY,startY:e.clientY,moved:false,scroller:list.closest('.shelf,.page')||list};
  handle.focus({preventScroll:true});handle.setPointerCapture(e.pointerId);e.preventDefault();
  document.body.append(marker);frame=requestAnimationFrame(animate);
 });
 document.addEventListener('pointermove',e=>{
  if(!drag||e.pointerId!==drag.pointerId)return;
  drag.y=e.clientY;
  if(!drag.moved&&Math.hypot(e.clientX-drag.x,e.clientY-drag.startY)>5){drag.moved=true;drag.row.classList.add('queue-dragging');document.body.classList.add('queue-reordering');}
  mark();e.preventDefault();
 },{passive:false});
 document.addEventListener('pointerup',e=>{if(drag&&e.pointerId===drag.pointerId)finish()});
 document.addEventListener('pointercancel',()=>finish(true));
 window.addEventListener('blur',()=>finish(true));
 document.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&drag){e.preventDefault();e.stopImmediatePropagation();finish(true);return;}
  const handle=e.target.closest('[data-queue-handle]');
  if(handle&&['ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();if(!saving&&!drag){startBusy();save(()=>step(handle.dataset.queueHandle,e.key==='ArrowUp'?-1:1));}}
 },true);
 document.addEventListener('click',e=>{
  if(e.target.closest('[data-queue-handle]')||(performance.now()<blockedUntil&&e.target.closest('[data-queue-id]')&&!e.target.closest('button'))){e.preventDefault();e.stopImmediatePropagation();}
 },true);
 return {get busy(){return !!drag||saving},idle:()=>idle,run:async(work)=>{if(drag||saving)return;startBusy();await save(work)}};
}
