"""Independent Vercel-hosted simulated entrant; no persistent disk required."""
import base64
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from server import forecast, VERSION, MAX_BODY

KEYS = {k['key_id']: k['public_key'] for k in json.loads((Path(__file__).resolve().parents[1] / 'keys.json').read_text())['keys'] if k.get('public_key')}


class handler(BaseHTTPRequestHandler):
    def respond(self, status, payload, request_id=''):
        raw = json.dumps(payload, separators=(',', ':'), allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('X-E2E-Backend', 'independent-vercel-project')
        self.send_header('X-E2E-Deployment', os.environ.get('VERCEL_URL', 'local-test'))
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
        print(json.dumps({'service': 'e2e-entrant', 'request_id': request_id, 'status': status}), flush=True)

    def do_GET(self):
        self.respond(200, {'status': 'ok', 'service': 'e2e-entrant',
                          'hosting': 'independent-vercel-project',
                          'mode': 'deterministic-simulated-ai',
                          'schema_version': VERSION,
                          'deployment': os.environ.get('VERCEL_URL', 'local-test')})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-SSA-Key-Id, X-SSA-Timestamp, X-SSA-Signature')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            size = 0
        if size <= 0 or size > MAX_BODY:
            return self.respond(413 if size > MAX_BODY else 400, {'error': 'invalid_body_size'})
        raw = self.rfile.read(size)
        try:
            ts = self.headers['X-SSA-Timestamp']
            kid = self.headers['X-SSA-Key-Id']
            if abs(time.time() - int(ts)) > 300:
                raise ValueError('expired')
            Ed25519PublicKey.from_public_bytes(base64.b64decode(KEYS[kid], validate=True)).verify(
                base64.b64decode(self.headers['X-SSA-Signature'], validate=True), ts.encode()+b'.'+raw)
        except Exception:
            return self.respond(401, {'error': 'invalid_signature'})
        try:
            prompt = json.loads(raw)
            if prompt['schema_version'] != VERSION or not isinstance(prompt['request_id'], str) or not prompt['request_id']:
                raise ValueError('Invalid envelope')
            reply = {'schema_version': VERSION, 'forecast': forecast(prompt['round']),
                     'reasoning_trace': 'Independent Vercel simulated AI: deterministic persistence from supplied context; no paid model calls.',
                     'crosstabs': {}}
        except (ValueError, TypeError, KeyError, OverflowError):
            return self.respond(422, {'error': 'invalid_request'})
        self.respond(200, reply, prompt['request_id'])
