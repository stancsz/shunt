"""Small resident HTTP adapter for the existing local Shunt weights."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from shunt.model import load, score
from shunt.policy import route
from shunt.config import load_settings
from shunt.systemone import decide


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
        scorer = GraphScorer(model, tokenizer, ids, bucket=512).score

    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status, body):
            data = json.dumps(body, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path != '/health':
                return self.send_json(404, {'error': 'not_found'})
            self.send_json(200, {'status': 'ready', 'adapter': args.adapter,
                                 'max_prompt_tokens': 512, 'calibrated': False,
                                 'mode': 'cuda_graph' if args.cuda_graph else 'eager'})

        def do_POST(self):
            if self.path not in ('/route', '/v1/systemone'):
                return self.send_json(404, {'error': 'not_found'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 65536:
                    return self.send_json(413, {'error': 'body must be 1–65536 bytes'})
                self.connection.settimeout(15)
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError('body must be a JSON object')
                if self.path == '/v1/systemone':
                    return self.send_json(200, decide(body, scorer, settings))
                task = body.get('task')
                metadata = dict(file_count=body.get('file_count'), ast_lines=body.get('ast_lines'),
                                attempt_count=body.get('attempt_count', 0),
                                core_interface=body.get('core_interface', False))
                route(task, [1.0, 0.0, 0.0], **metadata)  # Validate before GPU work.
                result = route(task, scorer(task), **metadata)
                result['target'] = settings.targets[result['route']].public()
                result.update(calibrated=False, backbone='Qwen/Qwen3.5-0.8B', adapter=args.adapter,
                              scope_provenance='caller-declared')
                self.send_json(200, result)
            except (ValueError, TypeError) as exc:
                self.send_json(422, {'error': str(exc)})
            except TimeoutError:
                self.send_json(408, {'error': 'request timeout'})
            except Exception:
                self.log_error('routing request failed')
                self.send_json(500, {'error': 'routing failed; inspect service logs'})

    # One GPU request at a time: GraphScorer is single-threaded.
    server = HTTPServer((args.host, args.port), Handler)
    print(f'Shunt ready at http://{args.host}:{args.port}', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
