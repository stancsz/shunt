# Shunt API: seven formats

Shunt classifies coding-task complexity into T1/T2/T3 and applies deterministic escalation rules. All seven adapters use the same local model and policy. They provide routing decisions; they do not execute the recommended target or provide a general-purpose chat agent.

Base URL: `http://127.0.0.1:18765`. Model identifier: `shunt`. Open Inference Protocol model version: `1`. Requests and responses use JSON, except OpenAI/Anthropic streaming responses, which use SSE. The former custom `POST /route` was removed and returns 404. There is no replacement proprietary decision endpoint.

| Format | Inference endpoint | Native result | Supported subset |
| --- | --- | --- | --- |
| Hugging Face deployed text-classification endpoint | `POST /models/shunt` | Batched arrays of label/score pairs | Text, softmax, top_k, batches |
| vLLM classification | `POST /classify` | List envelope with label/probs/num_classes | Text input, text batches, text messages |
| Open Inference Protocol HTTP/JSON | `POST /v2/models/shunt/infer` | Typed output tensors | JSON BYTES input, FP64/BYTES outputs; metadata/readiness |
| OPA Data API decision envelope | `POST /v1/data/shunt/route` | decision_id and result | One fixed decision document; task and scope are this policy's input schema |
| Jev System One | `POST /v1/systemone` | Named Choice answer and Shunt policy result | Existing fixed coding-complexity question |
| OpenAI Chat Completions | `POST /v1/chat/completions` | Assistant content containing decision JSON | Text messages, JSON content, normal and SSE responses |
| Anthropic Messages | `POST /v1/messages` | Text block containing decision JSON | Text messages, normal and SSE responses |

These are protocol adapters for Shunt's fixed classifier, not full implementations of seven providers. OPA policy management/Rego, generic Jev questions, arbitrary models, tools, images, audio, and general text generation are outside their supported contracts. OpenAI Responses API is not implemented. Coding CLIs still require an execution gateway if they expect model-generated code and tool calls.

## Shared task and policy semantics

Classification results are **raw uncalibrated semantic probabilities**, in order T1, T2, T3. The selected policy route can be higher: retries, unknown scope, blast radius, core-interface changes and risk guards may escalate it. Do not interpret the raw winning class as the final recommendation.

All formats except Jev accept these optional HTTP headers. They are Shunt extensions that preserve the native JSON payload contract:

```text
X-Shunt-File-Count: 1
X-Shunt-Ast-Lines: 12
X-Shunt-Attempt-Count: 0
X-Shunt-Core-Interface: false
```

Counts must be nonnegative integers; core-interface must be true/false. Omitted file or line scope invokes the existing unknown-scope policy, normally selecting T3. Scope is caller-declared, not discovered from the repository. OPA also accepts `input.scope`, OIP accepts scalar `parameters`, and Jev uses its existing `shunt` object. Supply scope in only one location. Jev uses only the body scope.

The six new adapters return `X-Shunt-Route` (comma-separated routes for a batch) and `X-Shunt-Calibrated: false`. Hugging Face and vLLM preserve native classification results; read that header for the policy route. OIP returns a separate route tensor. OPA, OpenAI and Anthropic return the policy result document:

```json
{
  "route": "T1",
  "probabilities": {"T1": 0.91, "T2": 0.07, "T3": 0.02},
  "semantic_margin": 0.84,
  "ast_file_count": 1,
  "overrides": {
    "lexical_risk": false,
    "ambiguity_bump": false,
    "circuit_breaker": false,
    "blast_radius": false,
    "core_interface": false,
    "unknown_scope": false,
    "structural_floor": 1
  },
  "target": {
    "model": "mimo-v2.6-distill-qwen-9b",
    "base_url": "http://127.0.0.1:11434/v1",
    "timeout_seconds": 120.0
  },
  "calibrated": false
}
```

This document is the fixed policy's result, carried inside native envelopes, not an additional HTTP API. Target credentials are never returned. The numbers above illustrate the structure and are not measured accuracy.

## 1. Hugging Face text classification

[Reference](https://huggingface.co/docs/inference-providers/tasks/text-classification). Shunt implements the deployed-endpoint batch envelope consumed by `InferenceClient.text_classification`, which unwraps the first row for a single string. The raw HTTP response always has an outer batch dimension.

```http
POST /models/shunt
Content-Type: application/json

{"inputs":"Fix a typo.","parameters":{"top_k":3,"function_to_apply":"softmax"}}
```

```json
[[{"label":"T1","score":0.91},{"label":"T2","score":0.07},{"label":"T3","score":0.02}]]
```

`inputs` also accepts an array of 1–16 strings. `top_k` is 1–3; only softmax is supported. Scores are sorted descending with stable tier order on ties. Only empty `options` is accepted; sigmoid/raw-logit output is rejected.

```python
from huggingface_hub import InferenceClient
with InferenceClient(model="http://127.0.0.1:18765/models/shunt") as client:
    print(client.text_classification("Fix a typo.", top_k=3))
```

## 2. vLLM classification

[Reference](https://docs.vllm.ai/en/latest/models/pooling_models/classify/).

```http
POST /classify
Content-Type: application/json

{"model":"shunt","input":["Fix a typo.","Investigate a deadlock."]}
```

The response uses `object: "list"`, `id`, `created`, `model`, and `data`. Each data element has `index`, the raw winning `label`, `probs` in T1/T2/T3 order, and `num_classes: 3`. `usage` reports the actual Shunt prompt tokens and zero generated completion tokens. `input` may be a string or a text batch. Alternatively provide `messages`; it follows the latest-user rule described below. Token-ID inputs, base64 outputs, multimodal inputs and disabling activation are rejected.

## 3. Open Inference Protocol

[Reference](https://docs.seldon.ai/seldon-core-2/v2.8/apis/inference/v2). Shunt supports HTTP/JSON inference and the required HTTP readiness/metadata routes. It does not advertise binary tensor, shared-memory or gRPC extensions.

```http
POST /v2/models/shunt/infer
Content-Type: application/json

{
  "id":"example-1",
  "parameters":{"file_count":1,"ast_lines":12},
  "inputs":[{"name":"task","datatype":"BYTES","shape":[1],"data":["Fix a typo."]}],
  "outputs":[{"name":"probabilities"},{"name":"classification"},{"name":"route"}]
}
```

The response echoes `id` and returns `model_name: "shunt"`, `model_version: "1"`, and output tensors: `probabilities` FP64 `[batch,3]`, `classification` BYTES `[batch]`, and policy `route` BYTES `[batch]`. BYTES data are JSON strings. Omit `outputs` to receive all three; select a subset by name. Flattened data length must match a `[1]` through `[16]` input shape. `/v2/models/shunt/versions/1/infer` selects the explicit version.

Discovery: `GET /v2`, `/v2/health/live`, `/v2/health/ready`, `/v2/models/shunt`, `/v2/models/shunt/ready`, and corresponding version-1 metadata/readiness endpoints. The server starts listening after model loading, so readiness means it has loaded. Model metadata declares the tensors and tier ordering is T1/T2/T3.

```python
import numpy as np
import tritonclient.http as triton
with triton.InferenceServerClient("127.0.0.1:18765") as client:
    task = triton.InferInput("task", [1], "BYTES")
    task.set_data_from_numpy(np.array(["Fix a typo."], dtype=object), binary_data=False)
    output = triton.InferRequestedOutput("route", binary_data=False)
    result = client.infer("shunt", [task], outputs=[output])
    print(result.as_numpy("route"))
```

## 4. OPA decision envelope

[Reference](https://www.openpolicyagent.org/docs/rest-api). OPA's Data API deliberately permits policy-specific input and result values. Shunt exposes only the fixed `shunt/route` decision document, using that envelope. It does not evaluate arbitrary Rego, expose other data paths, or implement OPA policy/compile/bundle APIs.

```http
POST /v1/data/shunt/route
Content-Type: application/json

{"input":{"task":"Fix a typo.","scope":{"file_count":1,"ast_lines":12}}}
```

Response: `{"decision_id":"<unique-id>","result":{...policy result...}}`. `input.task` must be a single string. Errors use OPA's `code`/`message` envelope. No authentication policy enforcement is provided by this adapter.

## 5. Jev System One

[Reference](https://docs.typesafe.ai/primitives/choice). The existing request remains supported, with exactly one fixed question and any nonempty question ID:

```json
{
  "model":"shunt",
  "state":"Fix a typo.",
  "questions":{
    "difficulty":{
      "type":"choice",
      "instructions":"Classify the coding task by complexity.",
      "criteria":{
        "T1":"Small local syntax, formatting, documentation, rename, boilerplate or simple unit test.",
        "T2":"Standard feature, CRUD, integration test, module refactor or translation of existing patterns.",
        "T3":"Deep root-cause diagnosis, concurrency, memory corruption, security design or architecture."
      }
    }
  },
  "shunt":{"file_count":1,"ast_lines":12}
}
```

Send it to `POST /v1/systemone`. Read `answers.difficulty.choice` and `probabilities` for the raw classifier, and `shunt.route` for the policy recommendation. Instructions/criteria must match exactly. Arbitrary Choice definitions, multiple questions, Score, Noul, confidence and general TypeSafe SDK compatibility are not supported.

## 6. OpenAI Chat Completions

```python
import json
from openai import OpenAI
with OpenAI(base_url="http://127.0.0.1:18765/v1", api_key="local") as client:
    response = client.chat.completions.create(
        model="shunt",
        messages=[{"role":"user","content":"Fix a typo."}],
        extra_headers={"X-Shunt-File-Count":"1","X-Shunt-Ast-Lines":"12"},
    )
    print(json.loads(response.choices[0].message.content))
```

Supported request fields: `model`, `messages`, `stream`, `metadata`, `max_tokens`, `max_completion_tokens`, and `response_format` with `text` or `json_object`. The response is a `chat.completion` with a single assistant JSON-text choice and `finish_reason: "stop"`. `GET /v1/models` lists `shunt`. `stream=True` emits `chat.completion.chunk` frames followed by `[DONE]`.

## 7. Anthropic Messages

```python
import json
from anthropic import Anthropic
with Anthropic(base_url="http://127.0.0.1:18765", api_key="local") as client:
    response = client.messages.create(
        model="shunt", max_tokens=256,
        messages=[{"role":"user","content":"Fix a typo."}],
        extra_headers={"X-Shunt-File-Count":"1","X-Shunt-Ast-Lines":"12"},
    )
    print(json.loads(response.content[0].text))
```

Supported fields: `model`, `messages`, positive `max_tokens` (required), `stream`, `metadata`, and `system`. The response uses a `message` object with one text block and `stop_reason: "end_turn"`. Streaming supports the SDK's `client.messages.stream(...)`, including message/content block start/delta/stop events.

### Message adapter semantics

OpenAI, Anthropic and vLLM `messages` requests classify the **latest user message only**. Earlier messages and supplied system/developer instructions do not replace the fixed classifier instructions. Message bodies are validated; text blocks are supported, while tool and image blocks are rejected. OpenAI accepts system/developer/user/assistant roles; Anthropic accepts user/assistant roles with system guidance in its separate field.

The server constructs the JSON answer from classification scores and policy. It does not generate answer text token by token: SSE frames are sent after inference finishes, and output/completion token usage is zero. Input usage is the actual tokenized classifier prompt, including its fixed instructions. Positive token-limit fields are accepted for SDK compatibility but do not shorten the deterministic decision document. Metadata is accepted as caller data but does not affect classification or policy. Temperature/sampling, tool calls, custom JSON schemas, audio, images and Responses API are rejected. These compatibility endpoints support routing clients, not a drop-in coding assistant.

## Limits, errors and operation

- Requests are limited to 65,536 bytes. Text batches contain at most 16 inputs, scored sequentially. Each task's full classifier prompt must fit 512 tokens; it is never silently truncated.
- Unknown fields/features are rejected rather than silently treated as supported. A malformed request returns 400 (422 on the retained Jev adapter); unknown endpoint/model paths return 404, oversized bodies 413, timeouts 408, unexpected inference failures 500. OpenAI and Anthropic use their native error envelopes; OIP/HF/vLLM use an error string. OPA uses code/message.
- The six new adapters expose policy-route headers. Jev retains its existing body extension. Native label probabilities are uncalibrated. These formats do not add authentication; keep the listener local or protect it with your gateway.
- All formats call the same resident GPU scorer, serially. The three target models are not contacted. Restart the host process or rebuild the Docker image to load updated code. Model weights and the trained adapter are unchanged.
- Install test/client dependencies with `uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt --torch-backend cu128`. SDK contract tests use OpenAI 3.46.0, Anthropic 2.5.0, huggingface-hub 2.4.0, and tritonclient 2.74.0; these versions are pinned. They exercise real loopback HTTP with controlled scorer outputs. Live GPU checks are recorded separately in GOAL.md.
