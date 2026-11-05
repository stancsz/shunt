"""Warm fixed-bucket CUDA graph scorer. One instance is single-threaded."""
import torch
from shunt.model import prompt


class GraphScorer:
    def __init__(self, model, tokenizer, label_ids, bucket=256):
        self.model=model.merge_and_unload().eval()
        self.tokenizer=tokenizer
        self.bucket=bucket
        # Only three vocabulary rows are ever consumed. Copy those frozen rows
        # into an inference-only head rather than computing 248,320 logits.
        original=self.model.lm_head
        selected=original.weight.detach()[label_ids].clone()
        head=torch.nn.Linear(original.in_features,3,bias=False,
                             device=selected.device,dtype=selected.dtype)
        head.weight=torch.nn.Parameter(selected,requires_grad=False)
        self.model.lm_head=head
        self.ids=torch.arange(3,device='cuda')
        self.static=self.encode('Initialize router.')
        # Reference DeltaNet attention uses fp32 matmuls. Capture their TF32
        # kernels, then restore the process setting; replay uses captured kernels.
        precision=torch.get_float32_matmul_precision()
        try:
            torch.set_float32_matmul_precision('high')
            with torch.inference_mode():
                side=torch.cuda.Stream()
                side.wait_stream(torch.cuda.current_stream())
                with torch.cuda.stream(side):
                    for _ in range(3): self.logits()
                torch.cuda.current_stream().wait_stream(side)
                self.graph=torch.cuda.CUDAGraph()
                with torch.cuda.graph(self.graph):
                    self.output=self.logits().double().softmax(-1)
        finally:
            torch.set_float32_matmul_precision(precision)

    def encode(self, task):
        text=prompt(self.tokenizer,task)
        if len(self.tokenizer.encode(text,add_special_tokens=False))>self.bucket:
            raise ValueError(f'Task exceeds {self.bucket}-token CUDA graph bucket')
        return self.tokenizer(text,return_tensors='pt',padding='max_length',
          max_length=self.bucket,add_special_tokens=False).to('cuda')

    def logits(self):
        return self.model(**self.static,use_cache=False,logits_to_keep=1).logits[:,-1].index_select(-1,self.ids).float()

    @torch.inference_mode()
    def score(self,task):
        batch=self.encode(task)
        for key in self.static: self.static[key].copy_(batch[key])
        self.graph.replay()
        return self.output[0].tolist()
