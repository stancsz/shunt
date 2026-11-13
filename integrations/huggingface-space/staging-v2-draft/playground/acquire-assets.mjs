import sha256 from './vendor/js-sha256-1.0.0.min.mjs';

export const REQUIRED_ASSETS = Object.freeze([
  'embed_tokens_fp16.onnx', 'embed_tokens_fp16.onnx_data',
  'decoder.onnx', 'decoder_model_merged_fp16.onnx_data',
]);
// This in-memory prototype intentionally cannot acquire the real multi-GB bundle.
// A disk-backed streaming implementation is needed before increasing the cap.
export const DEFAULT_LIMITS = Object.freeze({ maxFileBytes: 64 * 1024 * 1024, maxTotalBytes: 64 * 1024 * 1024 });

function validateUrl(raw, baseUrl) {
  if (typeof raw !== 'string' || raw.length > 4096) throw Error('Invalid asset URL');
  const url = new URL(raw, baseUrl);
  if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password || url.hash || url.search) throw Error('Unsafe asset URL');
  if (url.protocol === 'http:' && !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) throw Error('HTTP is allowed only for loopback testing');
  return url;
}

export function validateManifest(manifest, baseUrl = globalThis.location?.href || 'http://localhost/') {
  if (!manifest || !Array.isArray(manifest.files) || manifest.files.length !== REQUIRED_ASSETS.length) throw Error('Manifest must contain exactly four files');
  const byName = new Map();
  for (const item of manifest.files) {
    if (!item || typeof item !== 'object' || !REQUIRED_ASSETS.includes(item.name)) throw Error('Unknown or invalid manifest entry');
    if (byName.has(item.name)) throw Error(`Duplicate manifest entry: ${item.name}`);
    if (!Number.isSafeInteger(item.size) || item.size <= 0) throw Error(`Invalid byte size for ${item.name}`);
    if (!/^[a-f0-9]{64}$/i.test(item.sha256 || '')) throw Error(`Invalid SHA-256 for ${item.name}`);
    byName.set(item.name, { name: item.name, size: item.size, sha256: item.sha256.toLowerCase(), url: validateUrl(item.url, baseUrl).href });
  }
  const missing = REQUIRED_ASSETS.filter(name => !byName.has(name));
  if (missing.length) throw Error(`Missing manifest entries: ${missing.join(', ')}`);
  return REQUIRED_ASSETS.map(name => byName.get(name));
}

export async function acquireAssets(manifest, { signal, onProgress = () => {}, fetchImpl = fetch, baseUrl, limits = DEFAULT_LIMITS } = {}) {
  const files = validateManifest(manifest, baseUrl);
  if (!Number.isSafeInteger(limits.maxFileBytes) || !Number.isSafeInteger(limits.maxTotalBytes) || limits.maxFileBytes < 1 || limits.maxTotalBytes < 1) throw Error('Invalid acquisition limits');
  if (limits.maxFileBytes > DEFAULT_LIMITS.maxFileBytes || limits.maxTotalBytes > DEFAULT_LIMITS.maxTotalBytes) throw Error('Acquisition limits cannot exceed the in-memory prototype cap');
  const totalExpected = files.reduce((sum, f) => sum + f.size, 0);
  if (files.some(f => f.size > limits.maxFileBytes) || totalExpected > limits.maxTotalBytes) throw Error('Manifest exceeds acquisition size limits');
  const acquired = [];
  let completed = 0;
  for (const file of files) {
    if (signal?.aborted) throw new DOMException('Acquisition cancelled', 'AbortError');
    const response = await fetchImpl(file.url, { signal, redirect: 'error', credentials: 'omit', cache: 'no-store' });
    if (!response.ok || response.redirected || (response.url && new URL(response.url).href !== file.url) || (response.type === 'opaqueredirect')) throw Error(`Unsafe or failed response for ${file.name}`);
    const declared = response.headers?.get?.('content-length');
    if (declared && (!/^\d+$/.test(declared) || Number(declared) !== file.size)) throw Error(`Size mismatch for ${file.name}`);
    if (!response.body?.getReader) throw Error('Streaming response body is required');
    const reader = response.body.getReader();
    const chunks = []; const hash = sha256.create(); let received = 0;
    try {
      while (true) {
        if (signal?.aborted) throw new DOMException('Acquisition cancelled', 'AbortError');
        const { done, value } = await reader.read();
        if (done) break;
        received += value.byteLength;
        if (received > file.size || received > limits.maxFileBytes || completed + received > limits.maxTotalBytes) throw Error(`Size limit exceeded for ${file.name}`);
        hash.update(value); chunks.push(value);
        onProgress({ name: file.name, fileBytes: received, fileSize: file.size, totalBytes: completed + received, totalSize: totalExpected });
      }
    } catch (error) { await reader.cancel().catch(() => {}); if (signal?.aborted || error?.name === 'AbortError') throw new DOMException('Acquisition cancelled', 'AbortError'); throw Error(`Download failed for ${file.name}: ${error.message || error}`); }
    if (received !== file.size) throw Error(`Size mismatch for ${file.name}: expected ${file.size}, received ${received}`);
    if (hash.hex().toLowerCase() !== file.sha256) throw Error(`SHA-256 mismatch for ${file.name}`);
    acquired.push(new File(chunks, file.name, { type: 'application/octet-stream' }));
    completed += received;
  }
  return acquired;
}
