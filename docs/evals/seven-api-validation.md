# Seven-format API verification

Verified on 2026-11-05 against the host Shunt service at `http://127.0.0.1:18765`, using the existing local adapter and CUDA graph scorer.

- Full author suite: `python -m pytest -q -p no:cacheprovider` — **93 passed**.
- Actual GPU requests through all seven formats returned identical classifier probabilities. A retry count of two selected policy T3 while the raw classification was T1. Results: [seven-formats-live.json](seven-formats-live.json).
- Former custom `POST /route` returned 404.
- Live OpenAI and Anthropic SDK normal and SSE calls passed; live Hugging Face classification and Triton HTTP/JSON inference passed from the project environment. Versions are pinned in `requirements-dev.txt` and `requirements.txt`.
- Independent CLI reviewer: **READY** for all seven live HTTP contracts and OpenAI/Anthropic/Hugging Face client probes. Its interpreter lacked Triton, and pytest was not retried after the previously recorded temporary-directory access denial. These limits are preserved in [the independent review](seven-api-review.md); the author executed Triton separately.
- [Source manifest](seven-api-source-hashes.json) records the reviewed working-file bytes. The final review contains a transcription omission in the `scripts/check_api.py` hash; the manifest contains the complete digest. Git line-ending normalization may change byte hashes in other checkouts.

These checks cover the supported routing adapters described in [the API guide](../api.md), not complete vendor services, arbitrary chat generation or coding-agent tool execution. No model weights or policy rules changed. MiMo remained running locally and the Docker test container remained stopped.
