"""In-memory, disk-persisted vector store with role-based access control
applied *before* ranking — a chunk a role isn't permitted to see is never a
candidate for retrieval, not merely hidden from the final display.

A flat, brute-force cosine-similarity scan over a Python list is the right
size for a demo corpus (a few hundred chunks) and needs zero external
services — the same "right-size for the demo, document the upgrade path"
trade-off as outreach-iq's SQLite choice. At real enterprise corpus size,
swap this class for a hosted ANN index (pgvector, Pinecone, LanceDB) behind
the same `VectorStore` interface; nothing above this layer would change.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from policyiq.embeddings import cosine_similarity
from policyiq.models import DocumentChunk, EmbeddedChunk, Role, ScoredChunk


class VectorStore(ABC):
    @abstractmethod
    def add(self, embedded_chunks: list[EmbeddedChunk]) -> None: ...

    @abstractmethod
    def search(self, query_embedding: list[float], role: Role, top_k: int) -> list[ScoredChunk]:
        """Returns the top_k chunks visible to `role`, ranked by similarity.
        Chunks not visible to the role are excluded before ranking, not after."""

    @abstractmethod
    def is_empty(self) -> bool: ...


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._chunks: list[EmbeddedChunk] = []

    def add(self, embedded_chunks: list[EmbeddedChunk]) -> None:
        self._chunks.extend(embedded_chunks)

    def is_empty(self) -> bool:
        return len(self._chunks) == 0

    def search(self, query_embedding: list[float], role: Role, top_k: int) -> list[ScoredChunk]:
        eligible = [ec for ec in self._chunks if role in ec.chunk.visible_to]
        scored = [
            ScoredChunk(chunk=ec.chunk, score=cosine_similarity(query_embedding, ec.embedding))
            for ec in eligible
        ]
        scored.sort(key=lambda sc: sc.score, reverse=True)
        return scored[:top_k]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {"chunk": ec.chunk.model_dump(mode="json"), "embedding": ec.embedding}
            for ec in self._chunks
        ]
        path.write_text(json.dumps(payload), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> InMemoryVectorStore:
        store = cls()
        if not path.exists():
            return store
        payload = json.loads(path.read_text(encoding="utf-8"))
        store._chunks = [
            EmbeddedChunk(
                chunk=DocumentChunk.model_validate(row["chunk"]), embedding=row["embedding"]
            )
            for row in payload
        ]
        return store
