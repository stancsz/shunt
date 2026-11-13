import test from 'node:test';
import assert from 'node:assert/strict';
import {acquireStageLock, isV2StageName} from '../playground/stage-lock.mjs';
import {STAGING_LIMITS, cleanupV2Stage} from '../playground/stage-assets.mjs';
import {sha256File} from '../playground/hash-file.mjs';
import {createHash} from 'node:crypto';

const id = '123e4567-e89b-12d3-a456-426614174000';
const stage = `qev-stage-v2-${id}`;

function fakeLocks() {
  const held = new Set();
  return {held, async request(name, options, callback) {
    assert.equal(options.mode, 'exclusive');
    assert.equal(options.ifAvailable, true);
    if (held.has(name)) return callback(null);
    held.add(name);
    try { return await callback({name}); } finally { held.delete(name); }
  }};
}

test('v2 namespace does not accept legacy stage identifiers', () => {
  assert.equal(isV2StageName(stage), true);
  assert.equal(isV2StageName(`qev-stage-${id}`), false);
});

test('same-origin concurrent ownership is exclusive and explicit release permits next owner', async () => {
  const locks = fakeLocks();
  const first = await acquireStageLock(stage, locks);
  await assert.rejects(acquireStageLock(stage, locks), /in use in another tab/);
  await first();
  const second = await acquireStageLock(stage, locks);
  assert.equal(locks.held.size, 1);
  await second();
  assert.equal(locks.held.size, 0);
});

test('release failure leaves acquisition ownership held for retry', async () => {
  let calls = 0;
  const locks = {request: async (_name, _options, callback) => {
    const outcome = await callback({});
    if (++calls === 1) throw Error('simulated lock task failure');
    return outcome;
  }};
  const release = await acquireStageLock(stage, locks);
  await assert.rejects(release(), /simulated lock task failure/);
  // The failed Web Lock task has ended; this callback can safely reacquire.
  const retry = await acquireStageLock(stage, locks);
  await retry();
});

test('limits retain exact 2GB/file and 3GB total bounds', () => {
  assert.deepEqual(STAGING_LIMITS, {maxFileBytes: 2_000_000_000, maxTotalBytes: 3_000_000_000});
});

test('explicit cleanup refuses legacy names and releases v2 lock on storage failure', async () => {
  let released = false;
  const locks = {request: async (_name, _options, callback) => { try { return await callback({}); } finally { released = true; } }};
  const storage = {getDirectory: async () => ({removeEntry: async () => { throw Error('storage failure'); }})};
  await assert.rejects(cleanupV2Stage(stage, {storage, locks}), /storage failure/);
  assert.equal(released, true);
  await assert.rejects(cleanupV2Stage(`qev-stage-${id}`, {storage, locks}), /only accepts a v2/);
});

test('chunked file hashing preserves the digest and rejects an already-aborted signal', async () => {
  const bytes = new TextEncoder().encode('chunked hashing stays byte exact');
  const file = {size:bytes.length,slice(start,end){const part=bytes.slice(start,end);return {arrayBuffer:async()=>part.buffer.slice(part.byteOffset,part.byteOffset+part.byteLength)};}};
  const expected=createHash('sha256').update(bytes).digest('hex');
  assert.equal(await sha256File(file,5),expected);
  const controller=new AbortController();controller.abort();
  await assert.rejects(sha256File(file,5,{signal:controller.signal}),{name:'AbortError'});
});

test('empty-file hashing returns the standard digest and still honors pre-abort', async () => {
  const empty={size:0,slice(){assert.fail('empty files must not be read');}};
  assert.equal(await sha256File(empty),createHash('sha256').update(new Uint8Array()).digest('hex'));
  const controller=new AbortController();controller.abort();
  await assert.rejects(sha256File(empty,undefined,{signal:controller.signal}),{name:'AbortError'});
});
