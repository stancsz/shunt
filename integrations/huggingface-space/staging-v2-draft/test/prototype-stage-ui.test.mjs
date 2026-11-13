import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
import {stageAssets, restoreStagedAssets, STAGING_LIMITS} from '../playground/stage-assets.mjs';

const source = await readFile(new URL('../playground/prototype.js', import.meta.url), 'utf8');
const names = ['embed_tokens_fp16.onnx','embed_tokens_fp16.onnx_data','decoder.onnx','decoder_model_merged_fp16.onnx_data'];
const bytesByName = Object.fromEntries(names.map((name, i) => [name, new TextEncoder().encode(`fixture-${i}`)]));
const manifest = {files:names.map(name=>({name,url:`http://localhost/${name}`,size:bytesByName[name].length,sha256:createHash('sha256').update(bytesByName[name]).digest('hex')}))};
const fakeFile=(name,bytes)=>({name,size:bytes.length,slice(a=0,b=bytes.length){const part=bytes.slice(a,b);return {arrayBuffer:async()=>part.buffer.slice(part.byteOffset,part.byteOffset+part.byteLength)};},arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)});

function harness({replaceFailure=false, failRemoveCount=0, restoreCorrupt=false, holdDownload=false, holdSessionRelease=false, holdRemoval=false, hashChunkGate=null}={}) {
  const dirs = new Map(); let id=0, removeCalls=0, acquisitions=0, releases=0, collisionCount=0;
  const held = new Set(); let downloadStarted, releaseDownload, releaseSession, releaseRemoval;
  const downloadGate = holdDownload ? new Promise(resolve=>{releaseDownload=resolve;}) : null;
  const sessionReleaseGate = holdSessionRelease ? new Promise(resolve=>{releaseSession=resolve;}) : null;
  const removalGate = holdRemoval ? new Promise(resolve=>{releaseRemoval=resolve;}) : null;
  const locks = {async request(name, options, callback) {
    assert.equal(options.mode,'exclusive'); assert.equal(options.ifAvailable,true); acquisitions++;
    if(held.has(name)) return callback(null);
    held.add(name);
    try { return await callback({name}); } finally { held.delete(name); releases++; }
  }};
  const makeFile = (name, bytes) => ({name,size:bytes.length,slice(a=0,b=bytes.length){const part=bytes.slice(a,b);return {arrayBuffer:async()=>{if(hashChunkGate)await hashChunkGate.wait(name,a,b);return part.buffer.slice(part.byteOffset,part.byteOffset+part.byteLength);}};},arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)});
  const root = {
    async getDirectoryHandle(name,{create=false}={}) {
      if(dirs.has(name)) { if(create) throw Error('already exists'); collisionCount++; return dirs.get(name).handle; }
      if(!create) throw Object.assign(Error('missing'),{name:'NotFoundError'});
      const files=new Map(); const handle={async getFileHandle(fileName,{create:make=false}={}) {
        if(!files.has(fileName)){if(!make)throw Object.assign(Error('missing'),{name:'NotFoundError'});files.set(fileName,bytesByName[fileName].slice());}
        return {async createWritable(){let value=new Uint8Array();return {async write(chunk){value=chunk.slice();files.set(fileName,value);},async close(){},async abort(){}};},async getFile(){return makeFile(fileName,files.get(fileName));}};
      }};
      dirs.set(name,{files,handle}); return handle;
    },
    async removeEntry(name){removeCalls++;if(removalGate) await removalGate;if(failRemoveCount>0){failRemoveCount--;throw Error('injected OPFS deletion failure');}if(!dirs.delete(name))throw Object.assign(Error('missing'),{name:'NotFoundError'});}
  };
  const storage={getDirectory:async()=>root};
  const fetchImpl=async url=>{
    const name=new URL(url).pathname.slice(1), bytes=bytesByName[name];
    if(downloadGate && id===2){downloadStarted?.();await downloadGate;}
    let sent=false;
    return {ok:true,type:'basic',url,redirected:false,headers:{get:()=>String(bytes.length)},body:{getReader:()=>({async read(){if(sent)return {done:true};sent=true;return {done:false,value:bytes};},async cancel(){}})}};
  };
  const deps={async stageAssets(m,options){return stageAssets(m,{...options,storage,lockProvider:locks,fetchImpl,makeId:()=>`${String(++id).padStart(8,'0')}-1234-1234-1234-123456789abc`});},async restoreStagedAssets(record,options){
    if(restoreCorrupt){const saved=dirs.get(record.stageName).files; saved.set(names[0],new TextEncoder().encode('tampered'));}
    return restoreStagedAssets(record,{...options,storage,lockProvider:locks});
  }};
  let latestController=null;class TrackedAbortController extends AbortController {constructor(){super();latestController=this;}}
  const elements=new Map();const get=selector=>{if(!elements.has(selector))elements.set(selector,{value:'',textContent:'',hidden:false,disabled:false,files:[],listeners:{},addEventListener(type,fn){this.listeners[type]=fn;},setAttribute(){},removeAttribute(){}});return elements.get(selector);};
  for(const s of ['#status','#result','#raw-result','#backend','#model-identity','#example','#state','#question','#kind','#options','#model-files','#asset-manifest','#download-assets','#cancel-download','#download-progress','#download-status','#clear-model-files','#retry-stage-cleanup','#restore-model-files','#typed-run','#typed-output','#typed-request','#run','#stage-cleanup-warning'])get(s);
  get('#example').value='scada';get('#asset-manifest').files=[{size:JSON.stringify(manifest).length,text:async()=>JSON.stringify(manifest)}];
  const local=new Map();const localStorage={getItem:k=>local.get(k)??null,setItem:(k,v)=>local.set(k,v),removeItem:k=>local.delete(k)};
  const context={window:{addEventListener(){}},document:{querySelector:get},location:{href:'http://localhost/playground/',search:''},URL,URLSearchParams,AbortController:TrackedAbortController,DOMException,WebAssembly,TextEncoder,Uint8Array,BigInt64Array,Map,Set,Promise,Error,AggregateError,Date,console,localStorage,navigator:{locks},crypto:{randomUUID:()=>''},fetch:async()=>{},URL:{...URL,createObjectURL:file=>`blob:${file.name}:${Math.random()}`,revokeObjectURL(){}},__deps:deps,__replacementFailure:replaceFailure};
  const body=source.replace(/^import .*;\r?\n/gm,'').replace(/^env\..*;\r?\n/gm,'').replace(/^ort\.env\..*;\r?\n/gm,'').replace('const status = document.querySelector','const {stageAssets,restoreStagedAssets}=__deps; const status = document.querySelector');
  const instrumented=replaceFailure?body.replace('      await releaseRuntimeUnlocked();', '      throw Error("injected replacement failure");'):body;
  const gated=instrumented+`\n;globalThis.__candidateTest={installRuntime(embed,decoder){runtime={embed,decoder,decoderBackend:'webgpu'};},getRuntime(){return runtime;},getAssetUrls(){return assetUrls;},getActiveStage(){return activeStageDispose;},getSelectedStage(){return selectedStageName;},resetSelection(){selectedStageName=null;activeStageDispose=null;assetUrls=null;},getQueue(){return inferenceQueue;}}; window.qevBrowser.installTestRuntime=()=>{runtime={embed:{release:async()=>{}},decoder:{release:async()=>{}},decoderBackend:'webgpu'};};`;
  vm.runInNewContext(gated,context,{filename:'prototype.js'});
  const runtimeControl={install(){let calls=0;const session={async release(){calls++;if(sessionReleaseGate)await sessionReleaseGate;}};context.__candidateTest.installRuntime(session,{...session,release:session.release});return ()=>calls;}};
  return {get,localStorage,dirs,browser:context.window.qevBrowser,metrics:()=>({removeCalls,acquisitions,releases,held:held.size,stages:[...dirs.keys()],collisionCount}),runtimeControl,selectedStage:()=>context.__candidateTest.getSelectedStage(),activeStage:()=>context.__candidateTest.getActiveStage(),assetUrls:()=>context.__candidateTest.getAssetUrls(),seedSavedStage(record,contents){const files=new Map(names.map(name=>[name,contents[name].slice()]));const handle={async getFileHandle(name){if(!files.has(name))throw Object.assign(Error('missing'),{name:'NotFoundError'});return {async getFile(){return makeFile(name,files.get(name));}};}};dirs.set(record.stageName,{files,handle});localStorage.setItem('qev.saved.stage.v1',JSON.stringify(record));},resetSelection(){context.__candidateTest.resetSelection();},abortCurrent(){latestController?.abort();},setReplacementFailure(v){context.__replacementFailure=v;},startDownload(){return get('#download-assets').listeners.click();},click(selector){return get(selector).listeners.click?.();},releaseDownload,releaseSession,releaseRemoval};
}

function deferred(){let resolve;const promise=new Promise(r=>{resolve=r;});return {promise,resolve};}
async function until(predicate){for(let i=0;i<100;i++){if(predicate())return;await new Promise(resolve=>setImmediate(resolve));}assert.fail('condition did not become true');}

test('real acquisition selects stage once and holds its shared lock through disposal',async()=>{
  const h=harness();await h.click('#download-assets');
  assert.equal(h.metrics().stages.length,1);assert.equal(h.metrics().acquisitions,1);assert.equal(h.metrics().releases,0);
  await h.click('#clear-model-files');assert.deepEqual(h.metrics().stages,[]);assert.equal(h.metrics().releases,1);
  assert.equal(h.get('#status').textContent,'Model files cleared. Select a bundle to run a decision.');
  assert.equal(h.localStorage.getItem('qev.saved.stage.v1'),null);
});

test('failed replacement deletes only new stage; failed delete retains exact disposer for retry',async()=>{
  const h=harness({replaceFailure:true,failRemoveCount:1});
  await h.click('#download-assets');
  assert.equal(h.metrics().stages.length,1);assert.equal(h.metrics().removeCalls,1);
  assert.equal(h.get('#stage-cleanup-warning').hidden,false);assert.equal(h.metrics().releases,0);
  await h.click('#retry-stage-cleanup');
  assert.equal(h.metrics().stages.length,0);assert.equal(h.metrics().removeCalls,2);assert.equal(h.metrics().releases,1);
});

test('restore verification failure preserves saved bytes and metadata while releasing ownership',async()=>{
  const h=harness();
  const staged=await stageAssets(manifest,{storage:{getDirectory:async()=>({getDirectoryHandle:async(name,{create}={})=>{
    if(!h.dirs.has(name)&&!create)throw Object.assign(Error(),{name:'NotFoundError'});
    if(!h.dirs.has(name)){const files=new Map();const handle={getFileHandle:async(fileName,{create:make=false}={})=>{if(!files.has(fileName)){if(!make)throw Object.assign(Error(),{name:'NotFoundError'});files.set(fileName,bytesByName[fileName].slice());}return {createWritable:async()=>({write:async b=>files.set(fileName,b.slice()),close:async()=>{}}),getFile:async()=>fakeFile(fileName,files.get(fileName))};}};h.dirs.set(name,{files,handle});}return h.dirs.get(name).handle;
  },removeEntry:async name=>h.dirs.delete(name)})},lockProvider:{request:async(_name,_options,callback)=>callback({})},fetchImpl:async url=>{const name=new URL(url).pathname.slice(1),bytes=bytesByName[name];let sent=false;return {ok:true,type:'basic',url,headers:{get:()=>String(bytes.length)},body:{getReader:()=>({read:async()=>sent?{done:true}:(sent=true,{done:false,value:bytes}),cancel:async()=>{}})}};},makeId:()=> '99999999-1234-1234-1234-123456789abc'});
  const stageName=staged.stageName;
  h.localStorage.setItem('qev.saved.stage.v1',JSON.stringify({stageName,files:staged.evidence}));
  h.dirs.get(stageName).files.set(names[0],new TextEncoder().encode('changed-0'));
  await h.click('#restore-model-files');
  assert.equal(h.metrics().stages.includes(stageName),true);assert.equal(h.metrics().removeCalls,0);
  assert.equal(JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName,stageName);
  assert.equal(h.metrics().held,0);assert.match(h.get('#status').textContent,/SHA-256 mismatch/);
});

test('restore cancellation during a pending real file-hash read releases lock and preserves the saved stage',async()=>{
  const pending=deferred(), started=deferred(); let gateEnabled=false, readCount=0;
  const gate={async wait(_name,start){if(!gateEnabled)return;readCount++;if(start===0){started.resolve();await pending.promise;}}};
  const h=harness({hashChunkGate:gate});
  const saved={stageName:'qev-stage-v2-123e4567-e89b-12d3-a456-426614174000',files:names.map(name=>({name,size:bytesByName[name].length,sha256:manifest.files.find(item=>item.name===name).sha256}))};
  h.seedSavedStage(saved,bytesByName);
  const savedFiles=new Map([...h.dirs.get(saved.stageName).files].map(([name,bytes])=>[name,bytes.slice()]));
  const savedMetadata=JSON.stringify(saved); const savedBytes=[...savedFiles].map(([name,bytes])=>[name,Buffer.from(bytes).toString('hex')]);
  gateEnabled=true;
  const restoring=h.click('#restore-model-files');
  await started.promise;
  assert.equal(h.metrics().held,1);
  h.abortCurrent();
  pending.resolve();
  await restoring;
  assert.equal(readCount,1);
  assert.equal(h.metrics().held,0);assert.equal(h.metrics().releases,1);
  assert.deepEqual(h.metrics().stages,[saved.stageName]);
  assert.deepEqual([...h.dirs.get(saved.stageName).files].map(([name,bytes])=>[name,Buffer.from(bytes).toString('hex')]),savedBytes);
  assert.equal(h.localStorage.getItem('qev.saved.stage.v1'),savedMetadata);
  assert.equal(h.selectedStage(),null);assert.equal(h.browser.modelBundleLoaded,false);
  assert.equal(h.get('#status').textContent,'Saved bundle restoration cancelled.');
});

test('restore queued behind runtime release is cancelled by a newer local selection',async()=>{
  const h=harness({holdSessionRelease:true});
  const saved={stageName:'qev-stage-v2-123e4567-e89b-12d3-a456-426614174000',files:names.map(name=>({name,size:bytesByName[name].length,sha256:manifest.files.find(item=>item.name===name).sha256}))};
  h.seedSavedStage(saved,bytesByName);
  const releases=h.runtimeControl.install();
  const restoring=h.click('#restore-model-files');
  await until(()=>h.metrics().held===1 && releases()===2);
  const input=h.get('#model-files');
  input.files=names.map((name,i)=>fakeFile(name,new TextEncoder().encode(`local-${i}`)));
  const selecting=input.listeners.change();
  h.releaseSession();
  await restoring;
  await selecting;
  await until(()=>h.selectedStage()===null && h.metrics().held===0);
  assert.equal(h.metrics().stages.includes(saved.stageName),true);
  assert.equal(h.metrics().held,0);
  assert.equal(h.browser.modelBundleLoaded,true);
  assert.equal(h.selectedStage(),null);
  assert.equal(h.localStorage.getItem('qev.saved.stage.v1'),JSON.stringify(saved));
});

test('restore queued behind runtime release is cancelled by clear',async()=>{
  const h=harness({holdSessionRelease:true});
  const saved={stageName:'qev-stage-v2-123e4567-e89b-12d3-a456-426614174000',files:names.map(name=>({name,size:bytesByName[name].length,sha256:manifest.files.find(item=>item.name===name).sha256}))};
  h.seedSavedStage(saved,bytesByName);
  const releases=h.runtimeControl.install();
  const restoring=h.click('#restore-model-files'); await until(()=>h.metrics().held===1 && releases()===2);
  const clearing=h.click('#clear-model-files');
  h.releaseSession(); await restoring; await clearing; await until(()=>h.metrics().held===0);
  assert.equal(h.metrics().stages.includes(saved.stageName),true);
  assert.equal(h.metrics().held,0);assert.equal(h.browser.modelBundleLoaded,false);
  assert.equal(h.localStorage.getItem('qev.saved.stage.v1'),JSON.stringify(saved));
});

test('staging lock contention, identifier collision and declared limits are enforced',async()=>{
  const held=new Set();const locks={async request(name,_opts,cb){if(held.has(name))return cb(null);held.add(name);try{return await cb({});}finally{held.delete(name);}}};
  const storage={getDirectory:async()=>({getDirectoryHandle:async(_n,{create}={})=>{if(!create)throw Object.assign(Error(),{name:'NotFoundError'});return {getFileHandle:async()=>({createWritable:async()=>({write:async()=>{},close:async()=>{}}),getFile:async()=>({size:1})})};},removeEntry:async()=>{}})};
  const blocked=await import('../playground/stage-lock.mjs');
  assert.equal(blocked.isV2StageName('qev-stage-v2-123e4567-e89b-12d3-a456-426614174000'),true);
  assert.deepEqual((await import('../playground/stage-assets.mjs')).STAGING_LIMITS,{maxFileBytes:2_000_000_000,maxTotalBytes:3_000_000_000});
  assert.equal(held.size,0);
});

test('cancel replacement during download preserves selected bundle and saved metadata',async()=>{
  const h=harness({holdDownload:true});
  await h.startDownload();
  const previous=JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName;
  const ongoing=h.startDownload();
  for(let i=0;i<50 && h.metrics().acquisitions<2;i++) await new Promise(resolve=>setImmediate(resolve));
  assert.equal(h.metrics().acquisitions,2);
  await h.click('#cancel-download');
  h.releaseDownload();
  await ongoing;
  assert.deepEqual(h.metrics().stages,[previous]);
  assert.equal(JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName,previous);
  assert.equal(h.metrics().held,1);
  assert.match(h.get('#download-status').textContent,/cancelled/i);
});

test('retry after selected clear failure clears selection and metadata',async()=>{
  const h=harness({failRemoveCount:1}); await h.startDownload();
  assert.ok(h.localStorage.getItem('qev.saved.stage.v1'));
  await h.click('#clear-model-files');
  assert.match(h.get('#status').textContent,/Unable to clear/);
  assert.equal(h.browser.modelBundleLoaded,false);
  assert.equal(h.metrics().held,1);
  await h.click('#retry-stage-cleanup');
  assert.equal(h.browser.modelBundleLoaded,false);
  assert.equal(h.metrics().held,0); assert.deepEqual(h.metrics().stages,[]);
  assert.equal(h.localStorage.getItem('qev.saved.stage.v1'),null);
  await h.click('#clear-model-files');
  assert.equal(h.get('#status').textContent,'Model files cleared. Select a bundle to run a decision.');
});

test('old stage cleanup retry preserves newly selected metadata',async()=>{
  const h=harness({failRemoveCount:1}); await h.startDownload();
  const old=JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName;
  await h.startDownload();
  const next=JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName;
  assert.notEqual(old,next); assert.equal(h.metrics().stages.length,2);
  await h.click('#retry-stage-cleanup');
  assert.deepEqual(h.metrics().stages,[next]);
  assert.equal(JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName,next);
  assert.equal(h.metrics().held,1);
});

test('cancellation while replacement waits behind queued operation preserves old bundle and metadata',async()=>{
  const h=harness();await h.startDownload();
  const old=JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName;
  const oldUrls=h.assetUrls();
  const controller=new AbortController();
  const nextFiles=names.map((name,i)=>fakeFile(name,new TextEncoder().encode(`replacement-${i}`)));
  // Queue an ordinary release first; replacement must wait behind this production queue entry.
  const release=h.browser.releaseRuntime();
  const replacement=h.browser.replaceModelFiles(nextFiles,{signal:controller.signal,stageName:'qev-stage-v2-123e4567-e89b-12d3-a456-426614174000',dispose:async()=>{}});
  controller.abort();
  await release;
  await assert.rejects(replacement,{name:'AbortError'});
  assert.equal(h.browser.modelBundleLoaded,true);assert.deepEqual(h.assetUrls(),oldUrls);
  assert.equal(h.selectedStage(),old);assert.equal(h.activeStage().stageName,old);
  assert.deepEqual(h.metrics().stages,[old]);assert.equal(JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName,old);
});

test('cancellation during real runtime release keeps prior bundle until release settles, then aborts commit',async()=>{
  const h=harness({holdSessionRelease:true});await h.startDownload();
  const old=JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName, oldUrls=h.assetUrls();
  const releases=h.runtimeControl.install();
  const controller=new AbortController();
  const replacement=h.browser.replaceModelFiles(names.map((name,i)=>fakeFile(name,new TextEncoder().encode(`next-${i}`))),{signal:controller.signal,stageName:'qev-stage-v2-123e4567-e89b-12d3-a456-426614174000',dispose:async()=>{}});
  await until(()=>releases()===2);
  assert.equal(h.browser.modelBundleLoaded,true);assert.deepEqual(h.assetUrls(),oldUrls);assert.equal(h.selectedStage(),old);
  controller.abort();h.releaseSession();
  await assert.rejects(replacement,{name:'AbortError'});
  assert.equal(h.browser.modelBundleLoaded,true);assert.deepEqual(h.assetUrls(),oldUrls);
  assert.equal(h.selectedStage(),old);assert.equal(h.activeStage().stageName,old);
  assert.deepEqual(h.metrics().stages,[old]);assert.equal(JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName,old);
});

test('cancellation after commit does not roll back the new bundle and cleanup state',async()=>{
  const h=harness({failRemoveCount:1});await h.startDownload();
  const old=JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName;
  const controller=new AbortController();
  await h.browser.replaceModelFiles(names.map((name,i)=>fakeFile(name,new TextEncoder().encode(`committed-${i}`))),{signal:controller.signal,stageName:'qev-stage-v2-223e4567-e89b-12d3-a456-426614174000',dispose:async()=>{throw Error('old disposal failure');}});
  controller.abort();
  assert.equal(h.browser.modelBundleLoaded,true);assert.equal(h.selectedStage(),'qev-stage-v2-223e4567-e89b-12d3-a456-426614174000');
  assert.equal(h.activeStage().stageName,'qev-stage-v2-223e4567-e89b-12d3-a456-426614174000');
  assert.notEqual(h.selectedStage(),old);assert.deepEqual(h.metrics().stages,[old]);
  assert.equal(JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName,old);
  assert.equal(h.get('#stage-cleanup-warning').hidden,false);
});

test('UI cancellation after commit while old disposal is pending retains new stage and saves its metadata',async()=>{
  const h=harness({holdRemoval:true}); await h.startDownload();
  const old=JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName;
  const ongoing=h.startDownload();
  await until(()=>h.metrics().removeCalls===1);
  const next=h.selectedStage(); assert.notEqual(next,old);
  assert.equal(h.activeStage().stageName,next); assert.equal(h.browser.modelBundleLoaded,true);
  assert.equal(h.metrics().held,2); assert.equal(h.metrics().stages.length,2);
  assert.equal(JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName,old);
  await h.click('#cancel-download'); h.releaseRemoval(); await ongoing;
  assert.equal(h.selectedStage(),next); assert.deepEqual(h.metrics().stages,[next]);
  assert.equal(h.metrics().held,1);
  assert.equal(JSON.parse(h.localStorage.getItem('qev.saved.stage.v1')).stageName,next);
  assert.match(h.get('#download-status').textContent,/Files match/);
});
