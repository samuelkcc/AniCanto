// AniCanto workbench presentation. Independent implementation.
export function activity(row,now=Date.now()/1000){
 const at=Number(row?.lastEventAt),progress=Number(row?.lastProgressAt);
 return {known:at>0,quiet:row?.status==='running'&&at>0&&now-at>120,lastEvent:at>0?Math.max(0,now-at):null,lastProgress:progress>0?Math.max(0,now-progress):null};
}
export function reviewMatches(item,filter){
 if(filter==='all')return true;
 if(filter==='checked'||filter==='deferred')return item.triage===filter;
 if(filter==='issues')return item.triage!=='checked'&&item.triage!=='deferred';
 return item.category===filter&&item.triage!=='checked';
}
export function staleFor(snapshot,index,engine,language){return (snapshot.staleRecordings||[]).find(x=>x.index===index+1&&x.engine===engine&&x.language===language);}
