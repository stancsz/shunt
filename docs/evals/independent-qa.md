# Independent CLI review receipts

Documentation note: execution targets below are displayed as T1, T2, and T3. Linked raw evaluation records retain the original runtime aliases.

These reviews accept the local trained prototype only. They do not certify production routing quality or general AC-4 latency. All workers used profile subroute-subagents, model default, and the process-local loopback base URL; native events and exit receipts remain under tmp/.


## qa-worker

Verdict: **acceptable as a local trained prototype**, with material limits. No must-fix defect reproduced in this review. This is not certification of production routing or AC4.

- Tests: `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` passed, **38 passed**.
- Adapter: safetensors loaded successfully; 264 tensors, 4,669,440 parameters, consistent with the configured rank-8 LoRA.
- Data split: **216 training rows / 36 intent families** and **36 validation rows / 18 intent families**, with no family overlap. These remain authored synthetic policy examples, not distinct real-world tasks.
- Recorded evaluation: base accuracy **24/36 (66.7%)**; adapter **34/36 (94.4%)**. This supports the narrow synthetic classification claim only—not downstream solve rates.
- Fresh CLI: an easy typo task with one file, 12 lines, and `--attempts 2` returned `T3`, with the circuit-breaker flag set. Scope is caller-declared; no AST parsing was verified.
- AC4 remains unmet: reported warm scoring p95 is about **100 ms**, versus the **30 ms** target. The timing is not full-path acceptance.

No `HEAD` exists in this checkout, so the review is bound to file hashes rather than a commit. Key hashes: `shunt/policy.py` `8a5e09a4…f7dc3252`; adapter `adapter_model.safetensors` `bd2c76d8…2263f450`; training data `18fefd82…6189639`. No files were edited.


## qa-final

Accepted for the stated scope: the local trained prototype, not production. The requested CLI completed successfully and returned `T3`; it inspected one supplied Python file, and the `attempts=2` circuit-breaker override set the structural floor to tier 3 despite the semantic scorer strongly preferring tier 1.

The CUDA graph enforces a 256-token prompt bound and raises `ValueError` when exceeded. `GraphScorer` is documented as single-threaded/not thread-safe; the one-shot CLI constructs one per run. The benchmark artifact reports 1,000 warm calls at 15.45 ms p50 / 16.19 ms p95, including AST inspection of one small fixture. Its own limitations exclude production load, concurrency, startup, and real-task acceptance; this is not a production latency guarantee.

One verification blocker remains: the exact pytest command yielded **38 passed, 3 errors**. The three `tests/test_scope.py` cases failed during `tmp_path` fixture setup because the sandbox denied scanning `C:\Users\stanc\AppData\Local\Temp\pytest-of-stanc`; their test bodies did not run. I made no workaround that writes files.

I hashed the reviewed source/docs, benchmark artifact, and adapter files. PowerShell abbreviated the displayed hashes, so I’m not presenting those truncated values as full receipts. No content-based must-fix was established in the reviewed delta; test acceptance is environment-limited as noted.


## qa-scope-tests

QA recheck passed: the exact command executed **all 41 tests**, with `41 passed in 0.08s`. This verifies the local test suite only; it makes no claim about production behavior.

SHA-256 hashes:

```text
8d9d4a7f4615e69b3c6d00be218f16c4b58c188c4b6f0b24331f91259c4bc325  shunt/graph.py
56f43bd90af2ab240390e644762bebb757d6af408d1e96d68916028f56656eb8  shunt/scope.py
312303f709176557b703fae58c576b00934c7ce0052e6edfaa5e04c5877bebfc  shunt/__main__.py
4b0a5377b5a117d1ca234fe901446f43bb253534bb0acd2700f3282f37cb1c5f  shunt/model.py
8a5e09a4d742498a3b11b5bb2e4a8a65c779890a7ccf029ec57078e3f7dc3252  shunt/policy.py
19e40326511cf1fa9a184ec230b6aa3467fb06aacf78c8334e49d0332ff5a382  tests/test_scope.py
6537b5a92e5796c9c4bdc5bdaf9e6102425ba90193cf0cfc770b4f37ce994dbd  scripts/benchmark_router.py
bd2c76d87f7adc1600146697e6c5f84be1dfbf94fac658197b9d8bdd2263f450  artifacts/shunt-lora/adapter_model.safetensors
```

Completed within the five-minute checkpoint and ten-minute deadline. Only the specified pytest basetemp scratch was created; source, docs, model, and artifact files were not edited.
