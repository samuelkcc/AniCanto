// A single stroke system shared by every platform; no platform emoji controls.
const paths={
 wand:'m4 20 13-13 3 3L7 23zM14 3V1m7 3 1-1M21 15h2M7 5l-1-1',
 mix:'M5 3v18M12 3v18M19 3v18M2 8h6m1 8h6m1-10h6',
 fullscreen:'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5',
 grip:'M9 5h.01M15 5h.01M9 12h.01M15 12h.01M9 19h.01M15 19h.01',up:'m6 15 6-6 6 6',down:'m6 9 6 6 6-6',
 logo:'M7 4h10a4 4 0 0 1 4 4v6a4 4 0 0 1-4 4h-6l-5 3 1-3a4 4 0 0 1-4-4V8a4 4 0 0 1 4-4zM7 9v4m3-6v8m4-7 4 3-4 3z',
 edit:'M4 4h16v12H4zM8 20h8m-4-4v4',roles:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8m8-7a4 4 0 0 1 0 7',
 review:'m3 6 1 1 2-2m3 1h12M3 12l1 1 2-2m3 1h12M3 18l1 1 2-2m3 1h12',
 export:'M12 16V3m-4 4 4-4 4 4M5 12v8h14v-8',queue:'M4 5h16v14H4zM8 9h1m3 0h5m-9 3h1m3 0h5m-9 3h1m3 0h5',
 terminal:'m4 6 5 5-5 5m8 0h7',settings:'M4 7h16M4 17h16M8 4v6m8 4v6',model:'m12 3 9 5v9l-9 5-9-5V8zM3 8l9 5 9-5m-9 5v9',folder:'M3 7V4h6l2 3h10v13H3z',
 home:'m3 11 9-8 9 8M5 9v12h5v-7h4v7h5V9',help:'M9.5 8a2.5 2.5 0 1 1 4 2c-1.5 1-1.5 1-1.5 3m0 3h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
 info:'M12 11v6m0-10h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',plus:'M12 5v14M5 12h14',close:'m6 6 12 12M6 18 18 6',
 play:'m8 4 13 8-13 8z',pause:'M8 5v14M16 5v14',stop:'M6 6h12v12H6z',chevron:'m9 5 7 7-7 7',back:'m15 5-7 7 7 7',
 sound:'m11 5-6 4H2v6h3l6 4zM15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14',subtitles:'M3 4h18v14h-6l-4 4v-4H3zM7 9h10M7 13h7',
 undo:'M9 5 4 10l5 5M4 10h10a6 6 0 0 1 0 12',redo:'m15 5 5 5-5 5m5-5H10a6 6 0 0 0 0 12',save:'M4 3h13l4 4v14H3V3zM7 3v6h10V3M7 21v-7h10v7',
 nav:'M3 4h18v16H3zM8 4v16',browser:'M3 4h18v16H3zM3 9h18',inspector:'M3 4h18v16H3zM16 4v16',trash:'M4 7h16M9 3h6l1 4H8zM6 7l1 14h10l1-14M10 11v6m4-6v6',
 restart:'M21 3v9h-9M21 12a9 9 0 1 0-3.2 6.9',
 refresh:'M20 7v5h-5M4 17v-5h5M6 6a8 8 0 0 1 13 3M5 15a8 8 0 0 0 13 3',clock:'M12 7v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
 check:'m5 12 4 4L19 6',warning:'m12 3 10 18H2zM12 9v5m0 3h.01',download:'M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5',spark:'m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z',
 split:'M12 3v18M3 8h5v8H3zM16 8h5v8h-5z',moon:'M20 14A9 9 0 0 1 10 3a9 9 0 1 0 10 11',sun:'M12 3v2m0 14v2M3 12h2m14 0h2M6 6l1 1m10 10 1 1M6 18l1-1M17 7l1-1M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0'
};
// Keep the in-app mark separate from the operating-system app icon. Its colour
// follows the selected studio theme, like the iPad waveform.circle.fill mark.
export function icon(name){if(name==='logo')return '<svg class="brand-waveform" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="currentColor"/><path d="M6.5 10.5v3m2.75-5.5v8m2.75-11v14m2.75-11v8m2.75-5.5v3" fill="none" stroke="var(--surface)" stroke-width="1.7" stroke-linecap="round"/></svg>';return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]||paths.settings}"/></svg>`}
