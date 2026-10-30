// New illustrated work scenes retain the original desktop character identities.
import {THEMES,esc} from './model.js';
const COPY={
 en:{title:'Assistant animation preview',demo:'Demonstration progress',overall:'Overall progress',note:'Preview only. This does not change your assistant or conversion settings.',activities:['Computer work','Listening and notes','Translation','Dubbing'],names:['Shion','Ocean','Energy','Ninja','Retro','Forest','Future','Mint','Moonflower'],idle:'Ready',paused:'Paused',done:'Output saved'},
 'zh-HK':{title:'助手動畫預覽',demo:'示範進度',overall:'整體進度',note:'只供預覽，唔會更改助手或轉換設定。',activities:['電腦處理','聆聽記錄','翻譯','配音'],names:['紫音','海洋','活力','忍者','復古','森林','未來','薄荷','月花'],idle:'準備就緒',paused:'已暫停',done:'成品已保存'},
 'zh-CN':{title:'助手动画预览',demo:'演示进度',overall:'整体进度',note:'仅供预览，不会更改助手或转换设置。',activities:['电脑处理','聆听记录','翻译','配音'],names:['紫音','海洋','活力','忍者','复古','森林','未来','薄荷','月花'],idle:'准备就绪',paused:'已暂停',done:'成品已保存'},
 ja:{title:'アシスタントの動作プレビュー',demo:'デモの進捗',overall:'全体の進捗',note:'プレビューのみ。アシスタントや変換設定は変更しません。',activities:['パソコン作業','聴き取りと記録','翻訳','吹き替え'],names:['紫音','海','活力','忍者','レトロ','森','未来','ミント','月花'],idle:'準備完了',paused:'一時停止',done:'出力を保存しました'}
};
export const ACTIVITIES=['computer','listening','translation','dubbing','sleep'];
const REST={en:'Resting','zh-HK':'休息待機','zh-CN':'休息待机',ja:'休憩中'};
export function workflowState(row={},journey={}){
 const phase=(journey.milestones||[]).find(m=>m.state==='running')?.id;
 const active=row.status==='running';
 const kind=(!active&&row.status!=='paused'?'translation':({recognition:'listening',roles:'listening',translation:'translation',voice:'dubbing',repair:'listening'})[phase]||'computer');
 const fraction=Number(journey.progress??row.progress??0);
 return {activity:kind,phase:phase||'',progress:Math.round(Math.min(1,Math.max(0,Number.isFinite(fraction)?fraction:0))*100),running:active,complete:row.status==='complete'||journey.complete===true,paused:row.status==='paused',hasProgress:active||row.status==='paused'||row.status==='complete',stepProgress:null};
}
function motionClass(o){if(o.resting)return 'is-resting';return o.running||o.demo?'is-working':o.paused||o.complete?'is-paused':'is-idle';}
export function workflowScene(theme='studio',options={},language='en'){
 if(!(theme in THEMES))theme='studio';
 const c=COPY[language]||COPY.en,kind=ACTIVITIES.includes(options.activity)?options.activity:'translation';
 return `<div class="assistant-workflow illustrated-activity ${options.demo?'assistant-preview':''} ${motionClass(options)}" data-work-activity="${kind}" data-theme="${theme}" role="img" aria-label="${esc(kind==='sleep'?REST[language]||REST.en:c.activities[ACTIVITIES.indexOf(kind)])}" style="--work-accent:${THEMES[theme]}"><div class="work-illustration"><canvas class="activity-art" data-theme="${theme}" data-activity="${kind}" width="640" height="640" aria-hidden="true"></canvas></div></div>`;
}
export function assistantPreviewHTML(theme,activity,language){
 const c=COPY[language]||COPY.en,keys=Object.keys(THEMES);
 return `<section class="card stack assistant-preview-card"><h3>${esc(c.title)}</h3><div class="assistant-choice-grid" role="group" aria-label="${esc(c.title)}">${keys.map((key,i)=>`<button class="assistant-choice ${theme===key?'active':''}" data-action="assistant-demo-theme" data-value="${key}" aria-pressed="${theme===key}" style="--work-accent:${THEMES[key]}"><span class="assistant-color"></span>${esc(c.names[i])}</button>`).join('')}</div><div class="assistant-activity-tabs" role="group">${ACTIVITIES.map((kind,i)=>`<button data-action="assistant-demo-activity" data-value="${kind}" aria-pressed="${activity===kind}" class="${activity===kind?'active':''}">${esc(kind==='sleep'?REST[language]||REST.en:c.activities[i])}</button>`).join('')}</div>${workflowScene(theme,{activity,demo:true},language)}<small>${esc(c.note)}</small></section>`;
}
export function updateWorkflowScene(element,state,language){
 if(!element)return;
 const kind=state.activity,c=COPY[language]||COPY.en;
 element.dataset.workActivity=kind;element.querySelector('canvas').dataset.activity=kind;
 element.setAttribute('aria-label',c.activities[ACTIVITIES.indexOf(kind)]);
 for(const name of ['is-working','is-paused','is-idle'])element.classList.toggle(name,name===motionClass(state));
}
