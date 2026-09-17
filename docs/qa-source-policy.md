# Source policy for isolated QA rounds: `qa-friday-utc-v1`

For new synthetic `qa-*` test questions only. **This is not a Season 0 rule.** It
does not change existing questions, the resolver, archives or the real
leaderboard. It is implemented as pure functions in `tools/qa_source_policy.py`:
the caller supplies the snapshot and the clock, so it verifies offline and
repeatably.

## The test convention, stated explicitly

- The target day is a UTC Friday, with a cutoff of 23:59:59Z.
- The observation must fall on that Friday in UTC and no later than the cutoff. A
  stale cache from the previous day cannot stand in for it.
- The fetch time may not precede the observation nor follow the caller's clock,
  and archiving is allowed up to 24 hours after the cutoff. Data already archived
  on the Friday itself is accepted, so a normal early fetch is not refused.
- The decision stays `pending` until the grace period expires, rather than
  freezing a target-day value that may still be updated. On expiry it takes the
  latest `observed_at` among the legal snapshots, then the latest `fetched_at`; an
  exact tie breaks by canonical JSON ordering purely so the test is deterministic.
  That tie-break is a QA convention, not a claim about source authority.
- No legal data by the end of the grace period means `cancelled`. Neither
  `cancelled` nor `pending` counts in the scoring denominator.
- Nothing is silently overwritten or revived once decided. A later, different
  legal candidate is recorded as `revision_requires_review`; one past the archive
  window is recorded as `late_archive_ignored`. Repeated events are deduplicated.
- Every decision carries `policy_version`, `decision_version` and the SHA-256 of
  the chosen snapshot. Only `decision_version=1` is produced here; a
  manually-approved version 2 recomputation is out of scope for this tool.

## Limits

The tool trusts the observation and fetch clocks it is handed. It proves nothing
about a remote clock or about the authenticity of a fetch. Its events are return
values and are **not persisted automatically**; a lifecycle caller must store
them. It does not claim that a real future Friday has happened, and it does not
apply the convention retroactively to public Season 0.

Before any real adoption, someone still has to decide the timezone, a fixed
observation time, the precedence of conflicting evidence, the grace period, what
a cancellation does to the official board, and the approval and recomputation
flow for revisions.

## Verification

```sh
.local/venv/bin/python -m unittest tests.test_qa_source_policy -q
```

8 passing: timezone boundaries, a missing source, a stale cache, the cutoff and
grace boundaries, future and inverted clocks, a frozen decision not being
modified, a cancellation neither reviving nor counting in the denominator, and
the policy applying only to QA Friday rounds.
