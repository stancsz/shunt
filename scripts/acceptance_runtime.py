"""Measured local warm acceptance corpus; no model-target execution claims."""
import hashlib
import json
import time
from pathlib import Path
import torch
from shunt.graph import GraphScorer
from shunt.model import load, prompt
from shunt.policy import route
from shunt.scope import inspect_scope


def main():
    model,tok,ids=load('artifacts/shunt-lora')
    prior=torch.get_float32_matmul_precision()
    scorer=GraphScorer(model,tok,ids,bucket=512)
    assert torch.get_float32_matmul_precision()==prior
    paths=['shunt/model.py','shunt/policy.py','shunt/graph.py','shunt/scope.py',
           'shunt/__main__.py','scripts/train.py','scripts/evaluate.py','scripts/make_data.py','scripts/audit_router.py']
    long='Investigate why parallel writers lose updates. Repository context: '
    while len(tok.encode(prompt(tok,long+'helper.py contains an integer utility. '),add_special_tokens=False))<=508:
        long+='helper.py contains an integer utility. '
    tasks=['Fix indentation.','Add a REST endpoint using the existing pattern.',
           'Find why parallel updates corrupt persisted records.',long]
    measurements=[]; safety=True
    for i in range(1000):
        n=[1,2,8,9][i%4]; task=tasks[(i//4)%4]; attempt=2 if i%11==0 else 0
        torch.cuda.synchronize(); start=time.perf_counter()
        files,lines=inspect_scope(paths[:n]); after_ast=time.perf_counter()
        probs=scorer.score(task); after_model=time.perf_counter()
        decision=route(task,probs,files,lines,attempt)
        json.dumps(decision); end=time.perf_counter()
        if files>8 or attempt>=2: safety &= decision['route']=='T3'
        measurements.append({'files':n,'tokens':len(tok.encode(prompt(tok,task),add_special_tokens=False)),
          'inspection_ms':(after_ast-start)*1000,'inference_ms':(after_model-after_ast)*1000,
          'static_ms':((after_ast-start)+(end-after_model))*1000,'total_ms':(end-start)*1000})
    def p95(rows,key): return sorted(r[key] for r in rows)[int(.95*(len(rows)-1))]
    result={'n':len(measurements),'precision_restored':torch.get_float32_matmul_precision()==prior,
      'safety_passed':safety,'hardware':torch.cuda.get_device_name(),'bucket':512,
      'static_p95_ms':p95(measurements,'static_ms'),'inference_p95_ms':p95(measurements,'inference_ms'),
      'total_p95_ms':p95(measurements,'total_ms'),
      'by_files':{str(n):{'static_p95_ms':p95([r for r in measurements if r['files']==n],'static_ms'),
        'total_p95_ms':p95([r for r in measurements if r['files']==n],'total_ms')} for n in [1,2,8,9]},
      'max_input_tokens':max(r['tokens'] for r in measurements),
      'scope':'warm batch1; real Python source files reread each request; content-keyed parsing cache; four authored prompts incl near-limit context; no concurrency/startup or downstream execution',
      'source_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}}
    result['budgets_passed']=result['static_p95_ms']<5 and result['inference_p95_ms']<25 and result['total_p95_ms']<=30
    Path('artifacts/acceptance-runtime.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    assert safety and result['precision_restored'] and result['budgets_passed']


if __name__=='__main__': main()
