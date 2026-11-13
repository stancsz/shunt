import {sha256} from './vendor/js-sha256-1.0.0.min.mjs';

// Bound transient input allocation while retaining the standard SHA-256 digest.
export async function sha256File(file, chunkBytes = 4 * 1024 * 1024, {signal} = {}) {
  if (!file || !Number.isSafeInteger(file.size) || file.size < 0 ||
      typeof file.slice !== 'function' || !Number.isSafeInteger(chunkBytes) ||
      chunkBytes < 1 || chunkBytes > 4 * 1024 * 1024) throw new Error('Invalid file or hash chunk size');
  if (signal?.aborted) throw new DOMException('Hashing cancelled', 'AbortError');
  const hash = sha256.create();
  for (let start = 0; start < file.size; start += chunkBytes) {
    if (signal?.aborted) throw new DOMException('Hashing cancelled', 'AbortError');
    const end = Math.min(start + chunkBytes, file.size);
    const bytes = await file.slice(start, end).arrayBuffer();
    if (signal?.aborted) throw new DOMException('Hashing cancelled', 'AbortError');
    if (bytes.byteLength !== end - start) throw new Error('Incomplete file read while hashing');
    hash.update(new Uint8Array(bytes));
  }
  return hash.hex();
}
