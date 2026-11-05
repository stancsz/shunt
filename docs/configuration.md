# Execution model recommendations and configuration

Shunt classifies tasks into stable T1/T2/T3 tiers. It recommends the following execution models by default. These recommendations do not assert a proven ordering on your workload.

| Tier | Official weights | Assumed local Ollama model name | Responsibility |
| --- | --- | --- | --- |
| T1 | [XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B) | `mimo-v2.6-distill-qwen-9b` | Routine edits, simple fixes, boilerplate, and straightforward tests. |
| T2 | [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) | `qwen3.8:27b` | Feature implementation, integrations, debugging, and module refactoring. |
| T3 | [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) | `deepseek-v4.1-flash:1017` | Complex or high-risk work, ambiguity, and repeated failures. |

Tiers have no parameter-count requirement. MiMo and Qwen use their publishers' 9B and 27B designations. DeepSeek's Hugging Face repository lists 763B parameters; total stored and active-per-token counts are different concepts. MiMo is an official Xiaomi research SFT checkpoint; its model card reports SWE Pro avg@3 of 44.6 against Qwen3.5-9B's 32.0 and Terminal-Bench 2.1 avg@1 of 37.1 against 27.0. These are publisher-reported results. Qwen is Apache 2.0 licensed; MiMo and DeepSeek are MIT licensed according to the linked cards.

## Load settings

Install the project requirements, including `python-dotenv`, then copy the [example](../.env.example):

```powershell
Copy-Item .env.example .env
```

Launch from the repository root. The CLI and HTTP server read `.env` from the current working directory once at startup. Precedence is per key: process environment, then `.env`, then built-in defaults. A per-tier setting takes precedence over its shared fallback. Thus a per-tier URL in `.env` still wins over a shared URL from the process environment. Server `--host` and `--port` arguments override their configuration values. Restart after changing settings; there is no live reload.

`.env` and `.env.*` are gitignored except `.env.example`. The loader does not modify the process environment and disables `${...}` interpolation, preserving literal credential values. Use standard dotenv quoting for values with spaces or `#`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `SHUNT_HOST` | `127.0.0.1` | Shunt HTTP listening address. |
| `SHUNT_PORT` | `18765` | Shunt HTTP listening port, 1 through 65535. |
| `SHUNT_TARGET_BASE_URL` | `http://127.0.0.1:11434/v1` | Shared OpenAI-compatible target URL, including the target port and `/v1` path. |
| `SHUNT_TARGET_API_KEY` | Empty | Shared target credential; local Ollama is assumed unauthenticated. |
| `SHUNT_TARGET_TIMEOUT_SECONDS` | `120` | Positive, finite timeout metadata for a downstream caller. |
| `SHUNT_T1_MODEL`, `SHUNT_T2_MODEL`, `SHUNT_T3_MODEL` | Local names in the table above | Model names understood by your target servers. |
| `SHUNT_T1_BASE_URL`, `SHUNT_T2_BASE_URL`, `SHUNT_T3_BASE_URL` | Shared URL | Optional per-tier endpoint, including its own port. |
| `SHUNT_T1_API_KEY`, `SHUNT_T2_API_KEY`, `SHUNT_T3_API_KEY` | Shared credential | Optional per-tier credential. Explicitly empty disables inherited authentication for that tier. |
| `SHUNT_T1_TIMEOUT_SECONDS`, `SHUNT_T2_TIMEOUT_SECONDS`, `SHUNT_T3_TIMEOUT_SECONDS` | Shared timeout | Optional per-tier timeout metadata. |

URLs must use HTTP or HTTPS and must not contain embedded credentials, query strings, or fragments. Put credentials in API-key settings. The target key is separate from Shunt's inbound HTTP service, which remains unauthenticated and bound to loopback by default.

## Example: separate servers

```dotenv
SHUNT_HOST=127.0.0.1
SHUNT_PORT=18765
SHUNT_TARGET_BASE_URL=http://127.0.0.1:11434/v1
SHUNT_TARGET_API_KEY=
SHUNT_TARGET_TIMEOUT_SECONDS=120

SHUNT_T1_MODEL=mimo-v2.6-distill-qwen-9b
SHUNT_T2_MODEL=qwen3.8:27b
SHUNT_T2_BASE_URL=http://127.0.0.1:11435/v1
SHUNT_T3_MODEL=deepseek-v4.1-flash:1017
SHUNT_T3_BASE_URL=https://inference.example.com/v1
SHUNT_T3_API_KEY="replace-with-your-key"
SHUNT_T3_TIMEOUT_SECONDS=300
```

The default deployment assumption is that all three execution models can be served through Ollama's OpenAI-compatible API. These are assumed aliases, not verified registry tags or tested hosting recipes. Import/create the selected weights under these names or set names that already exist on your servers. No target connectivity, hardware fit, or serving support is implied by loading configuration.

## Output and integration

An eligible T1 decision from the CLI or the `result` of `POST /v1/data/shunt/route` includes:

```json
{
  "route": "T1",
  "probabilities": {"T1": 0.9, "T2": 0.05, "T3": 0.05},
  "target": {
    "model": "mimo-v2.6-distill-qwen-9b",
    "base_url": "http://127.0.0.1:11434/v1",
    "timeout_seconds": 120.0
  }
}
```

Other existing decision fields are omitted above for brevity. `route()` remains a pure policy function: it returns tier decisions without loading `.env` or adding target settings. The application entry points attach `target` after policy evaluation, including after escalation.

Shunt does not invoke execution models. A downstream application can use the same loader to obtain credentials and endpoint settings locally:

```python
from shunt.config import load_settings

settings = load_settings()
target = settings.targets[decision["route"]]
# Supply target.model, target.base_url, target.api_key, and
# target.timeout_seconds to your downstream OpenAI-compatible client.
```

API keys are excluded from routing responses and configuration object representations. Target timeouts are configuration for downstream integrations, not enforced outbound timers in Shunt, since Shunt makes no target requests.

## Compatibility

Previously, `route` and `probabilities` used hardcoded execution-model aliases. They now use T1/T2/T3 consistently; consumers must update lookups accordingly. Historical evaluation JSON and receipts are preserved as originally recorded. Their model-alias keys do not describe the new wire format. The classification labels, policy floors, escalation rules, trained adapter, and router backbone are unchanged.
