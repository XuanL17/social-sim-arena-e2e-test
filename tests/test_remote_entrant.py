"""Exercise the deployable backend over TCP and restart its SQLite store."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ssa import signing
from tools.probe_agent_api import envelope
spec = importlib.util.spec_from_file_location('remote_entrant', ROOT / 'examples/remote-entrant/server.py')
remote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote)

with tempfile.TemporaryDirectory() as directory:
    db = str(Path(directory) / 'replies.sqlite')
    expected = {}
    for attempt in range(2):
        server = remote.serve('127.0.0.1', 0, ROOT / 'site/keys.json', db)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        try:
            assert requests.get(url+'/healthz', timeout=5).json()['status'] == 'ok'
            for shape in ('scalar', 'profile', 'ranking'):
                raw = json.dumps(envelope(shape, 'restart-'+shape)).encode()
                headers = {'Content-Type': 'application/json', **signing.sign(signing.TEST_PRIVATE_KEY, raw, signing.TEST_KEY_ID)}
                response = requests.post(url+'/forecast', data=raw, headers=headers, timeout=5)
                assert response.status_code == 200, response.text
                if attempt == 0:
                    expected[shape] = response.json()
                else:
                    assert response.json() == expected[shape]
                assert requests.post(url+'/forecast', data=raw, timeout=5).status_code == 401
            assert requests.options(url+'/forecast', timeout=5).status_code == 204
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
    import sqlite3
    with sqlite3.connect(db) as connection:
        assert connection.execute('SELECT count(*) FROM replies').fetchone()[0] == 3
print('passed: all shapes over TCP, unsigned rejection, CORS, health and persistent restart idempotency')
