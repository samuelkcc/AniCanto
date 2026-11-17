// Check website language selection and the consent expiry with isolated storage.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const code = fs.readFileSync('website/language-preferences.js', 'utf8');
const rememberKey = 'anicanto.website.remember-language.v1';
const sessionKey = 'anicanto.website.session-language';
const period = 180 * 24 * 60 * 60 * 1000;
function fixture({tags=['en'], path='/', query='', session, saved}={}) {
  const local = new Map(saved ? [[rememberKey, JSON.stringify(saved)]] : []);
  const tab = new Map(session ? [[sessionKey, session]] : []);
  const storage = map => ({getItem:key=>map.get(key)??null, setItem:(key,value)=>map.set(key,value), removeItem:key=>map.delete(key)});
  const input = {checked:false, addEventListener:(name,fn)=>input.change=fn};
  const context = {URL, Date, navigator:{languages:tags}, location:{href:'https://anicanto.com'+path+query, pathname:path},
    localStorage:storage(local), sessionStorage:storage(tab), window:{addEventListener(){}},
    document:{documentElement:{lang:'zh-Hant'}, querySelectorAll:selector=>selector==='[data-remember-language]'?[input]:[]}};
  vm.runInNewContext(code,context);
  return {api:context.window.AniCantoPreferences,local,tab,input};
}
let count=0;
for (const [tags,expected] of [
  [['zh-HK'],'zh-HK'], [['zh-Hant-HK'],'zh-HK'], [['zh-MO'],'zh-HK'], [['yue-Hant'],'zh-HK'],
  [['zh-TW'],'zh-Hant'], [['zh-Hant-TW'],'zh-Hant'], [['zh-Hant'],'zh-Hant'], [['zh'],'zh-Hant'],
  [['zh-CN'],'zh-Hans'], [['zh-Hans'],'zh-Hans'], [['zh-Hans-SG'],'zh-Hans'], [['zh-SG'],'zh-Hans'],
  [['en-US'],'en'], [['ja-JP'],'ja'], [['fr-FR','zh-TW'],'zh-Hant'], [['de-DE'],'en'],
  [['en-US','zh-TW'],'en'], [['zh-TW','en-US'],'zh-Hant']
]) { assert.equal(fixture({tags}).api.resolveLanguage(),expected);count++; }
for (const language of ['zh-HK','zh-Hant','zh-Hans','en','ja']) {
  assert.equal(fixture({path:'/'+language+'/'}).api.resolveLanguage(),language);
  assert.equal(fixture({path:'/ja/',query:'?lang='+language,session:'en'}).api.resolveLanguage(),language);
  assert.equal(fixture({session:language}).api.resolveLanguage(),language);
  count+=3;
}
const consentedAt=Date.now()-1000, expiresAt=consentedAt+period;
let f=fixture({saved:{version:1,language:'zh-HK',consentedAt,expiresAt}});
f.api.setLanguage('zh-Hant');
assert.deepEqual(JSON.parse(f.local.get(rememberKey)),{version:1,language:'zh-Hant',consentedAt,expiresAt});count++;
f=fixture();f.api.setLanguage('zh-Hant');assert.equal(f.local.has(rememberKey),false);count++;
f.input.checked=true;f.input.change();assert.equal(JSON.parse(f.local.get(rememberKey)).language,'zh-Hant');count++;
f.input.checked=false;f.input.change();assert.equal(f.local.has(rememberKey),false);count++;
f=fixture({saved:{version:1,language:'zh-Hant',consentedAt:Date.now()-period-1000,expiresAt:Date.now()-1000}});
assert.equal(f.api.resolveLanguage(),'en');assert.equal(f.local.has(rememberKey),false);count++;
console.log(JSON.stringify({passed:true,cases:count}));
