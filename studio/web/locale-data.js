import {LOCALE as japanese} from './locales/ja.js';
import {LOCALE as simplifiedChinese} from './locales/zh-CN.js';

export function localeData(language){
 if(language==='ja')return japanese;
 if(language==='zh-CN')return simplifiedChinese;
 return null;
}
