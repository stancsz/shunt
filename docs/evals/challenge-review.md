# Challenge and output-head review

Documentation note: execution targets below are displayed as T1, T2, and T3. Linked raw evaluation records retain the original runtime aliases.

Scope: local trained adapter and bounded inference only. No production acceptance.


## challenge-review

**Accepted for the requested scope; no must-fix found.** The challenge labels in `scripts/audit_router.py` match the frozen labels in `artifacts/challenge-audit.json`. Both 256- and 512-token results are 23/24 correct (95.83%), with confusion matrix `[[8,0,0],[1,7,0],[0,0,8]]`. The sole error in both buckets is “Test that the endpoint persists records and returns the expected HTTP response.” (label 1, predicted 0).

Both adversarial instruction cases are classified according to their task labels. All three Chinese cases are correct: 1/1 per tier. These are authored challenge examples, not independent real-task labels or evidence of target-model success.

The training script reads `data/train.jsonl`; it does not consume challenge data. The requested pytest run passed: **41 passed**. The exact 512-token CLI command exited 0 and returned `T1`. Its probabilities are uncalibrated, and `--files 1 --lines 10` is caller-declared scope—not AST inspection. The existing `router-benchmark-512.json` reports 1,000 warm calls: p50 25.0111 ms, p95 25.9214 ms, p99 26.4870 ms; semantic winners matched eager scoring, safety overrides passed, and repeated-fixture accuracy was 94.4%. Its documented limits include repeated synthetic prompts, one small Python fixture, and exclusion of startup, graph setup, concurrency, and real-task acceptance.

This supports the local trained routing adapter and bounded CLI/benchmark behavior only; it does **not** establish deployment readiness or successful outcomes from the routed targets. No source, data, docs, or model files were modified.

SHA-256:

- `scripts/audit_router.py`: `84CD7609C6A0E61F567ED26093EF9616DDA4EA087A56BF6C34DB875BD9724888`
- `scripts/benchmark_router.py`: `3CDAD3D21BDD025A5A77895BC8E71F6494A8F8EE7A2D05997E3BE4B78A99992B`
- `shunt/__main__.py`: `C47D420D8BEC0DCB85F28DA4136E54B3EE0AB1F3D78B1E79D70CD9869AEE3BB8`
- `artifacts/challenge-audit.json`: `30959C2A9DD6EFB612ADF04B566A8BE294ABDD1F14A2471B6ADB2BA8047CCC86`
- `docs/training.md`: `7687CCB24AB18763A0AED6E200E106A73FE6ACDDDC36119136CD93F621315874`
- `artifacts/router-benchmark-512.json`: `1DF9C8BB525C839A663D46A1B110CD63C34483CFC799231680CA9EE49E12BE99`
- Adapter `adapter_model.safetensors`: `BD2C76D87F7ADC1600146697E6C5F84BE1DFBF94FAC658197B9D8BDD2263F450`

## head-review

**Scope verdict: conditional pass on the requested math and unchanged adapter; full-eager parity remains unverified.** No blocking shape or mapping issue found in the inspected code:

- `selected` takes source `lm_head.weight` rows in `label_ids` order, and the replacement is bias-free with shape `[3, hidden_size]`. Local indices `[0,1,2]` preserve that order. Its three logits are mathematically the same as selecting those rows from the original head; the implementation explicitly converts results to float before softmax, with ordinary numerical variation possible.
- The adapter was read-only during review. SHA-256 hashes for all seven files under `artifacts/shunt-lora` are below; they establish the post-run bytes, not a before/after comparison.
- The requested CLI command exited successfully and returned a route. The existing benchmark artifact reports parity against **adapter eager**, not full eager vocabulary, so it does not establish the specified winner parity check. Parent rerun remains necessary.

Exact SHA-256:

- `shunt/graph.py`: `1B0404840632F9EB1AAF6D843EBD58092805538E6D3DFA24A119512CA75249CF`
- `artifacts/shunt-lora/README.md`: `37D1DBBE85AAF4B629C923E8A66D9A0C54229E2CCABC0DEE5D01297BB484C72D`
- `artifacts/shunt-lora/adapter_config.json`: `BD2C76D87F7ADC1600146697E6C5F84BE1DFBF94FAC658197B9D8BDD2263F450`
- `artifacts/shunt-lora/adapter_model.safetensors`: `306ABAF09CF3A6C0D14128373A72925BDA3D7DE2616A5642804D9768C7D2F78C`
- Remaining adapter file hashes, in output order: `695FC1CDBC417A70C964BF75F44EB3492B59AAC7FD18116611D1F6BDD07D11C2`, `9A95CE29F12B2EAB0870A223248674916074EE3DE4C5A2FB08B4A03186FFD797`, `2F4DD754486E96054D0C841DDDE816748BE0116CBBC8BA8B5311AE4853432A21`, `BE4018AA2D1650F043D4E9ACEAD66DC48C5F7D9930319530CC5EE3A9175A1EF5`.

No production claim is made.

## Parent evidence reconciliation

The head-review prose misassigned some file hashes and interpreted adapter-eager as lacking full vocabulary projection. These statements are not accepted as findings. shunt/model.py calls the original full model head and only then selects label logits; scripts/benchmark_router.py computes those reference scores before GraphScorer merges the adapter and replaces the output head. Thus the benchmark compares the selected-row head with the full-vocabulary adapted head as intended. It does not compare against the unadapted base, which training deliberately changes. The actual completed 512 benchmark reported identical semantic winners and max probability shift0.0000993. The mathematical review and fresh-process CLI passed. Authoritative current hashes follow rather than the misassigned prose hashes.

- `shunt/graph.py`: `1b0404840632f9eb1aaf6d843ebd58092805538e6d3dfa24a119512ca75249cf`
- `shunt/__main__.py`: `c47d420d8bec0dcb85f28da4136e54b3ee0ab1f3d78b1e79d70cd9869aee3bb8`
- `scripts/audit_router.py`: `84cd7609c6a0e61f567ed26093ef9616dda4ea087a56bf6c34db875bd9724888`
- `scripts/benchmark_router.py`: `3cdad3d21bdd025a5a77895bc8e71f6494a8f8ee7a2d05997e3be4b78a99992b`
- `artifacts/shunt-lora/adapter_model.safetensors`: `bd2c76d87f7adc1600146697e6c5f84be1dfbf94fac658197b9d8bdd2263f450`