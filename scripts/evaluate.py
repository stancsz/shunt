"""Paired frozen-base / adapter semantic evaluation and warm scoring timings."""
import argparse
import json
import time
from pathlib import Path
import torch
from shunt.model import load, score


def main():
    p=argparse.ArgumentParser(); p.add_argument('--adapter'); p.add_argument('--output',required=True)
    a=p.parse_args(); model,tok,ids=load(a.adapter)
    rows=[json.loads(s) for s in Path('data/validation.jsonl').read_text().splitlines()]
    for _ in range(3): score(model,tok,ids,rows[0]['task'])
    matrix=[[0]*3 for _ in range(3)]; records=[]; timings=[]
    for row in rows:
        torch.cuda.synchronize(); start=time.perf_counter()
        probs=score(model,tok,ids,row['task'])
        torch.cuda.synchronize(); timings.append((time.perf_counter()-start)*1000)
        pred=max(range(3),key=lambda i:probs[i]); matrix[row['label']][pred]+=1
        records.append(dict(row,prediction=pred,probabilities=probs))
    result={'adapter':a.adapter,'n':len(rows),'accuracy':sum(matrix[i][i] for i in range(3))/len(rows),
      'confusion_true_rows':matrix,'warm_scoring_p50_ms':sorted(timings)[len(timings)//2],
      'warm_scoring_p95_ms':sorted(timings)[int(.95*(len(timings)-1))],
      'latency_scope':'tokenization + model + softmax; not full AC-4 acceptance',
      'data_scope':'held-out synthetic intent templates; not real target execution',
      'device':torch.cuda.get_device_name(),'records':records}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))


if __name__=='__main__': main()
