"""Registration mistakes must fail before any HTTPS call or output write."""
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.run_agent_e2e import registered_endpoint, run

sample = json.loads((ROOT / 'examples/e2e/e2e_demo.json').read_text())
url, registration = registered_endpoint(ROOT / 'examples/e2e/e2e_demo.json')
assert url == sample['route']['url']
assert registration['entrant_id'] == 'e2e_demo'
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'e2e_demo.json'
    for status in ('revoked', 'retired'):
        path.write_text(json.dumps({**sample, 'status': status}))
        with patch('tools.run_agent_e2e.requests.post') as post:
            try:
                run(registration_path=path)
            except ValueError as error:
                assert 'revoked or retired' in str(error)
            else:
                raise AssertionError('Inactive registration was called')
            post.assert_not_called()
    path.write_text(json.dumps({**sample, 'entrant_id': 'different_id'}))
    try:
        registered_endpoint(path)
    except ValueError as error:
        assert 'filename' in str(error)
    else:
        raise AssertionError('Mismatched identity accepted')
for url in ('http://example.com/forecast', 'https://example.com/forecast?token=x',
            'https://user:pass@example.com/forecast',
            'https://social-simulation-arena.com/api/example-agent',
            'https://www.socialsimarena.com/api/example-agent'):
    with patch('tools.run_agent_e2e.requests.post') as post:
        try:
            run(url)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Unsafe endpoint accepted: {url}')
        post.assert_not_called()
print('passed: registration identity, revoked/retired no-call behavior and endpoint isolation')
