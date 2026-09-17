# Isolated QA: what runs here and where it stands

This fork rehearses the full arena loop -- hosted endpoint, signing, private
storage, free OpenRouter models, isolated cron -- without touching the official
repository. Live refresh is disabled; `site/data.json` is a committed snapshot.

Each layer has its own report. This page is the index and the current state; it
does not repeat their evidence.

| Layer | Report |
| --- | --- |
| API contract, questions, scoring | [qa-api-contract.md](qa-api-contract.md) |
| Persistence into a private repository | [qa-storage.md](qa-storage.md) |
| Isolated season lifecycle | [qa-lifecycle.md](qa-lifecycle.md) |
| Free-model repeat/race/rate-limit behaviour | [qa-free-stability.md](qa-free-stability.md) |
| Source policy for synthetic QA rounds | [qa-source-policy.md](qa-source-policy.md) |
| Browser re-test of the site | [qa-ui.md](qa-ui.md) |
| End-to-end report, 2026-09-15 | [validation-2026-09-15.md](validation-2026-09-15.md) |
| Signed POST intake, hosted rehearsal | [qa-signed-hosted-2026-09-17.md](qa-signed-hosted-2026-09-17.md) |
| Automatic publication to `qa-results` | [qa-auto-publish.md](qa-auto-publish.md) |

## Passing

- Questionnaire and upload entry points on Vercel write for real into a private
  repository, survive replay, reject a conflicting rewrite, and read back
  independently.
- Pre-publication answers are refused, `answer_schema` is standalone, and the
  17 open questions carry source URLs. Verified against the deployed site.
- 49 contract/storage/lifecycle/source-policy tests, 28 bundle regressions and
  6 offline free-endpoint fault injections.
- 21 days of real Wikimedia archives; one already-finished week resolved by
  historical replay. The future week's forecast is frozen and waits for the
  real result on 2026-09-29.
- Two lifecycle Actions runs; the second restored the artifact and left both
  frozen forecasts unchanged.
- Two read-only QA workflows every 6 hours. Source work and model calls stop
  on 2026-10-01 UTC. Reports publish to the `qa-results` branch only.

## Failing or waiting

- **Free-model availability.** The first scheduled stability run failed:
  Liquid and Dots answered and replayed from cache, Nex and Gemma returned 502.
  This is upstream capacity, not our code, but it means no long-run pass can be
  claimed.
- **Cold-cache concurrency.** Two simultaneous identical requests to Liquid and
  to Dots each produced two different generations with different `sd`. Strict
  concurrent idempotence fails; the Runtime Cache offers reuse, not a lock.
- **The real future resolution has not happened yet.** `wiki-top10-2026-09-27`
  resolves on 2026-09-29.

Of the five defects the first audit found, the three API ones are fixed. The two
interface defects (UI-01, UI-02) were fixed on `fix-ui-lifecycle` and ported
upstream; see [qa-ui.md](qa-ui.md).

## Cloud evidence

- Lifecycle, first run: [35037356150](https://github.com/assassin808/social-sim-arena-e2e-test/actions/runs/35037356150)
- Lifecycle, restore check: [35037416735](https://github.com/assassin808/social-sim-arena-e2e-test/actions/runs/35037416735)
- Free stability, failing run: [35037359038](https://github.com/assassin808/social-sim-arena-e2e-test/actions/runs/35037359038)
- Machine reports: `site/qa-storage-hosted.json`, `qa-stability/latest.json`,
  `qa-lifecycle/report.json`
