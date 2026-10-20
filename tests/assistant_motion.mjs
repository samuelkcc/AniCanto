import assert from 'node:assert/strict';
globalThis.matchMedia=()=>({matches:false,addEventListener(){}});globalThis.document={addEventListener(){}};
const {joints,deform,CYCLE}=await import('../studio/web/assistant-motion.js');const {ASSISTANT_RIGS}=await import('../studio/web/assets/assistant-rigs.js');
for(const rig of Object.values(ASSISTANT_RIGS)){
 for(const uv of [[rig.anchorX,.65],[rig.anchorX-.12,1]]){const rest=deform(...uv,joints(0),rig);for(let t=0;t<12;t+=.1){const xy=deform(...uv,joints(t),rig);assert(Math.hypot(xy[0]-rest[0],xy[1]-rest[1])<1e-10,'Body/left sole anchor moves');}}
 for(let v=0;v<=1;v+=.05)for(let u=0;u<=1;u+=.05){const a=deform(u,v,joints(0),rig),b=deform(u,v,joints(CYCLE),rig);assert(Math.hypot(a[0]-b[0],a[1]-b[1])<1e-10,'Cycle seam');let previous=a;for(let t=.1;t<=12;t+=.1){const next=deform(u,v,joints(t),rig);assert(Math.hypot(next[0]-previous[0],next[1]-previous[1])<.015,'Discontinuous pose');assert(next[0]>.02&&next[0]<.98&&next[1]>.01&&next[1]<.99,'Limb leaves its canvas');previous=next;}}
 const handA=deform(.25,.48,joints(.5),rig),handB=deform(.25,.48,joints(1.5),rig);assert(Math.hypot(handA[0]-handB[0],handA[1]-handB[1])>.004,'No actual hand articulation');
}
console.log('Nine aligned continuous rigs: planted body/foot anchors, continuous cycle, actual hand articulation and full bounds passed.');
