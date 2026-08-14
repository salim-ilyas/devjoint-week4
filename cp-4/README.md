# Checkpoint 4 — Failure Case Documentation

## Goal
Document at least 3 real failure cases with root cause analysis.

## API used
**OpenAI**, matching the switch made in Checkpoints 2-3 after hitting
a Gemini quota error.
- Model under test: `gpt-4.1-nano`
- Judge model: `gpt-4o`

## What's here
- **`new_testset.json`** — the 15 stress questions above. Every numeric/
  string reference answer (letter counts, multiplication, date math,
  the reversed word, word count) was computed and verified with
  actual Python code before being written into this file — not
  guessed or typed by hand.
- **`run_new_set.py`** — runs each question through `gpt-4.1-nano`, then
  a `gpt-4o` judge grades it PASS/FAIL with a one-line reason. The
  judge is explicitly instructed that for counting/math/spelling
  questions, the answer must be **exactly** correct — "close" doesn't
  pass.
- **`results.json`** — generated when you run the script; full detail
  per question.

## Verification already done (before you run it live)
Since I can't call the OpenAI API myself, I verified what I *could*
verify without it:
1. **All reference answers** were computed with actual code (see the
   `new_testset.json` note above), not hand-calculated.
2. **The script's logic was tested with mocked API responses** —
   confirmed `get_model_answer()` correctly extracts response text,
   `judge_answer()` correctly parses PASS/FAIL JSON, correctly strips
   markdown code fences some models wrap JSON in, and fails safe
   (defaults to FAIL, doesn't crash) on malformed judge output.

What's **not** yet verified: what `gpt-4.1-nano` actually answers when
you run this for real. That's the one part that requires your API key
and can't be tested from here.

## Setup & Run
```bash
pip install -r requirements.txt
cp .env.example .env
# paste your real OPENAI_API_KEY into .env
python run_new_set.py
```


**Root cause categories:**
- *poor retrieval* — the system failed to look up or supply a piece of external/factual information it needed (only applicable if retrieval was actually involved)
- *poor prompt* — the question was clear, but lacked an instruction the model needed (e.g. didn't ask it to double-check or show its work)
- *unclear question* — the question itself is ambiguous or could reasonably be read more than one way
- *tokenization limitation* — the model cannot reliably access individual characters within a word (it processes text in larger chunks/tokens), causing errors on letter-counting, substring-counting, spelling, reversing, or alphabetizing tasks specifically
- *reasoning/calculation error* — the model had all the information and instructions it needed, but made a genuine mistake while working through a multi-step calculation or logical argument
- *hallucination* — the model confidently stated a specific fact or number as true when it should have expressed uncertainty or admitted not knowing
- *other* — none of the above fit; explain the actual cause
