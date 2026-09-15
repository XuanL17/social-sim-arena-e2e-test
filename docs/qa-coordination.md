# Independent QA pass

Two independent testing agents were assigned:

1. API/scoring: publication and deadline boundaries, standalone schemas, source provenance, bundle acceptance and scoring contracts. Outputs: `qa-api-scoring.md`, `tests/test_qa_api_scoring.py`.
2. UI: browser interactions, scalar/profile/ranking detail consistency, registration state and responsive layout. Outputs: `qa-ui.md`, optionally `tests/site/qa_details.js`.

The main agent additionally ran `tests/test_qa_free_resilience.py`: six offline fault-injection tests passed. These cover 429/5xx and timeout behavior, invalid forecast rejection, zero-cost confirmation, changed-question cache isolation and model override allowlisting. No API key or network is required, and no real model calls are made by these tests.

This pass is a QA/reproduction pass. Confirmed defects remain tracked separately from passing regression tests. No changes to the official competition, no paid model calls, and no live registration submissions are part of this pass.

## Reviewed results

API agent: 71 existing checks passed; six new regression tests produced three passes and three expected failures. Main agent independently reran those six tests using `python -m unittest tests.test_qa_api_scoring -v` and confirmed the outcome. Expected failures are known unfixed defects, not successful validation.

Confirmed API issues: standalone human answer schema loses its definitions, machine-readable source URLs are empty, and the bundle normalizer accepts answers before publication. The latter was reproduced locally, not by submitting to online storage.

Review correction: the current Wikipedia question already explicitly describes the daily top-1000 aggregation and tie/exclusion rules. The earlier report's wording concern should be treated as a low-priority title clarification, not as an undefined resolution method.
