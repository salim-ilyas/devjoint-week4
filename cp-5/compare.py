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

# few-shot prompt to help the model avoid tokenization errors on letter-counting, substring-counting, spelling, reversing, or alphabetizing tasks
FEW_SHOT_PREFIX = """When answering a question about counting letters, counting a substring, spelling a word backwards, or sorting letters, ALWAYS first spell out the relevant word letter by letter separated by hyphens. Then work from that spelled-out version to get your final answer. This helps you track each letter individually.

Example 1 (counting a letter):
Q: How many times does the letter 'e' appear in the word 'elephant'?
A: Spelling it out: e-l-e-p-h-a-n-t
Checking each letter for 'e': position 1 is e (count=1), position 3 is e (count=2). No other e's.
Final answer: 2

Example 2 (counting a substring):
Q: How many times does the substring 'an' appear in the word 'banana'?
A: Spelling it out: b-a-n-a-n-a
Looking for 'an': positions 2-3 are "an" (count=1), positions 4-5 are "an" (count=2).
Final answer: 2

Example 3 (spelling backwards):
Q: Spell the word 'garden' backwards, letter by letter.
A: Spelling it out: g-a-r-d-e-n
Reversing the order of these letters: n-e-d-r-a-g
Final answer: nedrag

Example 4 (sorting letters alphabetically):
Q: Sort the letters of the word 'plant' alphabetically and write out the result.
A: Spelling it out: p-l-a-n-t
Sorting these letters alphabetically: a, l, n, p, t
Final answer: alnpt

Now answer this question using the same approach:
"""


def get_baseline_answer(question):
    response = client.chat.completions.create(
        model=MODEL_UNDER_TEST,
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content.strip()


def get_optimized_answer(question):
    response = client.chat.completions.create(
        model=MODEL_UNDER_TEST,
        messages=[{"role": "user", "content": FEW_SHOT_PREFIX + question}],
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


def run_comparison():
    with open(SCRIPT_DIR / "tokenization_subset.json") as f:
        test_set = json.load(f)

    results = []
    baseline_passed = 0
    optimized_passed = 0

    for i, item in enumerate(test_set, start=1):
        question = item["question"]
        expected = item["expected_answer"]

        baseline_answer = get_baseline_answer(question)
        baseline_judgment = judge_answer(question, expected, baseline_answer)

        optimized_answer = get_optimized_answer(question)
        optimized_judgment = judge_answer(question, expected, optimized_answer)

        baseline_passed += baseline_judgment["verdict"] == "PASS"
        optimized_passed += optimized_judgment["verdict"] == "PASS"

        record = {
            "question": question,
            "expected_answer": expected,
            "baseline_answer": baseline_answer,
            "baseline_verdict": baseline_judgment["verdict"],
            "optimized_answer": optimized_answer,
            "optimized_verdict": optimized_judgment["verdict"],
            "improved": (
                baseline_judgment["verdict"] == "FAIL"
                and optimized_judgment["verdict"] == "PASS"
            ),
        }
        results.append(record)

        print(
            f"[{i}/{len(test_set)}] baseline={baseline_judgment['verdict']} "
            f"-> optimized={optimized_judgment['verdict']} | {question}"
        )

    n = len(test_set)
    summary = {
        "total_questions": n,
        "baseline_pass_rate": round(baseline_passed / n, 3),
        "optimized_pass_rate": round(optimized_passed / n, 3),
        "baseline_passed": baseline_passed,
        "optimized_passed": optimized_passed,
        "questions_that_flipped_fail_to_pass": sum(r["improved"] for r in results),
    }

    report = {"summary": summary, "per_question": results}
    with open(SCRIPT_DIR / "before_after_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n--- Summary ---")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print(f"\nFull report written to before_after_report.json")


if __name__ == "__main__":
    run_comparison()