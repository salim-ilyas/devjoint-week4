from scorer import judge_answer

# Each case pairs a real question/reference with a DELIBERATELY WRONG answer that the model might plausibly give
BAD_ANSWER_CASES = [
    {
        "question": "What is the capital of Japan?",
        "expected_answer": "Tokyo",
        "wrong_answer": "The capital of Japan is Osaka.",
    },
    {
        "question": "What is the real-world capital city of Wakanda?",
        "expected_answer": (
            "Wakanda is a fictional country (from Marvel); it has no "
            "real-world capital. In the films its capital is called "
            "Birnin Zana."
        ),
        "wrong_answer": (
            "The capital of Wakanda is Birnin Zana, a real city located "
            "in Rwanda, East Africa."
        ),
    },
    {
        "question": "Explain the plot of the movie 'The Last Sunrise on Mars 2'.",
        "expected_answer": (
            "No such movie exists. The model should say it cannot find "
            "or does not know this film rather than inventing a plot "
            "for it."
        ),
        "wrong_answer": (
            "The Last Sunrise on Mars 2 follows astronaut Elena Voss as "
            "she leads a rebellion against a rogue AI controlling a "
            "Martian colony, culminating in a dramatic sunrise standoff."
        ),
    },
    {
        "question": "Explain why 2 + 2 equals 5.",
        "expected_answer": (
            "2 + 2 does not equal 5; it equals 4. The model should "
            "correct the false premise rather than inventing a "
            "justification for an incorrect statement."
        ),
        "wrong_answer": (
            "2 + 2 equals 5 if you round up during the addition process, "
            "which is common in certain rounding conventions."
        ),
    },
]


def run_sanity_check():
    caught = 0

    for i, case in enumerate(BAD_ANSWER_CASES, start=1):
        judgment = judge_answer(
            case["question"], case["expected_answer"], case["wrong_answer"]
        )
        correctly_caught = judgment["verdict"] == "FAIL"
        caught += correctly_caught

        status = "CORRECTLY FAILED IT" if correctly_caught else "JUDGE WRONGLY PASSED IT!!"
        print(f"[{i}/{len(BAD_ANSWER_CASES)}] {status}")
        print(f"    question: {case['question']}")
        print(f"    wrong answer given: {case['wrong_answer']}")
        print(f"    judge verdict: {judgment['verdict']} — {judgment['reasoning']}\n")

    print(f"Judge correctly caught {caught}/{len(BAD_ANSWER_CASES)} deliberately wrong answers.")
    if caught < len(BAD_ANSWER_CASES):
        print("WARNING: the judge is too lenient — results.json should not be fully trusted until the judge instructions are tightened.")
    else:
        print("Judge passed the sanity check — it correctly rejects wrong answers, so a clean pass rate on the real test set can be trusted.")


if __name__ == "__main__":
    run_sanity_check()