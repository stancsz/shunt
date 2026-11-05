"""Experimental fixed-shape CUDA graph inference, compared against eager logits."""
import json
import time
from pathlib import Path
import torch
from shunt.model import load, prompt, option_logits, inputs


def main():
    model,tok,ids=load('artifacts/shunt-lora')
    model=model.merge_and_unload().eval()
    gpu_ids=torch.tensor(ids,device='cuda')
    def logits(batch):
        return model(**batch,use_cache=False,logits_to_keep=1).logits[:,-1].index_select(-1,gpu_ids).float()
    rows=[json.loads(x) for x in Path('data/validation.jsonl').read_text().splitlines()]
    length=256
    def encode(task):
        p=prompt(tok,task)
        if len(tok.encode(p,add_special_tokens=False))>length:
            raise ValueError('Input exceeds graph bucket')
        return tok(p,return_tensors='pt',padding='max_length',max_length=length,
                   add_special_tokens=False).to('cuda')
    static=encode(rows[0]['task'])
    with torch.inference_mode():
        side=torch.cuda.Stream()
        side.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(side):
            for _ in range(3): logits(static)
        torch.cuda.current_stream().wait_stream(side)
        graph=torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph):
            captured=logits(static).double().softmax(-1)
        timings=[]; correct=0; max_error=0
        for row in rows:
            torch.cuda.synchronize(); start=time.perf_counter()
            batch=encode(row['task'])
            for key in static: static[key].copy_(batch[key])
            graph.replay(); probs=captured[0].tolist()
            torch.cuda.synchronize(); timings.append((time.perf_counter()-start)*1000)
            eager=option_logits(model,inputs(tok,[row['task']]),ids).double().softmax(-1)[0]
            max_error=max(max_error,max(abs(a-b) for a,b in zip(probs,eager.tolist())))
            correct+=max(range(3),key=lambda i:probs[i])==row['label']
        result={'n':len(rows),'accuracy':correct/len(rows),'p50_ms':sorted(timings)[len(rows)//2],
          'p95_ms':sorted(timings)[int(.95*(len(rows)-1))],'max_probability_error':max_error,
          'bucket':length,'mode':'merged LoRA CUDA graph experiment; excludes scope inspection'}
        Path('artifacts/graph-eval.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))


if __name__=='__main__': main()
