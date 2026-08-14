# Checkpoint 5 — Fix a Failure Category, With Before/After Proof

## Goal
Take one failure category identified in Checkpoint 4 and actually fix
it — via fine-tuning or few-shot prompting — then prove the fix
worked with a before/after comparison.

## Approach chosen: few-shot prompting, not fine-tuning
Fine-tuning requires uploading a training dataset, running a training
job, waiting for it to complete, and costs money per run — a heavy
option for fixing one specific behavior. At the same time, Open AI does
not have fine-tuning services for new users since May, 2026. Few-shot 
prompting achieves the same goal by showing the model 2 worked 
examples directly in the prompt, with no training step and no 
extra cost beyond normal API calls.

## Category being fixed: tokenization limitation
This was the most common failure category from Checkpoint 4 —
letter-counting, substring-counting, spelling backwards, and sorting
letters all failed because the model processes text in tokens
(sub-word chunks), not individual characters, so it can't directly
"see" letter-by-letter structure.

## The fix
`FEW_SHOT_PREFIX` in `compare.py` instructs the model to **spell the
relevant word out letter-by-letter, separated by hyphens, before
answering** — e.g. "s-t-r-a-w-b-e-r-r-y" — with **4 worked examples**,
one for each task type actually present in `tokenization_subset.json`:
letter counting, substring counting, spelling backwards, and
alphabetizing. An earlier draft only demonstrated counting tasks,
leaving the model to generalize the technique to reversing/sorting
questions on its own with no example to follow — that gap is now
closed.

## What's here
- **`tokenization_subset.json`** — exactly the 5 questions from
  Checkpoint 4's actual `new_testset.json` that fall into the
  tokenization-limitation category (letter/substring counting,
  spelling backwards, sorting letters). This was rebuilt to match your
  real Checkpoint 4 test set exactly — an earlier draft included 2
  extra questions that weren't actually in `new_testset.json`, which
  would have made this checkpoint "fix" failures that were never
  documented.
- **`compare.py`** — runs every question TWICE against
  `gpt-4.1-nano`:
  - **baseline**: the plain question (identical to how Checkpoint 4
    tested it)
  - **optimized**: the question with `FEW_SHOT_PREFIX` prepended
  Both answers are judged using `JUDGE_INSTRUCTIONS` copied
  **verbatim** from Checkpoint 4's `run_new_set.py` — using the same
  grading standard in both checkpoints is what makes the before/after
  comparison valid. A stricter or looser judge here would risk making
  any "improvement" an artifact of different grading rather than a
  real fix.

## Verification already done
Since I can't call the OpenAI API myself, I verified what I could
without it, using mocked responses:
- confirmed `get_baseline_answer()` sends the plain question
  unmodified, while `get_optimized_answer()` genuinely includes the
  few-shot prefix — this matters because a bug here would silently
  make baseline and optimized identical, invalidating the whole
  comparison
- confirmed the judge correctly parses PASS/FAIL JSON

What's not yet verified: how much the fix actually helps in practice.
That requires your API key.
