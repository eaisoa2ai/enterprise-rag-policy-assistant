"""Review is pure logic, so every combination of flags is tested directly
against `evaluate_review` without touching LangGraph, embeddings, or an LLM.
"""
from datetime import UTC, datetime

import pytest

from policyiq.config import Thresholds
from policyiq.models import GroundednessCheck, QueryResult, RetrievalResult, Role
from policyiq.review import evaluate_review

THRESHOLDS = Thresholds(confidence_floor=0.6)


def _base_result() -> QueryResult:
    return QueryResult(
        query_id="q1",
        question="How many PTO days do I get?",
        role=Role.EMPLOYEE,
        started_at=datetime.now(UTC),
    )


def test_happy_path_does_not_require_review():
    result = _base_result()
    result.retrieval = RetrievalResult(
        confidence=0.9, reasoning_summary="ok", query="q", role=Role.EMPLOYEE,
        chunks=[], attempt=1, sufficient=True,
    )
    result.groundedness = GroundednessCheck(confidence=0.9, reasoning_summary="ok", is_grounded=True)
    result.answered = True

    result = evaluate_review(result, THRESHOLDS)

    assert result.requires_review is False
    assert result.review_reasons == []


@pytest.mark.parametrize(
    "confidence,expect_flagged",
    [(0.60, False), (0.59, True), (0.0, True), (1.0, False)],
)
def test_confidence_floor_boundary(confidence, expect_flagged):
    result = _base_result()
    result.retrieval = RetrievalResult(
        confidence=confidence, reasoning_summary="ok", query="q", role=Role.EMPLOYEE,
        chunks=[], attempt=1, sufficient=True,
    )
    result.answered = True

    result = evaluate_review(result, THRESHOLDS)

    assert result.requires_review is expect_flagged


def test_insufficient_retrieval_requires_review():
    result = _base_result()
    result.retrieval = RetrievalResult(
        confidence=0.9, reasoning_summary="ok", query="q", role=Role.EMPLOYEE,
        chunks=[], attempt=2, sufficient=False,
    )
    result.answered = False

    result = evaluate_review(result, THRESHOLDS)

    assert result.requires_review is True
    assert any("relevant content" in r for r in result.review_reasons)


def test_ungrounded_answer_requires_review():
    result = _base_result()
    result.retrieval = RetrievalResult(
        confidence=0.9, reasoning_summary="ok", query="q", role=Role.EMPLOYEE,
        chunks=[], attempt=1, sufficient=True,
    )
    result.groundedness = GroundednessCheck(
        confidence=0.3, reasoning_summary="failed", is_grounded=False,
        unsupported_claims=["fabricated claim"],
    )
    result.answered = False

    result = evaluate_review(result, THRESHOLDS)

    assert result.requires_review is True
    assert any("groundedness" in r.lower() for r in result.review_reasons)


def test_declined_answer_requires_review():
    result = _base_result()
    result.answered = False

    result = evaluate_review(result, THRESHOLDS)

    assert result.requires_review is True
    assert any("declined" in r.lower() for r in result.review_reasons)


def test_recorded_errors_require_review():
    result = _base_result()
    result.errors = ["Vector store is empty."]

    result = evaluate_review(result, THRESHOLDS)

    assert result.requires_review is True
    assert any("error(s) recorded" in r for r in result.review_reasons)
