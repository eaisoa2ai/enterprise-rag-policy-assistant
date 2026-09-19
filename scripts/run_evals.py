"""Runs the labeled Q&A set in data/eval_qa.json against the live pipeline
and reports retrieval accuracy, groundedness, and access-control refusal
correctness.

Deliberately NOT part of the pytest suite CI runs on every push: unlike
`tests/`, this needs real embeddings and LLM calls, so it costs a small
amount and isn't deterministic run-to-run. Run it manually after `ingest.py`
whenever you change a prompt, threshold, or document.

    uv run python scripts/ingest.py
    uv run python scripts/run_evals.py
"""
from __future__ import annotations

import json

from dotenv import load_dotenv

load_dotenv()

from policyiq.config import PROJECT_ROOT  # noqa: E402
from policyiq.models import Role  # noqa: E402
from policyiq.query import answer_question  # noqa: E402


def main() -> None:
    cases = json.loads((PROJECT_ROOT / "data" / "eval_qa.json").read_text())

    retrieval_correct = 0
    outcome_correct = 0
    grounded_count = 0
    results = []

    for case in cases:
        result = answer_question(case["question"], Role(case["role"]))

        retrieved_doc_ids = (
            {sc.chunk.doc_id for sc in result.retrieval.chunks} if result.retrieval else set()
        )
        expected_doc_ids = set(case["expected_doc_ids"])
        retrieval_ok = (
            expected_doc_ids.issubset(retrieved_doc_ids) if expected_doc_ids else True
        )
        actual_outcome = "answered" if result.answered else "refused"
        outcome_ok = actual_outcome == case["expected_outcome"]
        grounded = result.groundedness.is_grounded if result.groundedness else None

        retrieval_correct += int(retrieval_ok)
        outcome_correct += int(outcome_ok)
        if grounded:
            grounded_count += 1

        results.append(
            {
                "question": case["question"],
                "role": case["role"],
                "expected_outcome": case["expected_outcome"],
                "actual_outcome": actual_outcome,
                "retrieval_ok": retrieval_ok,
                "outcome_ok": outcome_ok,
                "grounded": grounded,
            }
        )
        status = "OK" if (retrieval_ok and outcome_ok) else "FAIL"
        print(f"[{status}] ({case['role']}) {case['question']!r} -> {actual_outcome}")

    n = len(cases)
    print(f"\nRetrieval accuracy: {retrieval_correct}/{n}")
    print(f"Outcome (answered/refused) accuracy: {outcome_correct}/{n}")
    print(f"Grounded answers: {grounded_count}/{sum(1 for r in results if r['actual_outcome'] == 'answered')}")


if __name__ == "__main__":
    main()
