import sha256 from './vendor/js-sha256-1.0.0.min.mjs';
import {validateManifest, REQUIRED_ASSETS} from './acquire-assets.mjs';
import {sha256File} from './hash-file.mjs';
import {acquireStageLock, isV2StageName} from './stage-lock.mjs';

// Local research staging only. This does not authenticate the manifest or enable release.
export const STAGING_LIMITS = Object.freeze({maxFileBytes: 2_000_000_000, maxTotalBytes: 3_000_000_000});

// Only immutable Hub resolve URLs opt into automatic redirects. Browser Fetch hides
// intermediate hops; final-origin validation does not authenticate a manifest.
export function isImmutableHubUrl(value) {
  const u = new URL(value);
  return u.protocol === 'https:' && u.hostname === 'huggingface.co' && !u.port &&
    /^\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/resolve\/[0-9a-f]{40}\/.+/i.test(u.pathname);
}
export function validHubDestination(value) {
  if (!value) return false;
  const u = new URL(value);
  return u.protocol === 'https:' && !u.username && !u.password && !u.port &&
    (u.hostname === 'huggingface.co' || u.hostname.endsWith('.cdn.hf.co'));
}


export async function stageAssets(manifest, {signal, onProgress = () => {}, onCleanupFailure = () => {}, fetchImpl = fetch,
  storage = globalThis.navigator?.storage, makeId = () => globalThis.crypto.randomUUID(), baseUrl,
  limits = STAGING_LIMITS, lockProvider = globalThis.navigator?.locks} = {}) {
  const files = validateManifest(manifest, baseUrl);
  if (!Number.isSafeInteger(limits.maxFileBytes) || !Number.isSafeInteger(limits.maxTotalBytes) ||
      limits.maxFileBytes < 1 || limits.maxTotalBytes < 1 || limits.maxFileBytes > STAGING_LIMITS.maxFileBytes ||
      limits.maxTotalBytes > STAGING_LIMITS.maxTotalBytes) throw Error('Invalid staging limits');
  let total = 0;
  for (const file of files) { total += file.size; if (!Number.isSafeInteger(total) || file.size > limits.maxFileBytes || total > limits.maxTotalBytes) throw Error('Manifest exceeds staging size limits'); }
  if (signal?.aborted) throw new DOMException('Acquisition cancelled', 'AbortError');
  if (typeof storage?.getDirectory !== 'function') throw Error('Browser private file storage is unavailable');
  const root = await storage.getDirectory();
  const id = makeId();
  if (!/^[a-f0-9-]{36}$/i.test(id)) throw Error('Invalid staging identifier');
  const name = `qev-stage-v2-${id}`;
  // Claim the versioned namespace before even checking/creating its directory.
  const releaseLock = await acquireStageLock(name, lockProvider);
  let lockReleased = false;
  const unlock = async () => { if (!lockReleased) { await releaseLock(); lockReleased = true; } };
  // Do not reuse an existing directory, even if a generated identifier collides.
  let dir;
  try {
    try { await root.getDirectoryHandle(name); throw Error('Staging identifier already exists'); }
    catch (error) { if (error.name !== 'NotFoundError') throw error; }
    dir = await root.getDirectoryHandle(name, {create:true});
  } catch (error) { await unlock(); throw error; }
  let disposed = false;
  const dispose = async () => {
    if (!disposed) { await root.removeEntry(name, {recursive:true}); disposed = true; }
    await unlock();
  };
  const result = []; let completed = 0;
  try {
    for (const file of files) {
      if (signal?.aborted) throw new DOMException('Acquisition cancelled', 'AbortError');
      const hub = isImmutableHubUrl(file.url);
      const response = await fetchImpl(file.url, {signal, redirect:hub?'follow':'error', credentials:'omit', cache:'no-store'});
      const valid = response.ok && response.type !== 'opaqueredirect' && (hub
        ? validHubDestination(response.url)
        : !response.redirected && (!response.url || new URL(response.url).href === file.url));
      if (!valid) { try { await response.body?.cancel(); } catch {} throw Error(`Unsafe or failed response for ${file.name}`); }
      const declared = response.headers?.get?.('content-length');
      if (declared && (!/^\d+$/.test(declared) || Number(declared) !== file.size)) { try { await response.body?.cancel(); } catch {} throw Error(`Size mismatch for ${file.name}`); }
      if (!response.body?.getReader) throw Error('Streaming response body is required');
      const reader = response.body.getReader();
      let handle, writer;
      const hash = sha256.create(); let received = 0;
      try {
        handle = await dir.getFileHandle(file.name, {create:true});
        writer = await handle.createWritable();
        while (true) {
          if (signal?.aborted) throw new DOMException('Acquisition cancelled', 'AbortError');
          const {done, value} = await reader.read(); if (done) break;
          received += value.byteLength;
          if (received > file.size || completed + received > limits.maxTotalBytes) throw Error(`Size limit exceeded for ${file.name}`);
          hash.update(value); await writer.write(value);
          onProgress({name:file.name,fileBytes:received,fileSize:file.size,totalBytes:completed+received,totalSize:total});
        }
        if (signal?.aborted) throw new DOMException('Acquisition cancelled', 'AbortError');
        if (received !== file.size) throw Error(`Size mismatch for ${file.name}`);
        if (hash.hex().toLowerCase() !== file.sha256) throw Error(`SHA-256 mismatch for ${file.name}`);
        await writer.close();
      } catch (error) { await reader.cancel().catch(()=>{}); if (writer) await writer.abort().catch(()=>{}); throw error; }
      const staged = await handle.getFile();
      if (staged.size !== file.size) throw Error(`Staged file size mismatch for ${file.name}`);
      result.push(staged); completed += received;
    }
    if (signal?.aborted) throw new DOMException('Acquisition cancelled', 'AbortError');
    return {files:result, dispose, releaseLock:unlock, stageName:name, evidence:files.map(({name,size,sha256}) => ({name,size,sha256}))};
  } catch (error) {
    try { await dispose(); } catch (cleanup) { onCleanupFailure({dispose, stageName:name}); throw new AggregateError([error, cleanup], 'Staging failed and cleanup failed; v2 ownership remains held until cleanup succeeds'); }
    throw error;
  }
}

// Restore only an explicitly remembered stage; never create or remove storage on failure.
export async function restoreStagedAssets(record, {storage = globalThis.navigator?.storage, onProgress = () => {}, signal = null, lockProvider = globalThis.navigator?.locks} = {}) {
  if (!record || !isV2StageName(record.stageName) || !Array.isArray(record.files) || record.files.length !== REQUIRED_ASSETS.length) throw Error('Invalid v2 saved stage metadata');
  const byName = new Map(); let total = 0;
  for (const item of record.files) {
    if (!item || !REQUIRED_ASSETS.includes(item.name) || byName.has(item.name) || !Number.isSafeInteger(item.size) || item.size < 1 || item.size > STAGING_LIMITS.maxFileBytes || !/^[a-f0-9]{64}$/i.test(item.sha256 || '')) throw Error('Invalid saved stage metadata');
    total += item.size; if (!Number.isSafeInteger(total) || total > STAGING_LIMITS.maxTotalBytes) throw Error('Saved stage exceeds size limits'); byName.set(item.name,item);
  }
  if (REQUIRED_ASSETS.some(name=>!byName.has(name)) || typeof storage?.getDirectory !== 'function') throw Error('Saved stage unavailable');
  if(signal?.aborted) throw new DOMException('Restoration cancelled','AbortError');
  const root = await storage.getDirectory(); const releaseLock = await acquireStageLock(record.stageName, lockProvider);
  let lockReleased = false;
  const unlock = async () => { if (!lockReleased) { await releaseLock(); lockReleased = true; } };
  let directory;
  try { directory = await root.getDirectoryHandle(record.stageName); } catch (error) { await unlock(); throw error; }
  const files=[];
  try {
  for (const name of REQUIRED_ASSETS) {
    if(signal?.aborted) throw new DOMException('Restoration cancelled','AbortError');
    const item=byName.get(name), handle=await directory.getFileHandle(name), file=await handle.getFile();
    if(file.size!==item.size) throw Error(`Saved size mismatch for ${name}`);
    onProgress(name);
    if((await sha256File(file, undefined, {signal})).toLowerCase()!==item.sha256.toLowerCase()) throw Error(`Saved SHA-256 mismatch for ${name}`);
    if(signal?.aborted) throw new DOMException('Restoration cancelled','AbortError');
    files.push(file);
  }
  } catch (error) { await unlock(); throw error; }
  let disposed=false;
  const dispose = async () => { if(!disposed){await root.removeEntry(record.stageName,{recursive:true});disposed=true;} await unlock(); };
  return {files, releaseLock:unlock, stageName:record.stageName, evidence:record.files,
    dispose, abandon:unlock};
}

// Explicit v2-only cleanup. It refuses stages in use and never touches legacy names.
export async function cleanupV2Stage(stageName, {storage = globalThis.navigator?.storage, locks = globalThis.navigator?.locks} = {}) {
  if (!isV2StageName(stageName)) throw Error('Cleanup only accepts a v2 stage identifier');
  const release = await acquireStageLock(stageName, locks);
  try { const root = await storage.getDirectory(); await root.removeEntry(stageName, {recursive:true}); }
  finally { await release(); }
}
