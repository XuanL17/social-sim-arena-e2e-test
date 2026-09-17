# Simple GitHub registration

The website creates a prefilled file link in the test arena. It does not use OAuth,
accept a username, or generate private keys. The user generates Ed25519 keys locally.

1. Fill details and public key; click Submit registration via GitHub.
2. GitHub guides forking if needed. Save on a new branch, open a PR targeting
   qa-signed-intake-registry in assassin808/social-sim-arena-e2e-test.
3. The submitted file initially contains `"github": ""`. Validation intentionally
   fails until identity is bound. A trusted pull_request_target workflow reads the
   PR author's GitHub identity and posts an inline account-binding suggestion.
4. The participant checks the displayed account and public key, then clicks
   Commit suggestion. This records confirmation in Git history. No manual username
   entry is needed. A wrong-account PR should be closed and resubmitted.
5. Existing ownership/schema checks must pass; the maintainer reviews and merges.

The binding workflow never checks out contributor code, invokes contributor scripts,
or writes to repository contents. Its only write permission is PR comments. This
works with external forks without an OAuth token or bot write access to the fork.
The workflow must be discoverable on the default branch, and is also installed on the QA target branch. Only this comment-only workflow was added to the test fork main; the official repository is unchanged.
Existing entrants are never automatically rebound; existing ownership checks remain.

The website OAuth endpoints/session implementation has been removed. Previously
created OAuth credentials are no longer used; the OAuth app/grants can be revoked
in GitHub settings independently. The separate GitHub App for signed answer POST
persistence is retained. Signature verification and answer encryption are unchanged.

Test URL: https://assassin808-ssa-registration.vercel.app/submit.html
Vercel Preview protection remains enabled. External first-time GitHub fork creation
still requires a second real account to finish manual acceptance testing.

## Hosted verification — 2026-09-17

Test PR: https://github.com/assassin808/social-sim-arena-e2e-test/pull/3
The bot derived assassin808 from PR metadata and posted an inline suggestion.
The browser Apply suggestion → Commit changes operation recorded that account in
the file. The PR remains open, not merged. Initial validation failure on the empty
github field is intentional until confirmation.

Local registration form and workflow-script fixtures passed. Signed answer POST
implementation was not modified. The previously tested OAuth flow is superseded.

After applying the binding suggestion, all three checks passed (ownership/schema, binding workflow, hygiene).
