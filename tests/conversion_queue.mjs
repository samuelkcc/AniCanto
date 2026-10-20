import assert from 'node:assert/strict';
import {ConversionQueue,pendingVideos} from '../studio/web/conversion-queue.js';
const rows=[{id:'done',status:'complete'},{id:'a',status:'waiting'},{id:'b',status:'waiting'},{id:'bad',status:'attention'}];
const q=new ConversionQueue();
q.begin(rows,{selected:'done',all:true});assert.equal(q.next(rows),'a');assert.equal(q.next(rows),'b');assert.equal(q.next(rows),null,'Never rerun completed or attention items automatically');
q.begin(rows,{selected:'b',all:true});assert.equal(q.next(rows),'a','Queue order, not selected waiting row');assert.equal(q.next(rows),'b');assert.equal(q.next(rows),null,'Failed launch left waiting cannot loop');
q.begin(rows,{selected:'bad',all:true});assert.equal(q.next(rows),'bad');assert.equal(q.next(rows),'a');q.stop();assert.equal(q.next(rows),null);
q.begin(rows,{selected:'b'});assert.equal(q.next(rows),'b');assert.equal(q.next(rows),null,'Expert selected only');
q.begin(rows,{all:true,includeAttention:true});assert.equal(q.next(rows),'a');assert.equal(q.next(rows),'b');assert.equal(q.next(rows),'bad');assert.equal(q.next(rows),null);
const paused=rows.map(r=>({...r,...(r.id==='b'?{status:'paused'}:{})}));q.begin(paused,{selected:'b',all:true});assert.equal(q.next(paused),'b','Resume paused selected first');assert.equal(q.next(paused),'a');
q.restore('a');assert.equal(q.next(rows),'b','Restore live session without repeating active item');
q.begin([{id:'done',status:'complete'}],{selected:'done',all:true});assert.equal(q.next([{id:'done',status:'complete'}]),null,'Batch action never reruns a completed output');
q.begin([{id:'done',status:'complete'}],{selected:'done'});assert.equal(q.next([{id:'done',status:'complete'}]),'done','Explicit new version remains a single-video action');
assert.equal(pendingVideos(rows).length,2);
console.log('Conversion queue: ordering, resume, pause, restore, failures, expert single and completed skips passed.');

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
live[0].status='waiting';q.begin(live,{selected:'a'});q.reorder(reordered);assert.equal(q.next(reordered),'a');assert.equal(q.next(reordered),null,'Reorder cannot turn a single Expert job into a batch');
