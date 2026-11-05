# Shunt LoRA training and policy

## Current local acceptance

The trained adapter and warm runtime now meet the measured local timing budgets on the RTX 5070 Ti. [Acceptance evidence](evals/acceptance-runtime.json) records 1,000 calls across 1/2/8/9 supplied Python source files and four authored prompts up to 502 tokens, using the 512-token graph. Static inspection plus lexical policy measured **2.87 ms p95**, inference **22.98 ms p95**, and combined routing/serialization **25.41 ms p95**. Retry and blast-radius safety probes passed. These are warm, batch-one measurements with a content-keyed parsing cache, not guarantees for cold startup, concurrency, arbitrary repository sizes or other languages.

The runtime captures float32 reference-attention matrix operations using TF32 (`high` precision), then restores the caller's precision setting in `finally`. The captured graph retains its chosen kernels. The unchanged adapter still scores 23/24 on the challenge set; predictions and final routes match the earlier run for all challenge cases. See [updated challenge measurements](evals/challenge-audit-tf32.json). The separate near-limit 502-token audit measured **23.66 ms p95** after this change.

AST inspection now memoizes pure line counting in a 32-entry LRU keyed by resolved filename and actual source text. Every request rereads the files, so timestamp preservation cannot conceal changed content. Changed and malformed contents are tested. Eight actual source files measured **3.21 ms p95** in the isolated warm inspection test; [full results](evals/scope-benchmark-cached.json) distinguish first-use timing.

The pre-optimization timings later in this document are historical evidence of the issues that prompted these changes; they do not describe the current TF32 graph runtime. Probabilities remain uncalibrated semantic scores. No downstream target execution or production-quality claim is made.

## Execution target configuration

The trained A/B/C semantic labels and escalation rules are unchanged by model selection. Runtime decisions now use stable T1/T2/T3 keys. Default execution recommendations and `.env` overrides are defined in [configuration](configuration.md). Historical evaluation artifacts retain their original model-alias keys; their policy and latency measurements predate the configuration change. No adapter retraining is required solely to remap a tier.

## Contract

The user selected Shunt as the codename of a trained LoRA adapter for Qwen3.5-0.8B. This supersedes the earlier frozen-weights-only prototype direction. Training learns the semantic tier, while deterministic policy retains authority over escalation. No provider requests are sent during local training or inference after the base weights are downloaded.

## Data and objective

`scripts/make_data.py` authors 216 balanced training examples from 36 intent templates and six subject names. The 36 validation examples use 18 separate intent templates and two unseen subject names. Both are synthetic English policy supervision, not measured coding outcomes, expert-reviewed labels, or an independent real-world test. Subject substitutions are correlated examples, not independent evidence. Do not claim 252 distinct task families.

The prompt describes the three task categories with labels A, B and C. The tokenizer verifies each label occupies a single token and continues the actual non-thinking chat template without boundary changes. Cross-entropy is computed over the three next-token logits, without generating text. LoRA rank is 8, alpha 16, dropout 0.05; AdamW learning rate is 0.0002, seed 42, batch size 4, three epochs. The language model's attention and MLP projection layers receive adapters; the vision encoder and original weights remain frozen. The adapter has 4,669,440 trainable parameters in this configuration.

The training run writes `artifacts/shunt-lora/adapter_model.safetensors`, adapter configuration, tokenizer files, and `training.json` containing losses, data hash, prompt hash, label IDs and timing. Base weights are at `models/Qwen3.5-0.8B`. These large/downloaded outputs are gitignored. Requirements pin the tested core package versions; Hugging Face download metadata records the fetched base revision.

## Complete routing policy

- Preserve the semantic distribution when a guard changes the final route. Scores are not calibrated solve probabilities.
- Promote the semantic winner once when the top-two margin is below 0.15; cap at tier 3. At exactly 0.15, do not promote (floating comparison tolerance 1e-12).
- Tier 1 eligibility requires exactly one known file, fewer than 50 known scoped lines, and attempt count zero. Other known scopes impose at least tier 2.
- Tier 3 is mandatory for unknown scope, more than eight files, a declared core interface/base class change, two or more prior attempts, or a risk token.
- Risk matching scans the task text case-insensitively as ASCII alphanumeric tokens. Underscores and hyphens separate tokens: `auth_handler` matches `auth`, while `clock` does not match `lock`. The full token list is in `shunt/policy.py`. Attached code must be included in task text if it should be scanned. This guard does not detect every semantic hazard.
- Choose the maximum of the structural/risk/retry floor and the ambiguity-promoted semantic tier. Stable ties begin with the lowest tier before ambiguity promotion.
- Reject malformed metadata and distributions. Empty tasks and eager prompts exceeding 512 tokens fail explicitly. Scope metadata can be caller-declared or inspected with repeatable `--scope-file` arguments. The Python inspector deduplicates resolved file paths, parses each complete file, and counts the union of top-level AST statement line ranges including decorators. It rejects unsupported languages, missing or malformed files and files over one megabyte. It measures supplied scope, not future edits. Core-interface status must be declared with `--core-interface`. Unknown file count is represented as null and forces tier 3, a documented extension to AC-1's known-scope integer contract.
- Model load or scoring failures stop with an error; they do not produce invented probabilities or dispatch a lower-tier target.

## Evaluation and limits

`scripts/evaluate.py` compares semantic labels against the held-out synthetic set and records the confusion matrix, per-task scores and warm p50/p95. Run frozen base and adapter separately after training stops. The timing includes prompt construction, tokenization, model scoring and softmax; it excludes process startup, model load and static scope parsing. It is not full AC-4 acceptance and 36 measurements are not a robust production latency estimate.

The Windows environment uses PyTorch reference implementations when `causal_conv1d` and `flash-linear-attention` are absent. Actual latency must be reported even if it misses the design target. Policy unit tests cover malformed inputs, lexical boundaries, retry transitions, scope and ambiguity boundaries. Independent review and a fresh-process adapter reload are required before claiming the trained artifact is usable.

Future acceptance needs authorized real coding tasks, target execution outcomes, multilingual and adversarial prompts, calibration, and representative full-path latency measurements. Synthetic accuracy cannot substitute for these results.

## CUDA graph path

`--cuda-graph` merges the trained adapter into the in-memory BF16 model, selects the three frozen output-head rows for the route labels, then warms and captures one fixed bucket. The source adapter on disk is unchanged. The default bucket is 256 tokens; `--graph-tokens 512` selects the tested larger bucket. Prompts longer than the selected bucket fail explicitly. Reuse one `GraphScorer` instance in a long-lived single-threaded caller; it is not thread-safe. The one-shot CLI still pays model load and graph setup on every invocation, so warm timings do not describe CLI startup time.

`scripts/benchmark_router.py` compares graph scores against unmerged adapter eager scores, then measures 1,000 warm calls including Python AST fixture inspection, tokenization, scoring, lexical policy and JSON serialization. It repeats the 36 synthetic validation prompts and tests retry and scope floors. This is a bounded local benchmark, not production p95 or a cross-language AST guarantee. Reduced-precision merge can shift probabilities slightly; semantic winners and policy decisions must be checked.

The downloaded base revision is `2fc06364715b967f1860aea9cf38778875588b17`; `scripts/download.py` pins it for reproduction.

## Post-training challenge audit

The unchanged trained adapter scored 23/24 on a separate authored challenge set in both graph buckets. All three prompt-injection probes and all three Chinese examples were correct. The error was “Test that the endpoint persists records and returns the expected HTTP response,” predicted Tier 1 rather than Tier 2. Complete records are in [challenge-audit.json](evals/challenge-audit.json). These labels were not fed into training or used to select a checkpoint; this remains a small authored evaluation, not a real execution-outcome benchmark.

The three-row output head preserved all semantic winners on the original validation set, with maximum probability difference below 0.0001 versus unmerged adapter eager scoring. The updated 512-token warm graph pipeline measured 25.38 ms p95 across 1,000 repeated-fixture calls, including the same tiny Python AST fixture (inspection p95 0.85 ms). See [raw measurement](evals/router-benchmark-512.json).

Near-limit prompt measurements (100 repeats each) were 15.18 ms p95 at 250 tokens and 25.64 ms at 502 tokens, including scoring and policy but excluding AST inspection. Oversize inputs failed explicitly in both buckets. The 502-token scoring result exceeds AC-4's separate under-25-ms inference budget, even though the measured full repeated-fixture pipeline remains below 30 ms. General AC-4 acceptance therefore remains open; do not silently discard the component budget or substitute the shorter-prompt result.
