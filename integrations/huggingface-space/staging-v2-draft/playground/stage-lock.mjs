// Hold one exclusive browser lock for as long as a staged bundle is active.
export const V2_STAGE_PREFIX = 'qev-stage-v2-';
export function isV2StageName(stageName) { return typeof stageName === 'string' && new RegExp(`^${V2_STAGE_PREFIX}[a-f0-9-]{36}$`, 'i').test(stageName); }
export async function acquireStageLock(stageName, locks = globalThis.navigator?.locks) {
  if (!isV2StageName(stageName)) throw Error('Invalid v2 stage identifier');
  if (!locks?.request) throw Error('This browser cannot safely share saved downloads across tabs');
  let release, accept, reject;
  const held = new Promise(resolve => { release = resolve; });
  const ready = new Promise((resolve, fail) => { accept=resolve; reject=fail; });
  const task=locks.request(`qev-stage-v2:${stageName}`, {mode:'exclusive',ifAvailable:true}, async lock => {
    if (!lock) { reject(Error('This saved download is in use in another tab')); return; }
    accept(); await held;
  });
  task.catch(reject);
  await ready;
  let released=false;
  return async () => { if (!released) { released=true; release(); await task; } };
}
