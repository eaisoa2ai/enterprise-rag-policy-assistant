"""Pure routing/review logic — no LLM calls, no I/O, fully unit-testable.
Same pattern as outreach-iq's routing.py: inspects a finished QueryResult
and decides whether a human should look at it before the answer is trusted.
"""
from __future__ import annotations

from policyiq.config import Thresholds
from policyiq.models import QueryResult


def evaluate_review(result: QueryResult, thresholds: Thresholds) -> QueryResult:
    reasons: list[str] = []

    for label, output in (
        ("retrieval", result.retrieval),
        ("answer draft", result.draft),
        ("groundedness check", result.groundedness),
    ):
        if output is not None and output.confidence < thresholds.confidence_floor:
            reasons.append(
                f"{label} confidence {output.confidence:.2f} below floor "
                f"{thresholds.confidence_floor:.2f}"
            )

    if result.retrieval is not None and not result.retrieval.sufficient:
        reasons.append("Retrieval did not find sufficiently relevant content")

    if result.groundedness is not None and not result.groundedness.is_grounded:
        reasons.append("Generated answer failed the groundedness check")

    if not result.answered:
        reasons.append("System declined to answer")

    if result.errors:
        reasons.append(f"{len(result.errors)} error(s) recorded during the query")

    result.review_reasons = reasons
    result.requires_review = bool(reasons)
    return result
