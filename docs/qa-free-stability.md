# Free models: repeats, races and rate limits

## Real concurrent HTTPS

Each of four models received two simultaneous cold-cache requests with identical
bodies; a model that answered then got one replay.

- **Liquid** -- two 200s, different generation IDs, `sd` 12 and 10; the replay hit
  the last cache entry. **Concurrent idempotence fails.**
- **Dots** -- two 200s, different generation IDs, `sd` 1 and 10; the replay hit the
  last cache entry. **Concurrent idempotence fails.**
- **Nex** -- two 502s, about 45 s. The failure is kept.
- **Gemma** -- two 502s, about 0.4 s. The failure is kept.

Every successful response reported an OpenRouter cost of 0; there is no paid
fallback. Results are in `qa-stability/latest.json`.

The Runtime Cache offers reuse, not atomic claim or global single execution, so a
successful serial replay must not be read as concurrent idempotence.

## Offline fault injection

Six checks pass: 429 and 5xx; no retry on timeout; errors not cached; invalid
JSON and invalid forecasts refused; a missing or non-zero cost refused; a changed
input isolating the cache; a model outside the allowlist refused as an override.
Injecting a 429 offline is not acceptance under real rate limiting, and we do not
deliberately exhaust the account quota.

## Time-boxed observation

A read-only GitHub workflow sends one fresh request to each of the four free
models every six hours and, on success, verifies the cache replay: at most four
new inferences per run, with no automatic retry and no paid downgrade when a
provider fails. It stops calling after 2026-09-30. Each run's result is kept as
an Actions artifact for 30 days and published to the `qa-results` branch; see
[qa-auto-publish.md](qa-auto-publish.md).

```sh
python tools/qa_free_stability.py --race   # reproduce the race
python tools/qa_free_stability.py          # scheduled single-request mode
```

It signs with the protocol's public test seed, so neither a private signing key
nor an OpenRouter key needs to live in Actions.

Long-run stability needs many runs before it can be computed, and cannot be
claimed now. Strict concurrent idempotence needs atomic shared storage or a lock
plus durable results; this round only confirms and records the gap.
