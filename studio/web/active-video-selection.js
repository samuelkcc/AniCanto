// Keep the visible video bound to the worker until its saved completion arrives.
export function selectionOwner(state, active) {
 return active?.rowID || state.queue?.find(row=>row.status==='running')?.id || null;
}
export function selectionLocked(state, active, pending=false) {
 return !!(pending || selectionOwner(state,active));
}
export function selectionLockCopy(language) {
 return ({'zh-HK':'請先暫停並儲存，然後切換影片。','zh-CN':'请先暂停并保存，然后切换视频。',ja:'先に一時停止して保存してから、動画を切り替えてください。'})[language] || 'Pause and save before switching videos.';
}
