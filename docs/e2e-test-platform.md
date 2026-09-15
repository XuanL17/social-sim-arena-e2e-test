# Personal E2E test platform

Repository: https://github.com/assassin808/social-sim-arena-e2e-test

This fork is an independent test installation. The inherited season and results
are a historical snapshot, not results produced by this test installation.
The yellow banner identifies every HTML page as a test platform.

## Isolation

- Web registration links and raw-data fallback target this fork.
- Production domain redirects are removed.
- The production signing public key is replaced by a newly generated independent
  key. Its private seed stays in ignored `.local/e2e-signing.env`. The public `ssa-test` key is
  retained for endpoint contract probes only.
- Refresh, source probes, candidate generation, auto-merge and the original
  Vercel preview workflows have a `.disabled` suffix. Do not re-enable them
  before configuring a synthetic season and reviewing their side effects.
- Legacy questionnaire storage targets `assassin808/social-sim-arena-e2e-test-intake`.
  That separate private repository is not provisioned yet. Without storage
  credentials the API returns a storage-unavailable error, rather than using
  the official intake repository.
- Do not copy the original checkout's `.env`, Vercel project binding, provider
  keys or participant endpoint registry into an active test runner.

## Offline simulation

```sh
python3.12 -m venv .local/venv
.local/venv/bin/python -m pip install requests jsonschema pillow cryptography pyyaml
.local/venv/bin/python tools/run_sandbox_cycle.py --json
```

This exercises generated scalar, profile and ranking questions, bundle intake,
resolution and production scoring in a temporary directory. It does not prove
that the hosted registration and Agent API dispatch flow works.

## Your entrant API

```sh
.local/venv/bin/python examples/agent-api/server.py
# In a second terminal:
.local/venv/bin/python tools/probe_agent_api.py --url http://127.0.0.1:8787/forecast
```

Replace the example with your own backend, expose it over HTTPS, and use this
fork's `submit.html` to probe it and generate a registration for this fork.
The contract is in `docs/agent-api.md`. A hosted endpoint needs browser CORS
support to pass the onboarding page's direct browser probe.

## Hosted rehearsal

Platform: https://social-sim-arena-e2e-test.vercel.app

Test dashboard: https://social-sim-arena-e2e-test.vercel.app/e2e.html

```sh
.local/venv/bin/python tools/run_agent_e2e.py --url https://social-sim-arena-e2e-test.vercel.app/api/example-agent
```

This sends nine real HTTPS requests (valid, repeated and bad-signature for
three shapes), parses answers with the production parsers, applies bundle
normalization at a simulated receipt time, rejects late answers and scores
synthetic outcomes. The synthetic source registry exists in memory only.
Records stay under `.local/e2e-agent-records`; `site/e2e-results.json` is the
publishable report. This route intentionally bypasses registration review and
scheduled dispatch; it is an operator rehearsal command.

The hosted example endpoint accepts this test platform's independent signing
key. Your backend should load `site/keys.json` from this fork. Never publish
`.local/e2e-signing.env`. The Vercel app itself needs no signing private key
because the rehearsal caller runs locally.

Deploy updates with `vercel deploy --prod --yes --scope yangs-projects-36e22525`.
The directory is linked to the independent project; no upstream project is used.

## Work still needed for a full scheduled competition run

Register your own test endpoint; configure an active synthetic season and a
scheduled dispatcher restricted to test entrants; exercise the GitHub review
and merge flow. The hosted dashboard reports manual rehearsal results, not
scheduled competition results. Legacy questionnaire storage is not enabled.
