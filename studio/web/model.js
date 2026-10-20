export const ENGINES=[['drama3','Drama 3'],['gpt-sovits-v2','GPT V2 Pro+'],['gpt-sovits','GPT V4'],['cosyvoice3','CosyVoice 3'],['voxcpm2','VoxCPM2'],['wsyue','WenetSpeech-Yue']];
export const THEMES={studio:'#7050B9',ocean:'#007E91',energy:'#B84D18',ninja:'#426D61',retro:'#B34372',forest:'#47773E',future:'#3268BC',mint:'#23796A',moonflower:'#8051AA'};
export const PHASES=['prepare','recognition','roles','translation','voice','repair','export'];
export function visibleMilestones(stages,basic){return basic?stages.filter(r=>!['roles','repair'].includes(r.id)):stages;}
export function esc(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
export function tc(n){n=Math.max(0,Number(n)||0);return `${Math.floor(n/3600).toString().padStart(2,'0')}:${Math.floor(n/60%60).toString().padStart(2,'0')}:${(n%60).toFixed(1).padStart(4,'0')}`}
export function shortTime(n){return n==null?'—':n<1?'<1s':n>=3600?`${Math.floor(n/3600)}h ${Math.floor(n/60%60)}m`:`${Math.floor(n/60)}:${Math.floor(n%60).toString().padStart(2,'0')}`}
export function bytes(n){return n==null?'—':n>=1e9?(n/1e9).toFixed(1)+' GB':n>0&&n<1e6?Math.max(1,Math.ceil(n/1000))+' KB':(n/1e6).toFixed(0)+' MB'}
export function filename(path){return String(path||'').split(/[\\/]/).pop()}
export function cueAt(cues,t){return cues.findIndex(c=>c.start<=t&&t<c.end)}
export function takeAt(takes,index,engine,language){return [...takes].reverse().find(r=>r.index===index+1&&r.engine===engine&&r.language===language)}
import {ASSISTANT_RIGS} from './assets/assistant-rigs.js';
export function themeAssets(key,variant=1){key=key==='ensemble'?'studio':key;key=key in THEMES?key:'studio';variant=[1,2,3,4].includes(variant)?variant:1;const rig=ASSISTANT_RIGS[key==='ensemble'?'studio':key];return {key,color:THEMES[key],cover:`./assets/welcome-${key}-${variant}.png`,runner:`./assets/${rig.image}?v=${rig.sha256.slice(0,12)}`,runnerSize:`400% ${100*rig.imageSize[1]/(rig.imageSize[1]-(rig.rowCuts?.[2]??rig.imageSize[1]*2/3))}%`,variant}}
export function captionAt(cues,t,language){const i=cueAt(cues,t);return i<0?'':cues[i][language==='en'?'english':'text']||''}
// Progress belongs to an attempt, not a project forever. A new submission may
// legitimately restart; within a run, repairs cannot move the bar backwards.
export function mergeJourney(previous,next,runID){return {...next,runID,progress:Math.max(previous?.runID===runID?previous.progress||0:0,Number(next?.progress)||0)}}

export function selectableEngines(platform,hardware){return ENGINES.filter(([id])=>id!=='cosyvoice3'||platform==='win32'&&hardware?.backend==='cuda');}
