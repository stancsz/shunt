import json
import threading
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from shunt.systemone import CRITERIA, INSTRUCTIONS, decide
from shunt.config import load_settings


def request_body():
    return {'model': 'shunt', 'state': 'Fix a typo.', 'questions': {'difficulty': {
        'type': 'choice', 'instructions': INSTRUCTIONS, 'criteria': CRITERIA.copy()}},
        'shunt': {'file_count': 1, 'ast_lines': 12, 'attempt_count': 2}}


def test_choice_is_raw_and_policy_route_is_separate(tmp_path):
    result = decide(request_body(), lambda _: [0.8, 0.1, 0.1],
                    load_settings(tmp_path / 'absent', environ={}))
    assert result['answers']['difficulty']['choice'] == 'T1'
    assert result['answers']['difficulty']['probabilities'] == {'T1': 0.8, 'T2': 0.1, 'T3': 0.1}
    assert result['shunt']['route'] == 'T3'
    assert result['shunt']['calibrated'] is False
    assert 'confidence' not in result['answers']['difficulty']


@pytest.mark.parametrize('change', ['type', 'instructions', 'criteria', 'multiple', 'state'])
def test_rejects_unsupported_requests_before_scoring(tmp_path, change):
    body = request_body()
    question = body['questions']['difficulty']
    if change == 'multiple':
        body['questions']['other'] = question.copy()
    elif change == 'state':
        body['state'] = {'task': 'Fix a typo'}
    else:
        question[change] = {'type': 'noul', 'instructions': 'Other question', 'criteria': {'yes': None}}[change]
    def no_score(_):
        pytest.fail('invalid request reached scorer')
    with pytest.raises(ValueError):
        decide(body, no_score, load_settings(tmp_path / 'absent', environ={}))


def test_http_systemone(monkeypatch, tmp_path):
    import shunt.server as service
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(service, 'load', lambda _: (None, None, None))
    monkeypatch.setattr(service, 'score', lambda *args: [0.8, 0.1, 0.1])
    monkeypatch.setattr('sys.argv', ['shunt.server', '--port', '0'])
    ready = threading.Event()
    servers = []
    def create_server(address, handler):
        server = HTTPServer(address, handler)
        servers.append(server)
        ready.set()
        return server
    monkeypatch.setattr(service, 'HTTPServer', create_server)
    thread = threading.Thread(target=service.main, daemon=True)
    thread.start()
    assert ready.wait(10)
    server = servers[0]
    try:
        url = f'http://127.0.0.1:{server.server_port}/v1/systemone'
        def post(body):
            return urlopen(Request(url, data=json.dumps(body).encode(),
                                   headers={'Content-Type': 'application/json'}), timeout=5)
        with post(request_body()) as response:
            assert json.load(response)['answers']['difficulty']['choice'] == 'T1'
        invalid = request_body()
        invalid['questions']['difficulty']['type'] = 'noul'
        with pytest.raises(HTTPError) as error:
            post(invalid)
        assert error.value.code == 422
    finally:
        server.shutdown()
        thread.join(10)
