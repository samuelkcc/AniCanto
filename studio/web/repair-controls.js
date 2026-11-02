import {controlCopy,repairGroups} from './workflow-guide.js';
import {esc} from './model.js';
export const REPAIR_BINDINGS={translationReview:'translationTextReview',autoRepair:'aiAutoFix',durationLimit:'limitSpeechDuration',excessiveAudibleOverlap:'repairExcessiveAudibleOverlap',safeEndpoint:'safeEndpointCheck',borrowGaps:'analyzeBackgroundGaps',alternateEngine:'automaticAlternateVoice',systemVoice:'automaticSystemVoice'};
export function repairControls(s,language,locked=false){
 const control=id=>{
  const title=controlCopy(id,language,'title');let value=Boolean(s[REPAIR_BINDINGS[id]]);
  const disabled=locked||(['alternateEngine','systemVoice'].includes(id)&&!s.aiAutoFix)||(id==='excessiveAudibleOverlap'&&s.limitSpeechDuration);
  if(id==='contentReview')return `<label class="setting-switch"><span>${esc(title)}</span><select aria-label="${esc(title)}" data-setting="contentChecks" ${locked?'disabled':''}>${[0,1,2].map(n=>`<option value="${n}" ${n===Number(s.contentChecks||0)?'selected':''}>${n}</option>`).join('')}</select></label>`;
  return `<label class="setting-switch"><span class="switch-copy">${esc(title)}</span><span class="switch-control"><input aria-label="${esc(title)}" type="checkbox" role="switch" data-setting="${REPAIR_BINDINGS[id]}" ${value?'checked':''} ${disabled?'disabled':''}><span class="switch-track" aria-hidden="true"></span></span></label>`;
 };
 return repairGroups(language).map(group=>`<details class="repair-group settings-section" data-repair-group="${group.id}"><summary><strong>${esc(group.label)}</strong></summary><div class="settings-section-body">${group.items.map(control).join('')}</div></details>`).join('');
}
