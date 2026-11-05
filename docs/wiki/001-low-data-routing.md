# 001 — How can Shunt route coding tasks with little or no task-specific training data?

- **scope:** Shunt's three-tier coding-task policy, using `T1`, `T2`, and `T3` as provider-independent execution tiers.
- **status:** draft; recommendations await project evaluation.
- **verified:** 2026-11-04 (primary-source review; no local inference benchmark).
- **decision it feeds:** Select a router that can start without a Shunt training corpus, while preserving deterministic escalation and a measurable latency target.

## Answer

**Subsequent project decision:** The user selected `Qwen/Qwen3.5-0.8B` and then authorized training Shunt as its LoRA adapter for routing. See the [selected backbone](../routing-architecture.md#selected-routing-backbone) and [local results](../evals/local-prototype.md) for the current implementation and measured prototype evidence. The embedding and NLI comparisons below remain research alternatives; the initial frozen-weights recommendation is superseded. Research statements below describe the earlier investigation, not the current training status.

Start with deterministic safety rules plus a frozen, small semantic encoder. Compare an embedding-prototype implementation with an NLI cross-encoder before selecting the production semantic adapter. Neither requires training on Shunt tasks. Keep policy, semantic scoring, and model-target configuration separate. This is a recommendation, not a measured result or a change to the existing acceptance criteria.

The central distinction is between **matching a task description to a tier** and **predicting which model can solve it**. Zero-shot semantic models can supply the former. Model-specific success predictions require evidence from the actual targets and workload. The supplied model aliases do not establish their capabilities, provider identity, price ordering, or strict quality ordering; all remain unverified for this project.

### Methods and trade-offs

| Method | Shunt-specific training needed? | How it would work here | Assessment |
| --- | --- | --- | --- |
| Static rules | No | Check retry count, declared scope, protected interfaces, and lexical risk. | Required safety layer and useful baseline; limited semantic understanding. |
| Embedding prototypes | No | Embed authored tier descriptions once; embed each task and compare cosine similarity. | Recommended first latency candidate. Similarity is not entailment or success probability. |
| NLI cross-encoder | No | Score each task paired with one of three natural-language tier hypotheses. | Recommended challenger; directly supports entailment-style scoring, but three pairs add inference work. |
| Instruction model with three labels | No, or a few prompt examples | Ask a local model to choose a tier; optionally score constrained label tokens. | Flexible baseline; prompt prefill, label bias and serving overhead make the latency assumption risky. |
| Existing pretrained router | No new local training, but trained upstream | Supply routing policy and configured target mapping to a router such as Arch-Router. | Worth a later comparison; published task coverage is not evidence for Shunt coding quality. |
| Retrieval from resolved tasks | Small labeled experience store; no weight updates | Retrieve similar tasks and their verified outcomes. | Useful after experience exists; cold start and repository leakage need handling. |
| Supervised preference router | Yes, unless accepting a transferred pretrained router | Learn cheaper-versus-stronger selection from comparative outcomes. | RouteLLM is a relevant later baseline, not evidence that training-free deployment needs no validation. |
| Execute and escalate | No classifier training; needs validators | Try an eligible lower tier, validate the result, escalate on failure. | Can provide direct evidence, but consumes execution time and model cost; not a 30 ms routing decision. |

Embedding retrieval is supported by Sentence Transformers' documented query/corpus design [S1]. NLI score construction is explicit in Transformers [S2]. Arch-Router is an upstream-trained 1.5B preference router with support for adding targets without retraining [S5]. RouteLLM uses preference training and data augmentation, and reports transfer across model pairs [S6]. The assessments above are Shunt-specific engineering inferences, not benchmark claims from those sources.

### Concrete zero-data scoring recipes

**Embedding candidate:** author one comparable-length description per tier using the semantic tasks in the architecture document. Avoid using unfamiliar model names as the semantic descriptions. Cache normalized vectors for these descriptions. For task vector `x` and tier vectors `v_i`, compute `s_i = cosine(x, v_i)` and `p_i = softmax(s_i / T)`. Start with a fixed, recorded `T` rather than claiming calibration. Extra prototypes per tier are possible, but freeze their count and aggregation rule before evaluation to avoid accidental bias. `all-MiniLM-L6-v2` is a concrete small English embedding baseline; its card documents 384-dimensional vectors and default truncation beyond 256 word pieces [S3]. Mixed-language tasks and long code contexts require separate evaluation.

**NLI candidate:** pair the task with hypotheses such as “This task requires a small local syntactic edit,” “This task requires standard feature implementation or module-level work,” and “This task requires deep diagnosis or architectural reasoning.” Batch the three pairs. Read the checkpoint's actual entailment label mapping, then normalize the three entailment logits with softmax. Transformers' single-label zero-shot path implements that normalization; its multi-label path instead normalizes entailment against contradiction separately for each label and does not provide the required sum-to-one distribution across tiers [S2]. A candidate checkpoint is `cross-encoder/nli-MiniLM2-L6-H768`, whose publisher identifies it as an English NLI model [S4]; verify configuration and revision before use.

Neither recipe yields calibrated coding success probabilities. A large top-two margin can occur when all three descriptions fit poorly. Retain raw scores and scorer version for diagnosis. Treat the existing 0.15 margin as a policy constant to test, not a universal confidence boundary. Softmax temperature, wording, and candidate descriptions can change that margin. Calibration research demonstrates that neural confidence can be misleading and describes temperature scaling [S7]; fitting a temperature requires labeled calibration data and therefore belongs to the low-data option.

### Review of the current architecture

1. **Keep overrides outside the weighted score.** A weighted sum can allow a strong semantic score to offset a safety trigger. Implement hard guards separately, then select the maximum required tier. The weights currently have no operational definition. A simple precedence policy is enough to express the mandatory behavior.
2. **Clarify what the distribution means.** AC-1 can return a normalized semantic distribution with explicit `calibrated: false` metadata. It should not describe those values as the probability of a successful patch. Overrides may change the selected route without changing the semantic distribution. The embedding candidate changes the stated cross-encoder/logit method in AC-4; adopting it requires an explicit specification revision, not silent acceptance under the existing wording.
3. **Scope is partly unknown before execution.** An AST can describe supplied files and symbols, but not establish all future edits implied by an arbitrary prompt. Accept declared candidate paths and symbol ranges from the caller; report scope provenance and completeness. Repository-wide dependency traversal is a separate operation. Unknown scope must not be represented as zero files. Proposed conservative fallback: Tier 3 when scope needed for eligibility is unavailable.
4. **Make tier floors complete.** Proposed policy: Tier 1 requires one known file, fewer than 50 scoped lines, zero attempts, and no risk trigger; otherwise use at least Tier 2. Core-interface changes, more than eight files, risk triggers, or two attempts require Tier 3. Apply ambiguity promotion to the original semantic winner, then take the maximum of that result and the structural/retry floor. Do not accidentally promote twice. These fill previously unspecified cases and need acceptance before implementation.
5. **Keep lexical policy literal and auditable.** Define case folding, token boundaries, scanned fields, and how code identifiers match. `lock` must not accidentally match every occurrence of `clock`; whether `auth_handler` matches `auth` requires an explicit rule. A request to add a comment mentioning `async` still escalates under the supplied literal policy. Conversely, a dangerous task can avoid these words. Passing the keyword guard proves policy compliance, not comprehensive safety. Generic “migration” in Tier 2 conflicts with the Tier 3 trigger whenever that word appears; retain the override precedence.
6. **Typed output does not require generated prose.** Construct the output directly from numeric model outputs and policy decisions. For a generative classifier, verify tokenizer label IDs and access to logits; restricting labels does not eliminate prompt processing. First-token scoring still requires prefill of the task context [S8]. A 27B model is therefore an unverified latency candidate, not a shortcut to a 25 ms guarantee.
7. **Separate no API charge from free execution.** Local inference can avoid a metered external request, while still using hardware, memory, and electricity. Downstream task execution may incur API charges. No evidence currently proves the stated latency or cost target for Shunt.

### Smallest complete implementation proposal

```text
task + caller-supplied scope + failure state
  -> validate inputs / derive hard tier floor
  -> frozen semantic adapter -> distribution and semantic winner
  -> one-tier ambiguity promotion of semantic winner
  -> max(promoted winner, hard floor)
  -> typed decision + all reasons + versions
```

Keep this in one process with three small boundaries: a scope inspector, an interchangeable semantic scorer, and a pure policy function. Tier-to-provider mapping belongs in configuration. No vector database, learned weight combiner, service mesh, or online training is needed for the initial experiment. Proposed timeout behavior is Tier 3 with an explicit scorer-unavailable reason; if inference is skipped or fails, do not fabricate semantic probabilities. Resolving that failure response versus AC-1's unconditional distribution requirement is a specification decision.

### Little-data path and validation plan

Zero task-specific training does not mean zero evaluation. Proposed experiment sizes below are starting budgets, not statistical guarantees:

1. Assemble about 120 representative coding task states from authorized repository issues and small controlled tasks. Include local edits, multi-file work, diagnosis, missing scope, retries and risk cases. Keep prompt variants and tasks from the same issue or repository family in the same split.
2. Use a development portion to inspect failures, then freeze descriptions, tokenizer limits, normalization, matching rules, and policy. Reserve a held-out portion for the final comparison. Any threshold tuning is low-data adaptation and must be reported as such.
3. Check the policy independently of semantic accuracy: attempts 0/1/2; files 1/2/8/9; lines 49/50; margin just below, at and above 0.15; all lexical terms; core-interface scope; combined triggers; invalid and unknown inputs. AC-2's 100% requirement applies to these deterministic conditions. Finite tests do not prove all semantic risks are detected.
4. Compare rules-only, frozen embeddings, and NLI against reviewed tier labels. Report confusion matrices, costly under-routing, over-escalation and coverage. Policy labels alone do not prove economic value. Separately run a feasible subset on the three real targets in isolated workspaces, with existing tests and patch review, recording success, retries, total cost and completion time. Do not assume Tier 3 always wins.
5. Benchmark local routing on declared hardware with frozen model revisions. Record load/cold-start separately and measure warm batch-one p50/p95/p99 over at least 1,000 representative requests at documented concurrency, including tokenization, inspection, scoring, policy and serialization. Include prompt-length bands, cache misses, queueing and malformed inputs. Enforce a documented input bound; silent truncation must not hide risk fields. ONNX/OpenVINO and quantization are documented optimization options [S9], but speed and quality must be remeasured together.
6. If the zero-data candidates miss quality targets, add a small reviewed store of actual outcomes, retrieve neighbors, or fit a simple threshold/calibrator. Synthetic examples can test boundaries or supply development coverage; they cannot alone establish the actual models' solve rates. Delay preference-router training until measured evidence justifies it.

Before deployment, define the allowable task-success regression and under-routing rate; the architecture currently specifies no numeric end-task quality floor. A measured latency failure must remain a failure of AC-4 rather than being hidden by renaming the benchmark. This research task does not claim implementation acceptance.

## Receipts

All links inspected 2026-11-04. Confidence is high for the described source mechanisms; applicability and performance on Shunt remain unverified.

- **S1:** [Sentence Transformers semantic search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html) — embed corpus and queries, then compare vectors.
- **S2:** [Transformers zero-shot classification implementation](https://github.com/huggingface/transformers/blob/main/src/transformers/pipelines/zero_shot_classification.py) — hypothesis pairing, entailment label lookup, single-label versus multi-label normalization. Mutable source; pin a revision for implementation.
- **S3:** [all-MiniLM-L6-v2 publisher model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) — embedding baseline and input limits.
- **S4:** [NLI MiniLM publisher model card](https://huggingface.co/cross-encoder/nli-MiniLM2-L6-H768) — candidate pretrained NLI checkpoint.
- **S5:** [Arch-Router paper](https://arxiv.org/abs/2506.16655) — trained preference matching, target extensibility; not a Shunt coding benchmark.
- **S6:** [RouteLLM paper](https://arxiv.org/abs/2406.18665) — preference-data training and transfer; not proof for these three targets.
- **S7:** [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599) — confidence calibration and temperature scaling; not Shunt-specific calibration evidence.
- **S8:** [Transformers LLM optimization guide](https://huggingface.co/docs/transformers/llm_tutorial_optimization) — prompt processing and autoregressive inference mechanics.
- **S9:** [Sentence Transformers inference efficiency](https://sbert.net/docs/sentence_transformer/usage/efficiency.html) — ONNX, OpenVINO and backend optimization options.

## Review limits and changelog

- 2026-11-04: Created from the current routing design and primary sources. Repository contained architecture documentation only. No model download, local inference, target execution or latency measurement was performed.
- Advisor consultation was attempted once using the configured API and `default`; it returned HTTP 400, invalid model name. No alternate route was substituted. No advisor response or independent acceptance is claimed; `decision_changed: false`, provider usage unavailable.
