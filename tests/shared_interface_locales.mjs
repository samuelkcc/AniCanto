import assert from 'node:assert/strict';
import {initialLanguage,interfaceLanguageOptions,INTERFACE_LANGUAGES,INTERFACE_LANGUAGE_NAMES} from '../studio/web/interface-language.js';
import {localeData} from '../studio/web/locale-data.js';
import {translate} from '../studio/web/i18n.js';
import {chapters} from '../studio/web/help.js';
import {aboutCopy} from '../studio/web/about-copy.js';
import {licenceCopy} from '../studio/web/licence-copy.js';
import {privacyCopy} from '../studio/web/privacy-copy.js';

assert.equal(initialLanguage(null,['ja-JP']),'ja');
assert.equal(initialLanguage(null,['zh-Hans-CN']),'zh-CN');
assert.deepEqual(INTERFACE_LANGUAGES,['zh-HK','zh-CN','ja','en']);
assert.equal(INTERFACE_LANGUAGE_NAMES['zh-HK'],'繁體中文');
assert.equal(INTERFACE_LANGUAGE_NAMES['zh-CN'],'简体中文');
assert.deepEqual([...interfaceLanguageOptions('zh-HK').matchAll(/<option value="([^"]+)"/g)].map(match=>match[1]),INTERFACE_LANGUAGES);
for(const language of INTERFACE_LANGUAGES){
 const policy=privacyCopy(language);
 assert.equal(policy.sections.length,5);
 assert(policy.sections.every(section=>section.title&&section.text.length>50));
 assert(policy.sections[0].text.includes('AniCanto'));
}
for(const language of ['zh-CN','ja']){
 const copy=localeData(language);
 assert(Object.keys(copy.ui).length>=870);
 assert(Object.keys(copy.help).length>=190);
 assert.equal(Object.keys(copy.terms).length,7);
 assert.equal(aboutCopy(language).length,4);
 assert.equal(licenceCopy(language).length,6);
 assert.equal(chapters(language).length,chapters('en').length);
 assert.notEqual(chapters(language)[0].title,chapters('en')[0].title);
 assert.notEqual(translate('Welcome to your dubbing studio',language),'Welcome to your dubbing studio');
 assert(interfaceLanguageOptions(language).includes(`value="${language}" selected`));
 for(const [source,value] of Object.entries(copy.ui)){
  const tokens=text=>[...text.matchAll(/\$\d+|\{[A-Za-z_][A-Za-z_0-9]*\}/g)].map(m=>m[0]).sort();
  assert.deepEqual(tokens(value),tokens(source),`${language}: ${source}`);
 }
}
console.log('Four interface languages, documentation and placeholders passed.');
