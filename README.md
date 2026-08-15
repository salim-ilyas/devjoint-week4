# Week 4 — AI Output Evaluation & Small Model Adaptation

Evaluates `gpt-4.1-nano` (small model) with an LLM-as-judge pipeline,
tracks accuracy/latency/cost, documents real failure cases with root
cause analysis, and fixes one failure category via few-shot prompting
— with before/after proof.

## Folder structure
```
checkpoint-1/   Test set (20 Q&A pairs, incl. outliers)
checkpoint-2/   LLM-as-judge automated scoring
checkpoint-3/   Monitored metrics (accuracy, latency, token cost)
checkpoint-4/   Documented failure cases + root cause analysis
checkpoint-5/   Few-shot fix for a failure category + before/after
checkpoint-6/   Written report tying it all together
```
Each folder has its own README with that checkpoint's specifics.

## Setup (once)
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt   # inside whichever checkpoint you're running
cp .env              # then paste your real OPENAI_API_KEY
```

## API note
Started on Gemini, switched to OpenAI after hitting a Gemini quota
error (Checkpoint 2 onward). Model under test also changed partway
through: `gpt-4o-mini` (Checkpoints 2-3, scored 20/20 — too clean to
analyze failures from) → `gpt-4.1-nano` (Checkpoints 4-5, chosen
specifically to surface real weaknesses). Judge model throughout:
`gpt-4o`.

## Headline results
- Checkpoint 2: 20/20 passed, including all 6 outlier questions
- Checkpoint 3: 95% pass rate, ~2.5s avg latency, ~$0.0001/question
- Checkpoint 4: 3 documented failures, all root-caused to
**tokenization limitation** (model can't reliably see individual
letters in a word)
- Checkpoint 5: few-shot fix **tripled** the pass rate on affected
questions (20% → 60%) — full fix for letter-counting, partial for
reversing/sorting tasks
- Fine-tuning was ruled out: OpenAI closed self-serve fine-tuning to
new accounts in May 2026

Full methodology and results: `checkpoint-6/report.md`.