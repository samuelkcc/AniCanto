// One user-initiated session. Consume before launching so a failed or duplicated
// completion event cannot repeatedly retry the same movie.
export const pendingVideos=(rows,includeAttention=false)=>rows.filter(r=>['waiting','paused',...(includeAttention?['attention']:[])].includes(r.status));
export class ConversionQueue {
 constructor(){this.stop()}
 begin(rows,{selected,all=false,includeAttention=false}={}){
  this.enabled=all;this.includeAttention=includeAttention;this.attempted=new Set();this.explicit=new Set();
  this.pending=(all?rows.filter(r=>['waiting','paused',...(includeAttention?['attention']:[])].includes(r.status)):[]).map(r=>r.id);
  if(includeAttention)for(const r of rows)if(r.status==='attention')this.explicit.add(r.id);
  const chosen=rows.find(r=>r.id===selected);
  if(chosen&&(!all||chosen.status==='paused'||chosen.status==='attention')){
   this.pending=[chosen.id,...this.pending.filter(id=>id!==chosen.id)];
   this.explicit.add(chosen.id);
  }
 }
 restore(id,{includeAttention=false}={}){this.enabled=true;this.includeAttention=includeAttention;this.attempted=new Set([id]);this.explicit=new Set();this.pending=[]}
 // A move only changes future work. The current/attempted IDs stay consumed.
 reorder(rows){const rank=new Map(rows.map((r,i)=>[r.id,i]));this.pending.sort((a,b)=>(rank.get(a)??Infinity)-(rank.get(b)??Infinity));}
 next(rows){
  if(this.enabled)for(const r of pendingVideos(rows,this.includeAttention))if(!this.pending.includes(r.id)&&!this.attempted.has(r.id)){this.pending.push(r.id);if(r.status==='attention')this.explicit.add(r.id);}
  while(this.pending.length){
   const id=this.pending.shift();
   const row=rows.find(r=>r.id===id);
   if(this.attempted.has(id)||!row||row.status==='running')continue;
   if(!this.explicit.has(id)&&!['waiting','paused'].includes(row.status))continue;
   this.attempted.add(id);return id;
  }
  return null;
 }
 stop(){this.enabled=false;this.includeAttention=false;this.pending=[];this.attempted=new Set();this.explicit=new Set()}
}
