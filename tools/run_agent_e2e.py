"""Call a test HTTPS entrant and score three synthetic rounds in isolation.

No live refresh, provider keys, production season writes or upstream fetches.
The HTTP call is real; receipt/release times are simulated explicitly.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import requests
from jsonschema import validate
from ssa import agent_api, bundle, ranking_round, refresh, signing, series, participants
from tools import run_sandbox_cycle as cycle


def registered_endpoint(path):
    path = Path(path)
    registration = json.loads(path.read_text())
    validate(registration, json.loads((ROOT / 'schema/entrant.schema.json').read_text()))
    entrant_id = registration['entrant_id']
    if path.stem != entrant_id:
        raise ValueError('Registration filename must match entrant_id')
    if registration.get('type') != 'participant':
        raise ValueError('Rehearsal registration must be a participant')
    if participants.revoked(entrant_id, str(path.parent)):
        raise ValueError('Registration is revoked or retired; no endpoint was called')
    route = participants.route(entrant_id, str(path.parent))
    if route is None:
        raise ValueError('Registration has no Agent API route')
    return route['base'], registration


def run(url=None, registration_path=None, *, signing_config=None, persist=True):
    registration = None
    if registration_path:
        if url is not None:
            raise ValueError('Choose a URL or a registration, not both')
        url, registration = registered_endpoint(registration_path)
    entrant_id = registration['entrant_id'] if registration else 'e2e_demo'
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use an HTTPS test endpoint without credentials, query or fragment')
    if any(parsed.hostname == host or parsed.hostname.endswith('.' + host) for host in ('social-simulation-arena.com', 'socialsimarena.com')):
        raise ValueError('The official platform is not a test endpoint')
    env = signing_config if signing_config is not None else dict(line.split('=', 1) for line in
               (ROOT / '.local/e2e-signing.env').read_text().splitlines() if '=' in line)
    key = env['SSA_SIGNING_KEY']
    key_id = env['SSA_SIGNING_KEY_ID']
    if signing.public_key_of(key) != signing.published_keys().get(key_id):
        raise ValueError('Signing key does not match this test platform public key')
    rounds = cycle.read(cycle.ROUNDS)['rounds']
    questions = cycle.generated_bundle(rounds)
    source = cycle.read(cycle.SOURCE_OBSERVATIONS)
    answers, calls = [], []
    for r in rounds:
        # Synthetic source declarations exist only during envelope construction.
        fixture_series = {name: {'label': name} for name in source['series']}
        with patch.dict(series.SERIES, fixture_series):
            prompt = agent_api.build_envelope(entrant_id, r)
        body = json.dumps(prompt, sort_keys=True, separators=(',', ':')).encode()
        def post(corrupt=False):
            headers = {'Content-Type': 'application/json', **signing.sign(key, body, key_id)}
            if corrupt:
                headers[signing.HEADER_SIGNATURE] = 'A' * 88
            return requests.post(url, data=body, headers=headers, timeout=(15, 60), allow_redirects=False)
        reply = post()
        if reply.status_code != 200:
            raise RuntimeError(f"{r['round_id']}: HTTP {reply.status_code}: {reply.text[:160]}")
        replay = post()
        if replay.status_code != 200 or replay.json().get('forecast') != reply.json().get('forecast'):
            raise RuntimeError('Repeated request changed its forecast')
        bad = post(corrupt=True)
        if bad.status_code not in (401, 403):
            raise RuntimeError('Endpoint did not reject a corrupted signature')
        tt = r['target_type']
        if tt == 'continuous_normal':
            answer = agent_api.parse_scalar(reply.text)
        elif tt == 'profile_energy':
            answer = agent_api.parse_profile(reply.text, r['cells'])
        else:
            answer = agent_api.parse_ranking(reply.text, ranking_round.spec_for(r))
        answers.append({'round_id': r['round_id'], bundle.ANSWER_KEY[tt]: answer})
        calls.append({'round_id': r['round_id'], 'status': reply.status_code,
                      'idempotency': 'passed', 'bad_signature_status': bad.status_code,
                      'backend_service': reply.headers.get('X-E2E-Backend'),
                      'backend_deployment': reply.headers.get('X-E2E-Deployment'),
                      'llm_model': reply.headers.get('X-OpenRouter-Model'),
                      'llm_generation_id': reply.headers.get('X-OpenRouter-Generation'),
                      'llm_cost': reply.headers.get('X-OpenRouter-Cost'),
                      'replay_generation_id': replay.headers.get('X-OpenRouter-Generation'),
                      'replay_cache': replay.headers.get('X-E2E-Cache')})
    response = {'schema_version': questions['schema_version'], 'batch_id': questions['batch_id'],
                'entrant_id': entrant_id, 'answers': answers}
    received = datetime.fromisoformat(cycle.RECEIVED_AT.replace('Z', '+00:00'))
    accepted = bundle.normalise(response, questions, now=received, entrant=registration)
    if accepted['receipt']['accepted'] != 3:
        raise RuntimeError(json.dumps(accepted['results']))
    after = datetime(2028, 1, 18, tzinfo=timezone.utc)
    late = bundle.normalise(response, questions, now=after, entrant=registration)
    if late['receipt']['accepted'] != 0 or any(r.get('reason') != 'late' for r in late['results']):
        raise RuntimeError('Late submission was not rejected as late')
    records_dir = ROOT / '.local/e2e-agent-records'
    if persist:
        bundle.file_records(accepted['records'], str(records_dir))
    resolved, results = {}, []
    for r in rounds:
        rid = r['round_id']
        resolved[rid] = cycle.production_resolution(r, source['series'], source['ranking'], after)
        scores = cycle.score_record(r, accepted['records'][rid], resolved[rid])
        status = refresh.round_status(r, resolved, after)
        if status != 'resolved':
            raise RuntimeError(f'{rid}: {status}')
        results.append({'round_id': rid, 'shape': r['target_type'], 'status': status, 'scores': scores})
    report = {'environment': 'isolated-e2e-test', 'endpoint': url,
              'entrant_id': entrant_id, 'registration_validated': registration is not None,
              'run_at': datetime.now(timezone.utc).isoformat(),
              'simulated_received_at': cycle.RECEIVED_AT,
              'simulated_resolved_at': after.isoformat(),
              'scope': 'Real signed HTTPS calls; local production parsers, bundle normalization and scorers; synthetic clock and source outcomes. Does not run scheduled production refresh or GitHub registration review.',
              'calls': calls, 'receipt': accepted['receipt'], 'late_receipt': late['receipt'],
              'results': results}
    if persist:
        (ROOT / 'site/e2e-results.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--url')
    target.add_argument('--registration', help='Path to the participant JSON generated by submit.html')
    args = parser.parse_args()
    print(json.dumps(run(args.url, args.registration), indent=2))
