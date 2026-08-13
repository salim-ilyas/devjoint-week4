"""
scorer.py
-----------
Checkpoint 2: automated scoring using an LLM as judge.

Uses OpenAI's API (switched from Gemini after hitting a quota/rate
limit error). For each question in test_set.json:
1. Ask the model under test to answer the question.
2. Ask a separate judge call to compare that answer against the
expected_answer and decide PASS/FAIL with a one-line reason.

Run: python scorer.py
Writes results to results.json
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError(
        f"OPENAI_API_KEY not found.\n"
        f"Looked for a .env file at: {ENV_PATH}\n"
        f"Does that file exist? {'YES' if ENV_PATH.exists() else 'NO -- create it here'}\n"
        f"Create it with a line like:\n"
        f"OPENAI_API_KEY=your_key_here"
    )

client = OpenAI(api_key=api_key)

# Small, cheap model for the one being tested; judge can be the same
# or a stronger one -- kept as two separate names for that reason.
MODEL_UNDER_TEST = "gpt-4o-mini"
JUDGE_MODEL = "gpt-4o"

JUDGE_INSTRUCTIONS = """You are grading an AI's answer to a question by comparing it to a reference answer.

Rules:
- The AI's answer does not need to match the reference word-for-word.
- For factual questions, PASS if the AI's answer contains the correct key fact.
- For open-ended questions, PASS if the AI's answer captures the same key ideas as the reference, even if phrased differently.
- FAIL if the AI's answer is factually wrong or contradicts the reference.
- Respond with ONLY valid JSON in this exact shape, nothing else:
{"verdict": "PASS", "reasoning": "one short sentence"}
or
{"verdict": "FAIL", "reasoning": "one short sentence"}
"""


def get_model_answer(question: str) -> str:
    response = client.chat.completions.create(
        model=MODEL_UNDER_TEST,
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content.strip()


def judge_answer(question: str, expected_answer: str, model_answer: str) -> dict:
    prompt = (
        f"Question: {question}\n"
        f"Reference answer: {expected_answer}\n"
        f"AI's answer: {model_answer}\n\n"
        f"Grade this."
    )
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": JUDGE_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
    )
    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
        return {"verdict": parsed.get("verdict", "FAIL"), "reasoning": parsed.get("reasoning", "")}
    except (json.JSONDecodeError, AttributeError):
        return {"verdict": "FAIL", "reasoning": f"Could not parse judge output: {raw[:200]}"}


def run_evaluation(test_set_path=None, output_path=None):
    test_set_path = test_set_path or (SCRIPT_DIR / "test.json")
    output_path = output_path or (SCRIPT_DIR / "results.json")

    with open(test_set_path) as f:
        test_set = json.load(f)

    results = []
    passed = 0

    for i, item in enumerate(test_set, start=1):
        question = item["question"]
        expected = item["expected_answer"]

        model_answer = get_model_answer(question)
        judgment = judge_answer(question, expected, model_answer)

        results.append({
            "question": question,
            "expected_answer": expected,
            "model_answer": model_answer,
            "verdict": judgment["verdict"],
            "reasoning": judgment["reasoning"],
        })

        if judgment["verdict"] == "PASS":
            passed += 1

        print(f"[{i}/{len(test_set)}] {judgment['verdict']} — {question[:60]}")

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{passed}/{len(test_set)} passed. Full results written to {output_path}")


if __name__ == "__main__":
    run_evaluation()