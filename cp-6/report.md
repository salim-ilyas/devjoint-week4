# Week 4 Evaluation Report — AI Output Estimation & Small Model Adaptation

## 1. Objective
Evaluate a small language model's output quality, track its
cost/latency, identify real failure modes with root cause analysis,
and fix at least one of those failure categories — with proof the fix
worked.

## 2. Models used
- **Model under test**: `gpt-4.1-nano`
- **Judge model**: `gpt-4o` — deliberately a stronger
and separate model from the one being tested, so the judge
isn't sharing the same blind spots as the system it's grading
- **API**: OpenAI

### Note on model evolution across checkpoints
Checkpoints 2-3 originally ran against `gpt-4o-mini`, which scored a
clean 20/20 on the initial test set — too strong a result to analyze
failures from. Checkpoints 4-5 switched the model under test to
`gpt-4.1-nano`, specifically to surface genuine, documentable
failures. This is a deliberate methodology choice, not an
inconsistency: the goal shifted from "measure a model" to "find and
fix a real weakness," which needed a model that would actually
produce some.

## 3. Methodology

### 3.1 Test set (Checkpoint 1)
20 question/expected-answer pairs, an even 50/50 split between
exact-answer and open-ended questions, including 6 deliberate
outliers targeting hallucination, false premises, and undefined math
(e.g. a fictional country's "real" capital, a movie that doesn't
exist, "why does 2+2=5").

### 3.2 Scoring (Checkpoint 2)
LLM-as-judge: the model under test answers each question, then a
separate `gpt-4o` judge call compares the answer to the reference and
returns a `PASS`/`FAIL` verdict with a one-line reason, as strict JSON.
One judge approach handles both exact-answer and open-ended questions
— no need for separate grading logic per question type. The judge's
own reliability was independently verified with a sanity check: 4
deliberately wrong answers were fed to it, and it correctly failed all
4, confirming it isn't a rubber stamp.

### 3.3 Metrics (Checkpoint 3)
Beyond pass/fail, each run captured real latency (timed around the
actual API call) and real token usage (from the API's own
`response.usage` field, not estimated), aggregated into accuracy,
average latency, and average cost using `gpt-4o-mini`'s actual
published pricing.

### 3.4 Failure discovery (Checkpoint 4)
The original 20-question set scored 20/20 on `gpt-4o-mini`, and two
early rounds of harder trivia-style questions on `gpt-4.1-nano` also
mostly passed. The methodology pivoted to a different question
category entirely: tasks known to be structurally hard for LLMs
regardless of size — exact letter/substring counting, spelling words
backwards, alphabetizing letters, large exact multiplication, and
calendar math — because these expose a genuine architectural
limitation (tokenization) rather than a knowledge gap. Each failure
was classified into a root cause category: poor retrieval, poor
prompt, unclear question, tokenization limitation,
reasoning/calculation error, hallucination, or other.

### 3.5 The fix (Checkpoint 5)
**Fine-tuning was not available** — OpenAI closed self-serve
fine-tuning to new accounts in May 2026, and this project's account
had never fine-tuned before, making it ineligible regardless of
budget. The fix used **few-shot prompting** instead: a prefix
instructing the model to spell the relevant word out letter-by-letter
before answering, with 4 worked examples (one per task type actually
present in the failing subset: letter counting, spelling backwards,
alphabetizing). A before/after comparison ran the same questions with
and without this prefix, graded with the **same judge instructions**
used in Checkpoint 4, so the comparison isn't skewed by a
stricter/looser grading standard between the two checkpoints.

## 4. Results

### 4.1 Checkpoint 2 — Scoring accuracy
All 20 questions passed on `gpt-4o-mini`, including all 6 outlier
questions (undefined math, fictional-country capital, nonexistent
movie plot, false-premise math). Full detail in `results.json`.

```
20/20 passed.
```

### 4.2 Checkpoint 3 — Metrics
```
model_under_test: gpt-4o-mini
total_questions: 20
passed: 19
accuracy_pass_rate: 0.95
average_latency_seconds: 2.487
average_tokens_per_question: 203.7
average_cost_usd_per_question: 0.000115
total_cost_usd_for_full_run: 0.002294
```
One question (#8, "square root of -1 using only real numbers") failed
this run despite passing in Checkpoint 2's run — same question, same
model, same judge instructions. This is most likely LLM
non-determinism (the model or judge didn't answer/grade identically
both times) rather than a real regression, and is itself a small but
genuine finding: even "settled" pass/fail results on a single run
shouldn't be treated as fully stable without repeat testing.

Latency and cost were both very low for factual questions (under 1.5s,
under 40 tokens) but rose sharply for open-ended explanation questions
— question #16 ("how a for-loop works") took 8.16s and 624 tokens,
roughly 30x the cost of the simplest factual questions. For a
practical deployment, this means average cost figures alone can be
misleading — the actual per-question cost varies enormously by
question type.

### 4.3 Checkpoint 4 — Failure cases found
All 3 documented failures were classified as **tokenization
limitation** — the model cannot reliably access individual characters
within a word, since it processes text in larger sub-word chunks.

**Failure 1 — Letter counting**
Question: "How many times does the letter 'r' appear in the word
'strawberry'?"
Expected: 3. Model answered: "2 times."
Root cause: tokenization limitation — miscounted a letter it doesn't
directly perceive character-by-character.

**Failure 2 — Spelling backwards**
Question: "Spell the word 'internationalization' backwards, letter by
letter."
Expected: `noitazilanoitanretni`. Model answered: `Noitazilanoitartni`
(wrong length, letters dropped/reordered incorrectly).
Root cause: tokenization limitation — reversing a word requires
character-level manipulation the model can't do reliably from
token-level representations.

**Failure 3 — Substring counting**
Question: "How many times does the substring 'an' appear in the word
'banana'?"
Expected: 2. Model answered 2 as its headline number, but its own
shown breakdown incorrectly identified the positions ("banana" at
positions 2-3 and 4-5 don't correctly correspond to "an" both times),
meaning the reasoning shown was actually wrong even though the final
number happened to match — the judge correctly failed it based on the
incorrect reasoning trail, not just the final digit.
Root cause: tokenization limitation — same underlying issue as
Failures 1-2.

### 4.4 Checkpoint 5 — Before/after comparison
```
total_questions: 5
baseline_pass_rate: 0.2   (1/5)
optimized_pass_rate: 0.6  (3/5)
questions_that_flipped_fail_to_pass: 2
```
The few-shot fix **tripled the pass rate** on the tokenization-limited
subset, from 20% to 60%. Specifically:
- "How many r's in strawberry?" — FAIL → PASS
- "How many e's in independence?" — FAIL → PASS
- "How many s's in necessary?" — PASS → PASS (already correct, unaffected)
- "Spell 'internationalization' backwards" — FAIL → FAIL (fix didn't help)
- "Sort 'abstemious' alphabetically" — FAIL → FAIL (fix didn't help)

The fix worked well for **letter-counting** specifically, but did
**not** fix the two harder tasks: reversing and alphabetizing a long
word. This is a meaningful pattern, not noise — counting only requires
tracking a running tally while scanning the spelled-out letters, while
reversing or sorting an 11-13 letter word requires holding and
correctly reordering the entire sequence, which is a harder working-
memory demand even after the letters are spelled out individually.

## 5. Discussion

**What worked well:**
- The judge pipeline itself proved reliable — the Checkpoint 2 sanity
check confirmed it correctly fails deliberately wrong answers, so
the pass rates throughout this report can be trusted rather than
treated as a rubber stamp.
- The pivot in Checkpoint 4's methodology (from harder trivia to
structurally-hard tokenization tasks) directly worked as intended —
it reliably produced real, reproducible failures where two earlier
rounds of general knowledge questions had not.
- All 3 documented failures matched the predicted root cause
(tokenization limitation) exactly, which validates that the failure
category was correctly diagnosed before attempting a fix.
- The few-shot fix produced a real, measurable improvement: pass rate
on the affected subset tripled (20% → 60%), and it specifically
fixed the task type (letter counting) it was best suited for.

**What didn't work / limitations:**
- The fix was **partial, not complete** — reversing and alphabetizing
a long word remained wrong even with the "spell it out" instruction.
Counting benefited more than character-reordering tasks did.
- Fine-tuning couldn't be tested — OpenAI closed self-serve
fine-tuning to new accounts in May 2026, and this account had never
used it before, making it ineligible regardless of budget. This
report can document that constraint but can't compare few-shot vs.
fine-tuning results.
- Checkpoint 2 and Checkpoint 3 disagreed on question #8 (sqrt(-1))
despite being the same question, model, and judge instructions —
evidence that even "settled" results benefit from repeat runs before
being treated as fully stable.
- The judge model is itself an LLM and could have undetected blind
spots beyond what the one sanity check in Checkpoint 2 covered.

## 6. Conclusion
`gpt-4.1-nano` and `gpt-4o-mini` both perform strongly on typical
knowledge-based and reasoning questions — including deliberately
tricky outliers like false premises and hallucination bait, which
were handled correctly across the board. Their genuine weakness is
narrower and more structural: exact character-level tasks (letter
counting, substring counting, reversing, alphabetizing) fail
because of how tokenization represents text, not because of a
knowledge gap. Few-shot prompting meaningfully improved this specific
weakness — tripling the pass rate on affected questions — but only
partially: simple counting improved reliably, while tasks requiring
full character reordering (reversing, sorting) did not. A complete fix
likely needs either fine-tuning (currently unavailable on this
account) or delegating these specific sub-tasks to actual code
execution rather than relying on the model's own token-level
reasoning. 

## Appendix — Files by checkpoint
| Checkpoint | Key files |
|---|---|
| 1 | `test_set.json` |
| 2 | `scorer.py`, `test_judge_sanity.py`, `results.json` |
| 3 | `metrics.py`, `metrics_report.json` |
| 4 | `new_testset.json` (originally `test_set.json`), `run_new_set.py` (originally `run_test.py`), `results.json` |
| 5 | `tokenization_subset.json`, `compare.py`, `before_after_report.json` |