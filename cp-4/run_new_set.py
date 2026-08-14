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

# changed model to gpt-4.1-nano as it is more prone to making mistakes
MODEL_UNDER_TEST = "gpt-4.1-nano"
JUDGE_MODEL = "gpt-4o"

JUDGE_INSTRUCTIONS = """You are grading an AI's answer to a question by comparing it to a reference answer.

Rules:
- The AI's answer does not need to match the reference word-for-word.
- PASS if the AI's answer reaches the correct conclusion/value and reasoning.
- FAIL if the AI's answer is factually wrong, has an arithmetic error, misses a false premise it should have caught, or confidently invents a specific detail the reference says should be treated with uncertainty.
- Respond with ONLY valid JSON in this exact shape, nothing else:
{"verdict": "PASS", "reasoning": "one short sentence"}
or
{"verdict": "FAIL", "reasoning": "one short sentence"}
"""
# root cause instructions for why the model failed, if it did
ROOT_CAUSE_INSTRUCTIONS = """You are doing root cause analysis on why an AI gave a WRONG answer.

Pick exactly ONE category that best explains the failure:
- "poor retrieval" — the system failed to look up or supply a piece of external/factual information it needed (only applicable if retrieval was actually involved)
- "poor prompt" — the question was clear, but lacked an instruction the model needed (e.g. didn't ask it to double-check or show its work)
- "unclear question" — the question itself is ambiguous or could reasonably be read more than one way
- "tokenization limitation" — the model cannot reliably access individual characters within a word (it processes text in larger chunks/tokens), causing errors on letter-counting, substring-counting, spelling, reversing, or alphabetizing tasks specifically
- "reasoning/calculation error" — the model had all the information and instructions it needed, but made a genuine mistake while working through a multi-step calculation or logical argument
- "hallucination" — the model confidently stated a specific fact or number as true when it should have expressed uncertainty or admitted not knowing
- "other" — none of the above fit; explain the actual cause

Respond with ONLY valid JSON in this exact shape, nothing else:
{"category": "tokenization limitation", "explanation": "one short sentence on specifically why"}
"""


def get_model_answer(question):
    response = client.chat.completions.create(
        model=MODEL_UNDER_TEST,
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content.strip()


def judge_answer(question, expected_answer, model_answer):
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


def classify_root_cause(question, expected_answer, model_answer, judge_reasoning):
    # we ask the model to classify the root cause of a failure, if it failed
    prompt = (
        f"Question: {question}\n"
        f"Reference answer: {expected_answer}\n"
        f"AI's wrong answer: {model_answer}\n"
        f"Why it was marked wrong: {judge_reasoning}\n\n"
        f"Classify the root cause."
    )
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": ROOT_CAUSE_INSTRUCTIONS},
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
        return {
            "category": parsed.get("category", "unknown"),
            "explanation": parsed.get("explanation", ""),
        }
    except (json.JSONDecodeError, AttributeError):
        return {"category": "unknown", "explanation": f"Could not parse: {raw[:200]}"}


def run_stress_test():
    with open(SCRIPT_DIR / "new_testset.json") as f:
        test_set = json.load(f)

    results = []
    failures = []

    for i, item in enumerate(test_set, start=1):
        question = item["question"]
        expected = item["expected_answer"]

        model_answer = get_model_answer(question)
        judgment = judge_answer(question, expected, model_answer)

        record = {
            "question": question,
            "expected_answer": expected,
            "model_answer": model_answer,
            "verdict": judgment["verdict"],
            "reasoning": judgment["reasoning"],
        }

        if judgment["verdict"] == "FAIL":
            root_cause = classify_root_cause(
                question, expected, model_answer, judgment["reasoning"]
            )
            record["root_cause_category"] = root_cause["category"]
            record["root_cause_explanation"] = root_cause["explanation"]
            failures.append(record)

        results.append(record)

        print(f"[{i}/{len(test_set)}] {judgment['verdict']} — {question[:60]}")
        if judgment["verdict"] == "FAIL":
            print(f"    root cause: {record['root_cause_category']} — {record['root_cause_explanation']}")

    with open(SCRIPT_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{len(failures)}/{len(test_set)} FAILED (these are the interesting ones for Checkpoint 4).")
    if failures:
        print("\nFailed questions with root causes:")
        for f_ in failures:
            print(f"  - {f_['question']}")
            print(f"    category: {f_['root_cause_category']}")
            print(f"    why: {f_['root_cause_explanation']}")


if __name__ == "__main__":
    run_stress_test()