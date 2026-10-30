import {controlCopy,repairGroups} from './workflow-guide.js';
import {esc} from './model.js';
export const REPAIR_BINDINGS={translationReview:'translationTextReview',autoRepair:'aiAutoFix',durationLimit:'limitSpeechDuration',excessiveAudibleOverlap:'repairExcessiveAudibleOverlap',safeEndpoint:'safeEndpointCheck',borrowGaps:'analyzeBackgroundGaps',alternateEngine:'automaticAlternateVoice',systemVoice:'automaticSystemVoice'};
export function repairControls(s,language,locked=false){
 const control=id=>{
  const title=controlCopy(id,language,'title'),help=controlCopy(id,language);let value=Boolean(s[REPAIR_BINDINGS[id]]);
  const disabled=locked||(['alternateEngine','systemVoice'].includes(id)&&!s.aiAutoFix)||(id==='excessiveAudibleOverlap'&&s.limitSpeechDuration);
  if(id==='contentReview')return `<label class="setting-switch" title="${esc(help)}"><span>${esc(title)}</span><input aria-label="${esc(title)}" type="range" min="0" max="2" step="1" data-setting="contentChecks" value="${Number(s.contentChecks||0)}" ${locked?'disabled':''}><output>${Number(s.contentChecks||0)}</output></label>`;
  return `<label class="setting-switch" title="${esc(help)}"><span class="switch-copy">${esc(title)}</span><span class="switch-control"><input aria-label="${esc(title)}" type="checkbox" role="switch" data-setting="${REPAIR_BINDINGS[id]}" ${value?'checked':''} ${disabled?'disabled':''}><span class="switch-track" aria-hidden="true"></span></span></label>`;
 };
 return repairGroups(language).map(group=>`<fieldset class="repair-group" data-repair-group="${group.id}"><legend>${esc(group.label)}</legend>${group.items.map(control).join('')}</fieldset>`).join('');
}
