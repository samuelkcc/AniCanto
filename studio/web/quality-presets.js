// Read-only projections from the shared hardware planner. Do not infer fit from
// a GPU brand, change saved production settings or silently replace an engine.
export function matchingPreset(plan){return (plan?.qualityPresets||[]).find(p=>p.available&&Object.entries(p.requestedModels||{}).every(([k,v])=>v===plan.roles?.[k]))?.id||null;}
export function presetPlan(base,id){
 const p=base?.qualityPresets?.find(p=>p.id===id);
 if(!p?.available||!p.plan?.canDeployModels)throw Error('This quality preset is unavailable on this computer.');
 return {...base,...p.plan,qualityPresets:base.qualityPresets,recommendedPreset:base.recommendedPreset,hardware:p.plan.hardware||base.hardware,inventory:base.inventory,setupReady:!!base.setupReady&&Object.entries(p.requestedModels||{}).every(([k,v])=>v===base.roles?.[k]),qualityPreset:id,requestedModels:{...p.requestedModels}};
}
export function setupParameters(plan){
 if(!plan?.canDeployModels||(plan.qualityPresets?.length&&!plan.qualityPresets.some(p=>p.available)))throw Error('Choose a compatible quality preset before downloading.');
 return {...(plan.setupBackend?{backend:plan.setupBackend}:{}),engine:plan.engine,models:{...(plan.requestedModels||{})},removeOld:false,...(plan.dramaBackend?{dramaBackend:plan.dramaBackend}:{})};
}
export function presetReasons(p){
 const reasons=[];
 for(const code of p.blockers||[]){
  if(code==='insufficient-system-memory')reasons.push('Not enough system memory');
  else if(code==='insufficient-gpu-memory')reasons.push('Not enough dedicated GPU memory');
  else if(code==='insufficient-model-memory')reasons.push('Not enough memory available for models');
  else if(code==='full-drama-gpu-adapter-unavailable')reasons.push('Full Drama 3 GPU support is not available in this Windows build');
  else if(code==='platform-not-supported')reasons.push('Intel Macs are not supported');
  else if(code==='model-license-review-required')reasons.push('This model is awaiting licence verification');
 }
 if(!reasons.length&&!p.available)reasons.push('This combination is not supported on this computer');
 return [...new Set(reasons)];
}
