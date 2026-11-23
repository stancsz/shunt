# Shunt: market position and maturity

**Reviewed:** 2026-11-23<br>
**Product readiness:** research prototype. The local classifier and explicit policy have bounded synthetic and fixture evidence; production readiness is explicitly unestablished.<br>
**Market validation:** hypothesis. External use, task-level gains, adoption, and willingness to pay are unknown.

## Audience and job

The intended user is a coding-agent or AI-platform developer who wants a small local component to recommend a model tier before work is sent to an execution model. The job is to expose the recommendation and policy inputs while leaving invocation, user approval, and final outcome with the caller.

## Alternatives and position

| Substitute | What its primary source establishes | Shunt's testable position |
| --- | --- | --- |
| Rules and routing inside LiteLLM | The LiteLLM router supports configured routing strategies, retries, fallbacks, and deployment health behavior. | Shunt adds a learned local task score plus explicit scope/risk/ambiguity rules and returns a recommendation only. It must show better downstream outcomes than well-tuned rules before claiming value. |
| Learned model routers such as RouteLLM | RouteLLM studies selecting between stronger and weaker LLMs using preference data. | Shunt explores a small local classifier for coding-task tiers and separates recommendation from execution. No quality-adjusted cost advantage has been measured. |
| A fixed model tier | Simple, predictable, and avoids router errors or extra moving parts. | Shunt is valuable only if routing improves accepted work or cost enough to justify another model and policy layer. |

Sources: [LiteLLM router](https://docs.litellm.ai/docs/routing) and [RouteLLM paper](https://arxiv.org/abs/2406.18665). These describe adjacent capabilities; no direct product comparison was run.

## Evidence and limits

- One held-out synthetic prompt set measured 34/36 for the first adapter and 24/36 for the frozen base. The scenarios are synthetic and do not establish generalization to live coding requests.
- A warm CUDA fixture run measured 16.19 ms p95 over 1,000 calls. A broader 512-token acceptance run measured 25.41 ms p95 total across the supplied repository-size fixtures. Neither is end-to-end agent latency.
- The probabilities are uncalibrated. No study establishes accepted-task quality, savings, user trust, or production readiness.
- GitHub snapshot on 2026-11-23: 0 stars, 0 forks, and no published release. Repository visibility is not usage evidence.

## Adoption friction and next experiment

Teams must operate a local model, map requests to model tiers, decide policy thresholds, and handle recommendations safely. A router error can send sensitive, difficult, or expensive work to the wrong tier. The next decision-changing study is a preregistered natural coding-task comparison of a fixed model, explicit rules, and Shunt: blind-grade accepted patches, task time, model cost, and escalation errors; calibrate confidence on separate training and held-out data. Keep execution opt-in throughout.

## Product and research values

- **Recommendation stays separate:** Shunt does not invoke the selected execution model.
- **Policy is inspectable:** explicit rules own risk, scope, ambiguity, and retry promotion.
- **Calibration before confidence:** probabilities remain labeled uncalibrated until validated.
- **Downstream evidence matters:** classifier accuracy and fixture latency do not substitute for successful task outcomes.

## Sources

- [Project README](../README.md)
- [Production-readiness review](production-readiness-review.md)
- [Local prototype results](evals/local-prototype.md)
- [LiteLLM routing](https://docs.litellm.ai/docs/routing)
- [RouteLLM paper](https://arxiv.org/abs/2406.18665)
