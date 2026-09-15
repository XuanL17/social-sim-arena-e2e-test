"""Trigger the real platform -> independent backend test; publish only its report."""
import json
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = 'https://social-sim-arena-e2e-test.vercel.app'

def main():
    token = (ROOT / '.local/e2e-operator-token').read_text().strip()
    response = requests.post(PLATFORM+'/api/e2e/run',
        headers={'Authorization': 'Bearer '+token}, timeout=(15, 240))
    if response.status_code != 200:
        raise RuntimeError(f'Platform HTTP {response.status_code}: {response.text[:500]}')
    report = response.json()
    assert report['caller'] == 'vercel-server'
    assert report['backend'] == 'independent-vercel-project'
    assert report['registration_validated'] is True
    assert report['receipt']['accepted'] == 3 and report['late_receipt']['rejected'] == 3
    platform = report['platform_deployment']
    assert platform.startswith('social-sim-arena-e2e-test-')
    for call in report['calls']:
        assert call['status'] == 200 and call['bad_signature_status'] == 401
        assert call['backend_service'] == 'independent-vercel-project'
        assert call['backend_deployment'].startswith('social-sim-arena-e2e-agent-')
        assert call['backend_deployment'] != platform
        assert call['llm_generation_id'] and call['llm_model']
        assert float(call['llm_cost']) == 0
        assert call['replay_generation_id'] == call['llm_generation_id']
        assert call['replay_cache'] == 'hit'
    assert all(r['status'] == 'resolved' for r in report['results'])
    (ROOT / 'site/e2e-results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
