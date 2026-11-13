// Local prototype: static files only. URLs are pinned for a reproducible check.
import * as ort from './offline-vendor/ort.webgpu.bundle.min.mjs';
import {Qwen2Tokenizer, env} from './offline-vendor/transformers.web.min.js';
env.allowRemoteModels = false;
env.allowLocalModels = true;
env.localModelPath = new URL('./models/', location.href).href;
ort.env.wasm.wasmPaths = new URL('./offline-vendor/', location.href).href;
import {stageAssets, restoreStagedAssets} from './stage-assets.mjs';
import {compileTypedRequest, formatTypedResponse} from './typed-adapter.mjs';
const status = document.querySelector('#status');
const result = document.querySelector('#result');
const params = new URLSearchParams(location.search);
const assetBase = params.get('assets');
let dir;
const bundleFiles = ['embed_tokens_fp16.onnx','embed_tokens_fp16.onnx_data','decoder.onnx','decoder_model_merged_fp16.onnx_data'];
let assetUrls = null;
let activeStageDispose = null;
const pendingStageCleanups = [];
let selectedStageName=null;
const SAVED_STAGE_KEY='qev.saved.stage.v1';
function forgetStageIfCurrent(name) { try { const saved=JSON.parse(localStorage.getItem(SAVED_STAGE_KEY)||'null'); if(saved?.stageName===name) localStorage.removeItem(SAVED_STAGE_KEY); } catch {} }
function trackPendingCleanup(item) { if (!pendingStageCleanups.includes(item)) pendingStageCleanups.push(item); showPendingCleanup(); }
function showPendingCleanup() { const el=document.querySelector('#stage-cleanup-warning'); if(el) el.hidden=pendingStageCleanups.length===0; }
try {
  if (assetBase) {
    dir = new URL(assetBase, location.href);
    if (!['http:', 'https:'].includes(dir.protocol) || dir.username || dir.password || dir.search || dir.hash) throw new Error('invalid asset base');
    if (!dir.pathname.endsWith('/')) dir.pathname += '/';
  } else dir = null;
} catch {
  const message = 'Invalid asset base. Use an HTTP(S) directory URL without credentials, query, or fragment, or select the four local model files.';
  if (status) status.textContent = message;
  document.querySelector('#run')?.setAttribute('disabled', '');
  throw new Error(message);
}
const tokenizerId = params.get('tokenizer') || 'Qwen/Qwen3.5-0.8B';
const tokenizerRevision = params.get('tokenizerRevision') || '2fc06364715b967f1860aea9cf38778875588b17';
const supportedCheckpoint = 'ba-research/Qev1.0-Qwen3.5-0.8B';
const requestedModel = params.get('model');
const legacyCheckpoint = params.get('checkpoint');
const checkpointId = requestedModel || legacyCheckpoint || supportedCheckpoint;
const checkpointRevision = params.get('checkpointRevision') || 'unresolved-from-browser-assets';
const decoderBackend = params.get('backend') === 'wasm' ? 'wasm' : 'webgpu';
const backendSelector = document.querySelector('#backend');
if (backendSelector) backendSelector.value = decoderBackend;
const modelIdentity = document.querySelector('#model-identity');
if (modelIdentity) modelIdentity.textContent = supportedCheckpoint;
if ((requestedModel && legacyCheckpoint && requestedModel !== legacyCheckpoint) || checkpointId !== supportedCheckpoint) {
  const message = `Unsupported checkpoint "${checkpointId}". This static package supports only ${supportedCheckpoint}; changing the checkpoint URL does not load different weights.`;
  if (status) status.textContent = message;
  document.querySelector('#run')?.setAttribute('disabled', '');
  throw new Error(message);
}
const examples = {
  "scada": {
    "state": "On April 16, 2024, near Edson, Alberta, the Calgary control centre observed a drop in Emerson Creek compressor station discharge pressure at 10:48. At 10:50, a station operator reported an explosion and fire and suspected a rupture of the Grande Prairie Mainline. The Transportation Safety Board reports that the controller decided to shut down and isolate the suspected ruptured section.",
    "question": "Which operational team should review this incident report?",
    "kind": "choice",
    "options": [
      "Pipeline control and emergency response",
      "Pipeline integrity engineering",
      "Instrumentation maintenance"
    ],
    "source": "https://www.tsb.gc.ca/eng/rapports-reports/pipeline/2024/p24h0018/p24h0018.html",
    "sourceLabel": "Transportation Safety Board of Canada · investigation P24H0018"
  },
  "vendor": {
    "state": "In April 2022, a U.S. company that regularly purchased equipment from a business partner received an email requesting a change in payment information. According to the U.S. Department of Justice, the sender was a fraudster posing as the partner, and the company wired $2,462,000 to the identified account.",
    "question": "Which review should receive this incident report?",
    "kind": "choice",
    "options": [
      "Accounts payable and fraud investigation",
      "Vendor account maintenance",
      "Procurement and supplier management"
    ],
    "source": "https://www.justice.gov/usao-mdfl/pr/united-states-recovers-24-million-obtained-business-email-compromise",
    "sourceLabel": "U.S. Department of Justice · October 31, 2023"
  },
  "support": {
    "state": "On May 3, 2024, Google Cloud reported Firebase Authentication and Identity Platform authentication failures affecting some customers. Its engineering team identified a mitigation strategy and was implementing it. The service health update reported that the issue was resolved for affected users by 15:27 Pacific time.",
    "question": "Which support team should investigate reports matching this incident?",
    "kind": "choice",
    "options": [
      "Identity and authentication incident support",
      "Application support",
      "Cloud network operations"
    ],
    "source": "https://status.cloud.google.com/incidents/rErZ4r752o4rt4qaotfL",
    "sourceLabel": "Google Cloud Service Health · May 3, 2024"
  }
};
const exampleSelector = document.querySelector('#example');
function loadExample() {
  const example = examples[exampleSelector.value];
  document.querySelector('#state').value = example.state;
  document.querySelector('#question').value = example.question;
  document.querySelector('#kind').value = example.kind;
  document.querySelector('#options').value = example.options.join('\n');
  result.textContent = '';
  document.querySelector('#raw-result').textContent = '';
  status.textContent = 'Assets not yet verified';
  const link = document.querySelector('#example-source');
  if (link) { link.href = example.source; link.textContent = example.sourceLabel + ' ↗'; }
}
if (exampleSelector) { exampleSelector.addEventListener('change', loadExample); loadExample(); }
let runtime;
let runtimeStage = 'idle';
let feedCapture = null;
const feedCaptureEvents = [];
async function sha256Bytes(bytes) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),v=>v.toString(16).padStart(2,'0')).join('');
}
async function feedIdentity(feeds, metadata) {
  const tensors = {};
  for (const [name,tensor] of Object.entries(feeds).sort(([a],[b])=>a<b?-1:a>b?1:0)) {
    const view = new Uint8Array(tensor.data.buffer,tensor.data.byteOffset,tensor.data.byteLength);
    tensors[name] = {dtype:tensor.type,shape:Array.from(tensor.dims),bytes:view.byteLength,sha256:await sha256Bytes(view)};
  }
  const canonical = JSON.stringify(Object.fromEntries(Object.entries(tensors).map(([name,value])=>[name,Object.fromEntries(Object.entries(value).sort(([a],[b])=>a<b?-1:a>b?1:0))])));
  const item = { ...metadata, tensors, feedSetSha256:await sha256Bytes(new TextEncoder().encode(canonical)) };
  feedCaptureEvents.push(item);
  if (feedCaptureEvents.length>200) feedCaptureEvents.shift();
  if (feedCapture) feedCapture.push(item);
}
const runtimeEvents = [];
function recordRuntimeEvent(stage, outcome, error) {
  const event = {at: new Date().toISOString(), stage, outcome};
  if (error) {
    event.name = error.name || 'Error';
    event.message = String(error.message || error);
    event.stack = error.stack || null;
  }
  runtimeEvents.push(event);
  if (runtimeEvents.length > 100) runtimeEvents.shift();
}
// All callers, including the UI and the public window.qevBrowser API, share
// one queue. This protects WebGPU sessions from overlapping run/dispose calls.
let inferenceQueue = Promise.resolve();
function assetUrl(name) { if (assetUrls?.[name]) return assetUrls[name]; if (dir) return new URL(name,dir).href; throw Error('Select the four local model files first.'); }
function selectModelFiles(files) {
  const selected = Array.from(files || []);
  if (selected.length !== bundleFiles.length) throw Error(`Select exactly these ${bundleFiles.length} files: ${bundleFiles.join(', ')}`);
  const byName = new Map();
  for (const file of selected) {
    if (!bundleFiles.includes(file.name)) throw Error(`Unsupported model file: ${file.name}`);
    if (byName.has(file.name)) throw Error(`Duplicate model file: ${file.name}`);
    byName.set(file.name,file);
  }
  const missing = bundleFiles.filter(name => !byName.has(name));
  if (missing.length) throw Error(`Missing model file(s): ${missing.join(', ')}`);
  return Object.fromEntries(bundleFiles.map(name => [name,byName.get(name)]));
}
function createBundleUrls(files, createUrl=URL.createObjectURL) {
  const selected=selectModelFiles(files), urls={};
  try { for (const name of bundleFiles) urls[name]=createUrl(selected[name]); }
  catch(error) { for (const url of Object.values(urls)) URL.revokeObjectURL(url); throw error; }
  return urls;
}
function revokeBundleUrls(urls) { if (urls) for (const url of Object.values(urls)) URL.revokeObjectURL(url); }
async function initForBackend(backend, decoderGraphUrl = assetUrl('decoder.onnx')) {
  runtimeStage = 'runtime-init';
  if (backend === 'webgpu' && !navigator.gpu) throw Error('WebGPU is unavailable in this browser');
  status.textContent = 'Loading tokenizer';
  runtimeStage = 'tokenizer-load';
  if (tokenizerId !== 'Qwen/Qwen3.5-0.8B' || tokenizerRevision !== '2fc06364715b967f1860aea9cf38778875588b17') throw Error('Offline tokenizer identity is unsupported');
  const tokenizerBase = new URL('./models/Qwen/Qwen3.5-0.8B/', location.href);
  const [tokenizerJSON, tokenizerConfig] = await Promise.all(['tokenizer.json','tokenizer_config.json'].map(async name => { const r = await fetch(new URL(name,tokenizerBase)); if(!r.ok)throw Error(`Local tokenizer ${name} HTTP ${r.status}`); return r.json(); }));
  if (tokenizerConfig.tokenizer_class !== 'Qwen2Tokenizer') throw Error('Unexpected local tokenizer class');
  const tokenizer = new Qwen2Tokenizer(tokenizerJSON, tokenizerConfig);
  status.textContent = 'Loading embedding model (about 509 MB)';
  runtimeStage = 'embedding-session-create';
  const embed = await ort.InferenceSession.create(assetUrl('embed_tokens_fp16.onnx'),{executionProviders:['webgpu'],externalData:[{path:'embed_tokens_fp16.onnx_data',data:assetUrl('embed_tokens_fp16.onnx_data')}]});
  try {
  status.textContent = `Loading ${backend === 'wasm' ? 'WASM CPU' : 'WebGPU'} decision model (about 1.5 GB)`;
    runtimeStage = 'decoder-session-create';
    const decoderRuntime = backend === 'wasm'
      ? await import('./offline-vendor/ort.wasm.bundle.min.mjs')
      : ort;
    const decoder = await decoderRuntime.InferenceSession.create(decoderGraphUrl, {executionProviders:[backend],externalData:[{path:'decoder_model_merged_fp16.onnx_data',data:assetUrl('decoder_model_merged_fp16.onnx_data')}]});
    runtimeStage = 'ready';
    recordRuntimeEvent('runtime-init', 'success');
    return {tokenizer, embed, decoder, decoderBackend:backend, decoderRuntime};
  } catch (error) {
    recordRuntimeEvent(runtimeStage, 'error', error);
    runtimeStage = 'embedding-session-release-after-init-error';
    await embed.release();
    throw error;
  }
}
async function score(prompt) {
  const {tokenizer,embed,decoder,decoderRuntime,decoderBackend:activeBackend}=runtime;
  runtimeStage = 'tokenizer-encode';
  const text=tokenizer.apply_chat_template([{role:'user',content:prompt}],{tokenize:false,add_generation_prompt:true,enable_thinking:false});
  const encoded=await tokenizer(text,{padding:false,truncation:false});
  const ids=encoded.input_ids; const n=ids.dims[1];
  if(n>2048) throw Error('Input exceeds the model token limit');
  const tokenTensor=new ort.Tensor('int64',BigInt64Array.from(ids.data),[1,n]);
  let emb, out, feeds;
  try {
  runtimeStage = 'embedding-run';
  emb=await embed.run({input_ids:tokenTensor});
  const pos=new BigInt64Array(3*n); for(let k=0;k<3;k++) for(let i=0;i<n;i++) pos[k*n+i]=BigInt(i);
  feeds={inputs_embeds:activeBackend === 'wasm' ? new decoderRuntime.Tensor('float32',Float32Array.from(emb.inputs_embeds.data),emb.inputs_embeds.dims) : emb.inputs_embeds,attention_mask:new decoderRuntime.Tensor('int64',BigInt64Array.from({length:n},()=>1n),[1,n]),position_ids:new decoderRuntime.Tensor('int64',pos,[3,1,n])};
  for(let i=0;i<24;i++) {
    if(i%4===3) { for(const part of ['key','value']) feeds[`past_key_values.${i}.${part}`]=new decoderRuntime.Tensor('float16',new Uint16Array(0),[1,2,0,256]); }
    else { feeds[`past_conv.${i}`]=new decoderRuntime.Tensor('float16',new Uint16Array(6144*4),[1,6144,4]); feeds[`past_recurrent.${i}`]=new decoderRuntime.Tensor('float16',new Uint16Array(16*128*128),[1,16,128,128]); }
  }
  if (feedCapture) await feedIdentity(feeds,{phase:'score',backend:activeBackend,tokenCount:n,renderedPromptSha256:await sha256Bytes(new TextEncoder().encode(text)),tokenIdsSha256:await sha256Bytes(new Uint8Array(ids.data.buffer,ids.data.byteOffset,ids.data.byteLength)),decoderGraph:assetUrl('decoder.onnx'),decoderRuntime:`onnxruntime-web 1.31.1/${activeBackend}`,decoderSession:decoder?.handler?.session?.constructor?.name || 'onnxruntime-web-InferenceSession'});
  runtimeStage = 'decoder-run';
  out=await decoder.run(feeds, ['qev_scores']); return Number(out.qev_scores.data[n-1]);
  } catch (error) {
    recordRuntimeEvent(runtimeStage, 'error', error);
    throw error;
  } finally {
    runtimeStage = 'tensor-cleanup';
    tokenTensor.dispose();
    if (feeds) for (const tensor of Object.values(feeds)) if (tensor !== emb?.inputs_embeds) tensor.dispose();
    if (emb) for (const tensor of Object.values(emb)) tensor.dispose();
    if (out) for (const tensor of Object.values(out)) tensor.dispose();
  }
}
async function captureDecoderTrace(record, backend, diagnosticGraphUrl, requestedOutputs) {
  const sha256 = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
  if (!['wasm', 'webgpu'].includes(backend)) throw Error('Backend must be wasm or webgpu');
  if (!Array.isArray(requestedOutputs) || requestedOutputs.length < 1 || requestedOutputs.length > 8 ||
      requestedOutputs.some(name => typeof name !== 'string' || !name) || new Set(requestedOutputs).size !== requestedOutputs.length)
    throw Error('Select 1–8 unique diagnostic output names');
  const graphUrl = new URL(diagnosticGraphUrl, location.href);
  if (!['http:', 'https:', 'blob:'].includes(graphUrl.protocol) || graphUrl.username || graphUrl.password || graphUrl.search || graphUrl.hash)
    throw Error('Diagnostic graph URL must be HTTP(S) or Blob, without credentials, query, or fragment');
  const task = inferenceQueue.then(async () => {
    activeInferences++;
    try {
      if (runtime) await releaseRuntimeUnlocked();
      const configuredGraph = params.get('traceGraph');
      if (!configuredGraph || new URL(configuredGraph,location.href).href !== graphUrl.href)
        throw Error('Load this page with ?traceGraph=<diagnostic-graph-URL> before runtime initialization');
      const response = await fetch(graphUrl); if(!response.ok) throw Error(`Graph HTTP ${response.status}`);
      const graphBytes = await response.arrayBuffer();
      runtime = await initForBackend(backend, graphUrl.href);
      const traceSession = runtime.decoder;
      try {
        const available = traceSession.outputNames;
        if (requestedOutputs.some(name => !available.includes(name))) throw Error(`Requested output names absent from diagnostic graph: ${requestedOutputs.filter(name => !available.includes(name)).join(', ')}`);
        const prompt = (await compiledPrompts(record))[0];
        const rendered = runtime.tokenizer.apply_chat_template([{role:'user',content:prompt}],{tokenize:false,add_generation_prompt:true,enable_thinking:false});
        const encoded = await runtime.tokenizer(rendered,{padding:false,truncation:false});
        const ids = encoded.input_ids, n = ids.dims[1];
        if (n > 2048) throw Error('Input exceeds the model token limit');
        const tokenTensor = new runtime.decoderRuntime.Tensor('int64',BigInt64Array.from(ids.data),[1,n]);
        let emb, feeds, outputs;
        try {
          emb = await runtime.embed.run({input_ids:tokenTensor});
          const pos=new BigInt64Array(3*n); for(let k=0;k<3;k++) for(let i=0;i<n;i++) pos[k*n+i]=BigInt(i);
          feeds={inputs_embeds:backend==='wasm'?new runtime.decoderRuntime.Tensor('float32',Float32Array.from(emb.inputs_embeds.data),emb.inputs_embeds.dims):emb.inputs_embeds,attention_mask:new runtime.decoderRuntime.Tensor('int64',BigInt64Array.from({length:n},()=>1n),[1,n]),position_ids:new runtime.decoderRuntime.Tensor('int64',pos,[3,1,n])};
          for(let i=0;i<24;i++) {
            if(i%4===3) for(const part of ['key','value']) feeds[`past_key_values.${i}.${part}`]=new runtime.decoderRuntime.Tensor('float16',new Uint16Array(0),[1,2,0,256]);
            else {feeds[`past_conv.${i}`]=new runtime.decoderRuntime.Tensor('float16',new Uint16Array(6144*4),[1,6144,4]);feeds[`past_recurrent.${i}`]=new runtime.decoderRuntime.Tensor('float16',new Uint16Array(16*128*128),[1,16,128,128]);}
          }
          outputs = await traceSession.run(feeds, requestedOutputs);
          let total = 0;
          const tensors = requestedOutputs.map(name => {
            const tensor=outputs[name]; if(!tensor) throw Error(`Runtime omitted validated output ${name}`);
            const shape=Array.from(tensor.dims), count=shape.reduce((a,b)=>a*b,1); total+=count;
            if(shape.length<1 || shape.some(d=>!Number.isInteger(d)||d<1) || total>2000000) throw Error('Trace exceeds bounded scalar/tensor limits');
            if(tensor.type !== 'float32' && tensor.type !== 'float16') throw Error(`Unsupported capture type ${tensor.type}`);
            const half = v => {const s=v&32768?-1:1,e=(v>>>10)&31,f=v&1023;return e===31?(f?NaN:s*Infinity):s*(e?2**(e-15)*(1+f/1024):2**(-14)*f/1024);};
            const values=Array.from(tensor.data, tensor.type==='float16'?half:Number);
            if(values.length!==count || values.some(v=>!Number.isFinite(v))) throw Error(`Invalid values for ${name}`);
            return {name,shape,values};
          });
          return {backend, sameInput:{promptSha256:await sha256(new TextEncoder().encode(rendered)),tokenIds:Array.from(ids.data,String),embeddingSha256:await sha256(new Uint8Array(emb.inputs_embeds.data.buffer,emb.inputs_embeds.data.byteOffset,emb.inputs_embeds.data.byteLength))}, graph:{url:graphUrl.href,sha256:await sha256(graphBytes),outputs:requestedOutputs}, tensors};
        } finally {
          tokenTensor.dispose(); if(feeds) for(const tensor of Object.values(feeds)) if(tensor!==emb?.inputs_embeds) tensor.dispose();
          if(emb) for(const tensor of Object.values(emb)) tensor.dispose(); if(outputs) for(const tensor of Object.values(outputs)) tensor.dispose();
        }
      } finally { await releaseRuntimeUnlocked(); }
    } finally { activeInferences--; }
  });
  inferenceQueue=task.catch(()=>{}); return task;
}
async function compiledPrompts(record) {
  const prefix=`Context:\n${record.state}\n\nQuestion: ${record.question}\n`;
  if(record.kind==='noul') return [prefix+'Is the answer to this question yes? Answer Yes or No.'];
  return record.options.map(option=>prefix+`Proposed answer: ${option}\nIs this proposed answer correct? Answer Yes or No.`);
}
async function inferCpuReferenceUnlocked(record) {
  if (runtime?.decoderBackend === 'wasm') {
    const previous = runtime;
    runtime = null;
    const released = await Promise.allSettled([previous.embed.release(),previous.decoder.release()]);
    if (released.some(item=>item.status==='rejected')) throw Error('Failed to release WASM sessions before CPU comparison');
  }
  runtime ||= await initForBackend('webgpu');
  const prompts=await compiledPrompts(record);
  const values=[];
  for(const prompt of prompts) {
    const text=runtime.tokenizer.apply_chat_template([{role:'user',content:prompt}],{tokenize:false,add_generation_prompt:true,enable_thinking:false});
    const encoded=await runtime.tokenizer(text,{padding:false,truncation:false});
    const ids=encoded.input_ids, n=ids.dims[1];
    if(n>2048) throw Error('Input exceeds the model token limit');
    const tokenTensor=new runtime.decoderRuntime.Tensor('int64',BigInt64Array.from(ids.data),[1,n]);
    let emb, session, out, feeds, decoderTensorRuntime;
    try {
      runtimeStage = 'cpu-embedding-run';
      emb=await runtime.embed.run({input_ids:tokenTensor});
      runtimeStage = 'cpu-decoder-assets-fetch';
      const ortCpu=runtime.decoderBackend === 'wasm' ? runtime.decoderRuntime : await import('./offline-vendor/ort.wasm.bundle.min.mjs');
      runtimeStage = 'cpu-decoder-session-create';
      decoderTensorRuntime=ortCpu;
      session=runtime.decoderBackend === 'wasm' ? runtime.decoder : await decoderTensorRuntime.InferenceSession.create(assetUrl('decoder.onnx'),{executionProviders:['wasm'],externalData:[{path:'decoder_model_merged_fp16.onnx_data',data:assetUrl('decoder_model_merged_fp16.onnx_data')}]});
      runtimeStage = 'cpu-decoder-feed-create';
      const pos=new BigInt64Array(3*n); for(let k=0;k<3;k++) for(let i=0;i<n;i++) pos[k*n+i]=BigInt(i);
      feeds={inputs_embeds:new ortCpu.Tensor('float32',Float32Array.from(emb.inputs_embeds.data),emb.inputs_embeds.dims),attention_mask:new ortCpu.Tensor('int64',BigInt64Array.from({length:n},()=>1n),[1,n]),position_ids:new ortCpu.Tensor('int64',pos,[3,1,n])};
      for(let i=0;i<24;i++) {
        if(i%4===3) for(const part of ['key','value']) feeds[`past_key_values.${i}.${part}`]=new ortCpu.Tensor('float16',new Uint16Array(0),[1,2,0,256]);
        else { feeds[`past_conv.${i}`]=new ortCpu.Tensor('float16',new Uint16Array(6144*4),[1,6144,4]); feeds[`past_recurrent.${i}`]=new ortCpu.Tensor('float16',new Uint16Array(16*128*128),[1,16,128,128]); }
      }
      runtimeStage = 'cpu-decoder-run';
      out=await session.run(feeds,['qev_scores']); values.push(Number(out.qev_scores.data[n-1]));
    } catch (error) {
      recordRuntimeEvent(runtimeStage, 'error', error);
      throw error;
    } finally {
      runtimeStage = 'cpu-tensor-cleanup';
      tokenTensor.dispose();
      if(feeds) for(const tensor of Object.values(feeds)) tensor.dispose();
      if(emb) for(const tensor of Object.values(emb)) tensor.dispose();
      if(out) for(const tensor of Object.values(out)) tensor.dispose();
      if(session && runtime.decoderBackend !== 'wasm') await session.release();
    }
  }
  runtimeStage = 'ready';
  return record.kind==='noul'?[0,...values]:values;
}
async function compareDecoderBackends(record) {
  // Run each provider in a separate session and retain only scalar logits.
  // This is an operator/provider diagnostic, never a checkpoint parity result.
  const run = async backend => {
    const values = await inferCase(recordWithBackend(record, backend));
    return {backend, logits: values};
  };
  const [wasmResult, webgpuResult] = await Promise.allSettled([run('wasm'), run('webgpu')]);
  if (wasmResult.status === 'rejected' || webgpuResult.status === 'rejected') {
    return {
      wasm: wasmResult.status === 'fulfilled' ? wasmResult.value.logits : null,
      webgpu: webgpuResult.status === 'fulfilled' ? webgpuResult.value.logits : null,
      errors: {
        wasm: wasmResult.status === 'rejected' ? String(wasmResult.reason?.message || wasmResult.reason) : null,
        webgpu: webgpuResult.status === 'rejected' ? String(webgpuResult.reason?.message || webgpuResult.reason) : null,
      },
      sameRecord: true,
    };
  }
  const wasm = wasmResult.value.logits;
  const webgpu = webgpuResult.value.logits;
  if (wasm.length !== webgpu.length) throw Error('Backend logit count mismatch');
  return {wasm, webgpu, deltas: wasm.map((value, index) => value - webgpu[index]), sameRecord: true};
}
async function captureScoreFeeds(record, backend='wasm') {
  const events=[];
  const logits=await inferCase(recordWithBackend(record,backend), events);
  return {backend,logits,feeds:events};
}
function recordWithBackend(record, backend) { return {...record, backend}; }
async function inferCaseUnlocked(record, backend = decoderBackend) {
  if (record?.__qevInjectedFailure) {
    runtimeStage = 'controlled-failure-injection';
    throw new WebAssembly.RuntimeError('Qev acceptance injected failure (not original fault)');
  }
  if (runtime && runtime.decoderBackend !== backend) await releaseRuntimeUnlocked();
  runtime ||= await initForBackend(backend);
  const prefix=`Context:\n${record.state}\n\nQuestion: ${record.question}\n`;
  const values=[];
  if(record.kind==='noul') values.push(0,await score(prefix+'Is the answer to this question yes? Answer Yes or No.'));
  else for(const option of record.options) values.push(await score(prefix+`Proposed answer: ${option}\nIs this proposed answer correct? Answer Yes or No.`));
  return values;
}
async function recoverRuntimeAfterError(error) {
  const message = String(error?.message || error);
  if (error instanceof WebAssembly.RuntimeError || /memory access out of bounds/i.test(message)) {
    await releaseRuntimeUnlocked();
    recordRuntimeEvent('runtime-recovery', 'success', error);
    return true;
  }
  return false;
}
let activeInferences = 0, maxActiveInferences = 0;
async function inferCase(record, capture=null) {
  const task = inferenceQueue.then(async () => {
    feedCapture=capture;
    activeInferences++;
    maxActiveInferences = Math.max(maxActiveInferences, activeInferences);
    runtimeStage = 'request-queued';
    try {
      const backend = ['wasm', 'webgpu'].includes(record?.backend) ? record.backend : decoderBackend;
      const values = await inferCaseUnlocked(record, backend);
      runtimeStage = 'ready';
      return values;
    }
    catch (error) {
      recordRuntimeEvent(runtimeStage, 'error', error);
      runtimeStage = 'runtime-release-after-error';
      await recoverRuntimeAfterError(error);
      throw error;
    } finally { feedCapture=null; activeInferences--; }
  });
  inferenceQueue = task.catch(() => {});
  return task;
}
// Acceptance-only fault injection. This is not a reproduction of the original
// unknown-trigger memory fault; the browser harness uses it to test recovery.
async function injectControlledFailure() {
  return inferCase({__qevInjectedFailure: true});
}
async function injectControlledCpuFailure() {
  return inferCpuReference({__qevInjectedCpuFailure: true});
}
async function inferCpuReference(record) {
  const task = inferenceQueue.then(async () => {
    runtimeStage = 'cpu-reference-queued';
    if (record?.__qevInjectedCpuFailure) {
      runtimeStage = 'controlled-cpu-failure-injection';
      const injected = new WebAssembly.RuntimeError('Qev acceptance injected CPU diagnostic failure (not original fault)');
      recordRuntimeEvent(runtimeStage, 'error', injected);
      await recoverRuntimeAfterError(injected);
      throw injected;
    }
    try { return await inferCpuReferenceUnlocked(record); }
    catch (error) {
      recordRuntimeEvent(runtimeStage, 'error', error);
      runtimeStage = 'runtime-release-after-cpu-error';
      await recoverRuntimeAfterError(error);
      throw error;
    }
  });
  inferenceQueue = task.catch(() => {});
  return task;
}
async function releaseRuntimeUnlocked() {
  runtimeStage = 'runtime-release';
  const old = runtime;
  runtime = null;
  if (old) {
    const released = await Promise.allSettled([old.embed.release(), old.decoder.release()]);
    const failed = released.filter(item => item.status === 'rejected');
    if (failed.length) {
      const error = new Error(`Failed to release ${failed.length} model session(s)`);
      recordRuntimeEvent(runtimeStage, 'error', error);
      throw error;
    }
  }
  runtimeStage = 'idle';
  recordRuntimeEvent('runtime-release', 'success');
}
async function releaseRuntime() {
  const task = inferenceQueue.then(() => releaseRuntimeUnlocked());
  inferenceQueue = task.catch(() => {});
  return task;
}
window.qevBrowser = {inferCase, inferCpuReference, captureDecoderTrace, captureScoreFeeds, compareDecoderBackends, injectControlledFailure, injectControlledCpuFailure, releaseRuntime, get feedCaptures() { return feedCaptureEvents.slice(); }, get queueStats() { return {active:activeInferences, maximumActive:maxActiveInferences}; }, get diagnostics() { return {stage:runtimeStage, events:runtimeEvents.slice()}; }, get routing() { return {tokenizerId, tokenizerRevision, checkpointId, checkpointRevision, backend:decoderBackend, assets:dir?.href || (assetUrls ? 'local-blob-bundle' : 'local-files-not-selected'), runtime: `onnxruntime-web 1.31.1 / ${decoderBackend.toUpperCase()}`}; }, selectModelFiles(files) { return selectModelFiles(files); }, replaceModelFiles(files, {dispose = null, signal = null, stageName = null} = {}) {
  const next=createBundleUrls(files);
  const task=inferenceQueue.then(async()=>{
    try {
      if (signal?.aborted) throw new DOMException('Acquisition cancelled', 'AbortError');
      await releaseRuntimeUnlocked();
      if (signal?.aborted) throw new DOMException('Acquisition cancelled', 'AbortError');
    } catch(error) {
      try { revokeBundleUrls(next); } catch(cleanup) { throw new AggregateError([error,cleanup], 'Replacement and URL cleanup failed'); }
      throw error;
    }
    // Commit ownership before best-effort disposal; cleanup failure cannot roll it back.
    const oldUrls=assetUrls, oldDispose=activeStageDispose;
    assetUrls=next; activeStageDispose=dispose ? {dispose,stageName} : null; dir=null;
    if (stageName) selectedStageName=stageName;
    else if (oldDispose) {
      forgetStageIfCurrent(oldDispose.stageName);
      if(selectedStageName===oldDispose.stageName) selectedStageName=null;
    }
    try { revokeBundleUrls(oldUrls); } catch(error) { recordRuntimeEvent('url-cleanup','error',error); }
    if (oldDispose) { try { await oldDispose.dispose(); } catch(error) { trackPendingCleanup(oldDispose); recordRuntimeEvent('stage-cleanup','error',error); } }
    return true;
  });
  inferenceQueue=task.catch(()=>{}); return task;
}, clearModelFiles() {
  const task=inferenceQueue.then(async()=>{
    await releaseRuntimeUnlocked();
    revokeBundleUrls(assetUrls); assetUrls=null; dir=null;
    if (activeStageDispose) {
      const owned=activeStageDispose;
      try { await owned.dispose(); }
      catch(error) { trackPendingCleanup(owned);throw error; }
      activeStageDispose=null;
      forgetStageIfCurrent(owned.stageName);
      if(selectedStageName===owned.stageName) selectedStageName=null;
    }
  });
  inferenceQueue=task.catch(()=>{}); return task;
}, get modelBundleLoaded() { return Boolean(assetUrls); }};
let restoreController=null;
function abortRestore() { restoreController?.abort(); restoreController=null; }
const bundleInput=document.querySelector('#model-files');
if(bundleInput) bundleInput.addEventListener('change',async()=>{try{const files=selectModelFiles(bundleInput.files);acquisitionController?.abort();abortRestore();await window.qevBrowser.replaceModelFiles(Object.values(files));status.textContent='Local model files selected.';}catch(error){bundleInput.value='';status.textContent=`Model files rejected: ${error.message}`;}});
const manifestInput=document.querySelector('#asset-manifest'), downloadButton=document.querySelector('#download-assets'), cancelButton=document.querySelector('#cancel-download'), downloadProgress=document.querySelector('#download-progress'), downloadStatus=document.querySelector('#download-status');
let acquisitionController=null;
if(downloadButton) downloadButton.addEventListener('click',async()=>{
  if(!manifestInput?.files?.length){downloadStatus.textContent='Choose an explicit JSON manifest first.';return;}
  if(manifestInput.files.length!==1){downloadStatus.textContent='Choose exactly one manifest.';return;}
  if(manifestInput.files[0].size>65536){downloadStatus.textContent='Manifest exceeds 64 KiB.';return;}
  abortRestore();
  downloadButton.disabled=true; cancelButton.disabled=false; downloadProgress.hidden=false; downloadProgress.value=0; downloadProgress.max=1;
  acquisitionController=new AbortController();
  try {
    const manifest=JSON.parse(await manifestInput.files[0].text());
    const staged=await stageAssets(manifest,{signal:acquisitionController.signal,onCleanupFailure:item=>{pendingStageCleanups.push(item);showPendingCleanup();},onProgress:p=>{downloadProgress.value=p.totalBytes/p.totalSize;downloadStatus.textContent=`Downloading ${p.name}: ${p.fileBytes.toLocaleString()} / ${p.fileSize.toLocaleString()} bytes; verifying SHA-256…`;}});
      try {
        await window.qevBrowser.replaceModelFiles(staged.files,{dispose:staged.dispose,stageName:staged.stageName,signal:acquisitionController.signal});
      } catch (error) {
        try { await staged.dispose(); }
        catch(cleanupError) {
          trackPendingCleanup({dispose:staged.dispose,stageName:staged.stageName});
          throw new AggregateError([error,cleanupError], 'Replacement failed and staged data cleanup failed; cleanup remains retryable');
        }
        throw error;
      }
    selectedStageName=staged.stageName;
    let remembered=true;
    try { localStorage.setItem(SAVED_STAGE_KEY, JSON.stringify({stageName:staged.stageName,files:staged.evidence})); } catch { remembered=false; recordRuntimeEvent('stage-remember','error',new Error('Browser could not save stage metadata')); }
    downloadProgress.value=1; downloadStatus.textContent='Files match the selected manifest. Model identity and the manifest publisher are not verified.';
    bundleInput.value=''; status.textContent=remembered?'Manifest-matched bundle selected. You may restore this stage after reload.':'Bundle selected, but browser storage could not remember it for reload.';
  } catch(error) { downloadStatus.textContent=error.name==='AbortError'?'Download cancelled. No new bundle selected.':`Acquisition rejected: ${error.message}`; }
  finally { acquisitionController=null;downloadButton.disabled=false;cancelButton.disabled=true; }
});
if(cancelButton) cancelButton.addEventListener('click',()=>acquisitionController?.abort());
const clearBundleButton=document.querySelector('#clear-model-files');
if(clearBundleButton) clearBundleButton.addEventListener('click',async()=>{
  acquisitionController?.abort(); abortRestore(); clearBundleButton.disabled=true;
  try {
    await window.qevBrowser.clearModelFiles();
    if(bundleInput) bundleInput.value='';
    if(downloadStatus) downloadStatus.textContent='Selected bundle cleared. Interrupted downloads may leave browser storage.';
    if(downloadProgress) downloadProgress.hidden=true;
    status.textContent='Model files cleared. Select a bundle to run a decision.';
  } catch(error) { status.textContent=`Unable to clear model storage: ${error.message}`; }
  finally { clearBundleButton.disabled=false; }
});
const retryCleanupButton=document.querySelector('#retry-stage-cleanup');
if(retryCleanupButton) retryCleanupButton.addEventListener('click',async()=>{
  retryCleanupButton.disabled=true;
  const task=inferenceQueue.then(async()=>{
    const retry=pendingStageCleanups.splice(0);
    for(const item of retry) { try { await item.dispose(); if(item.stageName) { if(activeStageDispose===item) activeStageDispose=null; if(selectedStageName===item.stageName) selectedStageName=null; forgetStageIfCurrent(item.stageName); } } catch(error) { trackPendingCleanup(item); recordRuntimeEvent('stage-cleanup-retry','error',error); } }
    showPendingCleanup();
    status.textContent=pendingStageCleanups.length?'Some earlier model storage still could not be removed.':'Earlier model storage cleaned up.';
  });
  inferenceQueue=task.catch(()=>{});
  try { await task; } finally { retryCleanupButton.disabled=false; }
});
const restoreButton=document.querySelector('#restore-model-files');
if(restoreButton) restoreButton.addEventListener('click',async()=>{
  if(selectedStageName){status.textContent='A staged bundle is already selected.';return;}
  acquisitionController?.abort(); restoreButton.disabled=true; restoreController=new AbortController();
  const controller=restoreController;
  try {
    const saved=JSON.parse(localStorage.getItem(SAVED_STAGE_KEY) || 'null');
    const staged=await restoreStagedAssets(saved,{signal:controller.signal,onProgress:name=>{status.textContent=`Verifying saved ${name}…`;}});
    try {
      await window.qevBrowser.replaceModelFiles(staged.files,{dispose:staged.dispose,stageName:saved.stageName,signal:controller.signal});
      selectedStageName=saved.stageName;status.textContent='Saved bundle verified and selected. Model publisher and identity are not verified.';
    } catch(error) {
      // Failed replacement leaves the prior selection and saved stage intact.
      // Restore ownership remains available for a later retry; release without deleting data.
      try { await staged.abandon(); } catch(releaseError) { throw new AggregateError([error,releaseError], 'Restore failed and stage lock release failed'); }
      throw error;
    }
  } catch(error) { status.textContent=error.name==='AbortError'?'Saved bundle restoration cancelled.':`Unable to restore saved bundle: ${error.message}`; }
  finally {if(restoreController===controller)restoreController=null;restoreButton.disabled=false;}
});
window.qevTyped = {async decide(request) {
  const record = compileTypedRequest(request);
  const logits = await inferCase({...record, backend:document.querySelector('#backend')?.value});
  return {notice:'Experimental model-derived weights and confidence are not calibrated correctness probabilities.',response:formatTypedResponse(record, logits)};
}};
const typedButton = document.querySelector('#typed-run');
if (typedButton) typedButton.addEventListener('click', async () => {
  typedButton.disabled=true;
  const output=document.querySelector('#typed-output'); output.textContent='Running decision…';
  try { output.textContent=JSON.stringify(await window.qevTyped.decide(JSON.parse(document.querySelector('#typed-request').value)),null,2); }
  catch(error) { output.textContent=`Request failed: ${error.message}`; }
  finally { typedButton.disabled=false; }
});
window.addEventListener('beforeunload',()=>revokeBundleUrls(assetUrls));
const runButton = document.querySelector('#run');
if (runButton) runButton.onclick=async()=>{runButton.disabled=true; try{
  result.textContent='';
  const state=document.querySelector('#state').value, q=document.querySelector('#question').value, kind=document.querySelector('#kind').value;
  const options=document.querySelector('#options').value.split('\n').map(s=>s.trim()).filter(Boolean);
  if(!state || !q || (kind!=='noul' && (options.length<2||options.length>8))) throw Error('Provide context, a question and 2–8 options.');
  status.textContent='Loading model or running inference';
  const values=await inferCase({state,question:q,kind,options,backend:document.querySelector('#backend')?.value});
  const temperature=0.9334818708427981, max=Math.max(...values), exps=values.map(v=>Math.exp((v-max)/temperature)), total=exps.reduce((a,b)=>a+b,0), probabilities=exps.map(x=>x/total);
  const pct = p => `${(p * 100).toFixed(1)}%`;
  if (kind === 'noul') result.textContent = `Relative weights (not calibrated probabilities)\nYes   ${pct(probabilities[1])}\nNo    ${pct(probabilities[0])}`;
  else {
    const top = probabilities.indexOf(Math.max(...probabilities));
    const summary = kind === 'choice' ? `Highest-ranked option\n${options[top]}` : `Relative weighted score (not calibrated)\n${probabilities.reduce((sum, p, i) => sum + i * p, 0).toFixed(2)} / ${options.length - 1}`;
    result.textContent = `${summary}\n\nRelative weights (not calibrated probabilities)\n${options.map((option, i) => `${option}   ${pct(probabilities[i])}`).join('\n')}`;
  }
  document.querySelector('#raw-result').textContent=JSON.stringify({kind,logits:values,probabilities},null,2); status.textContent='Complete';
}catch(e){
  if (/memory access out of bounds/i.test(e.message)) {
    status.textContent='Model memory limit reached. Reload the page and try a shorter input.';
  } else status.textContent='Error: '+e.message;
  console.error(e);
}finally{runButton.disabled=false;}};
