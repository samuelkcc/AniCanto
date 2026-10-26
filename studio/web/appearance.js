// Runs before CSS and module imports. Native persisted settings are authoritative;
// a browser cache is only a fallback when there is no native startup value.
(()=>{
 const normalize=value=>['light','dark','system'].includes(value)?value:'system';
 let cached=null;try{cached=localStorage.getItem('anicanto-appearance');}catch{}
 const initial=normalize(window.__ANICANTO_APPEARANCE__??cached);
 const system=matchMedia('(prefers-color-scheme:dark)');
 let current=initial;
 const apply=value=>{
  current=normalize(value);
  const dark=current==='dark'||current==='system'&&system.matches;
  document.documentElement.classList.toggle('dark',dark);
  document.documentElement.style.colorScheme=dark?'dark':'light';
  try{localStorage.setItem('anicanto-appearance',current);}catch{}
  return {appearance:current,dark};
 };
 window.anicantoAppearance={initial,apply,system};
 apply(initial);
})();
