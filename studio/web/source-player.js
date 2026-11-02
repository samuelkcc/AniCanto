// Source segments stay in bounded memory. Prefer native HLS where available.
export async function attachSource(video,url,onError=()=>{},isCurrent=()=>true){
 if(!isCurrent())return()=>{};
 if(!url.includes('/index.m3u8')||video.canPlayType('application/vnd.apple.mpegurl')){
  video.src=url;video.preload='auto';video.load();return()=>{};
 }
 const {default:Hls}=await import('./vendor/hls.js/hls.light.min.mjs');
 if(!isCurrent())return()=>{};
 if(!Hls.isSupported())throw new Error('Source playback is unavailable in this browser.');
 const player=new Hls({enableWorker:false,maxBufferLength:12,maxMaxBufferLength:18,backBufferLength:6,maxBufferSize:32*1024*1024});
 player.on(Hls.Events.ERROR,(_event,data)=>{if(data.fatal)onError(data);});
 player.loadSource(url);player.attachMedia(video);
 return()=>player.destroy();
}
