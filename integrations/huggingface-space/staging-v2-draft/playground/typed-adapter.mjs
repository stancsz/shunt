// Narrow Open-Jev typed-request subset. This is not Shunt policy or a full System One implementation.
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
export function compileTypedRequest(request) {
  if (!object(request) || Object.keys(request).some(k => !['state','questions'].includes(k)) || typeof request.state !== 'string' || !request.state.trim() || !object(request.questions)) throw Error('Expected state text and exactly one typed question.');
  const entries=Object.entries(request.questions);
  if(entries.length!==1 || !entries[0][0] || !object(entries[0][1])) throw Error('Exactly one named question is supported.');
  const [id,definition]=entries[0], {type,instructions,criteria}=definition;
  if(Object.keys(definition).some(k=>!['type','instructions','criteria'].includes(k)) || typeof instructions!=='string' || !instructions.trim()) throw Error('Question requires text instructions and supported fields.');
  let question=instructions, options=[],keys=[],legend;
  if(type==='choice'){
    if(!object(criteria) || Object.keys(criteria).length<2 || Object.keys(criteria).length>8) throw Error('Choice requires 2–8 named candidates.');
    keys=Object.keys(criteria); if(keys.some(k=>!k || /^(0|[1-9][0-9]*)$/.test(k) || (criteria[k]!==null && typeof criteria[k]!=='string'))) throw Error('Choice names must be non-numeric text and descriptions must be text or null.');
    options=keys.map(k=>criteria[k]===null?k:`${k}: ${criteria[k]}`);
  } else if(type==='score'){
    if(!Array.isArray(criteria) || criteria.length<2 || criteria.length>8 || criteria.some(x=>typeof x!=='string')) throw Error('Score requires 2–8 text levels.');
    options=criteria.slice();keys=options.map((_,i)=>String(i));legend=Object.fromEntries(keys.map((k,i)=>[k,criteria[i]]));
  } else if(type==='noul'){
    if(criteria!==undefined && criteria!==null){
      if(!object(criteria) || Object.keys(criteria).some(k=>!['true','false'].includes(k)) || Object.values(criteria).some(v=>typeof v!=='string')) throw Error('Noul criteria support true and false text descriptions only.');
      if(Object.hasOwn(criteria,'true')) question+=`\nYes means: ${criteria.true}`;
      if(Object.hasOwn(criteria,'false')) question+=`\nNo means: ${criteria.false}`;
    }
    options=['no','yes'];keys=['false','true'];
  } else throw Error('Supported types: choice, score, noul.');
  return {id,kind:type,state:request.state,question,options,answer_keys:keys,...(legend?{legend}:{})};
}
export function formatTypedResponse(record, logits, temperature=0.9334818708427981) {
  if(!Array.isArray(logits)||logits.length!==record.answer_keys.length||logits.some(x=>!Number.isFinite(x))||!Number.isFinite(temperature)||temperature<=0)throw Error('Invalid model logits or temperature.');
  const max=Math.max(...logits),weights=logits.map(v=>Math.exp((v-max)/temperature)),sum=weights.reduce((a,b)=>a+b,0),p=weights.map(v=>v/sum), index=p.indexOf(Math.max(...p));
  let answer;
  if(record.kind==='noul')answer={type:'noul',noul:p[1]};
  else if(record.kind==='choice') answer={type:'choice',choice:record.answer_keys[index],probabilities:Object.fromEntries(record.answer_keys.map((k,i)=>[k,p[i]])),confidence:(p[index]-1/p.length)/(1-1/p.length)};
  else {const center=(p.length-1)/2,uniform=p.reduce((v,_,i)=>v+Math.abs(i-center),0)/p.length,distance=p.reduce((v,x,i)=>v+x*Math.abs(i-index),0);answer={type:'score',score:p.reduce((v,x,i)=>v+x*i,0),probabilities:Object.fromEntries(record.answer_keys.map((k,i)=>[k,p[i]])),confidence:Math.max(0,1-distance/uniform),legend:record.legend};}
  return {answers:{[record.id]:answer}};
}
