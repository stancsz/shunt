import argparse
import json
from shunt.model import load, score
from shunt.policy import route
from shunt.config import load_settings


def main():
    p=argparse.ArgumentParser(description='Shunt local three-tier LoRA router')
    p.add_argument('task'); p.add_argument('--files',type=int); p.add_argument('--lines',type=int)
    p.add_argument('--attempts',type=int,default=0); p.add_argument('--core-interface',action='store_true')
    p.add_argument('--scope-file',action='append',help='Explicit Python scope file; repeat for multiple files')
    p.add_argument('--adapter',default='artifacts/shunt-lora')
    p.add_argument('--cuda-graph',action='store_true',help='Use a warm fixed-token graph bucket')
    p.add_argument('--graph-tokens',type=int,choices=[256,512],default=256)
    a=p.parse_args()
    settings=load_settings()
    if a.scope_file:
        if a.files is not None or a.lines is not None:
            p.error('--scope-file cannot be combined with --files or --lines')
        from shunt.scope import inspect_scope
        a.files,a.lines=inspect_scope(a.scope_file)
    m,t,ids=load(a.adapter)
    if a.cuda_graph:
        from shunt.graph import GraphScorer
        probabilities=GraphScorer(m,t,ids,bucket=a.graph_tokens).score(a.task)
    else:
        probabilities=score(m,t,ids,a.task)
    decision=route(a.task,probabilities,a.files,a.lines,a.attempts,a.core_interface)
    decision['target']=settings.targets[decision['route']].public()
    decision.update(backbone='Qwen/Qwen3.5-0.8B',adapter=a.adapter,calibrated=False,
                    scope_provenance='AST of supplied Python files' if a.scope_file else 'caller-declared; no AST parser invoked')
    print(json.dumps(decision,indent=2))


if __name__=='__main__': main()
