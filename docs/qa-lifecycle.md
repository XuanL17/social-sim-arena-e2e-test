# Isolated season lifecycle

## What it is, and what it is allowed to touch

`tools/qa_lifecycle.py` reads two real Wikipedia weekly-top10 questions and
writes `qa-lifecycle/`. The test entrant is fixed as
`qa-persistence-public-source` and its algorithm is to copy the real ranking of a
week that finished before the deadline. It calls no LLM and neither the
production refresh nor the harness. This is a different test layer from the
free-model entrant tests; passing here is not "the LLM season passes".

- `sources/YYYY-MM-DD.json` -- the Wikimedia daily-top API response verbatim,
  its source URL, the first fetch time and a SHA-256. A repeated run reuses the
  archive and checks the digest; it never overwrites the first copy.
- `forecasts/` -- the predicted ranking, the real `filed_at`, the input week and
  an input digest. Kept after the first write, so a late answer is never
  backdated into a timely one.
- `resolutions/` -- the real seven-day result and its source digests. A question
  resolves only when all seven days succeeded.
- `report.json` / `index.html` -- an isolated board that marks historical replay
  against live test, and `pending` / `blocked` / `missed_deadline`. It is never
  merged into the official leaderboard.

A public source returning HTTP 429 gets at most three attempts, at least 1.2 s
apart, with a bounded `Retry-After` wait. Sustained failure prints `blocked` and
exits non-zero; archives already fetched are not lost. The runner stops fetching
and rewriting after **2026-10-01 00:00 UTC**.

## What has actually run

On 2026-09-15 the real official API returned **21 daily archives**. The first
attempt printed `blocked` on 429; the follow-up run with throttling reused the
existing archives and succeeded.

| Real question | Mode | Current result |
| --- | --- | --- |
| wiki-top10-2026-09-06 | historical_replay | resolved, production RBO loss **0.9466326921358921** |
| wiki-top10-2026-09-27 | live_test | forecast frozen before the 2026-09-18 14:00 UTC deadline, real result **pending** |

The replayed forecast was generated during this run from a pre-deadline
historical week. It is not a real, timely August 2026 submission. The future
question locks at **2026-09-18 14:00 UTC** and is due **2026-09-29 14:00 UTC**.
Finished days of the target week are archived day by day, but no outcome and no
score is produced before the release instant, and a missing day or a source error
produces no score either. A real future resolution can only wait for the real
result.

`python -m unittest tests.test_qa_lifecycle` covers pending -> resolved, a repeat
run neither re-fetching nor overwriting a forecast, a late answer refused, wrong
dates and incomplete weeks not resolving, and a tampered digest refused. Fixture
data stays in the unit tests and never reaches the public report.

## Workflow and publication boundary

`.github/workflows/qa-lifecycle.yml` runs on `workflow_dispatch` and every six
hours, and stops source work on 2026-10-01 UTC. It runs only on the test fork,
with `contents: read` and `actions: read`. It restores the previous
`qa-lifecycle-state` artifact with its own short-lived token to recover archives
and forecasts, then runs and uploads a complete artifact kept for 30 days.

It does **not** push, modify the default branch or deploy the platform. Results
reach the public page through the `qa-results` branch only; see
[qa-auto-publish.md](qa-auto-publish.md) for the permissions, the scope and the
failure fallback. The workflow has no push trigger, so it cannot retrigger
itself.

## Reproduce

```sh
.local/venv/bin/python -m unittest tests.test_qa_lifecycle
.local/venv/bin/python tools/qa_lifecycle.py
```

Deadlines and release times are judged from the real wall clock; there is no
command-line way to fake `now`. `--output` points at a different isolated
directory -- never at a production data directory.
