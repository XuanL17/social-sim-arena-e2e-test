"""Fork-specific guardrails; never contact a network endpoint."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ssa import signing, questionnaire_api

for p in (ROOT / 'site').glob('*.html'):
    text = p.read_text()
    assert 'Social-Atoms/social-sim-arena' not in text, p
    assert 'https://social-simulation-arena.com' not in text, p
assert questionnaire_api.INTAKE_REPO == 'assassin808/social-sim-arena-e2e-test-intake'
config = json.loads((ROOT / 'vercel.json').read_text())
assert not any(r.get('has') for r in config['routes'])
keys = signing.published_keys()
assert keys['ssa-live'] != 'NAUoC6NhjIAyDXQWLcR59Z1/X5yAFnFiNXdxgHEwKuE='
assert keys['ssa-test'] == signing.TEST_PUBLIC_KEY
for name in ['refresh', 'preview', 'auto-merge', 'source-probe', 'candidates']:
    assert not (ROOT / '.github/workflows' / f'{name}.yml').exists()
    assert (ROOT / '.github/workflows' / f'{name}.yml.disabled').exists()
print('passed: fork URLs, isolated intake, domain routing, signing keys and inactive live workflows')
