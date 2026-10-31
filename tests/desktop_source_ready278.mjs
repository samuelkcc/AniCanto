// Build 278 desktop source loading: the panel names the real source, and the four fault
// texts stay identical between the backend reader and the interface copy table.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {esc} from '../studio/web/model.js';
import {preparationCopy,preparationSourceKind,preparationSourceLabel} from '../studio/web/source-preparation-copy.js';

const python=fs.readFileSync(new URL('../Resources/source_preparation.py',import.meta.url),'utf8');
const constants=name=>{const match=python.match(new RegExp(`^${name}='([^']+)'`,'m'));assert(match,`${name}: missing`);return match[1].replace(/\\'/g,"'");};
const locales=['en','zh-HK','zh-CN','ja'];
const keys=Object.keys(preparationCopy('en'));
for(const language of locales){
 const copy=preparationCopy(language);
 assert.deepEqual(Object.keys(copy),keys,`${language}: copy keys`);
 for(const [key,value] of Object.entries(copy)){
  assert(typeof value==='string'&&value.length,`${language}.${key}`);
  if(language!=='en')assert(!value.startsWith('undefined'),`${language}.${key}`);
 }
 // A local source is never described as a provider download in the neutral texts.
 if(language==='zh-HK'||language==='zh-CN'){
  assert(!/雲端|云/.test(copy.note+copy.waiting+copy.source_local),`${language}: neutral loading text`);
 }
 if(language==='ja')assert(!/クラウド/.test(copy.note+copy.waiting+copy.source_local),`${language}: neutral loading text`);
}
// The backend faults and the interface copy must stay byte-identical.
for(const [constant,key] of [['CLOUD_ERROR','CLOUD'],['READ_ERROR','READ'],['STALLED_ERROR','STALLED'],['CANCELLED','CANCELLED']]){
 assert.equal(preparationCopy('en')[key],constants(constant),`${key}: copy drift`);
}
// Every fault reads in all four interface languages.
for(const language of locales)for(const key of ['CLOUD','READ','STALLED']){
 const text=preparationCopy(language)[key];
 assert(text&&!text.includes('undefined'),`${language}.${key}`);
}
// The loading panel template is the desktop one; the stub mirrors browser globals.
const source=fs.readFileSync(new URL('../studio/web/app.js',import.meta.url),'utf8');
const body=name=>{const start=source.indexOf(`function ${name}(`);assert(start>=0,`${name}: missing`);const rest=source.slice(start);
 const closes=[...rest.matchAll(/^\}/gm)].filter(match=>match.index>0).map(match=>match.index+1);
 const next=[...rest.matchAll(/^(?=function |const |let )/gm)].filter(match=>match.index>0).map(match=>match.index);
 const stops=[...closes,...next];assert(stops.length,`${name}: unterminated`);return rest.slice(0,Math.min(...stops))};
// The panel reads module bindings and two module-level values, so the stub injects them as names.
const render=(status,language)=>new Function('d',`const {esc,preparationCopy,preparationSourceLabel,bytes,state,sourcePreparation}=d;\n${body('preparationHTML')}\nreturn preparationHTML()`)(
 {esc,preparationCopy,preparationSourceLabel,bytes:value=>`${value} B`,state:{language},sourcePreparation:status});

for(const language of locales){
 // A file that is already on this computer: local wording, no provider claim, no source guess.
 const local=render({phase:'reading',totalBytes:0,bytesRead:0,provider:'local',needsHydration:false,hydrationReason:''},language);
 assert(local.includes(`${preparationCopy(language).source}: ${preparationCopy(language).source_local}`),`${language}: ${local}`);
 assert(!preparationCopy(language).waitingProvider.split('…')[0].length||!local.includes(preparationCopy(language).waitingProvider),`${language}: no provider wait`);
 assert(local.includes(preparationCopy(language).note)&&!local.includes(preparationCopy(language).noteProvider),`${language}: local note`);
 assert(local.includes('source-indeterminate'),`${language}: indeterminate track while no bytes are known`);
 // A provider-owned movie: byte progress, the provider name, and the download note.
 const drive=render({phase:'reading',totalBytes:4000000,bytesRead:1500000,provider:'onedrive',needsHydration:true,hydrationReason:'recall-attributes'},language);
 assert(drive.includes(preparationCopy(language).source_onedrive)&&drive.includes(preparationCopy(language).noteProvider),`${language}: ${drive}`);
 assert(drive.includes('38%')&&drive.includes('source-preparation')===false,`${language}: byte percentage`);
 assert(drive.includes('1500000 B')&&drive.includes('4000000 B'),`${language}: byte counts`);
 // An unanswered iCloud placeholder reads as iCloud, and a share reads as a share.
 assert.equal(preparationSourceKind({provider:'local',hydrationReason:'placeholder'}),'icloud');
 assert.equal(preparationSourceKind({provider:'local',hydrationReason:'network'}),'network');
 assert.equal(preparationSourceLabel({provider:'icloud',hydrationReason:'placeholder'},language),preparationCopy(language).source_icloud,language);
 assert.equal(preparationSourceLabel({provider:'network',hydrationReason:'network'},language),preparationCopy(language).source_network,language);
 const icloud=render({phase:'probing',totalBytes:2000,bytesRead:2000,provider:'local',needsHydration:true,hydrationReason:'placeholder'},language);
 assert(icloud.includes(preparationCopy(language).source_icloud),`${language}: ${icloud}`);
}
// Text from a provider can never inject markup into the loading panel.
const hostile=render({phase:'reading',provider:'local',needsHydration:false},'<script>alert(1)</script>');
assert(hostile.includes('&lt;script&gt;')===false&&!hostile.includes('<script>alert'),hostile);
// The keep-waiting question sits in the same loading card, in every interface language.
for(const language of locales)for(const key of ['waitTitle','waitIdle','waitNote','waitKeep','waitStop']){
 const value=preparationCopy(language)[key];
 assert(typeof value==='string'&&value.length,`${language}.${key}: missing`);
}
const stalled={phase:'reading',totalBytes:1000000000,bytesRead:536870912,provider:'google-drive',needsHydration:true,hydrationReason:'recall-attributes',waitingForDecision:true,idleSeconds:47};
for(const language of locales){
 const copy=preparationCopy(language);
 const card=render(stalled,language);
 assert(card.includes('class="source-wait"'),`${language}: wait card: ${card}`);
 assert(card.includes('data-action="keep-waiting-source"')&&card.includes('data-action="cancel-source-preparation"'),`${language}: both answers`);
 assert(card.includes('class="primary" data-action="keep-waiting-source"'),`${language}: keep waiting is the primary answer`);
 assert(card.includes(copy.waitTitle)&&card.includes(copy.waitKeep)&&card.includes(copy.waitStop),`${language}: wait copy`);
 assert(card.includes(`${copy.waitIdle} 47s`)&&card.includes('536870912 B'),`${language}: quiet time and bytes already read: ${card}`);
 assert(card.includes(copy.source_google_drive),`${language}: the slow provider is named`);
 // Two bytes have arrived and the read is quiet, so no fault text replaces the question.
 assert(!card.includes(copy.STALLED)&&!card.includes(copy.CLOUD),`${language}: a quiet provider is not a fault`);
 // A live read shows only the progress bar.
 assert(!render({...stalled,waitingForDecision:false},language).includes('class="source-wait"'),`${language}: no question while data flows`);
 assert(!render({...stalled,waitingForDecision:undefined},language).includes('class="source-wait"'),`${language}: no question by default`);
}
// A quiet provider must not be able to inject markup into the question either.
const hostileWait=render({...stalled,provider:'local',needsHydration:false},'<script>alert(1)</script>');
assert(!hostileWait.includes('<script>alert'),hostileWait);
// The host answers the wait request while the Python RPC stays busy with the provider read,
// so it must allow the operation and share the reader's rule exactly.
const host=fs.readFileSync(new URL('../studio/src-tauri/src/main.rs',import.meta.url),'utf8');
assert(host.includes('"source-prepare-wait"'),'host allowlist is missing source-prepare-wait');
const hostGrace=host.match(/const SOURCE_WAIT_GRACE_SECONDS:u64=(\d+)/);
assert(hostGrace,'host wait grace constant');
const backend=fs.readFileSync(new URL('../studio/backend.py',import.meta.url),'utf8');
assert(backend.includes("'source-prepare-wait'")&&backend.includes('grant_wait'),'backend wait operation');
assert(python.includes('def grant_wait(')&&python.includes('def wait_grant_remaining('),'reader wait rule');
const waitFile=host.match(/const SOURCE_WAIT_FILE:&str="([^"]+)"/);
assert(waitFile,'host wait file constant');
assert.equal(waitFile[1],python.match(/^WAIT_FILE='([^']+)'/m)[1],'wait file name drift');
assert.equal(Number(hostGrace[1]),Number(python.match(/^WAIT_GRACE=(\d+)/m)[1]),'wait grace seconds drift');
assert(python.includes('WAIT_AFTER_IDLE='),'reader asks after a fixed quiet time');
// The question needs a style rule, or it renders as loose text in the loading card.
const css=fs.readFileSync(new URL('../studio/web/styles.css',import.meta.url),'utf8');
assert(/\.source-wait\{/.test(css)&&/\.source-wait \.row\{/.test(css),'.source-wait style rule');
// The Windows worker route also streams provider movies, so it must not fail on quiet time.
const worker=fs.readFileSync(new URL('../Resources/source_access.py',import.meta.url),'utf8');
assert(!/if stalls>=IDLE_STALLS:\s*raise/.test(worker),'the worker copy must not fail on a quiet provider');
assert(worker.includes('does not time out'),'the worker tells the user the wait has no timeout');

console.log('PASS source loading names the real source, four languages, backend copy parity, three fault texts distinct, one keep-waiting question answered by the host');
