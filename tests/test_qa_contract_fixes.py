"""Offline regressions for independently usable contracts and release gates."""
import unittest
from datetime import datetime, timedelta, timezone
from jsonschema import Draft7Validator
from ssa import batches, bundle
from ssa.questionnaire_api import build_manifest, _resolution_source_url
from tests.test_bundle import read, SANDBOX, build_answers


class ContractFixes(unittest.TestCase):
    def test_all_manifest_schemas_have_resolvable_local_refs(self):
        manifest = build_manifest(now=datetime(2026, 9, 15, tzinfo=timezone.utc))
        for question in manifest['questions']:
            for schema in question['answer_schema'].values():
                Draft7Validator.check_schema(schema)
                def walk(value):
                    if isinstance(value, dict):
                        if '$ref' in value:
                            ref = value['$ref']
                            self.assertTrue(ref.startswith('#/'))
                            target = schema
                            for part in ref[2:].split('/'):
                                target = target[part.replace('~1', '/').replace('~0', '~')]
                        for item in value.values():
                            walk(item)
                    elif isinstance(value, list):
                        for item in value:
                            walk(item)
                walk(schema)

    def test_source_explicit_then_matching_task_then_provenance(self):
        data = {'tasks': [{'match': {'series': ['s'], 'target_type': 'profile_energy'},
                           'source': {'url': 'https://example.org/profile'}}],
                'series_provenance': {'s': 'archive'},
                'sources': {'archive': {'url': 'https://example.org/archive'}}}
        self.assertEqual(_resolution_source_url({'series': 's'}, data), 'https://example.org/archive')
        self.assertEqual(_resolution_source_url({'series': 's', 'target_type': 'profile_energy'}, data), 'https://example.org/profile')
        self.assertEqual(_resolution_source_url({'resolution_source_url': 'https://example.org/explicit'}, data), 'https://example.org/explicit')
        self.assertIsNone(_resolution_source_url({'series': 'unknown'}, data))

    def test_bundle_window_is_per_question_and_inclusive_at_open(self):
        doc = read(SANDBOX)
        response = build_answers(doc)
        for question in doc['questions']:
            opening = batches.published_at(question['lock_at'])
            for delta in (-1, 0):
                result = bundle.normalise(response, doc, now=opening + timedelta(seconds=delta))
                row = next(r for r in result['results'] if r['round_id'] == question['round_id'])
                self.assertEqual(row['status'], 'rejected' if delta < 0 else 'accepted')
                if delta < 0:
                    self.assertEqual(row['reason'], 'not_published')

if __name__ == '__main__':
    unittest.main()
