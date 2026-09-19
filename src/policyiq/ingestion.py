"""Loads policy documents (markdown with YAML frontmatter) and splits them
into overlapping, role-tagged chunks ready for embedding.

Frontmatter format:

    ---
    doc_id: hr_handbook
    title: Employee Handbook
    visible_to: [employee, hr]
    ---
    # body text...
"""
from __future__ import annotations

from pathlib import Path

import yaml

from policyiq.models import DocumentChunk, Role

_FRONTMATTER_DELIM = "---"


def parse_document(raw_text: str) -> tuple[dict, str]:
    """Splits a markdown file into (frontmatter dict, body text)."""
    lines = raw_text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        raise ValueError("Document is missing YAML frontmatter")

    try:
        end_index = lines[1:].index(_FRONTMATTER_DELIM) + 1
    except ValueError as exc:
        raise ValueError("Document frontmatter is not terminated") from exc

    frontmatter_raw = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :]).strip()
    frontmatter = yaml.safe_load(frontmatter_raw) or {}
    return frontmatter, body


def chunk_text(text: str, chunk_size_chars: int, overlap_chars: int) -> list[str]:
    """Packs whitespace-delimited words into chunks up to chunk_size_chars,
    carrying the tail of each chunk forward as overlap into the next one."""
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        current.append(word)
        current_len += len(word) + 1

        if current_len >= chunk_size_chars:
            chunks.append(" ".join(current))

            overlap_len = 0
            keep_from = len(current)
            for w in reversed(current):
                overlap_len += len(w) + 1
                keep_from -= 1
                if overlap_len >= overlap_chars:
                    break

            current = current[keep_from:]
            current_len = sum(len(w) + 1 for w in current)

    if current:
        chunks.append(" ".join(current))

    return chunks


def load_documents(
    documents_dir: Path, chunk_size_chars: int, overlap_chars: int
) -> list[DocumentChunk]:
    """Loads every .md file in documents_dir and returns all chunks, tagged
    with the roles allowed to see them."""
    chunks: list[DocumentChunk] = []

    for path in sorted(documents_dir.glob("*.md")):
        frontmatter, body = parse_document(path.read_text(encoding="utf-8"))

        doc_id = frontmatter["doc_id"]
        title = frontmatter["title"]
        visible_to = [Role(r) for r in frontmatter["visible_to"]]

        for i, piece in enumerate(chunk_text(body, chunk_size_chars, overlap_chars)):
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{doc_id}-{i}",
                    doc_id=doc_id,
                    doc_title=title,
                    text=piece,
                    visible_to=visible_to,
                )
            )

    return chunks
