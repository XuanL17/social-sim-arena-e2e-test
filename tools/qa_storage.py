#!/usr/bin/env python3
"""Real isolated intake persistence QA. No paid services, no credential output.

Default: real local HTTP handlers -> private GitHub test repository.
--hosted: deployed test platform -> its configured private storage.
Only default mode borrows local gh identity, in process memory, never Vercel.
"""
import argparse
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import requests
from api.questionnaire_submissions import handler as QuestionnaireHandler
from api.bundle_submissions import handler as BundleHandler
from ssa import bundle, questionnaire_api as qa

TEST_REPO = 'assassin808/social-sim-arena-e2e-test-intake'
HOSTED_URL = 'https://social-sim-arena-e2e-test.vercel.app'


def make_human(manifest):
    questions = [q for q in manifest['questions'] if q['board_id'] == 'topline']
    if not questions or any(q['target_type'] != 'continuous_normal' for q in questions):
        raise ValueError('QA currently requires an open continuous-only topline board')
    return {'track': 'human', 'submission': {
        'submission_version': 1, 'board_id': 'topline',
        'round_manifest': [q['round_id'] for q in questions],
        'username': 'isolated-storage-qa', 'contact_email': 'qa@example.invalid',
        'answers': [{'round_id': q['round_id'], 'target_type': q['target_type'],
                     'response': {'value': 0}} for q in questions],
        'commitment': {'accepted': True, 'terms_version': 'ssa-participant-v1'},
        'publication_consent': {'accepted': False, 'field': 'username',
                                'terms_version': 'ssa-publication-v1'}}}


def read_record(pathname):
    result = subprocess.run(['gh', 'api', f'repos/{TEST_REPO}/contents/{pathname}'],
                            capture_output=True, text=True, check=True)
    return json.loads(base64.b64decode(json.loads(result.stdout)['content']))


def make_bundle_response():
    rounds = json.loads((ROOT / 'questions/season0.json').read_text())['rounds']
    batch_id = bundle.next_batch_id(rounds)
    doc = json.loads((ROOT / 'questions/bundles' / (batch_id + '.json')).read_text())
    spec = importlib.util.spec_from_file_location('qa_entrant', ROOT / 'examples/bundle/entrant.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    anchors = {}
    for q in doc['questions']:
        if q['target_type'] == 'continuous_normal':
            anchors[q['round_id']] = 0
        elif q['target_type'] == 'profile_energy':
            anchors[q['round_id']] = {cell: 0 for cell in q['cells']}
        elif q['target_type'] == 'ranking_list' and not q.get('items'):
            anchors[q['round_id']] = ['QA_Article_' + str(i) for i in range(q['ranking_length'])]
    response = mod.build_response(doc, 'e2e_remote_backend', anchors, False, False)
    response['notes'] = 'Isolated persistence QA ' + secrets.token_hex(8)
    return response


def exercise(base_url, upload_token=None):
    manifest = (requests.get(HOSTED_URL + '/api/v1/questionnaire', timeout=30).json()
                if base_url == HOSTED_URL else qa.build_manifest())
    payload = make_human(manifest)
    headers = {'Idempotency-Key': 'storage-qa-' + secrets.token_hex(16)}
    endpoint = base_url + '/api/v1/questionnaire-submissions'
    first = requests.post(endpoint, json=payload, headers=headers, timeout=40)
    assert first.status_code == 201, ('create_status', first.status_code)
    receipt = first.json()
    stored = read_record('human/' + receipt['submission_id'] + '.json')
    assert stored['submission'] == payload['submission']
    assert stored['receipt_hash'] == receipt['receipt_hash'] == hashlib.sha256(qa.canonical_json(payload)).hexdigest()
    replay = requests.post(endpoint, json=payload, headers=headers, timeout=40)
    assert replay.status_code == 200 and replay.json()['idempotent_replay']
    assert replay.json()['received_at'] == receipt['received_at']
    changed = copy.deepcopy(payload)
    changed['submission']['answers'][0]['response']['value'] = 1
    conflict = requests.post(endpoint, json=changed, headers=headers, timeout=40)
    assert conflict.status_code == 409
    assert read_record('human/' + receipt['submission_id'] + '.json') == stored
    report = {'verified_at': datetime.now(timezone.utc).isoformat(), 'mode': 'hosted' if base_url == HOSTED_URL else 'local-http-real-github',
              'storage_repo': TEST_REPO, 'questionnaire': {
                  'create': 201, 'replay': 200, 'conflict': 409,
                  'independent_readback': True, 'original_unchanged': True,
                  'submission_id': receipt['submission_id'], 'receipt_hash': receipt['receipt_hash']}}
    if upload_token:
        response = make_bundle_response()
        url = base_url + '/api/v1/bundle-submissions'
        auth = {'Authorization': 'Bearer ' + upload_token}
        unauthorized = requests.post(url, json=response, timeout=40)
        assert unauthorized.status_code == 401
        first = requests.post(url, json=response, headers=auth, timeout=40)
        assert first.status_code == 200, ('bundle_create', first.status_code)
        body = first.json(); rec = body['receipt']
        assert rec['accepted'] > 0, 'No currently open bundle questions accepted'
        path = f"bundles/{response['batch_id']}/{response['entrant_id']}/{rec['response_sha256']}.json"
        stored = read_record(path)
        assert stored['response'] == response and stored['receipt'] == rec
        second = requests.post(url, json=response, headers=auth, timeout=40)
        assert second.status_code == 200 and second.json() == body
        report['bundle'] = {'unauthorized': 401, 'create': 200, 'replay': 200,
                            'independent_readback': True, 'accepted': rec['accepted'],
                            'rejected': rec['rejected'], 'response_sha256': rec['response_sha256']}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hosted', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    assert qa.INTAKE_REPO == TEST_REPO, 'Refusing non-test intake repository'
    meta = json.loads(subprocess.run(['gh', 'repo', 'view', TEST_REPO, '--json', 'isPrivate'],
                                    capture_output=True, text=True, check=True).stdout)
    assert meta['isPrivate'], 'Test intake must be private'
    if args.hosted:
        report = exercise(HOSTED_URL, os.environ.get('SSA_QA_UPLOAD_TOKEN'))
    else:
        class Handler(QuestionnaireHandler):
            def do_POST(self):
                if self.path == '/api/v1/bundle-submissions':
                    return BundleHandler.do_POST(self)
                return super().do_POST()
            def _json(self, status, payload):
                if self.path == '/api/v1/bundle-submissions':
                    return BundleHandler._json(self, status, payload)
                return super()._json(status, payload)
            def log_message(self, *_):
                pass
        # Route to the original handler and serializer; no storage/network mocks.
        old = {k: os.environ.get(k) for k in ('INTAKE_REPO_TOKEN', 'SUBMISSION_STORAGE_DIR',
                                             'SSA_UPLOAD_KEY_E2E_REMOTE_BACKEND')}
        token = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, check=True).stdout.strip()
        os.environ['INTAKE_REPO_TOKEN'] = token
        os.environ.pop('SUBMISSION_STORAGE_DIR', None)
        upload_token = secrets.token_urlsafe(32)
        os.environ['SSA_UPLOAD_KEY_E2E_REMOTE_BACKEND'] = upload_token
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            report = exercise('http://127.0.0.1:' + str(server.server_port), upload_token)
        finally:
            server.shutdown(); server.server_close()
            for k, value in old.items():
                if value is None: os.environ.pop(k, None)
                else: os.environ[k] = value
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
