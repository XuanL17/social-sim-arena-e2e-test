# Authorized automatic QA publication

User authorized automatic test webpage updates. The two test workflows now have a separate publication job with repository contents write permission. The job only calls `tools/publish_qa_results.py`, which hard-codes the test repository, qa-results branch and these two paths:

- qa-lifecycle/report.json
- qa-stability/latest.json

The branch contains reports only. No workflow writes main, no official repository is modified, and no broad personal token is used; publication uses GitHub's per-job token. Failed test runs still publish evidence if a report artifact exists. Updates stop after 2026-09-30 UTC. A shared publication concurrency group and non-forced branch updates prevent lost updates between the two jobs.

The test website reads those JSON files directly and refreshes once per minute while visible. Reports show test time, publication time and source run metadata. If the live branch cannot be read, the page labels the fallback as an older deployment snapshot instead of presenting it as current. No Vercel rebuild is needed for new results.

This is authorized test publication, not an approval to change official-season rules or merge the test fork into the official repository.
