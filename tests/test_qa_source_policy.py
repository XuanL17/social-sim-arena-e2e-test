import unittest
from tools.qa_source_policy import evaluate, denominator

DAY = '2026-09-18'
AFTER = '2026-09-20T00:00:00Z'

def snap(observed='2026-09-18T23:59:59Z', fetched='2026-09-19T01:00:00Z', value=4):
    return dict(observed_at=observed, fetched_at=fetched, value=value)

class SourcePolicy(unittest.TestCase):
    def evaluate(self, snapshots, now=AFTER, previous=None):
        return evaluate('qa-friday-1', DAY, snapshots, now, previous)

    def test_timezone_boundary(self):
        self.assertEqual(self.evaluate([snap(observed='2026-09-19T01:59:59+02:00')])['status'], 'resolved')
        self.assertEqual(self.evaluate([snap(observed='2026-09-19T02:00:00+02:00')])['status'], 'cancelled')

    def test_missing_source_pending_then_cancelled(self):
        self.assertEqual(self.evaluate([], '2026-09-19T23:59:58Z')['status'], 'pending')
        self.assertEqual(self.evaluate([], '2026-09-19T23:59:59Z')['status'], 'cancelled')

    def test_stale_cache_never_resolves(self):
        self.assertEqual(self.evaluate([snap(observed='2026-09-17T23:59:59Z')])['status'], 'cancelled')

    def test_grace_inclusive_and_late_archive_excluded(self):
        self.assertEqual(self.evaluate([snap(fetched='2026-09-19T23:59:59Z')])['status'], 'resolved')
        self.assertEqual(self.evaluate([snap(fetched='2026-09-20T00:00:00Z')])['status'], 'cancelled')

    def test_future_and_invalid_clock_order_not_used(self):
        self.assertEqual(self.evaluate([snap()], '2026-09-18T23:59:59Z')['status'], 'pending')
        self.assertEqual(self.evaluate([snap(fetched='2026-09-18T20:00:00Z')])['status'], 'cancelled')

    def test_revision_frozen_and_audited(self):
        old = self.evaluate([snap()])
        updated = self.evaluate([snap(value=9)], previous=old)
        self.assertEqual(updated['value'], 4)
        self.assertEqual(len(updated['events']), 1)
        self.assertEqual(self.evaluate([snap(value=9)], previous=updated), updated)

    def test_cancelled_not_resurrected_or_counted(self):
        cancelled = self.evaluate([])
        review = self.evaluate([snap()], previous=cancelled)
        self.assertEqual(review['status'], 'cancelled')
        self.assertEqual(len(review['events']), 1)
        self.assertEqual(denominator([review, self.evaluate([snap()]), self.evaluate([], '2026-09-18T00:00:00Z')]), 1)

    def test_only_new_qa_rounds_and_friday(self):
        for rid, day in [('production-round', DAY), ('qa-round', '2026-09-17')]:
            with self.assertRaises(ValueError):
                evaluate(rid, day, [], AFTER)

if __name__ == '__main__':
    unittest.main()
