# Personal E2E test platform

## Live services

Both services run in assassin808's Vercel account, in separate projects:

| Role | URL |
| --- | --- |
| Platform / test dashboard | https://social-sim-arena-e2e-test.vercel.app/e2e.html |
| Browser registration/probe | https://social-sim-arena-e2e-test.vercel.app/submit.html |
| Independent simulated AI API | https://social-sim-arena-e2e-agent.vercel.app/forecast |
| Backend health | https://social-sim-arena-e2e-agent.vercel.app/healthz |

No SSH server or custom domain is needed. The backend is a real hosted API that
simulates an AI deterministically, not a paid LLM. Vercel mode is stateless;
equal inputs produce equal answers without claiming durable SQLite storage.

## Verified path

The browser probe reaches the independent backend over HTTPS and passes CORS
and signed-request checks. Registration `entrants/e2e_remote_backend.json` was
validated with the production schema/ownership validator and merged through
[test registration PR #1](https://github.com/assassin808/social-sim-arena-e2e-test/pull/1).
GitHub reported no CI check runs on that PR; validation evidence is the local
validator result, not a claim of green hosted CI.

`POST /api/e2e/run` runs on the platform's Vercel server. It reads the merged
registration, requires its URL to match the configured backend, signs synthetic
questions, calls the separate backend, parses the responses and scores them.

The published `site/e2e-results.json` records three accepted/resolved shapes,
consistent repeat responses, three invalid signatures rejected with 401,
and three late synthetic submissions rejected. It records the platform and
backend deployment hostnames; they belong to different Vercel projects.
The platform also rejects calls without its operator token with HTTP 401.

## Repeat the hosted test

From this checkout:

```sh
.local/venv/bin/python tools/trigger_hosted_e2e.py
```

This local command only triggers the platform. The signed backend requests,
parsing and scoring execute in Vercel. It reads the operator token from ignored
`.local/e2e-operator-token`, checks the returned deployment identities and
results, and saves the successful report to `site/e2e-results.json`.

Publish a changed report or platform code from the repository root:

```sh
vercel deploy --prod --yes --scope yangs-projects-36e22525
```

Deploy backend changes from `examples/remote-entrant/` using the same command.
That directory has its own `.vercel` binding; do not copy project bindings
between the two directories.

## Isolation and configuration

- Repository: `assassin808/social-sim-arena-e2e-test`; all active web submission
  links point to this fork. Production domain redirects are removed.
- Root Vercel environment: `E2E_REMOTE_URL`, `E2E_OPERATOR_TOKEN`,
  `SSA_SIGNING_KEY`, `SSA_SIGNING_KEY_ID`. Only the platform holds private keys.
- Backend `keys.json` contains this test platform's public verification keys.
- Live refresh, source-probe, candidate generation, auto-merge and the upstream
  Vercel preview workflows retain `.disabled` suffixes.
- No production source refresh, original participant dispatch or paid LLM
  runs as part of this test. The dispatcher selects only the test registration.
- The original site interface retains inherited historical data, explicitly
  marked as a snapshot. Test scores live on the dedicated test dashboard.
- The test uses fixed synthetic source outcomes and an explicit simulated
  receipt/release clock. This is a manually triggered competition rehearsal,
  not a cron-driven live season.
- Legacy questionnaire storage is intentionally unconfigured and targets an
  independent intake repo name; that older intake route is not used here.

## Your own simulated or real AI implementation

Change the forecast implementation in `examples/remote-entrant/server.py` and
deploy from that directory. The Vercel adapter is `api/index.py`. Or replace the
registration endpoint and matching `E2E_REMOTE_URL` with another HTTPS service.
Load this fork's `site/keys.json` in an external server to verify signatures.

For a local rehearsal against a different registration file:

```sh
.local/venv/bin/python tools/run_agent_e2e.py --registration /path/to/your_entrant.json
```

This alternate command checks filename/identity, schema, route and revocation
before calling. Its calls execute locally, unlike `trigger_hosted_e2e.py`.

## Local checks

```sh
.local/venv/bin/python tests/test_e2e_isolation.py
.local/venv/bin/python tests/test_e2e_registration.py
.local/venv/bin/python tests/test_e2e_run_api.py
.local/venv/bin/python tests/test_agent_probe.py
.local/venv/bin/python tools/run_sandbox_cycle.py --json
```

`tests/test_remote_entrant.py` additionally checks TCP and SQLite restart behavior
for the optional standalone VM/container implementation. That persistence test
must not be described as Vercel storage verification.
