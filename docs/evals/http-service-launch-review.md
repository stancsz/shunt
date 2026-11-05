# Shunt local HTTP launch review

Documentation note: execution targets below are displayed as T1, T2, and T3. Linked raw evaluation records retain the original runtime aliases.

## Verdict: READY — local-only prototype launch

Observed on 2026-11-05 against the already-running service at `127.0.0.1:18765`:

- `GET /health` returned 200 with `status=ready`, adapter `artifacts/shunt-lora`, `max_prompt_tokens=512`, `calibrated=false`, and `mode=cuda_graph`.
- Live `POST /route` syntax task (`file_count=1`, `ast_lines=12`) returned 200 and `T1`.
- The same task with `attempt_count=2` returned 200 and `T3` (`circuit_breaker=true`, `structural_floor=3`).
- Negative scope (`file_count=-1`) returned 422: `file_count must be a nonnegative integer or None`.
- A task consisting of 2,000 repeated words returned 422: `Task exceeds 512-token CUDA graph bucket`.
- A final `GET /health` still returned 200 and `status=ready`.

These `/route` calls ran actual model inference for valid requests, not a mocked scorer. The probabilities were strongly concentrated on `T1` even when the retry policy overrode the final route to `T3`.

## Source, binding, and restart evidence

Reviewed `shunt/server.py`, `shunt/model.py`, `shunt/graph.py`, `shunt/policy.py`, and the README `Local HTTP service` section. Server code binds the configured host/port, defaults to loopback and port 18765, validates route metadata before model scoring, and reports an uncalibrated local CUDA-graph mode. The README documents `PYTHONPATH='.'` followed by `.venv/Scripts/python.exe -m shunt.server --cuda-graph` from repository root. With that environment and working directory, the specified venv interpreter’s `-m shunt.server --help` succeeded and displayed the same `server.py` arguments without loading the model or starting another instance.

`netstat` observed a listener on `127.0.0.1:18765` (PID 25308), not a wildcard/public bind. Windows process-command inspection was denied by the environment; therefore the listening PID’s executable and command line could not be independently confirmed. No service stop, restart, or second model/GPU instance was attempted.

SHA-256 fingerprints of `server.py`, `model.py`, `graph.py`, `policy.py`, and the adapter `adapter_config.json` are recorded in `probe.json` to bind these observations to the inspected candidate files.

## Limits / acceptance boundary

This is acceptance of local prototype launch behavior only. It is not public deployment or production acceptance: the endpoint is unauthenticated, source reports `calibrated=false`, and the README says scope is caller-declared and the endpoint only returns routing decisions rather than executing a target model. No accuracy or latency acceptance was performed. The documented process is a background instance without automatic restart; restart behavior was checked only with `--help`, not by stopping/restarting it. No claim is made about startup recovery, persistence, or robustness beyond the probes above.
