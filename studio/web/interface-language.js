// The WebView exposes the operating system's preferred UI languages.
export function initialLanguage(saved, preferred=[]){
 if(['en','zh-HK'].includes(saved))return saved;
 const primary=(preferred.find(x=>typeof x==='string'&&x.trim())||'en').toLowerCase();
 return /^(zh|yue)(-|_|$)/.test(primary)?'zh-HK':'en';
}
