"""GitHub-authenticated registration and OAuth callbacks; never log credentials."""
import json
from http.server import BaseHTTPRequestHandler
from ssa.registration_login import dispatch, LoginError


class handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def handle_request(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 <= length <= 16384:
                raise LoginError('invalid_body_size', 413)
            status, payload, extra = dispatch(self.command, self.path, self.headers, self.rfile.read(length))
        except LoginError as error:
            status, payload, extra = error.status, {'error': {'code': error.code}}, []
        except Exception:
            status, payload, extra = 503, {'error': {'code': 'service_unavailable'}}, []
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        for key, value in extra:
            self.send_header(key, value)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = handle_request
    do_POST = handle_request
