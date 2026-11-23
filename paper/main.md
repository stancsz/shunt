# A Recommend-Only Neural Router for Local Coding Tasks

Prototype architecture, synthetic held-out results, and evaluation boundaries

## Abstract

Shunt is a local coding-task router that recommends one of three configurable model tiers. A Qwen3.5-0.8B base model with a LoRA adapter scores task-complexity labels, while deterministic policy rules apply scope, risk, ambiguity, and retry handling. The router returns a recommendation and does not invoke the downstream execution model. In a bounded held-out synthetic prompt set, the trained adapter scored 34 of 36 compared with 24 of 36 for the frozen base. A warm CUDA-graph run measured 16.19 ms p95 over 1,000 fixture calls. These prototype measurements do not establish generalization, calibrated probabilities, cost reduction, downstream success, or production readiness.

## 1. Motivation and scope

Routing systems can reserve stronger models [R1] for requests that appear difficult, risky, or ambiguous, but poor recommendations can reduce task quality and retries can offset savings. Shunt explores local classification and policy for coding requests.

This report covers recommendation only. Shunt does not call execution models, so recommendation accuracy is not downstream code quality or accepted task completion.

## 2. Architecture and evidence

The learned component scores three label tokens using a Qwen3.5-0.8B base with LoRA. A separate deterministic policy applies scope floors, risk overrides, ambiguity promotion, and retry escalation. The final recommendation maps to one of three configurable tiers. The API exposes seven wire formats. Probabilities are uncalibrated.

Repository evidence [R2] reports that the held-out synthetic set scored 34/36 for the trained adapter versus 24/36 for the frozen base. This is a small-sample prototype result, not evidence of robustness to natural coding requests or distribution shift. A warm CUDA-graph measurement was 16.19 ms p95 over 1,000 fixture calls.

## Product and research values

Shunt is a local, recommend-only router for coding tasks. It scores a request and applies explicit policy rules; the calling application decides what happens next.

- **Decision/execution separation:** Shunt returns a tier recommendation and does not invoke target models.
- **Inspectable policy:** scope, risk, ambiguity, and retry rules are separate from the learned score.
- **Prototype evidence:** 34/36 versus 24/36 on one held-out synthetic set; 16.19 ms p95 on one warm fixture run.
- **Bounded claims:** probabilities are uncalibrated; generalization, downstream success, savings, and production readiness are not established.

## 3. Limits and next work

A broader 512-token run reported 25.41 ms p95 total, with separately summarized 22.98 ms inference and 2.87 ms static-processing p95. Component percentiles need not sum to total percentiles.

Future work needs representative held-out coding tasks, repository context, annotator agreement, calibration, accepted-task outcomes, human review time, latency, and cost. Current results do not establish production readiness.

## 4. Conclusion

Shunt separates learned scoring from deterministic routing and returns recommendations without invoking target models. End-to-end workload evaluation is needed to establish utility.

## References

[R1] Hu, Y., et al. RouterBench: A Benchmark for Multi-LLM Routing System. 2024. URL: https://arxiv.org/abs/2403.12031
[R2] Chen, S. Shunt repository. URL: https://github.com/stancsz/shunt