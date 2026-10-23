// The WebView exposes the operating system's preferred UI languages.
export const INTERFACE_LANGUAGES=['zh-HK','zh-CN','ja','en'];
export const INTERFACE_LANGUAGE_NAMES={en:'English','zh-HK':'繁體中文','zh-CN':'简体中文',ja:'日本語'};
export function interfaceLanguageOptions(selected){return INTERFACE_LANGUAGES.map(id=>`<option value="${id}" ${selected===id?'selected':''}>${INTERFACE_LANGUAGE_NAMES[id]}</option>`).join('');}
export function initialLanguage(saved, preferred=[]){
 if(INTERFACE_LANGUAGES.includes(saved))return saved;
 const primary=(preferred.find(x=>typeof x==='string'&&x.trim())||'en').toLowerCase().replace('_','-');
 if(/^ja(-|$)/.test(primary))return 'ja';
 if(/^zh-(cn|sg|hans)(-|$)/.test(primary))return 'zh-CN';
 if(/^(zh|yue)(-|$)/.test(primary))return 'zh-HK';
 return 'en';
}
