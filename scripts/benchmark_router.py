"""Bounded warm full router measurement with declared scope; no AST timing claim."""
import json
import argparse
import time
from pathlib import Path
import torch
from shunt.model import load, score
from shunt.graph import GraphScorer
from shunt.policy import route
from shunt.scope import inspect_scope


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bucket',type=int,choices=[256,512],default=256)
    parser.add_argument('--output',default='artifacts/router-benchmark.json')
    args=parser.parse_args()
    model,tok,ids=load('artifacts/shunt-lora')
    rows=[json.loads(x) for x in Path('data/validation.jsonl').read_text().splitlines()]
    # Compare adapter eager output before merging weights in reduced precision.
    reference=[score(model,tok,ids,r['task']) for r in rows]
    scorer=GraphScorer(model,tok,ids,bucket=args.bucket)
    error=0; same=True
    for row,ref in zip(rows,reference):
        p=scorer.score(row['task'])
        error=max(error,max(abs(a-b) for a,b in zip(p,ref)))
        same &= max(range(3),key=lambda i:p[i])==max(range(3),key=lambda i:ref[i])
    timings=[]; correct=0; overrides_ok=True
    fixture=Path('artifacts/scope-fixture.py')
    fixture.write_text('def add(a, b):\n    return a + b\n',encoding='utf-8')
    inspection=[]
    for i in range(1000):
        row=rows[i%len(rows)]
        # Exercise small, multi-file and retry/risk floors without changing semantic labels.
        files=[1,4,9][i%3]; attempts=2 if i%7==0 else 0
        torch.cuda.synchronize(); start=time.perf_counter()
        t0=time.perf_counter(); measured_files,measured_lines=inspect_scope([fixture])
        inspection.append((time.perf_counter()-t0)*1000)
        decision=route(row['task'],scorer.score(row['task']),files if i%3 else measured_files,measured_lines,attempts)
        json.dumps(decision)
        torch.cuda.synchronize(); timings.append((time.perf_counter()-start)*1000)
        correct+=max(decision['probabilities'],key=decision['probabilities'].get)==['T1','T2','T3'][row['label']]
        if files>8 or attempts>=2:
            overrides_ok &= decision['route']=='T3'
    timings.sort()
    result={'n':1000,'p50_ms':timings[499],'p95_ms':timings[949],'p99_ms':timings[989],
      'max_probability_difference_vs_adapter_eager':error,'same_semantic_winners':same,
      'safety_overrides_passed':overrides_ok,'bucket_tokens':args.bucket,
      'semantic_accuracy_repeated_fixture':correct/1000,
      'hardware':torch.cuda.get_device_name(),'mode':'merged BF16 LoRA + CUDA graph',
      'inspection_p95_ms':sorted(inspection)[949],
      'scope':'warm Python AST fixture inspection + prompt/tokenization/GPU/lexical-policy/JSON',
      'limitations':'36 synthetic prompts repeated; one small warm Python file; scope count overrides exercise policy; no load, graph setup, concurrency, or real task acceptance'}
    Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    assert same and overrides_ok, 'Graph scoring or safety regression'


if __name__=='__main__': main()
