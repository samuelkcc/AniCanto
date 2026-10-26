import {esc,scriptField} from './model.js';
export const processingPlayback=row=>row?.status==='running';
export function subtitleOptions(select,tracks,choice,t,hasScript=false,autoLabel='Automatic subtitles'){if(!select)return;const options=[['auto',autoLabel,true],['off','No captions',true],...tracks.map(r=>[r.id,r.title+(r.supported?'':` · ${t('Image subtitles unsupported')}`),r.supported]),...(hasScript?[['script:yue','Cantonese script',true],['script:zh','Mandarin script',true],['script:en','English script',true],['script:original','Original subtitles',true]]:[])];select.innerHTML=options.map(([id,title,enabled])=>`<option value="${esc(id)}" ${id===choice?'selected':''} ${enabled?'':'disabled'}>${esc(t(title))}</option>`).join('');}

export function translatedCaption(rows,time,language){const c=rows.find(c=>c.enabled!==false&&(c.captionStart??c.start)<=time&&time<(c.captionEnd??c.end));return c?String(c.captionText||c[scriptField(language)]||'').trim():'';}
export function hasTranslatedScript(rows,language){return rows.some(c=>c.enabled!==false&&String(c[scriptField(language)]||'').trim());}
export function playbackScriptTime(time,output,offset=0){return output?time:time-Math.max(0,Number(offset)||0);}
