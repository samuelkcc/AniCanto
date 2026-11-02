// Named scope selection stays inside the scrolling settings body.
import assert from 'node:assert/strict';
import fs from 'node:fs';
const js=fs.readFileSync('studio/web/app.js','utf8'),css=fs.readFileSync('studio/web/styles.css','utf8');
const inspector=js.split('\n').find(x=>x.startsWith('function inspectorHTML('));
assert(inspector.includes('return productionScopeControl()+'));
const start=js.indexOf('<aside class="inspector">'),shell=js.slice(start,js.indexOf('</aside>',start));
assert(shell.includes('<div id="inspector-content" class="inspector-content">${inspectorHTML()}</div>'));
assert(!shell.includes('productionScopeControl()'));
const scope=js.split('\n').find(x=>x.startsWith('function productionScopeControl('));
assert(scope.includes('<select data-setting="productionScopeGlobal"'));
assert(scope.includes('value="global"')&&scope.includes('value="video"'));
assert(!scope.includes('type="checkbox"'));
assert(js.includes("useGlobalSettings:el.value==='global'"));
const refresh=[...js.matchAll(/\$\('#inspector-content'\)\.innerHTML=([A-Za-z]+\(\))/g)].map(x=>x[1]);
assert(refresh.length>=4&&refresh.every(x=>x==='inspectorHTML()'));
assert(css.includes('.production-scope{padding:0;margin:0;display:grid;gap:8px}'));
assert(css.includes('.inspector-content{gap:12px;padding:14px}'));
console.log('PASS named scope menu, explicit values and scroll ownership across partial refreshes');
