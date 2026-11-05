# Production readiness review and evaluation proposal

Status: **NOT READY for production adoption on current evidence.** The local training/build and bounded runtime checks passed; general routing effectiveness and operational readiness have not been established. This review and proposal do not claim that the proposed evaluation has been executed.

## What the current evidence establishes

- `scripts/make_data.py` supplies 216 training rows from only 36 authored intent templates. The 36 validation rows come from 18 authored templates with two subject substitutions each. Different family-ID prefixes are not proof of semantic independence.
- The later 24-case challenge is also authored by the builder. Its 23/24 result and three successful injection probes are useful regression evidence, not broad robustness evidence. Three Chinese examples do not establish multilingual quality.
- `scripts/acceptance_runtime.py` repeats four authored prompts over 1,000 calls. It measures runtime with real supplied Python files, but does not represent 1,000 independently sampled routing scenarios.
- The software tests check implementation invariants. They do not demonstrate that the chosen target can solve a task, that the tiers are correctly ordered by capability/cost, or that routing improves total economics.
- The adapter has been trained. Calling this Shunt artifact a no-training router would be incorrect; no-task-specific-training candidates were an earlier research direction.

The previous independent READY verdict was expressly limited to the local trained prototype. It must not be presented as production approval. No trained weights, rules or historical receipts are changed by this review.

## Why the rules may not generalize

The lexical guard matches exact ASCII tokens. A direct policy probe with deliberately supplied low-tier probabilities `[0.9, 0.05, 0.05]` showed:

| Task and metadata | Observed route | Interpretation |
| --- | --- | --- |
| Fix a typo in an auth comment; one file, 20 lines | Tier 3 | A benign mention triggers the hard guard. |
| Find an authorization bypass; one file, 20 lines | Tier 1 | The token `authorization` does not match `auth`. |
| Investigate out-of-memory failures; one file, 20 lines | Tier 1 | The phrase does not match `OOM`. |
| Determine why two writers lose committed updates; one file, 20 lines | Tier 1 | A dangerous concept can avoid all listed tokens. |
| Apply formatting to nine independent files | Tier 3 | File count overrides semantic simplicity. |

These are guard-isolation probes, not observed end-to-end adapter failures. They demonstrate both over-escalation and incomplete protection if semantic scoring is wrong. The nine-file behavior implements the existing contract correctly; its economic usefulness remains unvalidated.

File count and line count are weak difficulty proxies. Supplied scope does not predict future edits or dependency impact. Core-interface risk depends on caller metadata. The fixed 0.15 margin is unvalidated, and confident wrong answers need not have small margins. Successful guard enforcement therefore does not establish comprehensive safety or generalization.

## How many tests?

I recommend **500 development cases plus a locked 2,000-case acceptance suite**. This is a practical initial budget, not a universal minimum or a certification threshold. NIST emphasizes realistic, representative test sets and the intended operating context rather than a fixed count [1]. Published routing research also demonstrates category-specific failures that aggregate capability scores can conceal [2].

Counts must distinguish distinct task families, correlated variants, repeated timing requests and software tests. For illustration, with zero observed failures in 2,000 genuinely independent, representative Bernoulli trials, the exact one-sided 95% upper failure-rate bound is `1 - 0.05^(1/2000)`, approximately 0.15%. With only 200 cases in a critical slice it is approximately 1.49%. Those bounds do not apply unchanged to correlated paraphrases or distribution shift, and zero observed failures do not prove zero risk.

## Proposed balance

| Locked acceptance category | Cases | Coverage |
| --- | ---: | --- |
| Realistic coding tasks | 1,200 | At least 30 repositories; several languages; varied scope and project sizes; approximately 400 cases per expected tier, plus traffic-weighted reporting. |
| Difficult/adversarial scenarios | 400 | Hidden security/concurrency risks, benign risk terms, mixed intents, incomplete context, contradictory metadata and injection. |
| Paired variations | 200 | Base/variant pairs testing paraphrase, translation, irrelevant context, and meaningful negation. Report dependence explicitly. |
| Structural/operational scenarios | 200 | Scope and retry boundaries, parser/model failure, input limits, changed files, concurrency and instance isolation. |
| Total | 2,000 | Report every category and critical slice separately; do not collapse heterogeneous tests into a headline accuracy. |

The separate 500 development cases are for training improvements, rule changes, calibration and threshold selection. Keep related issues, templates and repository families in the same split. Reserve acceptance cases before tuning; keep their expected labels and final results unavailable to the builder until a candidate is frozen. Track provenance, licenses/authorization, near duplicates, revisions and known public-benchmark exposure. Once acceptance failures inform a repair, retain them as regressions and replenish the untouched final set.

Use independent label review, double-review a sample and every high-risk case, adjudicate disagreements, and permit multiple acceptable routes where justified. The balanced suite estimates category behavior; deployment-weighted metrics require an explicit traffic distribution.

## Measure actual target outcomes

Policy labels alone cannot establish which target can solve a task. Initially run 300 stratified realistic tasks on all three execution targets: **900 initial task attempts** with the same context, harness, tool permissions, validators and budgets. Record actual provider/model identity, revision, success, retries, total cost and completion time. Additional retries/repeats are extra executions, not included in the 900 estimate. Repeat a subset to assess model stochasticity. Expand the study when uncertainty prevents a decision; 300 tasks do not automatically provide adequate power for a two-point noninferiority claim.

Compare always-Tier-3, frozen-base routing, rules-only and trained-adapter-plus-rules. Measure verified completion, critical under-routing, unnecessary escalation, cost per verified completion and end-to-end time. Evaluate whether individual rules help through ablation. This is consistent with routing's quality/cost objective, rather than merely predicting authored categories [3]. API execution cost and credentials must be established before running this proposed study.

## Proposed release gates

1. All explicit deterministic override invariants pass, including independent boundary and malformed-input checks.
2. No critical unsafe under-routing is observed in the designated safety suite; document the sample size and residual uncertainty.
3. A one-sided 95% confidence bound excludes more than a two-percentage-point completion-rate loss against always-Tier-3 on the paired outcome study. Expand the sample if inconclusive; use repository/task-family-aware uncertainty estimates.
4. Cost per verified completion improves against the baseline under the declared traffic mix. Set the economically meaningful savings target before evaluating results.
5. The original 5/25/30 ms runtime budgets pass on the declared deployment workload, with startup, cache misses, concurrency and failures reported separately. A repeated warm microbenchmark cannot cover these conditions.
6. Shadow operation precedes automated adoption, with monitored routing distribution, failures, version changes, and a tested fallback/rollback path.

These gates are proposals. They are not achieved results. Keep retry escalation as a hard rule; evaluate changes to lexical, file-count and ambiguity policies against outcomes before adopting them. Freeze the current adapter first, assemble development data and independently held acceptance data, and only then retrain.

## Sources

1. [NIST AI RMF: AI risks and trustworthiness](https://airc.nist.gov/airmf-resources/airmf/3-sec-characteristics/) — representative expected-use tests and robustness across circumstances.
2. [How Robust Are Router-LLMs?](https://arxiv.org/abs/2504.07113) — category-specific and safety weaknesses in evaluated routers; not a direct evaluation of Shunt.
3. [RouteLLM](https://arxiv.org/abs/2406.18665) — preference-based routing evaluated for quality/cost trade-offs; not evidence for Shunt's particular target aliases.
