import os
import json
import time
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

MODEL_UNDER_TEST = "gpt-4o-mini"
JUDGE_MODEL = "gpt-4o"

PRICING_PER_1M_TOKENS = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}

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


def get_model_answer_with_metrics(question):
    # we measure latency and token usage for the model's answer to the question.
    start = time.time()
    response = client.chat.completions.create(
        model=MODEL_UNDER_TEST,
        messages=[{"role": "user", "content": question}],
    )
    latency = time.time() - start

    usage = response.usage
    return {
        "answer": response.choices[0].message.content.strip(),
        "latency_seconds": round(latency, 3),
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
    }


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


def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    rates = PRICING_PER_1M_TOKENS[model]
    input_cost = (prompt_tokens / 1000000) * rates["input"]
    output_cost = (completion_tokens / 1000000) * rates["output"]
    return input_cost + output_cost


def run_metrics_evaluation(test_set_path=None, output_path=None):
    test_set_path = test_set_path or (SCRIPT_DIR / "test.json")
    output_path = output_path or (SCRIPT_DIR / "metrics_report.json")

    with open(test_set_path) as f:
        test_set = json.load(f)

    per_question = []
    passed = 0
    total_latency = 0.0
    total_tokens = 0
    total_cost = 0.0

    for i, item in enumerate(test_set, start=1):
        question = item["question"]
        expected = item["expected_answer"]

        answer_data = get_model_answer_with_metrics(question)
        judgment = judge_answer(question, expected, answer_data["answer"])
        cost = estimate_cost(
            answer_data["prompt_tokens"], answer_data["completion_tokens"], MODEL_UNDER_TEST
        )

        record = {
            "question": question,
            "model_answer": answer_data["answer"],
            "verdict": judgment["verdict"],
            "reasoning": judgment["reasoning"],
            "latency_seconds": answer_data["latency_seconds"],
            "prompt_tokens": answer_data["prompt_tokens"],
            "completion_tokens": answer_data["completion_tokens"],
            "total_tokens": answer_data["total_tokens"],
            "estimated_cost_usd": round(cost, 6),
        }
        per_question.append(record)

        passed += judgment["verdict"] == "PASS"
        total_latency += answer_data["latency_seconds"]
        total_tokens += answer_data["total_tokens"]
        total_cost += cost

        print(
            f"[{i}/{len(test_set)}] {judgment['verdict']} | "
            f"{answer_data['latency_seconds']}s | "
            f"{answer_data['total_tokens']} tokens"
        )

    n = len(test_set)
    summary = {
        "model_under_test": MODEL_UNDER_TEST,
        "total_questions": n,
        "passed": passed,
        "accuracy_pass_rate": round(passed / n, 3),
        "average_latency_seconds": round(total_latency / n, 3),
        "average_tokens_per_question": round(total_tokens / n, 1),
        "average_cost_usd_per_question": round(total_cost / n, 6),
        "total_cost_usd_for_full_run": round(total_cost, 6),
    }

    report = {"summary": summary, "per_question": per_question}
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print("\n****Summary****")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print(f"\nFull report written to {output_path}")


if __name__ == "__main__":
    run_metrics_evaluation()