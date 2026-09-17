# Persistence verification, 2026-09-15

## Product boundary

The older questionnaire path still has a schema, an HTTP handler and a route;
`docs/submission-design.md` describes it. The current test entrant flow is
endpoint registration, and `docs/bundle-submission.md` states that bundle upload
is optional and not switched on for Season 0. What follows checks that the
existing entry points work. It does not claim the official platform has enabled
them.

## Real storage, not a mock

A private repository `assassin808/social-sim-arena-e2e-test-intake` was created
and pinned in the source, so nothing official is touched. The original HTTP
handler was run behind a local server, synthetic QA records were written through
the real GitHub Contents API, and a separate `gh` request read them back.

| Case | Result |
| --- | --- |
| Questionnaire, first write | HTTP 201 |
| Same Idempotency-Key, same body | HTTP 200, original `received_at` kept |
| Same key, changed answer | HTTP 409, the stored file untouched |
| Independent read-back | submission and `receipt_hash` as expected |
| Bundle without upload credentials | HTTP 401 |
| Bundle with a dedicated temporary test credential | HTTP 200, 15 accepted, 2 refused as late |
| Bundle, identical body replayed | HTTP 200, receipt and results unchanged |
| Bundle, independent read-back | original response and receipt intact |

The two late ones are `mc-2026-w38-approval` and `aaii-2026-09-17`. That is not a
storage failure: their deadlines had really passed at run time.

Questionnaire record `ssa_7b7c70214d47baea3ba2d1a4`, hash
`b9f015c795f559bd0c522759def7f09c17a29d675aeeb5a0ab115c3e09dd1e8e`.
Bundle hash `1b20d9b11294983c645bc593af07ca9c6345abca7e66e15dbbfd3f4a364ce2f9`.
The machine report is in the ignored path `.local/qa-storage-real.json`. Two
synthetic records remain in the private repository; nothing was written to the
official repository, no official forecast file was created, and no real contact
details were used.

## Hosted: Vercel to persistent storage

After the owner configured a repository-scoped credential and redeployed, the
same checks ran from the deployed test site at 2026-09-15T23:53:38Z:
questionnaire 201 on create, 200 on identical replay, 409 on same key with a
changed body; an independent GitHub read-back matched hash and body, with the
stored file untouched. Bundle: 401 without a credential, 200 to create and 200 to
replay with the right one, 15 accepted and 2 correctly refused as late,
read-back consistent.

Machine evidence: `site/qa-storage-hosted.json`. Only the credential scoped to
that private test repository was used; no broad local `gh` token was copied to
the cloud, and the cloud upload token is limited to the test entrant. The
"real persistence" gap is closed. This still says nothing about the official
platform enabling the older entry points.

## Reproduce

```sh
.local/venv/bin/python -m unittest tests.test_qa_storage -v
.local/venv/bin/python tools/qa_storage.py --report .local/qa-storage-real.json
# once the scoped credential is configured and the test platform redeployed:
.local/venv/bin/python tools/qa_storage.py --hosted --report .local/qa-storage-hosted.json
```

The default mode borrows the local `gh` identity in process memory only and
restores the environment on exit: no token file is written, no token is printed,
no cloud token is configured. The script first checks that the repository is
pinned to the test repository and is private. Every run mints a new idempotency
key and leaves a new synthetic audit record, so it is not a read-only probe.

The 3 offline tests check the harness contract and the isolation constraints
only. They do not replace the real read/write evidence above, and nothing here
proves concurrent-write behaviour, long-run stability, or the hand-off from
manual review into official scoring.
