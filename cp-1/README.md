# Checkpoint 1 — Test Set

## Goal
Build 15-20 question/expected-answer pairs to evaluate an LLM against
— a mix of normal questions and outliers, so the evaluation doesn't
just measure performance on easy cases.

## What's here
`test_set.json` — 20 objects, each with just `question` and
`expected_answer`.

The 20 pairs are an even 50/50 split between exact-answer question
and open-ended questions.
6 of the 20 are deliberate outliers designed to catch common LLM
failure modes, mixed in among 14 normal questions — the file itself
doesn't label which is which, so grading has to actually look at each
answer rather than rely on a metadata flag.
