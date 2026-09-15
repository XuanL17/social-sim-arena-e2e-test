"""Operator-only Vercel -> independent server -> scoring rehearsal."""
import hmac
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlparse


def execute():
    url = os.environ.get('E2E_REMOTE_URL', '')
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.hostname.endswith('.vercel.app'):
        raise ValueError('Configure an independent server HTTPS URL in E2E_REMOTE_URL')
    signing_config = {key: os.environ.get(key, '') for key in ('SSA_SIGNING_KEY', 'SSA_SIGNING_KEY_ID')}
    if not all(signing_config.values()):
        raise ValueError('Independent test signing key is not configured')
    # Imported only after operator authentication and deployment config checks.
    from tools.run_agent_e2e import run
    registration = {'entrant_id': 'e2e_remote_backend', 'name': 'Remote simulated AI',
                    'type': 'participant', 'github': 'assassin808', 'status': 'active',
                    'route': {'kind': 'agent_api', 'url': url}}
    with tempfile.TemporaryDirectory(prefix='ssa-remote-e2e-') as directory:
        path = Path(directory) / 'e2e_remote_backend.json'
        path.write_text(json.dumps(registration))
        report = run(registration_path=path, signing_config=signing_config, persist=False)
    report['caller'] = 'vercel-server'
    report['backend'] = 'independent-server'
    return report


class handler(BaseHTTPRequestHandler):
    def respond(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        expected = os.environ.get('E2E_OPERATOR_TOKEN', '')
        if not expected:
            return self.respond(503, {'error': 'operator_access_not_configured'})
        supplied = self.headers.get('Authorization', '')
        if not hmac.compare_digest(supplied.encode(), ('Bearer '+expected).encode()):
            return self.respond(401, {'error': 'unauthorized'})
        try:
            report = execute()
        except ValueError as error:
            return self.respond(503, {'error': 'test_configuration_error', 'message': str(error)})
        except Exception:
            return self.respond(502, {'error': 'remote_rehearsal_failed'})
        self.respond(200, report)
