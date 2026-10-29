import assert from 'node:assert/strict';
import {ConversionQueue,pendingVideos,missedCompletion,restorableCompletion} from '../studio/web/conversion-queue.js';
const rows=[{id:'done',status:'complete'},{id:'a',status:'waiting'},{id:'b',status:'waiting'},{id:'bad',status:'attention'}];
const q=new ConversionQueue();
q.begin(rows,{selected:'done',all:true});assert.equal(q.next(rows),'a');assert.equal(q.next(rows),'b');assert.equal(q.next(rows),null,'Never rerun completed or attention items automatically');
q.begin(rows,{selected:'b',all:true});assert.equal(q.next(rows),'a','Queue order, not selected waiting row');assert.equal(q.next(rows),'b');assert.equal(q.next(rows),null,'Failed launch left waiting cannot loop');
q.begin(rows,{selected:'bad',all:true});assert.equal(q.next(rows),'a','Batch order does not prioritize the selected attention item');assert.equal(q.next(rows),'b');assert.equal(q.next(rows),null);q.stop();assert.equal(q.next(rows),null);
q.begin(rows,{selected:'b'});assert.equal(q.next(rows),'b');assert.equal(q.next(rows),null,'Explicit selected-video action only');
q.begin(rows,{all:true,includeAttention:true});assert.equal(q.next(rows),'a');assert.equal(q.next(rows),'b');assert.equal(q.next(rows),'bad');assert.equal(q.next(rows),null);
const paused=rows.map(r=>({...r,...(r.id==='b'?{status:'paused'}:{})}));q.begin(paused,{selected:'b',all:true});assert.equal(q.next(paused),'a','Batch resume follows queue order even if another paused item is selected');assert.equal(q.next(paused),'b');
q.begin(paused,{selected:'b'});assert.equal(q.next(paused),'b','Explicit single-video resume retains its target');assert.equal(q.next(paused),null);
q.restore('a');assert.equal(q.next(rows),'b','Restore live session without repeating active item');
q.begin([{id:'done',status:'complete'}],{selected:'done',all:true});assert.equal(q.next([{id:'done',status:'complete'}]),null,'Batch action never reruns a completed output');
q.begin([{id:'done',status:'complete'}],{selected:'done'});assert.equal(q.next([{id:'done',status:'complete'}]),'done','Explicit new version remains a single-video action');
assert.equal(pendingVideos(rows).length,2);
console.log('Conversion queue: ordering, resume, pause, restore, failures, explicit single-video and completed skips passed.');

q.begin(rows,{all:true});assert.equal(q.next(rows),'a');assert.equal(q.next(rows.map(r=>r.id==='b'?{...r,status:'complete'}:r)),null,'Do not restart a movie completed outside the session');

const unfinished=[{id:'a',status:'paused'},{id:'b',status:'attention'},{id:'c',status:'attention'},{id:'d',status:'complete'}];
q.begin(unfinished,{selected:'a',all:true,includeAttention:true});assert.equal(q.next(unfinished),'a');unfinished[0].status='attention';assert.equal(q.next(unfinished),'b');assert.equal(q.next(unfinished),'c');assert.equal(q.next(unfinished),null,'Preview/failure cannot retry itself forever or stop remaining explicit repairs');
q.restore('a',{includeAttention:true});assert.equal(q.next(unfinished),'b');assert.equal(q.next(unfinished),'c');assert.equal(q.next(unfinished),null,'Reload preserves explicit repair-all intent without replaying current item');

// Reorder remaining work during a live batch, preserving consumed IDs.
const live=[{id:'a',status:'waiting'},{id:'b',status:'waiting'},{id:'c',status:'waiting'}];
q.begin(live,{all:true});assert.equal(q.next(live),'a');live[0].status='running';
const reordered=[live[2],live[0],live[1]];q.reorder(reordered);
assert.equal(q.next(reordered),'c');assert.equal(q.next(reordered),'b');assert.equal(q.next(reordered),null);
q.restore('a');q.reorder(reordered);assert.equal(q.next(reordered),'c');assert.equal(q.next(reordered),'b');
live[0].status='waiting';q.begin(live,{selected:'a'});q.reorder(reordered);assert.equal(q.next(reordered),'a');assert.equal(q.next(reordered),null,'Reorder cannot turn a explicit single-video job into a batch');

const completed={runID:'r1',rowID:'a',action:'batch',code:0,paused:false};
assert.deepEqual(missedCompletion({lastFinished:completed,running:null},{id:'r1'},new Set()),completed);
assert.equal(missedCompletion({lastFinished:completed,running:{id:'r2'}},{id:'r2'},new Set()),null);
assert.equal(missedCompletion({lastFinished:completed},{id:'r2'},new Set()),null);
assert.equal(missedCompletion({lastFinished:completed},null,new Set(['r1'])),null);
assert.equal(missedCompletion({running:null},null,new Set()),null,'Quiet or missing worker is not proof of completion');
assert.equal(restorableCompletion({lastFinished:completed,running:null},{ui:{autoQueue:false}}),null);
assert.deepEqual(restorableCompletion({lastFinished:completed,running:null},{ui:{autoQueue:true}}),completed);
for(const patch of [{paused:true},{finalizationError:'write failed'},{action:'speech-studio'}])assert.equal(restorableCompletion({lastFinished:{...completed,...patch}},{ui:{autoQueue:true}}),null);
console.log('Native completion recovery: missed/duplicate/stale events, active ownership, pause and explicit queue intent passed.');
