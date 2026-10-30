import assert from 'node:assert/strict';
globalThis.matchMedia=()=>({matches:false,addEventListener(){}});globalThis.document={addEventListener(){}};
const {activityPoint,REST_HEAD,REST_HAIR,restHeadWeight}=await import('../studio/web/assistant-activity-motion.js');
for(const [theme,[cx,cy]] of Object.entries(REST_HEAD)){
 const a=[cx-.025,cy+.055],b=[cx+.025,cy+.055],times=[0,.5,1,2,3,4,6,8];assert.equal(restHeadWeight(...a,theme),1);assert.equal(restHeadWeight(...b,theme),1);
 const actual=t=>activityPoint(...a,t,4,false,theme),base=actual(0);assert(times.some(t=>Math.hypot(...actual(t).map((v,i)=>v-base[i]))>.001),'No head breathing');
 for(const t of times){const p=actual(t),q=activityPoint(...b,t,4,false,theme);const distance=Math.hypot((p[0]-q[0])/.92,(p[1]-q[1])/.90);assert(Math.abs(distance-.05)<1e-10,'Face proportions change');assert(Math.hypot(...p.map((v,i)=>v-base[i]))<.007,'Excessive rest motion');}
 for(const xy of [[.10,.85],[.8,.9],[.5,.95]])for(const t of times)assert.deepEqual(activityPoint(...xy,t,4,false,theme),activityPoint(...xy,0,4,false,theme),'Furniture or feet move');
 const hair=REST_HAIR[theme].slice(0,2);assert(times.some(t=>JSON.stringify(activityPoint(...hair,t,4,false,theme))!==JSON.stringify(activityPoint(...hair,0,4,false,theme))));
}
console.log('PASS nine rest poses: breathing and hair motion; rigid face geometry, bounded movement and fixed furniture');
