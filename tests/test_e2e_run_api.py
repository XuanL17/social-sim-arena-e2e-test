"""The Vercel dispatcher must authenticate before it can call any backend."""
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import sys
import threading
from unittest.mock import patch
import requests
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api import e2e_run

server = ThreadingHTTPServer(('127.0.0.1', 0), e2e_run.handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f'http://127.0.0.1:{server.server_port}/api/e2e/run'
try:
    with patch.dict(os.environ, {'E2E_OPERATOR_TOKEN': ''}), patch.object(e2e_run, 'execute') as execute:
        assert requests.post(url, timeout=5).status_code == 503
        execute.assert_not_called()
    with patch.dict(os.environ, {'E2E_OPERATOR_TOKEN': 'test-only-operator-token'}), patch.object(e2e_run, 'execute', return_value={'caller': 'vercel-server'}) as execute:
        assert requests.post(url, timeout=5).status_code == 401
        execute.assert_not_called()
        result = requests.post(url, headers={'Authorization': 'Bearer test-only-operator-token'}, timeout=5)
        assert result.status_code == 200 and result.json()['caller'] == 'vercel-server'
        execute.assert_called_once()
    with patch.dict(os.environ, {'E2E_REMOTE_URL': 'https://social-sim-arena-e2e-test.vercel.app/api/example-agent'}):
        try:
            e2e_run.execute()
        except ValueError as error:
            assert 'independent server' in str(error)
        else:
            raise AssertionError('Vercel function must not substitute for remote backend')
finally:
    server.shutdown()
    server.server_close()
    thread.join()
print('passed: operator authentication, disabled unconfigured dispatch and independent backend requirement')
