"""Typed contracts for every value that moves through the retrieval/answer
pipeline. Same discipline as outreach-iq and ClaimSight: no bare strings or
dicts crossing a module boundary, and every agent-produced output extends
`AgentOutput` so confidence/evidence/warnings are always available for the
review logic in `review.py`.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    EMPLOYEE = "employee"
    HR = "hr"
    IT = "it"
    LEGAL = "legal"
    FINANCE = "finance"


class AgentOutput(BaseModel):
    """Common contract every agent-produced output satisfies."""

    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    reasoning_summary: str
    warnings: list[str] = Field(default_factory=list)


# --- Documents and chunks ------------------------------------------------------


class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    doc_title: str
    text: str
    visible_to: list[Role]


class EmbeddedChunk(BaseModel):
    chunk: DocumentChunk
    embedding: list[float]


class ScoredChunk(BaseModel):
    chunk: DocumentChunk
    score: float


# --- Pipeline stages -------------------------------------------------------------


class RetrievalResult(AgentOutput):
    query: str
    role: Role
    chunks: list[ScoredChunk]
    attempt: int
    sufficient: bool


class Citation(BaseModel):
    doc_id: str
    doc_title: str
    chunk_id: str


class AnswerDraft(AgentOutput):
    answer_text: str
    citations: list[Citation]


class GroundednessCheck(AgentOutput):
    is_grounded: bool
    unsupported_claims: list[str] = Field(default_factory=list)


# --- Top-level result ------------------------------------------------------------


class QueryResult(BaseModel):
    """The full, typed record of one question asked by one role."""

    query_id: str
    question: str
    role: Role
    started_at: datetime

    retrieval: RetrievalResult | None = None
    draft: AnswerDraft | None = None
    groundedness: GroundednessCheck | None = None

    final_answer: str = ""
    answered: bool = False

    requires_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)

    errors: list[str] = Field(default_factory=list)
    completed_at: datetime | None = None
