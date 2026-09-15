"""Standalone simulated AI entrant. Run on a server separate from Vercel."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import sqlite3
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

VERSION = 'ssa-agent-api-v2'
MAX_BODY = 512 * 1024


def forecast(round_spec):
    context = round_spec.get('context') or {}
    def normal(history, default=50):
        values = [float(p['value']) for p in history if math.isfinite(float(p['value']))]
        mean = values[-1] if values else float(default)
        differences = [b-a for a, b in zip(values, values[1:])]
        sd = max(1.0, math.sqrt(sum(v*v for v in differences)/len(differences))) if differences else 5.0
        if not math.isfinite(mean):
            raise ValueError('Non-finite context')
        return {'mean': mean, 'sd': sd}
    kind = round_spec['target_type']
    if kind == 'continuous_normal':
        return normal(context.get('history') or [], context.get('persistence', 50))
    if kind == 'profile_energy':
        cells = round_spec['cells']
        if not isinstance(cells, list) or len(cells) < 2 or len(set(cells)) != len(cells):
            raise ValueError('Profile requires distinct cells')
        histories = context.get('history_by_cell') or {}
        return {'profile': {c: normal(histories.get(c) or []) for c in cells}}
    if kind == 'ranking_list':
        spec = round_spec['ranking']
        length = spec['length']
        items = spec.get('items')
        if not items:
            weeks = context.get('recent_weeks') or []
            latest = weeks[-1] if weeks else {}
            items = latest.get('items') or latest.get('ranking') or []
        exclusions = spec.get('exclusions') or {}
        titles = set(exclusions.get('titles') or [])
        prefixes = tuple(exclusions.get('prefixes') or [])
        items = list(dict.fromkeys(i for i in items if i not in titles and not (prefixes and i.startswith(prefixes))))
        if not isinstance(length, int) or length < 1 or len(items) < length:
            raise ValueError('Not enough ranking items')
        return {'ranking': items[:length]}
    raise ValueError('Unsupported target_type')


def serve(host, port, keys_file, db_file):
    keys = {row['key_id']: row['public_key'] for row in json.loads(Path(keys_file).read_text())['keys'] if row.get('public_key')}
    Path(db_file).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_file) as db:
        db.execute('CREATE TABLE IF NOT EXISTS replies (request_id TEXT, input_hash TEXT, response TEXT, created_at REAL, PRIMARY KEY(request_id, input_hash))')

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(20)

        def respond(self, status, payload):
            raw = json.dumps(payload, separators=(',', ':'), allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path != '/healthz':
                return self.respond(404, {'error': 'not_found'})
            with sqlite3.connect(db_file) as db:
                db.execute('SELECT 1 FROM replies LIMIT 1').fetchone()
            self.respond(200, {'status': 'ok', 'service': 'independent-e2e-entrant', 'mode': 'deterministic-simulated-ai', 'schema_version': VERSION})

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-SSA-Key-Id, X-SSA-Timestamp, X-SSA-Signature')
            self.send_header('Content-Length', '0')
            self.end_headers()

        def do_POST(self):
            if self.path != '/forecast':
                return self.respond(404, {'error': 'not_found'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                size = 0
            if size <= 0 or size > MAX_BODY:
                return self.respond(413 if size > MAX_BODY else 400, {'error': 'invalid_body_size'})
            raw = self.rfile.read(size)
            try:
                kid = self.headers['X-SSA-Key-Id']
                ts = self.headers['X-SSA-Timestamp']
                if abs(time.time() - int(ts)) > 300:
                    raise ValueError('expired')
                Ed25519PublicKey.from_public_bytes(base64.b64decode(keys[kid], validate=True)).verify(
                    base64.b64decode(self.headers['X-SSA-Signature'], validate=True), ts.encode()+b'.'+raw)
            except Exception:
                return self.respond(401, {'error': 'invalid_signature'})
            try:
                prompt = json.loads(raw)
                if prompt['schema_version'] != VERSION or not isinstance(prompt['request_id'], str) or not prompt['request_id']:
                    raise ValueError('Invalid envelope')
                digest = hashlib.sha256(json.dumps(prompt, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                with sqlite3.connect(db_file, timeout=20) as db:
                    db.execute('BEGIN IMMEDIATE')
                    row = db.execute('SELECT response FROM replies WHERE request_id=? AND input_hash=?', (prompt['request_id'], digest)).fetchone()
                    if row:
                        reply = json.loads(row[0])
                    else:
                        reply = {'schema_version': VERSION, 'forecast': forecast(prompt['round']),
                                 'reasoning_trace': 'Deterministic simulated AI: persistence forecast from supplied context; no paid model calls.', 'crosstabs': {}}
                        serialized = json.dumps(reply, allow_nan=False)
                        db.execute('INSERT INTO replies VALUES (?,?,?,?)', (prompt['request_id'], digest, serialized, time.time()))
            except (ValueError, TypeError, KeyError, OverflowError):
                return self.respond(422, {'error': 'invalid_request'})
            self.respond(200, reply)

    return ThreadingHTTPServer((host, port), Handler)


if __name__ == '__main__':
    serve(os.environ.get('HOST', '0.0.0.0'), int(os.environ.get('PORT', '8787')),
          os.environ.get('KEYS_FILE', '/app/keys.json'), os.environ.get('DB_FILE', '/data/replies.sqlite')).serve_forever()
