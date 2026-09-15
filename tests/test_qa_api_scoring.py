"""Independent QA: run python -m unittest tests.test_qa_api_scoring -v.

The three originally expected failures now protect repaired contracts.
No network calls or persistent writes.
"""
import unittest
from datetime import datetime, timedelta, timezone
from jsonschema import Draft7Validator
from ssa import bundle, scoring
from ssa.questionnaire_api import build_manifest, open_rounds
from tests.test_bundle import read, SANDBOX, build_answers

NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)


class APIAndScoringQA(unittest.TestCase):
    def test_manifest_exact_publication_and_lock(self):
        r = dict(round_id='qa-round', status='open',
                 published_at='2026-09-15T00:00:00Z',
                 deadline='2026-09-16T00:00:00Z', lock_at='2026-09-16T00:00:00Z')
        for delta, count in ((-1, 0), (0, 1), (86399, 1), (86400, 0)):
            self.assertEqual(len(open_rounds({'rounds': [r]}, NOW + timedelta(seconds=delta))), count)

    def test_human_manifest_schema_is_standalone(self):
        q = next(q for q in build_manifest(now=NOW)['questions']
                 if q['target_type'] == 'continuous_normal')
        Draft7Validator(q['answer_schema']['human']).validate({
            'round_id': q['round_id'], 'target_type': q['target_type'],
            'response': {'value': 0}})

    def test_manifest_supplies_machine_readable_resolution_sources(self):
        questions = build_manifest(now=NOW)['questions']
        self.assertTrue(questions)
        self.assertEqual([q['round_id'] for q in questions
                          if not q.get('resolution_source_url')], [])

    def test_bundle_rejects_before_publication(self):
        doc = read(SANDBOX)
        before = datetime.fromisoformat(doc['published_at'].replace('Z', '+00:00')) - timedelta(seconds=1)
        outcome = bundle.normalise(build_answers(doc), doc, now=before)
        self.assertEqual(outcome['receipt']['accepted'], 0)
        self.assertEqual(outcome['records'], {})

    def test_bundle_exact_deadline_rejects(self):
        doc = read(SANDBOX)
        at_close = datetime.fromisoformat(doc['deadline'].replace('Z', '+00:00'))
        outcome = bundle.normalise(build_answers(doc), doc, now=at_close)
        self.assertEqual(outcome['receipt']['accepted'], 0)
        self.assertTrue(all(r['reason'] == 'late' for r in outcome['results']))

    def test_crps_translation_and_scale_invariance(self):
        for outcome in (-100, -0.1, 0, 0.1, 100):
            original = scoring.crps_normal(0, 2, outcome)
            self.assertGreaterEqual(original, 0)
            self.assertAlmostEqual(scoring.crps_normal(10, 2, outcome + 10), original)
            self.assertAlmostEqual(scoring.crps_normal(0, 6, outcome * 3), original * 3)


if __name__ == '__main__':
    unittest.main()
