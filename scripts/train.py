"""Train the Shunt LoRA with a discriminative three-option loss."""
import argparse
import hashlib
import json
import random
import time
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from shunt.model import load, inputs, option_logits, SYSTEM


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--epochs',type=int,default=3)
    ap.add_argument('--batch-size',type=int,default=4); args=ap.parse_args()
    random.seed(42); torch.manual_seed(42)
    model,tok,ids=load(train=True)
    targets=r'.*language_model.*\.(q_proj|k_proj|v_proj|o_proj|in_proj_qkv|out_proj|gate_proj|up_proj|down_proj)'
    model=get_peft_model(model,LoraConfig(r=8,lora_alpha=16,lora_dropout=0.05,
          target_modules=targets, bias='none'))
    model.print_trainable_parameters()
    rows=[json.loads(x) for x in Path('data/train.jsonl').read_text().splitlines()]
    optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=2e-4)
    start=time.perf_counter(); history=[]
    for epoch in range(args.epochs):
        random.shuffle(rows); model.train(); total=0
        for step,offset in enumerate(range(0,len(rows),args.batch_size)):
            batch=rows[offset:offset+args.batch_size]
            optimizer.zero_grad(set_to_none=True)
            logits=option_logits(model,inputs(tok,[r['task'] for r in batch]),ids)
            loss=torch.nn.functional.cross_entropy(logits,torch.tensor([r['label'] for r in batch],device='cuda'))
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1)
            optimizer.step(); total+=loss.item()
            if step%10==0: print(json.dumps({'epoch':epoch+1,'step':step,'loss':loss.item()}),flush=True)
        history.append({'epoch':epoch+1,'mean_loss':total/(step+1)})
    out=Path('artifacts/shunt-lora'); out.mkdir(parents=True,exist_ok=True)
    model.save_pretrained(out); tok.save_pretrained(out)
    manifest={'base':'Qwen/Qwen3.5-0.8B','seed':42,'epochs':args.epochs,
      'batch_size':args.batch_size,'rank':8,'alpha':16,'learning_rate':2e-4,
      'training_seconds':time.perf_counter()-start,'history':history,
      'supervision':'synthetic authored policy labels; not execution outcomes',
      'data_sha256':hashlib.sha256(Path('data/train.jsonl').read_bytes()).hexdigest(),
      'prompt_sha256':hashlib.sha256(SYSTEM.encode()).hexdigest(),
      'label_token_ids':ids,'torch':torch.__version__}
    (out/'training.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)


if __name__=='__main__': main()
