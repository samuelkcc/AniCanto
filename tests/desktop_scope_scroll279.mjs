// Desktop build 279 inspector layout: the two scope switches scroll with the settings body.
import assert from 'node:assert/strict';
import fs from 'node:fs';

const js=fs.readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
const css=fs.readFileSync(new URL('../studio/web/styles.css',import.meta.url),'utf8');

// inspectorHTML is one line, so the whole function body is one read.
const oneLineFunction=(name)=>{const start=js.indexOf(`function ${name}(`);assert(start>=0,`${name}: missing`);
 const end=js.indexOf('\n',start);assert(end>start,`${name}: empty`);return js.slice(start,end)};

// The switches belong to the scrolling body, so they must come from inspectorHTML.
const inspector=oneLineFunction('inspectorHTML');
assert(inspector.includes('return productionScopeControl()+'),`switches are not first in the body: ${inspector}`);

// The shell must not place them outside #inspector-content.
const shellStart=js.indexOf('<aside class="inspector">');
assert(shellStart>=0,'inspector shell: missing');
const shell=js.slice(shellStart,js.indexOf('</aside>',shellStart));
assert(shell.includes('<div id="inspector-content" class="inspector-content">${inspectorHTML()}</div>'),`shell: ${shell}`);
assert(!shell.includes('productionScopeControl()'),'inspector shell still carries a pinned switch block');

// Every partial refresh keeps the switches in the same place.
const refresh=[...js.matchAll(/\$\('#inspector-content'\)\.innerHTML=([A-Za-z]+\(\))/g)].map(match=>match[1]);
assert(refresh.length>=4,`partial refresh sites: ${refresh.length}`);
assert(refresh.every(body=>body==='inspectorHTML()'),`partial refresh bodies: ${refresh.join(',')}`);

// The body keeps the switches in one column: the block adds no side padding and is never pinned.
const rule=/\.production-scope\{([^}]*)\}/.exec(css);
assert(rule,'.production-scope rule: missing');
assert(!/position\s*:/.test(rule[1]),`.production-scope is pinned again: ${rule[1]}`);
// Vertical spacing only: a side value here would move the switch column out of line.
assert(/padding:0 0 \d+px/.test(rule[1]),`block padding has a side value: ${rule[1]}`);
assert(/margin:0 0 -\d+px/.test(rule[1]),`block margin has a side value: ${rule[1]}`);
assert(!/(padding|margin)-(left|right)\s*:/.test(rule[1]),`side offset inside the block: ${rule[1]}`);
const switchRule=/\.production-scope \.setting-switch\{([^}]*)\}/.exec(css);
assert(switchRule,'.production-scope .setting-switch rule: missing');
assert(switchRule[1].includes('padding:8px 0')&&!/margin:[^;}]*[1-9]/.test(switchRule[1]),`switch column geometry: ${switchRule[1]}`);
// The shared body padding is the only horizontal offset for both switch groups.
assert(/\.inspector-content\{padding:18px/.test(css),'inspector body padding changed');

console.log('PASS build279 inspector: both scope switches scroll inside the settings body in one aligned switch column');
