# Checkpoint 2 — Automated Scoring Script

## Goal
Automatically grade the model's answers against `test_set.json`,
using an LLM as judge — so both exact-answer and open-ended questions
can be scored without manual review of every response.

## What's here
- **`scorer.py`**
  - `get_model_answer(question)` — sends the question to the model
    under test (`gpt-4o-mini`), returns its answer
  - `judge_answer(question, expected_answer, model_answer)` — sends a
    **separate, stronger** judge model (`gpt-4o`) a comparison prompt,
    returns a strict-JSON `PASS`/`FAIL` verdict with a one-line reason
  - `run_evaluation()` — runs all 20 questions through both steps,
    saves everything to `results.json`

- **`test_judge_sanity.py`** — a second, independent check: feeds the
  judge 4 **deliberately wrong** answers (a wrong capital, a fictional
  country's capital stated as real, an invented plot for a nonexistent
  movie, a fake justification for 2+2=5) and confirms the judge
  correctly returns `FAIL` on all of them. This exists because a
  clean pass rate on the real test set only means something if the
  judge itself can actually catch a wrong answer — this test proves
  that rather than assuming it.

## Why the judge is a different, stronger model than the one being tested
Using the same (or a weaker) model to both answer and grade risks the
judge sharing the same blind spots as the model it's evaluating. Since
this project's model under test is intentionally small (`gpt-4o-mini`,
fitting the "small model" theme of the week), the judge uses a
stronger model (`gpt-4o`) specifically so it's more likely to catch
subtle mistakes rather than rubber-stamping them.

## Results (actual)

`scorer.py`: **20/20 passed** on the full test set, including all 6
outlier questions (undefined math, fictional-country capital,
nonexistent-movie plot, false-premise math, etc.) — verified by
manually reading each outlier's `model_answer` in `results.json`, not
just trusting the verdict.

`test_judge_sanity.py`: judge correctly returned `FAIL` on all 4
deliberately wrong answers, confirming the grading pipeline itself is
not too lenient — so the 20/20 result above can be trusted rather than
being a false positive from a rubber-stamp judge.

## Requirements
- `openai`
- `python-dotenv`

Note: this checkpoint originally used the Gemini API, but switched to
OpenAI after hitting a Gemini `ResourceExhausted` error.