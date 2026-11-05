"""Wire adapters for the seven documented classification/decision formats."""
from dataclasses import dataclass, field
import json
import time
import uuid

from shunt.decision import validate, evaluate
from shunt.systemone import decide

MODEL = 'shunt'
VERSION = '1'
TIERS = ['T1', 'T2', 'T3']
POST_PATHS = {
    '/models/shunt': 'hf', '/classify': 'vllm',
    '/v2/models/shunt/infer': 'oip', '/v2/models/shunt/versions/1/infer': 'oip',
    '/v1/data/shunt/route': 'opa', '/v1/systemone': 'jev',
    '/v1/chat/completions': 'openai', '/v1/messages': 'anthropic',
}


@dataclass
class Reply:
    body: object
    headers: dict = field(default_factory=dict)
    events: list | None = None


def fields(body, allowed):
    extra = set(body) - set(allowed.split())
    if extra:
        raise ValueError('unsupported fields: ' + ', '.join(sorted(extra)))


def model(body, required=True):
    if (required or 'model' in body) and body.get('model') != MODEL:
        raise ValueError('model must be shunt')


def scope_headers(headers):
    result = {}
    for name in ('file_count', 'ast_lines', 'attempt_count', 'core_interface'):
        value = headers.get('X-Shunt-' + name.replace('_', '-'))
        if value is not None:
            if name == 'core_interface':
                if value.lower() not in ('true', 'false'):
                    raise ValueError('X-Shunt-Core-Interface must be true or false')
                result[name] = value.lower() == 'true'
            else:
                try:
                    result[name] = int(value)
                except ValueError:
                    raise ValueError('scope headers must contain nonnegative integer counts') from None
    return result


def texts(value):
    items = [value] if isinstance(value, str) else value
    if not isinstance(items, list) or not 1 <= len(items) <= 16:
        raise ValueError('input must be text or a batch of 1–16 texts')
    if any(not isinstance(x, str) or not x.strip() for x in items):
        raise ValueError('each input must be nonempty text')
    return items


def content_text(content):
    if isinstance(content, list):
        parts = []
        for part in content:
            if not isinstance(part, dict) or set(part) != {'type', 'text'} or part['type'] != 'text' or not isinstance(part['text'], str):
                raise ValueError('only text content blocks are supported')
            parts.append(part['text'])
        return '\n'.join(parts)
    if not isinstance(content, str):
        raise ValueError('message content must be text')
    return content


def message_text(body, anthropic=False):
    messages = body.get('messages')
    if not isinstance(messages, list) or not messages:
        raise ValueError('messages must be a nonempty array')
    latest = None
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError('messages must contain objects')
        fields(message, 'role content')
        roles = ('user', 'assistant') if anthropic else ('system', 'developer', 'user', 'assistant')
        if message.get('role') not in roles:
            raise ValueError('unsupported message role; tool messages are not supported')
        content = content_text(message.get('content'))
        if message['role'] == 'user':
            latest = content
    if latest is None or not latest.strip():
        raise ValueError('a nonempty user message is required')
    return latest


def count(scorer, task):
    # Production supplies actual tokenizer accounting. Stubs may omit it.
    counter = getattr(scorer, 'count_tokens', None)
    return counter(task) if counter else None


def dispatch(path, body, headers, scorer, settings):
    if not isinstance(body, dict):
        raise ValueError('body must be a JSON object')
    kind = POST_PATHS[path]
    if kind == 'jev':
        return Reply(decide(body, scorer, settings))
    scope = scope_headers(headers)
    extra = {}
    if kind == 'hf':
        fields(body, 'inputs parameters options')
        params = body.get('parameters', {})
        if not isinstance(params, dict):
            raise ValueError('parameters must be an object')
        fields(params, 'top_k function_to_apply')
        if params.get('function_to_apply', 'softmax') != 'softmax':
            raise ValueError('only softmax scores are supported')
        k = params.get('top_k', 3)
        if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 3:
            raise ValueError('top_k must be 1–3')
        options = body.get('options', {})
        if not isinstance(options, dict) or options:
            raise ValueError('only empty options are supported')
        tasks = texts(body.get('inputs'))
        extra.update(top_k=k, batch=isinstance(body['inputs'], list))
    elif kind == 'vllm':
        fields(body, 'model input messages encoding_format use_activation')
        model(body)
        if body.get('encoding_format', 'float') != 'float' or body.get('use_activation', True) is not True:
            raise ValueError('only float probabilities with activation are supported')
        if ('input' in body) == ('messages' in body):
            raise ValueError('supply exactly one of input or messages')
        tasks = [message_text(body)] if 'messages' in body else texts(body['input'])
    elif kind == 'oip':
        fields(body, 'id inputs outputs parameters')
        if 'id' in body and not isinstance(body['id'], str):
            raise ValueError('id must be a string')
        inputs = body.get('inputs')
        if not isinstance(inputs, list) or len(inputs) != 1 or not isinstance(inputs[0], dict):
            raise ValueError('exactly one task input tensor is required')
        tensor = inputs[0]
        fields(tensor, 'name shape datatype data')
        if not isinstance(tensor.get('data'), list):
            raise ValueError('tensor data must be an array of strings')
        tasks = texts(tensor.get('data'))
        if tensor.get('name') != 'task' or tensor.get('datatype') != 'BYTES' or tensor.get('shape') != [len(tasks)] or any(type(x) is not int for x in tensor['shape']):
            raise ValueError('task must be a BYTES tensor with shape [batch_size]')
        parameters = body.get('parameters', {})
        if not isinstance(parameters, dict):
            raise ValueError('parameters must be an object')
        fields(parameters, 'file_count ast_lines attempt_count core_interface')
        if scope and parameters:
            raise ValueError('use either scope headers or OIP parameters')
        scope = parameters or scope
        outputs = body.get('outputs', [{'name': x} for x in ('probabilities', 'classification', 'route')])
        if not isinstance(outputs, list) or not outputs or any(not isinstance(x, dict) or set(x) - {'name', 'parameters'} or x.get('name') not in ('probabilities', 'classification', 'route') for x in outputs):
            raise ValueError('outputs may select probabilities, classification, route')
        for output in outputs:
            if output.get('parameters', {}) not in ({}, {'binary_data': False}):
                raise ValueError('only JSON output tensors are supported; binary_data must be false')
        if len({x['name'] for x in outputs}) != len(outputs):
            raise ValueError('duplicate output names')
        extra.update(id=body.get('id'), outputs=outputs)
    elif kind == 'opa':
        fields(body, 'input')
        value = body.get('input')
        if not isinstance(value, dict):
            raise ValueError('input must contain task and optional scope')
        fields(value, 'task scope')
        if scope and 'scope' in value:
            raise ValueError('use either scope headers or input.scope')
        scope = value.get('scope', scope)
        tasks = texts(value.get('task'))
        if len(tasks) != 1 or not isinstance(value.get('task'), str):
            raise ValueError('OPA input.task must be a string')
    else:
        model(body)
        allowed = 'model messages stream metadata'
        allowed += ' max_tokens system' if kind == 'anthropic' else ' max_tokens max_completion_tokens response_format'
        fields(body, allowed)
        if not isinstance(body.get('stream', False), bool):
            raise ValueError('stream must be a boolean')
        if 'metadata' in body and not isinstance(body['metadata'], dict):
            raise ValueError('metadata must be an object')
        if kind == 'anthropic':
            if 'system' in body:
                content_text(body['system'])
            if 'max_tokens' not in body:
                raise ValueError('max_tokens is required')
        for key in ('max_tokens', 'max_completion_tokens'):
            if key in body and (isinstance(body[key], bool) or not isinstance(body[key], int) or body[key] < 1):
                raise ValueError(key + ' must be a positive integer')
        if 'response_format' in body and body['response_format'] not in ({'type': 'text'}, {'type': 'json_object'}):
            raise ValueError('supported response_format: text or json_object')
        tasks = [message_text(body, kind == 'anthropic')]
        extra['stream'] = body.get('stream', False)

    # Validate every item before doing any inference, including batches.
    for task in tasks:
        validate(task, scope)
        count(scorer, task)
    results = [evaluate(task, scope, scorer, settings) for task in tasks]
    counts = [count(scorer, task) for task in tasks]
    ident = uuid.uuid4().hex
    wire_headers = {'X-Shunt-Route': ','.join(x['route'] for x in results), 'X-Shunt-Calibrated': 'false'}
    if kind == 'hf':
        labels = [[{'label': k, 'score': v} for k, v in sorted(r['probabilities'].items(), key=lambda x: -x[1])][:extra['top_k']] for r in results]
        # Hugging Face's deployed-endpoint client unwraps the first batch row.
        return Reply(labels, wire_headers)
    if kind == 'vllm':
        value = {'id': 'classify-' + ident, 'object': 'list', 'created': int(time.time()), 'model': MODEL,
                 'data': [{'index': i, 'label': max(r['probabilities'], key=r['probabilities'].get),
                           'probs': list(r['probabilities'].values()), 'num_classes': 3} for i, r in enumerate(results)]}
        if all(x is not None for x in counts):
            value['usage'] = {'prompt_tokens': sum(counts), 'total_tokens': sum(counts), 'completion_tokens': 0}
        return Reply(value, wire_headers)
    if kind == 'oip':
        n = len(results)
        tensors = {
            'probabilities': {'name': 'probabilities', 'datatype': 'FP64', 'shape': [n, 3], 'data': [v for r in results for v in r['probabilities'].values()]},
            'classification': {'name': 'classification', 'datatype': 'BYTES', 'shape': [n], 'data': [max(r['probabilities'], key=r['probabilities'].get) for r in results]},
            'route': {'name': 'route', 'datatype': 'BYTES', 'shape': [n], 'data': [r['route'] for r in results]},
        }
        value = {'model_name': MODEL, 'model_version': VERSION, 'outputs': [tensors[x['name']] for x in extra['outputs']]}
        if extra['id'] is not None:
            value['id'] = extra['id']
        return Reply(value, wire_headers)
    if kind == 'opa':
        return Reply({'decision_id': ident, 'result': results[0]}, wire_headers)
    text = json.dumps(results[0], separators=(',', ':'))
    if kind == 'openai':
        value = {'id': 'chatcmpl-' + ident, 'object': 'chat.completion', 'created': int(time.time()), 'model': MODEL,
                 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': text}, 'finish_reason': 'stop'}]}
        if counts[0] is not None:
            value['usage'] = {'prompt_tokens': counts[0], 'completion_tokens': 0, 'total_tokens': counts[0]}
        if not extra['stream']:
            return Reply(value, wire_headers)
        def chunk(delta, finish=None):
            return {**{k: value[k] for k in ('id', 'created', 'model')}, 'object': 'chat.completion.chunk',
                    'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
        return Reply(None, wire_headers, [(None, chunk({'role': 'assistant', 'content': ''})),
                                          (None, chunk({'content': text})), (None, chunk({}, 'stop')), (None, '[DONE]')])
    value = {'id': 'msg_' + ident, 'type': 'message', 'role': 'assistant', 'model': MODEL,
             'content': [{'type': 'text', 'text': text}], 'stop_reason': 'end_turn', 'stop_sequence': None,
             'usage': {'input_tokens': counts[0] or 0, 'output_tokens': 0}}
    if not extra['stream']:
        return Reply(value, wire_headers)
    events = [('message_start', {'type': 'message_start', 'message': {**value, 'content': [], 'stop_reason': None}}),
              ('content_block_start', {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}}),
              ('content_block_delta', {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': text}}),
              ('content_block_stop', {'type': 'content_block_stop', 'index': 0}),
              ('message_delta', {'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': 0}}),
              ('message_stop', {'type': 'message_stop'})]
    return Reply(None, wire_headers, events)


def discovery(path):
    if path == '/v1/models':
        return {'object': 'list', 'data': [{'id': MODEL, 'object': 'model', 'created': 0, 'owned_by': 'shunt'}]}
    if path == '/v2':
        return {'name': 'shunt', 'version': VERSION, 'extensions': []}
    if path in ('/v2/models/shunt', '/v2/models/shunt/versions/1'):
        return {'name': MODEL, 'versions': [VERSION], 'platform': 'shunt_pytorch',
                'inputs': [{'name': 'task', 'datatype': 'BYTES', 'shape': [-1]}],
                'outputs': [{'name': name, 'datatype': dtype, 'shape': shape} for name, dtype, shape in
                            [('probabilities', 'FP64', [-1, 3]), ('classification', 'BYTES', [-1]), ('route', 'BYTES', [-1])]]}
    if path in ('/v2/health/live', '/v2/health/ready', '/v2/models/shunt/ready', '/v2/models/shunt/versions/1/ready'):
        return {}
    return None
