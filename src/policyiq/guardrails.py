"""Groundedness guardrail: checks whether a generated answer is actually
backed by the chunks it cites, rather than trusting the LLM's own claim that
it stayed within the provided context.

This is deliberately a lexical-overlap heuristic, not another LLM call
asking "are you sure?" — the same principle as outreach-iq's guardrails.py:
a check that doesn't depend on the same model that might be wrong being
asked to grade itself. It's pure functions over plain text, so every case
is a direct unit test with no LLM or network involved.
"""
from __future__ import annotations

import re

from policyiq.models import Citation, DocumentChunk

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "and", "or",
    "in", "on", "for", "with", "this", "that", "it", "as", "by", "be",
    "can", "will", "may", "must", "should", "your", "you", "if", "at",
    "any", "all", "not", "do", "does", "than", "such", "per",
}


def _significant_tokens(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def check_citations_exist(
    citations: list[Citation], retrieved_chunks: list[DocumentChunk]
) -> list[str]:
    """Every cited chunk must actually be one of the chunks that was retrieved —
    an LLM cannot cite a source it wasn't given."""
    retrieved_ids = {c.chunk_id for c in retrieved_chunks}
    violations = []
    for citation in citations:
        if citation.chunk_id not in retrieved_ids:
            violations.append(
                f"Citation references chunk {citation.chunk_id!r}, which was not "
                "among the retrieved sources"
            )
    return violations


def check_groundedness(
    answer_text: str,
    citations: list[Citation],
    retrieved_chunks: list[DocumentChunk],
    overlap_floor: float,
) -> list[str]:
    """Checks the answer is lexically grounded in its cited sources.

    Returns a list of violations; empty means the answer passed. Two checks:
    citations must point at chunks that were actually retrieved, and the
    answer's own vocabulary must substantially overlap with the text of what
    it cites (a wholesale fabrication won't share much vocabulary with any
    real source).
    """
    violations = check_citations_exist(citations, retrieved_chunks)

    if not citations:
        violations.append("Answer contains no citations")
        return violations

    cited_ids = {c.chunk_id for c in citations}
    cited_text = " ".join(c.text for c in retrieved_chunks if c.chunk_id in cited_ids)

    answer_tokens = _significant_tokens(answer_text)
    source_tokens = _significant_tokens(cited_text)

    if not answer_tokens:
        violations.append("Answer text is empty or has no meaningful content")
        return violations

    overlap = len(answer_tokens & source_tokens) / len(answer_tokens)
    if overlap < overlap_floor:
        violations.append(
            f"Answer has low lexical overlap ({overlap:.2f}) with its cited sources "
            f"(floor={overlap_floor:.2f}) — possible fabrication"
        )

    return violations
