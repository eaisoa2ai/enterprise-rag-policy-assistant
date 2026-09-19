"""The corrective-retrieval LangGraph: retrieve -> grade -> (retry retrieval
if weak) -> generate -> verify groundedness -> (retry generation once if
ungrounded) -> accept or decline.

Dependencies (vector store, embedder, thresholds) are injected via closure
in `build_graph()` rather than carried in the graph state — the state is
data describing one query's progress, not a place to stash services.
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from policyiq.agent.llm import generate_answer
from policyiq.config import Thresholds
from policyiq.embeddings import EmbeddingProvider
from policyiq.guardrails import check_groundedness
from policyiq.models import AnswerDraft, Role, ScoredChunk
from policyiq.observability import get_tracer
from policyiq.vectorstore import VectorStore

tracer = get_tracer()


class GraphState(TypedDict, total=False):
    question: str
    role: str
    attempt: int
    chunks: list[ScoredChunk]
    retrieval_sufficient: bool
    retrieval_confidence: float
    draft: AnswerDraft | None
    regenerated: bool
    groundedness_violations: list[str]
    is_grounded: bool
    final_answer: str
    answered: bool


def build_graph(vector_store: VectorStore, embedder: EmbeddingProvider, thresholds: Thresholds):
    def retrieve_node(state: GraphState) -> GraphState:
        with tracer.start_as_current_span("rag.retrieve") as span:
            attempt = state.get("attempt", 0) + 1
            top_k = thresholds.top_k * attempt  # widen the search on retry
            role = Role(state["role"])
            [embedding] = embedder.embed([state["question"]])
            chunks = vector_store.search(embedding, role, top_k)
            sufficient = bool(chunks) and chunks[0].score >= thresholds.min_relevance_score

            span.set_attribute("attempt", attempt)
            span.set_attribute("chunks_found", len(chunks))
            span.set_attribute("sufficient", sufficient)

            return {
                **state,
                "attempt": attempt,
                "chunks": chunks,
                "retrieval_sufficient": sufficient,
                "retrieval_confidence": chunks[0].score if chunks else 0.0,
            }

    def generate_node(state: GraphState) -> GraphState:
        with tracer.start_as_current_span("rag.generate") as span:
            strict = state.get("regenerated", False)
            draft = generate_answer(state["question"], state["chunks"], strict=strict)
            span.set_attribute("confidence", draft.confidence)
            span.set_attribute("citation_count", len(draft.citations))
            return {**state, "draft": draft}

    def verify_node(state: GraphState) -> GraphState:
        with tracer.start_as_current_span("rag.verify_groundedness") as span:
            draft = state["draft"]
            source_chunks = [sc.chunk for sc in state["chunks"]]
            violations = check_groundedness(
                draft.answer_text,
                draft.citations,
                source_chunks,
                thresholds.groundedness_overlap_floor,
            )
            is_grounded = not violations
            span.set_attribute("is_grounded", is_grounded)
            span.set_attribute("violation_count", len(violations))
            return {**state, "groundedness_violations": violations, "is_grounded": is_grounded}

    def mark_regenerated_node(state: GraphState) -> GraphState:
        return {**state, "regenerated": True}

    def accept_node(state: GraphState) -> GraphState:
        return {**state, "final_answer": state["draft"].answer_text, "answered": True}

    def decline_retrieval_node(state: GraphState) -> GraphState:
        return {
            **state,
            "final_answer": (
                "I couldn't find enough information you're authorized to see to "
                "answer that confidently. Please check with the relevant department."
            ),
            "answered": False,
        }

    def decline_groundedness_node(state: GraphState) -> GraphState:
        return {
            **state,
            "final_answer": (
                "I found related information but couldn't confidently ground a "
                "full answer in it. Recommend consulting the source document "
                "directly or escalating to the relevant department."
            ),
            "answered": False,
        }

    def route_after_retrieve(state: GraphState) -> str:
        if state["retrieval_sufficient"]:
            return "generate"
        if state["attempt"] < thresholds.max_retrieval_attempts:
            return "retrieve"
        return "decline_retrieval"

    def route_after_verify(state: GraphState) -> str:
        if state["is_grounded"]:
            return "accept"
        if not state.get("regenerated", False):
            return "regenerate"
        return "decline_groundedness"

    graph = StateGraph(GraphState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("verify", verify_node)
    graph.add_node("mark_regenerated", mark_regenerated_node)
    graph.add_node("accept", accept_node)
    graph.add_node("decline_retrieval", decline_retrieval_node)
    graph.add_node("decline_groundedness", decline_groundedness_node)

    graph.set_entry_point("retrieve")
    graph.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {
            "generate": "generate",
            "retrieve": "retrieve",
            "decline_retrieval": "decline_retrieval",
        },
    )
    graph.add_edge("generate", "verify")
    graph.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "accept": "accept",
            "regenerate": "mark_regenerated",
            "decline_groundedness": "decline_groundedness",
        },
    )
    graph.add_edge("mark_regenerated", "generate")
    graph.add_edge("accept", END)
    graph.add_edge("decline_retrieval", END)
    graph.add_edge("decline_groundedness", END)

    return graph.compile()
