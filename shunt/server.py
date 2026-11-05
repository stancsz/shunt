"""Small resident HTTP adapter for the existing local Shunt weights."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit

from shunt.model import load, score, prompt
from shunt.config import load_settings
from shunt.protocols import POST_PATHS, dispatch, discovery


def make_handler(scorer, settings, adapter='artifacts/shunt-lora', mode='eager'):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status, body, headers=None):
            data = json.dumps(body, ensure_ascii=False).encode('utf-8')
            self.send_bytes(status, data, 'application/json; charset=utf-8', headers)

        def send_bytes(self, status, data, content_type, headers=None):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/health':
                return self.send_json(200, {'status': 'ready', 'adapter': adapter,
                                 'max_prompt_tokens': 512, 'calibrated': False,
                                 'mode': mode, 'formats': sorted(set(POST_PATHS.values()))})
            value = discovery(path)
            if value is not None:
                return self.send_json(200, value)
            self.send_json(404, {'error': 'not_found'})

        def fail(self, status, message):
            path = urlsplit(self.path).path
            if path == '/v1/chat/completions':
                value = {'error': {'message': message, 'type': 'invalid_request_error' if status < 500 else 'server_error', 'param': None, 'code': None}}
            elif path == '/v1/messages':
                value = {'type': 'error', 'error': {'type': 'invalid_request_error' if status < 500 else 'api_error', 'message': message}}
            elif path == '/v1/data/shunt/route':
                value = {'code': 'invalid_parameter' if status < 500 else 'internal_error', 'message': message}
            else:
                value = {'error': message}
            self.send_json(status, value)

        def do_POST(self):
            path = urlsplit(self.path).path
            if path not in POST_PATHS:
                return self.send_json(404, {'error': 'not_found'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 65536:
                    return self.fail(413, 'body must be 1–65536 bytes')
                if self.headers.get('Transfer-Encoding'):
                    return self.fail(400, 'chunked request bodies are not supported')
                self.connection.settimeout(15)
                body = json.loads(self.rfile.read(length))
                reply = dispatch(path, body, self.headers, scorer, settings)
                if reply.events is None:
                    return self.send_json(200, reply.body, reply.headers)
                blocks = []
                for event, value in reply.events:
                    prefix = f'event: {event}\n' if event else ''
                    payload = value if value == '[DONE]' else json.dumps(value, ensure_ascii=False)
                    blocks.append(prefix + 'data: ' + payload + '\n\n')
                self.send_bytes(200, ''.join(blocks).encode('utf-8'), 'text/event-stream', reply.headers)
            except (ValueError, TypeError) as exc:
                self.fail(422 if path == '/v1/systemone' else 400, str(exc))
            except TimeoutError:
                self.fail(408, 'request timeout')
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception:
                self.log_error('routing request failed')
                self.fail(500, 'routing failed; inspect service logs')

    return Handler


def main():
    settings = load_settings()
    parser = argparse.ArgumentParser(description='Serve the local Shunt adapter')
    parser.add_argument('--host', default=settings.host)
    parser.add_argument('--port', type=int, default=settings.port)
    parser.add_argument('--adapter', default='artifacts/shunt-lora')
    parser.add_argument('--cuda-graph', action='store_true')
    args = parser.parse_args()
    model, tokenizer, ids = load(args.adapter)
    scorer = lambda task: score(model, tokenizer, ids, task)
    if args.cuda_graph:
        from shunt.graph import GraphScorer
        graph = GraphScorer(model, tokenizer, ids, bucket=512)
        scorer = lambda task: graph.score(task)

    def tokens(task):
        size = len(tokenizer.encode(prompt(tokenizer, task), add_special_tokens=False))
        if size > 512:
            raise ValueError('Task exceeds the supported 512-token prompt limit')
        return size
    if tokenizer is not None:
        scorer.count_tokens = tokens

    # One GPU request at a time: GraphScorer is single-threaded.
    server = HTTPServer((args.host, args.port), make_handler(scorer, settings, args.adapter,
                        'cuda_graph' if args.cuda_graph else 'eager'))
    print(f'Shunt ready at http://{args.host}:{args.port}', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
