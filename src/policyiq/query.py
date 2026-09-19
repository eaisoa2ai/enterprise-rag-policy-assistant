"""Top-level entry point: answer one question for one role, apply review,
audit, and return the full typed result. Mirrors outreach-iq's campaign.py
structure — build the pipeline, run it, wrap raw output into typed models,
route for review, write the audit entry.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from opentelemetry.trace import Status, StatusCode

from policyiq.agent.graph import build_graph
from policyiq.audit import write_audit_entry
from policyiq.config import PROJECT_ROOT, settings
from policyiq.embeddings import OpenAIEmbeddingProvider
from policyiq.models import GroundednessCheck, QueryResult, RetrievalResult, Role
from policyiq.observability import get_tracer
from policyiq.review import evaluate_review
from policyiq.vectorstore import InMemoryVectorStore

tracer = get_tracer()


def _resolve_store_path() -> Path:
    path = Path(settings.vectorstore_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def answer_question(question: str, role: Role) -> QueryResult:
    query_id = f"query_{uuid.uuid4().hex[:12]}"
    started_at = datetime.now(UTC)
    result = QueryResult(query_id=query_id, question=question, role=role, started_at=started_at)

    with tracer.start_as_current_span("policyiq.query") as span:
        span.set_attribute("role", role.value)
        span.set_attribute("question", question)

        vector_store = InMemoryVectorStore.load(_resolve_store_path())

        if vector_store.is_empty():
            error = "Vector store is empty. Run `python scripts/ingest.py` first."
            result.errors.append(error)
            span.set_status(Status(StatusCode.ERROR, description=error))
        else:
            try:
                embedder = OpenAIEmbeddingProvider()
                graph = build_graph(vector_store, embedder, settings.thresholds)
                raw = graph.invoke({"question": question, "role": role.value})

                chunks = raw.get("chunks", [])
                result.retrieval = RetrievalResult(
                    confidence=raw.get("retrieval_confidence", 0.0),
                    evidence=[f"{sc.chunk.doc_title} ({sc.chunk.chunk_id})" for sc in chunks],
                    reasoning_summary=(
                        f"Retrieved {len(chunks)} chunk(s) visible to {role.value} in "
                        f"{raw.get('attempt', 1)} attempt(s)"
                    ),
                    query=question,
                    role=role,
                    chunks=chunks,
                    attempt=raw.get("attempt", 1),
                    sufficient=raw.get("retrieval_sufficient", False),
                )

                if raw.get("draft") is not None:
                    result.draft = raw["draft"]

                if "is_grounded" in raw:
                    violations = raw.get("groundedness_violations", [])
                    result.groundedness = GroundednessCheck(
                        confidence=1.0 if raw["is_grounded"] else 0.3,
                        reasoning_summary=(
                            "Answer citations are lexically grounded in retrieved sources"
                            if raw["is_grounded"]
                            else "Answer failed the groundedness check"
                        ),
                        warnings=violations,
                        is_grounded=raw["is_grounded"],
                        unsupported_claims=violations,
                    )

                result.final_answer = raw.get("final_answer", "")
                result.answered = raw.get("answered", False)
                span.set_attribute("answered", result.answered)

            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                result.errors.append(str(exc))

        result = evaluate_review(result, settings.thresholds)
        result.completed_at = datetime.now(UTC)
        span.set_attribute("requires_review", result.requires_review)

        write_audit_entry(
            stage="Query",
            input_summary={"question": question, "role": role.value},
            output=result.model_dump(mode="json"),
            review_decision="human_review" if result.requires_review else "auto_answered",
            warnings=result.review_reasons,
        )

    return result
