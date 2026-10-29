import {esc} from './model.js';
// Known human labels only. Classifier codes and diagnostic dictionaries are
// retained by the backend/debug download, never used as main-interface copy.
export function performanceLabel(label){return ({laughter:'Laughter',baby_laughter:'Baby laughter',belly_laugh:'Loud laughter',crying_sobbing:'Crying / sobbing',sigh:'Sigh',breathing:'Breathing',gasp:'Gasp',screaming:'Scream',shout:'Shout',yell:'Yell',moaning_groaning:'Moan / groan',unavailable:'Audio analysis unavailable'})[label]||'Uncertain reaction';}
export function workflowNoticesHTML(notices,t){return notices.map(n=>`<section class="card warning workflow-notice"><h4>${esc(t(n.title))}</h4><p>${esc(t(n.message))}</p>${n.metrics?.length?`<dl class="notice-metrics">${n.metrics.map(x=>`<div><dt>${esc(t(x.label))}</dt><dd>${Number.isFinite(Number(x.value))?Number(x.value):'—'}</dd></div>`).join('')}</dl>`:''}</section>`).join('');}
