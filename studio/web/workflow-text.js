import {WORKFLOW} from './assets/workflow-localization.js';
const cjk=/[\u3400-\u9fff]/u;
export function workerText(text,language,stage=false){
 text=String(text||'');if(language==='zh-HK')return text;
 if(Object.hasOwn(WORKFLOW.exact,text))return WORKFLOW.exact[text];
 if(!cjk.test(text))return text;
 const track=text.match(/^音軌 (\d+)\/(\d+) · ([^·]+) · ([^·]+) · (.*)$/u);
 if(track)return `Audio track ${track[1]}/${track[2]} · ${workerText(track[3].trim(),language)} · ${track[4].trim()} · ${workerText(track[5],language)}`;
 for(const [pattern,replacement] of WORKFLOW.patterns){
  const re=new RegExp(pattern,'u');if(!re.test(text))continue;
  const value=text.replace(re,replacement);
  if(!cjk.test(value))return value;
  if(value.includes(' · ')){const parts=value.split(' · ').map(p=>workerText(p,language));if(parts.every(p=>!p.startsWith('Worker diagnostic')))return parts.join(' · ');}
  break;
 }
 if(text.includes(' · ')){const parts=text.split(' · ').map(p=>workerText(p,language));if(parts.every(p=>!p.startsWith('Worker diagnostic')))return parts.join(' · ');}
 return stage?'Processing':'Worker diagnostic received; see Detailed process log for the original text.';
}
export function projectWarning(text,language){
 if(language==='zh-HK'||!cjk.test(String(text||'')))return String(text||'');
 const rows=[...String(text).matchAll(/對白覆蓋：([^·\n]+) · ([^—\n]+) — 有錄音 (\d+)\/(\d+)；缺聲 (\d+)/gu)];
 if(rows.length)return rows.map(m=>`${workerText(m[1].trim(),language)} · ${m[2].trim()} — recorded ${m[3]}/${m[4]}, missing ${m[5]}.`).join(' ')+' Open Review report for affected lines and recovery status.';
 return 'Dubbing needs attention. Open Review report for affected lines and recovery status.';
}
