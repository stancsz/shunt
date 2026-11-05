"""Contract checks over real loopback HTTP, with deterministic classifier scores."""
import json
import threading
from http.server import HTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pytest

from shunt.config import load_settings
from shunt.server import make_handler
from shunt.systemone import INSTRUCTIONS, CRITERIA


@pytest.fixture
def endpoint(tmp_path):
    calls = []
    def scorer(task):
        calls.append(task)
        return [0.8, 0.1, 0.1]
    scorer.count_tokens = lambda task: 32
    server = HTTPServer(('127.0.0.1', 0), make_handler(scorer, load_settings(tmp_path / 'absent', environ={})))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', calls
    finally:
        server.shutdown()
        thread.join(5)
        server.server_close()


SCOPE = {'X-Shunt-File-Count': '1', 'X-Shunt-Ast-Lines': '12', 'X-Shunt-Attempt-Count': '2'}
TASK = 'Fix a typo.'


def post(endpoint, path, body, headers=None):
    request = Request(endpoint[0] + path, data=json.dumps(body).encode(),
                      headers={'Content-Type': 'application/json', **(headers or {})})
    return urlopen(request, timeout=5)


@pytest.mark.parametrize('path,body', [
    ('/models/shunt', {'inputs': TASK}),
    ('/classify', {'model': 'shunt', 'input': TASK}),
    ('/v2/models/shunt/infer', {'id': 'request-1', 'inputs': [{'name': 'task', 'datatype': 'BYTES', 'shape': [1], 'data': [TASK]}]}),
    ('/v1/data/shunt/route', {'input': {'task': TASK}}),
    ('/v1/chat/completions', {'model': 'shunt', 'messages': [{'role': 'user', 'content': TASK}]}),
    ('/v1/messages', {'model': 'shunt', 'max_tokens': 256, 'messages': [{'role': 'user', 'content': TASK}]}),
])
def test_format_contract_and_policy_separation(endpoint, path, body):
    with post(endpoint, path, body, SCOPE) as response:
        value = json.load(response)
        assert response.headers['X-Shunt-Route'] == 'T3'
        assert response.headers['X-Shunt-Calibrated'] == 'false'
    if path == '/models/shunt':
        assert value == [[{'label': 'T1', 'score': 0.8}, {'label': 'T2', 'score': 0.1}, {'label': 'T3', 'score': 0.1}]]
    elif path == '/classify':
        assert value['data'] == [{'index': 0, 'label': 'T1', 'probs': [0.8, 0.1, 0.1], 'num_classes': 3}]
        assert value['usage'] == {'prompt_tokens': 32, 'total_tokens': 32, 'completion_tokens': 0}
    elif path.endswith('/infer'):
        assert value['id'] == 'request-1'
        outputs = {x['name']: x for x in value['outputs']}
        assert outputs['probabilities']['data'] == [0.8, 0.1, 0.1]
        assert outputs['classification']['data'] == ['T1']
        assert outputs['route']['data'] == ['T3']
    else:
        result = (value['result'] if path.startswith('/v1/data') else
                  json.loads(value['choices'][0]['message']['content']) if 'choices' in value else
                  json.loads(value['content'][0]['text']))
        assert result['route'] == 'T3'
        assert result['probabilities']['T1'] == 0.8
        assert result['target']['model'] == 'deepseek-v4.1-flash:1017'
    assert endpoint[1] == [TASK]


def test_jev_preserved(endpoint):
    body = {'model': 'shunt', 'state': TASK, 'questions': {'complexity': {
        'type': 'choice', 'instructions': INSTRUCTIONS, 'criteria': CRITERIA}},
        'shunt': {'file_count': 1, 'ast_lines': 12, 'attempt_count': 2}}
    with post(endpoint, '/v1/systemone', body) as r:
        result = json.load(r)
    assert result['answers']['complexity']['choice'] == 'T1'
    assert result['shunt']['route'] == 'T3'


@pytest.mark.parametrize('path,body', [
    ('/models/shunt', {'inputs': ['', TASK]}),
    ('/models/shunt', {'inputs': TASK, 'parameters': {'function_to_apply': 'sigmoid'}}),
    ('/models/shunt', {'inputs': TASK, 'parameters': {'top_k': True}}),
    ('/classify', {'model': 'other', 'input': TASK}),
    ('/classify', {'model': 'shunt', 'input': [TASK, 42]}),
    ('/classify', {'model': 'shunt', 'input': [1, 2, 3]}),
    ('/v2/models/shunt/infer', {'inputs': [{'name': 'task', 'datatype': 'BYTES', 'shape': [2], 'data': [TASK]}]}),
    ('/v2/models/shunt/infer', {'inputs': [{'name': 'task', 'datatype': 'BYTES', 'shape': [True], 'data': [TASK]}]}),
    ('/v1/data/shunt/route', {'input': {'task': TASK, 'scope': {'attempt_count': -1}}}),
    ('/v1/chat/completions', {'model': 'shunt', 'messages': [{'role': 'user', 'content': TASK}], 'tools': []}),
    ('/v1/messages', {'model': 'shunt', 'max_tokens': True, 'messages': [{'role': 'user', 'content': TASK}]}),
    ('/v1/messages', {'model': 'shunt', 'messages': [{'role': 'user', 'content': TASK}]}),
    ('/v1/messages', {'model': 'shunt', 'max_tokens': 10, 'messages': [{'role': 'user', 'content': [{'type': 'image', 'source': {}}]}]}),
    ('/v1/messages', {'model': 'shunt', 'max_tokens': 10, 'system': [{'type': 'image', 'source': {}}], 'messages': [{'role': 'user', 'content': TASK}]}),
    ('/models/shunt', {'inputs': [TASK] * 17}),
])
def test_reject_before_inference(endpoint, path, body):
    with pytest.raises(HTTPError) as error:
        post(endpoint, path, body)
    assert error.value.code == 400
    assert endpoint[1] == []


def test_batch_and_latest_user(endpoint):
    with post(endpoint, '/classify', {'model': 'shunt', 'input': [TASK, 'Format code.']}) as r:
        assert len(json.load(r)['data']) == 2
    with post(endpoint, '/v1/chat/completions', {'model': 'shunt', 'messages': [
        {'role': 'system', 'content': 'Some other instructions'},
        {'role': 'user', 'content': 'Old task'}, {'role': 'assistant', 'content': 'Old answer'},
        {'role': 'user', 'content': [{'type': 'text', 'text': TASK}]}]}) as r:
        assert json.loads(json.load(r)['choices'][0]['message']['content'])['route'] == 'T3'
    assert endpoint[1] == [TASK, 'Format code.', TASK]


def test_removed_route_and_discovery(endpoint):
    with pytest.raises(HTTPError) as error:
        post(endpoint, '/route', {'task': TASK})
    assert error.value.code == 404
    for path in ('/v1/models', '/v2', '/v2/health/live', '/v2/health/ready',
                 '/v2/models/shunt', '/v2/models/shunt/versions/1/ready'):
        with urlopen(endpoint[0] + path) as response:
            assert response.status == 200


@pytest.mark.parametrize('headers', [{'X-Shunt-File-Count': '-1'}, {'X-Shunt-Core-Interface': 'yes'}, {'X-Shunt-Ast-Lines': 'NaN'}])
def test_invalid_scope_headers_before_inference(endpoint, headers):
    with pytest.raises(HTTPError) as error:
        post(endpoint, '/classify', {'model': 'shunt', 'input': TASK}, headers)
    assert error.value.code == 400
    assert endpoint[1] == []


def test_native_errors_and_body_limit(endpoint):
    for path in ('/v1/messages', '/v1/chat/completions', '/v1/data/shunt/route'):
        with pytest.raises(HTTPError) as error:
            post(endpoint, path, {})
        value = json.load(error.value)
        if path == '/v1/messages':
            assert value['type'] == 'error' and value['error']['type'] == 'invalid_request_error'
        elif path == '/v1/chat/completions':
            assert value['error']['type'] == 'invalid_request_error'
        else:
            assert value['code'] == 'invalid_parameter'
    with pytest.raises(HTTPError) as error:
        post(endpoint, '/models/shunt', {'inputs': 'x' * 66000})
    assert error.value.code == 413
    assert endpoint[1] == []


def test_sdk_clients(endpoint):
    from openai import OpenAI
    from anthropic import Anthropic
    from huggingface_hub import InferenceClient
    import numpy as np
    import tritonclient.http as triton
    with OpenAI(base_url=endpoint[0] + '/v1', api_key='local', max_retries=0) as client:
        assert client.models.list().data[0].id == 'shunt'
        result = client.chat.completions.create(model='shunt', messages=[{'role': 'user', 'content': TASK}])
        assert json.loads(result.choices[0].message.content)['route'] == 'T3'
        chunks = list(client.chat.completions.create(model='shunt', messages=[{'role': 'user', 'content': TASK}], stream=True))
        assert chunks[-1].choices[0].finish_reason == 'stop'
        assert json.loads(''.join(c.choices[0].delta.content or '' for c in chunks))['route'] == 'T3'
    with Anthropic(base_url=endpoint[0], api_key='local', max_retries=0) as client:
        result = client.messages.create(model='shunt', max_tokens=256, messages=[{'role': 'user', 'content': TASK}])
        assert json.loads(result.content[0].text)['route'] == 'T3'
        with client.messages.stream(model='shunt', max_tokens=256, messages=[{'role': 'user', 'content': TASK}]) as stream:
            assert json.loads(''.join(stream.text_stream))['route'] == 'T3'
            assert stream.get_final_message().stop_reason == 'end_turn'
    client = InferenceClient(model=endpoint[0] + '/models/shunt')
    try:
        scores = client.text_classification(TASK, top_k=2)
        assert scores[0].label == 'T1' and scores[0].score == 0.8
    finally:
        client.close()
    client = triton.InferenceServerClient(endpoint[0].removeprefix('http://'))
    try:
        assert client.is_server_ready() and client.is_model_ready('shunt')
        tensor = triton.InferInput('task', [1], 'BYTES')
        tensor.set_data_from_numpy(np.array([TASK], dtype=object), binary_data=False)
        # JSON tensors only; the protocol's binary extension is not advertised.
        output = triton.InferRequestedOutput('route', binary_data=False)
        result = client.infer('shunt', [tensor], outputs=[output])
        assert result.as_numpy('route').tolist() == ['T3']
    finally:
        client.close()
