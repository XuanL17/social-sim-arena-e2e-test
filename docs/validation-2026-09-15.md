# End-to-end validation report, 2026-09-15

## Conclusion

**Partly passing. The whole automated season cannot be called verified.** The
test used an isolated Vercel backend, an existing OpenRouter key and a named set
of free models. Real questions can be fetched and answered. Free-model
availability, source freshness and the older submission entry point all remain
risks. No future question has a real result yet, and no score is invented.

## Four models against three real answer shapes

Civiqs angry share, Civiqs 16-cell net approval, Wikipedia 10-article ranking --
all three taken verbatim from the public upstream question set. Requests went
from a local validator to the real Vercel backend; an earlier synthetic
three-question test separately covered the platform-to-backend link. Receipt and
deadline judgements ran production rules locally and wrote nothing into official
records.

| Free model | Scalar | 16-cell profile | Ranking |
| --- | --- | --- | --- |
| liquid/lfm-2.5-2.6b:free | pass | pass | invalid ranking, correctly refused |
| nex-agi/nex-n2.5-mini:free | timeout | pass | backend failure |
| google/gemma-4-31b-it:free | fail | fail | fail |
| dots-studio/dots-3-note-preview:free | pass | pass | pass |

6 of 12 pass. Every pass includes a real generation, validation by the production
parser, a cached replay of the identical request, receipt at the current time and
refusal after the deadline. All six generations were separately queried against
the OpenRouter generation API: `total_cost = 0`. A failure never switches to a
paid model. Gemma's result says its output is incompatible with the current
strict schema configuration, not that the model is unusable. A single run is not
a reliability statistic.

Machine evidence: `site/validation-live-free.json`, which keeps the failures
rather than overwriting them with green.

## Fetching questions, and the sources behind them

- Upstream public `season0.json`: HTTP 200, 151 questions.
- The test platform questionnaire: 99 before the fix, all 99 texts matching
  upstream.
- 82 of those had not reached `published_at`; the UI showed only the 17 open
  ones. The publication-window check in the API was fixed so a machine entrant
  cannot receive an unpublished question early.
- This week's bundle on GitHub Raw: HTTP 200, 17 questions. The site does not
  route `/questions/bundles/...` and returns 404; the official Raw link works.
- The Civiqs page returns 200 and the production adapter parses 603
  observations, latest 2026-09-14, net approval -26.5. The Wikimedia daily-top
  API returns 200 and the production parser keeps 999 entries.
- **Note:** the test snapshot still marks Civiqs stale/failing from an older
  archive, which differs from the page parsing today. A reachable source is not
  proof that automatic archiving and future resolution have recovered. Refresh is
  switched off in this environment by design.

## Scoring

- **1,911 published CRPS values were recomputed** from the raw forecast files --
  including the crowd's quantiles, not just its displayed mean and sd -- and match
  the public scores to four decimals.
- Profile energy, ranking/RBO, real historical examples, bundle receipt,
  deadlines, the resolver and adapter time rules were all exercised.
- Three pre-existing test failures were found: a stale navigation source
  assertion, the two 404 files differing, and the test fork's maintainer and
  disabled workflows not matching the original repository's assumptions. Each was
  fixed and re-run.
- A real future question can only be settled once its real result is published.
  Every real question this round is marked pending; no synthetic or backtest
  score is passed off as a future result.

## Browser interaction

Run test was actually used on the entrant page: browser Ed25519 signature,
cross-origin POST, real model response, HTTP 200 in about 7.45 s. After filling
in the registration details the JSON and the GitHub link pointed at the test
fork; switching the URL to HTTP blocked the test and disabled submission. No
duplicate registration pull request was created.

On the questions page the Open filter and a Civiqs search behaved correctly, and
cards showed the right shape, the 16-cell count, the deadline and the source
link. Page-render tests covered the board, the calendar, the model filter and the
detail data. No claim is made about every device, about accessibility, or about
sustained load.

Two display defects found here are recorded in full, with their fixes, in
[qa-ui.md](qa-ui.md): the Crowd forecast refitted as a normal on the
single-forecast page, and scored profile and ranking questions still wearing the
number template.

The browser section originally tested only the scalar shape while claiming "the
whole API is compatible"; it now states scalar only, with profile and ranking
tested separately. The 404 page was brought in line with the test environment's
identity and links.

## Are the questions sound?

1. **Scalar attitude questions.** Population, metric, unit and date are clear and
   suit a forecast of "what this source will publish". They should not be read as
   an error-free measurement of what the public actually thinks: Civiqs models
   survey results, it does not run a census.
2. **The 16-cell profile.** Forecasting the structure across demographic groups
   at once is meaningful, but the groups overlap, so the 16 numbers are not
   mutually exclusive populations to be summed. The unit is net percentage points
   (approve minus disapprove), not a 0-100% approval share. The historical energy
   score verifies; that is not evidence of strong predictive skill.
3. **The Wikipedia ranking.** The week window, the namespace exclusions and the
   tie rule are all stated. The real target is a summed ranking over truncated
   daily top-1000 lists, which is not exactly a ranking by full weekly pageviews.
   The first sentence of the question text is broader than that; the truncation
   belongs in the title. RBO measures point-ranking quality, not probabilistic
   calibration.
4. **Auditability.** Before the fix, all 99 manifest entries had an empty
   `resolution_source_url` while the UI showed a source link. A machine API should
   state the source URL, `observed_at`, the fetch time and the rules for
   revision, postponement and cancellation. "Friday dashboard" in particular
   needs a fixed timezone and reading time, or a day with several updates becomes
   a dispute.
5. **Questionnaire schema.** The returned human `answer_schema` referenced
   `#/definitions/round_id` without carrying the root definitions, so it could not
   be used standalone. Both this and the source URL are fixed; see
   [qa-api-contract.md](qa-api-contract.md).

## Not yet passing

- Real persistent writes through the older questionnaire and upload entry points
  were unverified at the time of this report; they were verified later the same
  day, see [qa-storage.md](qa-storage.md).
- The complete season loop: scheduled fetch, new archive, real future
  resolution, automatic leaderboard publication. The test cron is limited and the
  result has not happened yet.
- Long-run stability of several free models under repeats, races and rate
  limits; see [qa-free-stability.md](qa-free-stability.md).
- A single Friday cutoff and source-failure rule; see
  [qa-source-policy.md](qa-source-policy.md) for the isolated QA convention and
  the decisions still open.

## Reproduce

```sh
.local/venv/bin/python tools/validate_live_free.py
```

Fetches the questions and tests the four models. It consumes free-tier calls and
never calls a paid model.

`tools/audit_question_quality.py` audits the downloaded snapshots under
`.local/validation-*.json` and recomputes local raw forecast scores.
`site/validation-quality.json` is the pre-fix audit evidence.

Sources: [Civiqs methodology](https://civiqs.com/content/methodology),
[Wikimedia top-1000 API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/examples/project-metrics.html).
