"""Entry point: ask PolicyIQ a question as a given role.

    uv run python main.py --question "How many vacation days do I get?" --role employee
    uv run python main.py --question "What's the wire-transfer approval limit?" --role finance
"""
from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()

from policyiq.models import Role  # noqa: E402
from policyiq.query import answer_question  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask PolicyIQ a policy question.")
    parser.add_argument("--question", required=True)
    parser.add_argument("--role", required=True, choices=[r.value for r in Role])
    args = parser.parse_args()

    result = answer_question(args.question, Role(args.role))

    print(f"\nQ ({args.role}): {args.question}")
    print(f"A: {result.final_answer}")
    print(f"\nAnswered: {result.answered}")
    if result.draft:
        print(f"Citations: {[c.chunk_id for c in result.draft.citations]}")
    print(f"Requires review: {result.requires_review}")
    if result.review_reasons:
        print("Reasons:")
        for reason in result.review_reasons:
            print(f"  - {reason}")
    if result.errors:
        print(f"Errors: {result.errors}")

    print("\nFull result:")
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
