"""Offline contract for the real QA harness; not a persistence claim."""
import unittest
from tools.qa_storage import make_human, make_bundle_response, TEST_REPO
from ssa import questionnaire_api as qa, bundle


class StorageQAContract(unittest.TestCase):
    def test_target_is_only_isolated_repository(self):
        self.assertEqual(TEST_REPO, qa.INTAKE_REPO)
        self.assertEqual(TEST_REPO, 'assassin808/social-sim-arena-e2e-test-intake')

    def test_human_payload_matches_current_contract(self):
        body = make_human(qa.build_manifest())
        self.assertEqual(qa.validate_submission(body), body)
        self.assertFalse(body['submission']['publication_consent']['accepted'])
        self.assertTrue(body['submission']['contact_email'].endswith('.invalid'))

    def test_bundle_payload_is_schema_valid(self):
        body = make_bundle_response()
        envelope_errors, answer_errors = bundle.split_response_errors(body)
        self.assertEqual(envelope_errors, [])
        self.assertFalse(any(answer_errors.values()))


if __name__ == '__main__':
    unittest.main()
