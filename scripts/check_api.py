"""Check all seven formats against a running Shunt service using actual inference."""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from shunt.systemone import INSTRUCTIONS, CRITERIA


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:18765')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    task = 'Fix a missing closing parenthesis.'
    scope = {'file_count': 1, 'ast_lines': 12, 'attempt_count': 2}
    requests = {
        'hf': ('/models/shunt', {'inputs': task}),
        'vllm': ('/classify', {'model': 'shunt', 'input': task}),
        'oip': ('/v2/models/shunt/infer', {'inputs': [{'name': 'task', 'datatype': 'BYTES', 'shape': [1], 'data': [task]}]}),
        'opa': ('/v1/data/shunt/route', {'input': {'task': task}}),
        'jev': ('/v1/systemone', {'model': 'shunt', 'state': task, 'shunt': scope,
                 'questions': {'difficulty': {'type': 'choice', 'instructions': INSTRUCTIONS, 'criteria': CRITERIA}}}),
        'openai': ('/v1/chat/completions', {'model': 'shunt', 'messages': [{'role': 'user', 'content': task}]}),
        'anthropic': ('/v1/messages', {'model': 'shunt', 'max_tokens': 256, 'messages': [{'role': 'user', 'content': task}]}),
    }
    headers = {'Content-Type': 'application/json', 'X-Shunt-File-Count': '1',
               'X-Shunt-Ast-Lines': '12', 'X-Shunt-Attempt-Count': '2'}
    report = {}
    distributions = []
    for kind, (path, body) in requests.items():
        request = Request(args.base_url.rstrip('/') + path, data=json.dumps(body).encode(), headers=headers)
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
            route = response.headers.get('X-Shunt-Route')
        if kind == 'hf':
            probabilities = {x['label']: x['score'] for x in result[0]}
        elif kind == 'vllm':
            probabilities = dict(zip(('T1', 'T2', 'T3'), result['data'][0]['probs']))
        elif kind == 'oip':
            tensors = {x['name']: x['data'] for x in result['outputs']}
            probabilities = dict(zip(('T1', 'T2', 'T3'), tensors['probabilities']))
            assert tensors['route'] == ['T3']
        else:
            decision = (result['shunt'] if kind == 'jev' else result['result'] if kind == 'opa' else
                        json.loads(result['choices'][0]['message']['content']) if kind == 'openai' else
                        json.loads(result['content'][0]['text']))
            route = decision['route']
            probabilities = decision['probabilities']
        assert route == 'T3', (kind, route)
        distributions.append(probabilities)
        report[kind] = {'status': 200, 'policy_route': route, 'probabilities': probabilities}
    assert all(x == distributions[0] for x in distributions), 'adapter probabilities diverged'
    try:
        urlopen(Request(args.base_url + '/route', data=b'{}', headers={'Content-Type': 'application/json'}), timeout=10)
    except HTTPError as error:
        assert error.code == 404
    else:
        raise AssertionError('removed /route still responds')
    report['removed_route'] = 404
    if args.output:
        args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
