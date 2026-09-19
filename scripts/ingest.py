"""Loads data/documents/*.md, chunks and embeds them, and persists the
result to the configured vector store path.

Run with: uv run python scripts/ingest.py
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from policyiq.config import PROJECT_ROOT, settings  # noqa: E402
from policyiq.embeddings import OpenAIEmbeddingProvider  # noqa: E402
from policyiq.ingestion import load_documents  # noqa: E402
from policyiq.models import EmbeddedChunk  # noqa: E402
from policyiq.vectorstore import InMemoryVectorStore  # noqa: E402


def main() -> None:
    documents_dir = PROJECT_ROOT / settings.documents_dir
    chunks = load_documents(
        documents_dir,
        settings.thresholds.chunk_size_chars,
        settings.thresholds.chunk_overlap_chars,
    )
    print(f"Loaded {len(chunks)} chunks from {documents_dir}")

    embedder = OpenAIEmbeddingProvider()
    texts = [c.text for c in chunks]

    batch_size = 100
    embedded: list[EmbeddedChunk] = []
    for i in range(0, len(texts), batch_size):
        batch = chunks[i : i + batch_size]
        vectors = embedder.embed([c.text for c in batch])
        embedded.extend(EmbeddedChunk(chunk=c, embedding=v) for c, v in zip(batch, vectors))
        print(f"Embedded {min(i + batch_size, len(texts))}/{len(texts)} chunks")

    store = InMemoryVectorStore()
    store.add(embedded)

    store_path = Path(settings.vectorstore_path)
    if not store_path.is_absolute():
        store_path = PROJECT_ROOT / store_path
    store.save(store_path)
    print(f"Saved vector store with {len(embedded)} chunks to {store_path}")


if __name__ == "__main__":
    main()
