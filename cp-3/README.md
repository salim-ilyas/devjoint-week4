# Checkpoint 3 — Monitored Metrics

## Goal
Track more than just right/wrong: accuracy (pass rate), average
latency, and average token cost across the test set.

## What's here
`metrics.py` runs the same answer-then-judge flow as Checkpoint 2, but
additionally captures **real** numbers from the API's own response for
each question:
- **Latency** — wall-clock time for the model-under-test call, timed
  with `time.time()` around the actual request
- **Token usage** — `prompt_tokens`, `completion_tokens`,
  `total_tokens`, read directly from `response.usage` (not estimated)
- **Estimated cost** — token counts converted to a dollar estimate
  using `gpt-4o-mini`'s published per-token pricing

These are aggregated into a summary: accuracy/pass-rate, average
latency, average tokens per question, and average + total cost.

## What's measured, specifically
Metrics are tracked for the **model under test** (`gpt-4o-mini`) only,
not the judge (`gpt-4o`) — the judge is grading infrastructure, not
the system being evaluated, so its cost/latency isn't part of "how
good/expensive is this small model" that Checkpoint 3 is really
asking.

## Pricing used (verify before trusting for a real budget)
As of early 2026: `gpt-4o-mini` is $0.15 per 1M input tokens and $0.60
per 1M output tokens. OpenAI changes pricing periodically — check
https://openai.com/api/pricing/ before using these numbers for
anything beyond a rough estimate.