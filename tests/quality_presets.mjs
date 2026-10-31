import assert from 'node:assert/strict';
import fs from 'node:fs';
const {matchingPreset,presetPlan,setupParameters,presetReasons}=await import('data:text/javascript;base64,'+fs.readFileSync('studio/web/quality-presets.js').toString('base64'));
const roles={text:'small-text',voice:'gpt'},preset={id:'balanced',available:true,requestedModels:roles,plan:{canDeployModels:true,engine:'gpt',roles,modelDownloadBytes:42}};
const base={roles,setupReady:true,qualityPresets:[preset,{id:'quality',available:false,blockers:['insufficient-system-memory']}],hardware:{memoryGB:16},recommendedPreset:'balanced'};
assert.equal(matchingPreset(base),'balanced');assert.deepEqual(presetPlan(base,'balanced').hardware,base.hardware);
assert.equal(presetPlan(base,'balanced').setupReady,true);assert.throws(()=>presetPlan(base,'quality'));
// Model removal is opt-in. The setup call never deletes installed models unless the user ticks the Model centre control.
const chosen=presetPlan(base,'balanced');assert.deepEqual(setupParameters(chosen),{engine:'gpt',models:roles,removeOld:false});
// A plan that carries removeOld never turns removal on by itself; only the Model centre checkbox can.
assert.equal(setupParameters({...chosen,removeOld:true}).removeOld,false);
const frozen=setupParameters(chosen);chosen.requestedModels.text='different';assert.equal(frozen.models.text,'small-text');
assert.throws(()=>setupParameters({canDeployModels:false}));assert.throws(()=>setupParameters({canDeployModels:true,qualityPresets:[{available:false}]}));assert.deepEqual(presetReasons(base.qualityPresets[1]),['Not enough system memory']);
console.log('Quality template fit guards, exact setup parameters and frozen bootstrap selection passed');
