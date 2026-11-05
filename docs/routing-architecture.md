# Shunt routing architecture

## Purpose and status

See [low-data routing research](wiki/001-low-data-routing.md) for implementation candidates, design review, and a validation plan. Its proposed policy clarifications do not supersede the criteria below.

Shunt routes coding tasks to one of three model targets using semantic classification, structural scope, lexical risk, and prior failures. The original design used zero-shot inference without custom training data. The user subsequently selected a trained LoRA implementation; see [training and policy](training.md). The local prototype now includes a trained adapter, deterministic policy, Python file-scope inspection, and measured synthetic evaluation. The criteria below remain the target contract; prototype evidence does not establish production acceptance.

## Selected routing backbone

Shunt uses `Qwen/Qwen3.5-0.8B` as its selected base model for the Jev-style routing decision engine. This is the local classifier backbone; the three execution targets are listed below. The [official model card](https://huggingface.co/Qwen/Qwen3.5-0.8B) documents a 0.8B language model and non-thinking support.

The implementation freezes the original weights and trains the Shunt LoRA adapter on authored policy examples, using text-only input and non-thinking mode. Present the task and three tier descriptions as options `A`, `B`, and `C`; verify their token IDs in the exact prompt context; read their next-token logits after one forward pass; and normalize those scores across the three options. Construct the typed output directly and apply the structural, lexical, ambiguity, and retry policy. No generated answer or prose parsing is needed.

The scores are uncalibrated semantic choice probabilities, not measured probabilities of successful task execution. Pin the model revision, tokenizer, prompt, and inference runtime when implementing. Routing quality and the latency target remain unverified. This selection supersedes the earlier `Qwen/Qwen3-0.6B` prototype suggestion and the research entry's initial embedding-first recommendation for the chosen implementation.

## Routing tiers

| Tier | Default recommendation | Typical semantic tasks | Structural guidance |
| --- | --- | --- | --- |
| T1 | MiMo-V2.6-Distill-Qwen-9B | Syntax, formatting and lint fixes; docstrings and comments; local renames and symbol extraction; boilerplate and single-function tests. | One file, fewer than 50 lines of AST scope, no previous attempt, and no high-risk lexical trigger. |
| T2 | Qwen3.8-27B | Standard features and CRUD endpoints across files; module refactoring; documentation-informed integration tests; code-pattern translation and migration. | Two to eight files, standard cross-module imports, and at most one previous attempt, unless a higher-tier override applies. |
| T3 | DeepSeek-V4.1-Flash-1017 | Race conditions, deadlocks and memory leaks; distributed architecture and security protocols; circular dependencies and state corruption; root-cause analysis of failed tests. | Core interfaces or base classes, more than eight files, high-risk lexical triggers, or at least two previous attempts. |

High-risk lexical triggers are `async`, `mutex`, `lock`, `atomic`, `race`, `segfault`, `deadlock`, `OOM`, `migration`, `cryptography`, and `auth`. A match is a Tier 3 override, including when the semantic description would otherwise suggest a lower tier.

## Composite decision

The proposed router combines three signals:

```text
route_score = w1 * semantic_entailment(prompt)
            + w2 * blast_radius(AST)
            + w3 * failure_state
```

Semantic entailment ranks the three targets. Blast radius captures the static scope and lexical risk; failure state reflects `attempt_count`. The formula describes the intended inputs, not a defined scoring implementation: weights and score calibration remain to be specified. Safety overrides take precedence over semantic scores.

| Primary semantic match | Margin | Scope or risk | Attempts | Final target |
| --- | --- | --- | --- | --- |
| `T1` | At least 0.15 | One file, no risk keyword | 0 | `T1` |
| `T1` | Below 0.15 | One or two files, no risk keyword | 0 | `T2` (ambiguity bump) |
| `T2` | At least 0.15 | Two to eight files, no risk keyword | 0 or 1 | `T2` |
| `T2` | Below 0.15 | Any | Any | `T3` (ambiguity bump) |
| Any | Any | More than eight files or a risk keyword | Any | `T3` (scope or lexical override) |
| Any | Any | Any | At least 2 | `T3` (circuit breaker) |
| `T3` | Any | Any | Any | `T3` |

An ambiguity bump promotes the semantic winner by one tier, capped at Tier 3. The margin is the difference between the highest and second-highest normalized semantic probabilities. Core interface or base-class changes also trigger Tier 3. If multiple overrides apply, the result remains Tier 3 and all applicable flags should be retained.

The user authorized setting the routing rules. The complete policy now imposes at least Tier 2 when Tier 1 scope eligibility fails, and Tier 3 when scope is unknown. Matching rules and Python AST line-scope semantics are defined in [training and policy](training.md). Core-interface status is a caller declaration; automatic repository-wide interface discovery and calibrated solve probabilities remain outside the current implementation.

Tiers represent responsibilities, not parameter ranges. The defaults above can be replaced independently through [environment configuration](configuration.md). The policy uses stable tier labels; model names, endpoints, and credentials belong at the application boundary.

## Output contract

The CLI and HTTP API serialize stable T1, T2, and T3 labels in `route` and `probabilities`. Both add public `target` metadata resolved from configuration; credentials are never included. This replaces the historical model-alias wire values; raw evaluation receipts retain their original values. See [configuration and migration](configuration.md).

Return a strict typed structure with at least:

```text
route: one of "T1", "T2", "T3"
probabilities: normalized probability for each of the three targets
semantic_margin: number
ast_file_count: nonnegative integer
overrides:
  lexical_risk: boolean
  ambiguity_bump: boolean
  circuit_breaker: boolean
```

Probabilities must be finite, nonnegative, and sum to one within the implementation's documented numeric tolerance. They represent semantic probabilities, so the selected route can differ from the semantic winner after an override. The contract should also expose scope and core-interface overrides when those triggers apply, so the final selection is explainable. The serialization format and any additional metadata remain implementation choices.

## Acceptance criteria

Current measured local evidence is summarized in [training and acceptance](training.md#current-local-acceptance). The supported runtime is warm batch-one CUDA graph inference up to 512 total prompt tokens on the tested RTX 5070 Ti, with explicitly supplied Python file scope or declared metadata. AC-1's file count is a nonnegative integer for known scope; the configured conservative unknown-scope extension reports null with an explicit flag and forces Tier 3. Core-interface status is caller-declared. Cold startup, arbitrary languages and production traffic are not covered by this local acceptance.

1. **Typed output:** Return the target, normalized distribution over all three targets, semantic margin, AST file count, and `lexical_risk`, `ambiguity_bump`, and `circuit_breaker` flags in a strict typed structure.
2. **Tier 3 safety guard:** Route every task with `attempt_count >= 2`, more than eight touched AST files, or a high-risk concurrency/security keyword to `T3`, regardless of lower-tier semantic scores.
3. **Ambiguity escalation:** When the top-two zero-shot probability margin is below 0.15, promote a Tier 1 semantic winner to Tier 2 or a Tier 2 winner to Tier 3. Tier 3 remains Tier 3.
4. **Latency and cost:** Combined static AST and lexical inspection (under 5 ms) and local `Qwen/Qwen3.5-0.8B` first-token logit evaluation (under 25 ms) must complete in at most 30 ms at p95, with $0 marginal API cost. The selected backbone replaces the original cross-encoder or larger-model scoring candidate; the timing and cost thresholds are unchanged.

The latency and cost criterion is a target, not a measured result. Acceptance requires a representative workload and a documented local hardware and model configuration, timing boundaries, sample size, percentile calculation, and evidence that the evaluated path incurs no per-request API charge. Feasibility of local inference within the budget is unverified.
