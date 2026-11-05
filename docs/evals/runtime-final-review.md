# Independent final local acceptance

Documentation note: execution targets below are displayed as T1, T2, and T3. Linked raw evaluation records retain the original runtime aliases.

## Verdict: READY for the stated local scope

The trained Shunt LoRA three-tier router passed the requested local acceptance checks. The independent runtime suite reported **42 passed**. A fresh CLI run using the 512-token CUDA graph returned `T3` for `--attempts 2`; unknown scope yielded `ast_file_count: null` and the Tier 3 safety overrides. Scope parsing rereads supplied Python files and keys its 32-entry LRU by file content; the tests exercise same-timestamp content changes and parse failures. Graph capture restores the saved TF32 precision setting in `finally`, including on capture failure by source inspection.

The runtime artifact reports 1,000 warm batch-1 measurements on an RTX 5070 Ti: static p95 **2.87 ms**, inference p95 **22.98 ms**, combined p95 **25.41 ms**—within the **5/25/30 ms** budgets. Its recorded source hashes match the current bytes. The 512-token CLI run also verified attempt-based escalation; the runtime report’s safety check covers attempt and file-count overrides.

Important limits: these figures cover warm local routing with authored prompts and supplied Python scope—not startup, concurrency, downstream model execution, or production workloads. The challenge audit uses authored cases, not independently labeled real tasks; its reported 95.8% challenge accuracy is not evidence of general routing quality. Semantic probabilities are uncalibrated. Caller-declared core-interface status and automatic repository-wide interface discovery remain outside the supported scope. No production generalization is warranted.

No must-fix issue reproduced. The existing adapter was not changed. This checkout has no Git `HEAD`, so review is bound to file hashes rather than a commit/tree SHA. The reviewed adapter-weight SHA-256 is `bd2c76d87f7adc1600146697e6c5f84be1dfbf94fac658197b9d8bdd2263f450`; graph source SHA-256 is `8bef7db2e3792c3d600d44a4e2bd5fe2dffdf917c7d94e100dc77d916fe979cb`.
