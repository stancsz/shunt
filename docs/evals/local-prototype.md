# Shunt local prototype results

Measured on the local RTX 5070 Ti, using the pinned Qwen3.5-0.8B base and trained rank-8 Shunt adapter. Machine-readable evidence and artifact hashes are in [local-prototype.json](local-prototype.json).

| Check | Observed result | Scope |
| --- | --- | --- |
| Training | 216 examples, three epochs, about 46 seconds | Authored synthetic policy labels; original weights frozen |
| Saved adapter | 18,716,576 bytes; 264 tensors; 4,669,440 parameters | Reloaded from safetensors in a fresh process |
| Frozen base classification | 24/36 (66.7%) | Held-out synthetic intent templates |
| Shunt classification | 34/36 (94.4%) | Same held-out templates; two Tier 2 tasks classified as Tier 1 |
| Eager adapter scoring | About 100 ms p95 | Tokenization and scoring only; fails 30 ms target |
| Warm CUDA graph router | 16.19 ms p95; 16.64 ms p99, 1,000 calls | 256-token bucket; repeated 36-prompt fixture; includes one small Python AST fixture, lexical policy and JSON |
| AST fixture inspection | 0.80 ms p95 | One tiny warm Python file; not a repository-wide parsing guarantee |
| Graph comparison | Same semantic winners; max probability shift 0.000107 | Compared with the unmerged eager adapter on those 36 prompts |
| Deterministic tests | 41 passed | Policy and Python scope boundaries |

The benchmark has concurrency one and excludes model loading, CUDA graph setup, cold file reads, and unseen input distributions. Only the optimized bounded warm path meets the timing target in this measurement. Full production AC-4 acceptance remains unverified. There is no metered model API call on the measured inference path; hardware costs are not zero.

The prototype produces decisions for the three configured targets but does not execute those targets. It does not establish their relative quality or prices. No real coding-task success, multilingual accuracy or calibrated confidence is claimed.

Independent CLI reviews found no reproduced must-fix defect in the local trained prototype: adapter tensors loaded, all 41 tests passed with isolated scratch, and fresh eager and CUDA-graph invocations with two previous attempts selected Tier 3. See [content-bound review receipts](independent-qa.md). Production and general latency acceptance were not approved.
