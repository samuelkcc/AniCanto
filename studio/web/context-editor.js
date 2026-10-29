import {esc} from './model.js';

// Display captions do not change the selected recording or review decision.
export function editCueField(cue,key,value){
 if(cue[key]===value)return false;
 cue[key]=value;
 if(key!=='captionText'){cue.audioTake=null;delete cue.reviewDecisions;}
 return true;
}

export function effectiveMix(settings={}){
 const value=Number(settings.backgroundGain??.8);
 return {backgroundGain:Math.max(0,Math.min(1.5,Number.isFinite(value)?value:.8)),backgroundDucking:Boolean(settings.backgroundDucking)};
}

export function mixerHTML({settings,t,field,settingSwitch,locked=false,scope=''}){
 const mix=effectiveMix(settings),gain=mix.backgroundGain;
 return `<section class="context-mixer stack"><span class="pill">${esc(scope)}</span>${field('Export background level',`<div class="mixer-level"><input type="range" min="0" max="1.5" step=".05" data-setting="backgroundGain" value="${gain}" aria-label="${esc(t('Export background level'))}" ${locked?'disabled':''}><output id="mix-gain-value">${Math.round(gain*100)}%</output></div>`)}${settingSwitch('backgroundDucking','Lower background while speaking',mix.backgroundDucking,locked?'disabled':'')}</section>`;
}
