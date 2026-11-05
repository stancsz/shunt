import json
import threading
from http.server import HTTPServer
from urllib.request import Request, urlopen

import pytest

from shunt.config import load_settings


def test_defaults_and_example(tmp_path):
    settings = load_settings(tmp_path / 'missing.env', environ={})
    assert (settings.host, settings.port) == ('127.0.0.1', 18765)
    assert [t.model for t in settings.targets.values()] == [
        'mimo-v2.6-distill-qwen-9b', 'qwen3.8:27b', 'deepseek-v4.1-flash:1017']
    assert all(t.base_url == 'http://127.0.0.1:11434/v1' for t in settings.targets.values())
    assert load_settings('.env.example', environ={}) == settings


def test_dotenv_precedence_and_secret_redaction(tmp_path):
    path = tmp_path / '.env'
    path.write_text('SHUNT_PORT=19000\nSHUNT_TARGET_BASE_URL=http://localhost:11435/v1/\n'
                    'SHUNT_TARGET_API_KEY="shared-${literal}-secret"\n'
                    'SHUNT_T2_MODEL=custom-model\nSHUNT_T2_API_KEY=\n'
                    'SHUNT_T3_BASE_URL=https://example.com:8443/v1\n', encoding='utf-8')
    settings = load_settings(path, environ={'SHUNT_PORT': '19001', 'SHUNT_T3_TIMEOUT_SECONDS': '300'})
    assert settings.port == 19001
    assert settings.targets['T1'].api_key == 'shared-${literal}-secret'
    assert settings.targets['T2'].api_key == ''  # Explicitly disable shared auth.
    assert settings.targets['T2'].model == 'custom-model'
    assert settings.targets['T1'].base_url == 'http://localhost:11435/v1'
    assert settings.targets['T3'].base_url == 'https://example.com:8443/v1'
    assert settings.targets['T3'].timeout_seconds == 300
    assert 'secret' not in repr(settings)
    assert 'secret' not in json.dumps({k: v.public() for k, v in settings.targets.items()})


@pytest.mark.parametrize('env', [
    {'SHUNT_PORT': '0'}, {'SHUNT_PORT': '65536'}, {'SHUNT_PORT': 'oops'},
    {'SHUNT_T1_MODEL': ''}, {'SHUNT_T1_BASE_URL': 'file:///tmp/model'},
    {'SHUNT_T1_BASE_URL': 'https://user:secret@example.com/v1'},
    {'SHUNT_T1_BASE_URL': 'http://localhost:99999/v1'},
    {'SHUNT_T1_BASE_URL': 'http://localhost:0/v1'},
    {'SHUNT_T1_BASE_URL': 'https://example.com/v1?key=secret'},
    {'SHUNT_T1_TIMEOUT_SECONDS': 'nan'}, {'SHUNT_T1_TIMEOUT_SECONDS': '0'},
])
def test_reject_invalid_settings_without_leaking_values(tmp_path, env):
    with pytest.raises(ValueError) as error:
        load_settings(tmp_path / 'missing.env', environ=env)
    assert 'secret' not in str(error.value)


def test_cli_uses_dotenv_target_with_stubbed_inference(tmp_path, monkeypatch, capsys):
    import shunt.__main__ as cli
    monkeypatch.chdir(tmp_path)
    (tmp_path / '.env').write_text('SHUNT_T1_MODEL=local-test\nSHUNT_T1_API_KEY=test-secret\n')
    monkeypatch.setattr(cli, 'load', lambda _: (None, None, None))
    monkeypatch.setattr(cli, 'score', lambda *args: [0.9, 0.05, 0.05])
    monkeypatch.setattr('sys.argv', ['shunt', 'format code', '--files', '1', '--lines', '12'])
    cli.main()
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result['route'] == 'T1'
    assert result['target']['model'] == 'local-test'
    assert 'test-secret' not in output


def test_http_uses_env_binding_and_escalated_target_with_stubbed_inference(tmp_path, monkeypatch):
    import shunt.server as service
    monkeypatch.chdir(tmp_path)
    (tmp_path / '.env').write_text('SHUNT_HOST=127.0.0.1\nSHUNT_PORT=19002\n'
                                 'SHUNT_T3_MODEL=remote-test\nSHUNT_T3_API_KEY=test-secret\n'
                                 'SHUNT_T3_BASE_URL=http://localhost:11436/v1\n')
    monkeypatch.setattr(service, 'load', lambda _: (None, None, None))
    monkeypatch.setattr(service, 'score', lambda *args: [0.9, 0.05, 0.05])
    monkeypatch.setattr('sys.argv', ['shunt.server', '--port', '0'])
    ready = threading.Event()
    servers = []

    def create_server(address, handler):
        assert address == ('127.0.0.1', 0)  # CLI port overrides .env.
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
        body = json.dumps({'task': 'format code', 'file_count': 1, 'ast_lines': 12,
                           'attempt_count': 2}).encode()
        request = Request(f'http://127.0.0.1:{server.server_port}/route', data=body,
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=5) as response:
            raw = response.read().decode()
        result = json.loads(raw)
        assert result['route'] == 'T3'
        assert set(result['probabilities']) == {'T1', 'T2', 'T3'}
        assert result['target']['model'] == 'remote-test'
        assert result['target']['base_url'] == 'http://localhost:11436/v1'
        assert 'test-secret' not in raw
    finally:
        server.shutdown()
        thread.join(10)
    assert not thread.is_alive()
