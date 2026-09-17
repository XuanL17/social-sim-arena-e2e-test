# Independent browser re-test of the site, 2026-09-15

## Scope and method

Read-only interaction in a real browser at
`https://social-sim-arena-e2e-test.vercel.app`: number, profile and ranking
detail pages, filters, the locked state of the registration form, and a 390x844
phone viewport. Live `/data.json` (`generated_at 2026-09-15T05:04:07Z`) was the
reference for scores. Run test was not triggered, no model was called, no
registration pull request was opened, no entrant data was written, and nothing
was changed or deployed. The phone viewport was restored afterwards.

## Failing, independently reproducible

### UI-01 - P1 - Crowd scores differently on two pages

- Question page, [Michigan August
  prelim](https://social-sim-arena-e2e-test.vercel.app/#question/umich-2026-08-prelim):
  the Crowd row reads `62.2 +/- 12.0 / Error 11.2 / CRPS 5.52`. The question
  table itself was fixed in an earlier round and passes.
- Clicking that row opens the [single Crowd
  forecast](https://social-sim-arena-e2e-test.vercel.app/#forecast/umich-2026-08-prelim/crowd),
  which reads `CRPS 6.70` -- same round, same entrant, same forecast.
- Expected: both pages use the one published score `5.523`, formatted `5.52`. The
  single-forecast page must not refit a quantile forecast as a normal.
- Evidence, from the real DOM: question row `22 Crowd Aug 12, 07:00 AM 62.2 +/-
  12.0 11.2 5.52`; forecast page Error tile `11.2 / CRPS 6.70`.

### UI-02 - P1 - Scored profile and ranking questions still read "awaiting resolution"

- [Google Trends
  9/5](https://social-sim-arena-e2e-test.vercel.app/#question/trends-basket-2026-09-05):
  reads `locked - answer expected Sep 5`, `no number forecasts`, headers
  `Error / CRPS`, every score a dot.
- [Wikipedia
  9/6](https://social-sim-arena-e2e-test.vercel.app/#question/wiki-top10-2026-09-06):
  reads `locked - answer expected Sep 8`, same number template.
- Live `/data.json` already carries `profile.rounds` with Trends 9/5 GLM web+sfc
  `energy: 1.2464` and Trends 9/12 `energy: 2.4927`, and `ranking.rounds` with
  Wiki 9/6 Claude Opus web+sfc `loss: 0.806`. In the main `rounds` array all
  three are still `awaiting_resolution`.
- Expected: a scored question's status matches its published score; a profile
  shows Energy and its per-cell result, a ranking shows its loss and the actual
  order, neither borrows the number template's CRPS column. Two layers are
  involved: the status the pipeline publishes, and the page template.
- [Civiqs 16-cell
  w37](https://social-sim-arena-e2e-test.vercel.app/#question/civiqs-profile-2026-w37)
  wears the same number template, but has no published result this round, so its
  empty scores are not counted as a separate defect.

**Both are fixed.** `attach_round_scores` now marks a scored profile or ranking
round resolved and carries its outcome, and one `forecastScore` function serves
the question, forecast and entrant pages. Ported upstream as
[PR #124](https://github.com/Social-Atoms/social-sim-arena/pull/124).

## Passing, and where the coverage stops

| Check | Result |
| --- | --- |
| Questions -> Open -> search "Civiqs" | returns the open Civiqs questions including the 16-cell one, with deadline, shape and source link visible |
| No match, `zzqa-no-match` | shows "No matching questions" and suggests changing the filter |
| Questions -> Enter the arena -> Register an agent | opens submit.html; the human entry point stays disabled |
| Registration form before the endpoint test | with ordinary test strings, an HTTP URL and an illegal id, Submit for review and Copy JSON stay disabled. Run test was not clicked, so no claim is made about pre-send error messages |
| Phone, 390x844 | question cards, status filters and the registration copy are readable and reachable; the document does not exceed the viewport and the nav scrolls sideways locally. One representative viewport only |
| Phone, profile row | the Civiqs w38 Persistence row opens its single forecast and the 16-cell mean/sd table is readable |
| Phone cleanup | default viewport restored |

## Suggested regression on any future fix

Compare the question table, the single forecast and the task board against the
same published score, using three fixed historical samples: a Crowd quantile
number, a resolved 5-cell profile and a resolved 10-item ranking. A screenshot,
or one page rendering without error, does not show that the scores agree.

This report does not cover payment, external writes, automatic resolution or
free-model reliability.
