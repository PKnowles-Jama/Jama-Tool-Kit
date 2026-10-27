"""Native HTTP adapter for an existing trusted HTTPS reverse proxy."""
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
from .service import Reader, Rejected, load_config

ROOT = Path(__file__).resolve().parents[2] / 'frontend'


def handler(config, demo=False):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # No query strings, bearer headers, or customer content in process logs.

        def send(self, status, data, mime='application/json'):
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self' " + config['jamaOrigin'] + "; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors " + config['jamaOrigin'])
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            if path == '/health':
                return self.send(200, b'{"status":"ok"}')
            if path == '/viewer-config.json':
                return self.send(200, json.dumps(config).encode())
            if path in ('/', '/spa', '/spa/', '/spa/panel'):
                path = '/index.html'
            target = (ROOT / path.lstrip('/')).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not target.is_file() or (not demo and target.is_relative_to(ROOT / 'demo')):
                return self.send(404, b'{"error":"Not found"}')
            mime = {'.js': 'text/javascript', '.wasm': 'application/wasm'}.get(target.suffix, mimetypes.guess_type(str(target))[0] or 'application/octet-stream')
            self.send(200, target.read_bytes(), mime)

        def do_POST(self):
            try:
                if config['mode'] != 'adapter' or self.path not in ('/api/context', '/api/asset'):
                    raise Rejected(404, 'Unknown endpoint')
                if (self.headers.get('Origin') != config['publicOrigin']
                        or self.headers.get('Sec-Fetch-Site') not in (None, 'same-origin')
                        or self.headers.get('Content-Type', '').split(';')[0] != 'application/json'):
                    raise Rejected(403, 'Application origin or content type is not allowed')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384:
                    raise Rejected(413, 'Invalid request size')
                auth = self.headers.get('Authorization', '')
                if not auth.startswith('Bearer ') or not 0 < len(auth[7:]) <= 8192 or any(c.isspace() for c in auth[7:]):
                    raise Rejected(401, 'Delegated bearer token required')
                payload = json.loads(self.rfile.read(length))
                reader = Reader(config, auth[7:])
                if self.path == '/api/context':
                    self.send(200, json.dumps(reader.context(payload)).encode())
                else:
                    data, mime = reader.asset(payload)
                    self.send(200, data, mime)
            except Rejected as error:
                self.send(error.status, json.dumps({'error': str(error)}).encode())
            except (ValueError, KeyError, TypeError):
                self.send(400, b'{"error":"Invalid context, manifest, or artifact"}')
            except Exception:
                self.send(502, b'{"error":"Viewer read failed"}')
    return Handler


def serve(args):
    config = load_config(args.config)
    print(f'Hardware viewer on {args.host}:{args.port}; place behind configured HTTPS ingress.')
    ThreadingHTTPServer((args.host, args.port), handler(config, args.demo)).serve_forever()
