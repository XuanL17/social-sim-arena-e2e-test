# GitHub-authenticated registration (test fork)

The form no longer accepts a GitHub username. GitHub OAuth identifies the user;
POST /api/registration calls /user again and overwrites the submitted github field.
Users generate Ed25519 keys locally and submit only public keys. Existing signed
forecast POST and answer encryption are unchanged.

## User flow

1. Connect GitHub and select the intended account. The form displays the verified login.
2. Fill entrant details and a locally generated public key.
3. Submit: the backend creates/reuses a fork, creates a registration branch and file,
   and opens a PR **using the user's OAuth token**, not the platform bot.
4. Existing author/owner CI and maintainer review remain required. A PR is not an
   approved registration. No automatic merge or direct registry write is added.

The test target is qa-signed-intake-registry, never upstream or main.
This is new registration only; existing entrant edits are rejected with 409.

## Deployment

Create a dedicated GitHub OAuth App. Do not reuse the GitHub installation private
key as an OAuth client secret. Keep expiring access tokens enabled and device flow
disabled. Exact callback (no wildcard):
https://assassin808-ssa-registration.vercel.app/api/auth/github/callback

Set these on the test Vercel **Preview** environment only:

- SSA_OAUTH_CLIENT_ID
- SSA_OAUTH_CLIENT_SECRET (sensitive)
- SSA_OAUTH_COOKIE_KEY (sensitive; a Fernet.generate_key() value)
- SSA_REGISTRATION_ORIGIN=https://assassin808-ssa-registration.vercel.app
- SSA_REGISTRATION_REPO=assassin808/social-sim-arena-e2e-test
- SSA_REGISTRATION_BASE=qa-signed-intake-registry

Point that stable Vercel alias at the tested Preview deployment. Always start
OAuth from this origin; cookies do not transfer across deployment hosts.

OAuth requests public_repo, which grants access to the user's public repositories,
not just this test repo. The implementation only operates on the configured arena
and the authenticated user's fork. GitHub's authorization screen is the consent
boundary; do not describe this OAuth scope as repository-scoped. No private-repo
scope is requested. A future scoped GitHub App would require a separate installation
and permission design; it is not silently substituted here.

## Security and limits

- State cookie + PKCE and a fixed callback prevent login response substitution.
- OAuth tokens stay in an encrypted Secure/HttpOnly/SameSite=Lax cookie, valid for
  30 minutes; no token is returned in JSON or placed in browser storage.
- POST requires same Origin and a session CSRF token; /user is checked on submission.
- The short-lived website login credential is separate from the entrant's long-lived
  signing private key. No database or platform-issued forecast token is added.
- Switching accounts clears the old site session and requests GitHub account selection.
- Logout clears the browser session; users can revoke the OAuth grant in GitHub settings.
- No raw exceptions, request bodies, codes, cookies or tokens are logged by handlers.
  Hosting access-log retention for OAuth callback query parameters is a separate
  provider setting; do not claim every hosting log is redacted by this code.
- Fork initialization and GitHub conflicts can require a retry. A deterministic
  branch and existing-PR lookup reuse an identical request; concurrent attempts can
  temporarily return 503 and should retry. Success is reported only with a PR URL.
- No endpoint probing is added here; endpoint review/probing remains part of approval.

## Validation

Run PYTHONPATH=. .local/venv/bin/python tests/test_registration_login.py and
PYTHONPATH=. .local/venv/bin/python tests/test_signed_registration.py.
Coverage includes forged usernames, private-key fields, CSRF, missing/tampered
sessions, wrong OAuth state, PKCE, changed GitHub identity, existing entrants,
repeat submissions, and user-authored PR creation. Live OAuth requires the dedicated
client credentials and a real user authorization; mocked tests do not prove it.

## Hosted verification — 2026-09-17

- Stable test page: https://assassin808-ssa-registration.vercel.app/submit.html
- OAuth app: SSA E2E Registration, application 3863799; secret only in Vercel Preview.
- Real browser OAuth: account selector → GitHub consent → callback → verified
  `Connected as @assassin808` display. Username is not an editable input.
- Real registration PR: https://github.com/assassin808/social-sim-arena-e2e-test/pull/2
  Author assassin808 (not bot), base qa-signed-intake-registry, only
  entrants/qa-oauth-login-20260917.json changed. Ownership validation and hygiene CI passed.
- Repeated browser submission returned the same PR #2. It remains open for review;
  this test did not merge or activate the registration.
- Unauthenticated hosted session request returns login_required.
- Local authentication tests: 14 passed; registration form suite passed; existing
  signed HTTP suite: 14 passed. Private signing keys were not uploaded.
- A different external user's first-time fork path is covered with a GitHub mock,
  but has not yet been exercised with a second real GitHub account.
- Deployment protection remains enabled; external testers may need Vercel access.
