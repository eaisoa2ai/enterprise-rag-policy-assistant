import pytest

from policyiq.ingestion import chunk_text, load_documents, parse_document


def test_parse_document_splits_frontmatter_and_body():
    raw = "---\ndoc_id: foo\ntitle: Foo Policy\nvisible_to: [employee]\n---\n# Foo\nSome body text."
    frontmatter, body = parse_document(raw)

    assert frontmatter == {"doc_id": "foo", "title": "Foo Policy", "visible_to": ["employee"]}
    assert body == "# Foo\nSome body text."


def test_parse_document_requires_frontmatter():
    with pytest.raises(ValueError, match="frontmatter"):
        parse_document("# Just a heading\nNo frontmatter here.")


def test_chunk_text_respects_size_and_overlap():
    text = " ".join(f"word{i}" for i in range(200))  # ~1200 chars
    chunks = chunk_text(text, chunk_size_chars=300, overlap_chars=50)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) > 0

    # Overlap: some of the tail of chunk 0 should reappear somewhere in the
    # head of chunk 1 — the overlap window is several words wide, so this
    # checks the two windows intersect rather than an exact boundary match.
    tail_words = set(chunks[0].split()[-10:])
    head_words = set(chunks[1].split()[:10])
    assert tail_words & head_words


def test_chunk_text_empty_input_returns_no_chunks():
    assert chunk_text("   ", chunk_size_chars=300, overlap_chars=50) == []


def test_load_documents_reads_and_tags_all_markdown_files(tmp_path):
    (tmp_path / "doc_a.md").write_text(
        "---\ndoc_id: doc_a\ntitle: Doc A\nvisible_to: [employee]\n---\n"
        + " ".join(f"w{i}" for i in range(150)),
        encoding="utf-8",
    )
    (tmp_path / "doc_b.md").write_text(
        "---\ndoc_id: doc_b\ntitle: Doc B\nvisible_to: [hr, legal]\n---\nShort body.",
        encoding="utf-8",
    )

    chunks = load_documents(tmp_path, chunk_size_chars=300, overlap_chars=50)

    doc_ids = {c.doc_id for c in chunks}
    assert doc_ids == {"doc_a", "doc_b"}

    doc_b_chunk = next(c for c in chunks if c.doc_id == "doc_b")
    assert doc_b_chunk.doc_title == "Doc B"
    from policyiq.models import Role

    assert doc_b_chunk.visible_to == [Role.HR, Role.LEGAL]
