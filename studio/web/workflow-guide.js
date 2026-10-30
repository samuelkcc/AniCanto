import {WORKFLOW_GUIDE,WORKFLOW_GUIDE_SHA} from './assets/workflow-controls-guide.js';
export {WORKFLOW_GUIDE,WORKFLOW_GUIDE_SHA};
export function controlCopy(id,language,part='body'){const item=WORKFLOW_GUIDE.items.find(i=>i.id===id);return item?.[part]?.[language]||item?.[part]?.en||'';}

export function panelCopy(part,language){return WORKFLOW_GUIDE.presentation?.[part]?.[language]||WORKFLOW_GUIDE.presentation?.[part]?.en||'';}

export function repairGroups(language){return (WORKFLOW_GUIDE.groups||[]).map(g=>({...g,label:g.title[language]||g.title.en}));}
