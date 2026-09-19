from policyiq.embeddings import cosine_similarity
from policyiq.models import EmbeddedChunk, Role
from policyiq.vectorstore import InMemoryVectorStore


def test_cosine_similarity_identical_vectors_is_one():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_similarity_zero_vector_does_not_divide_by_zero():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_search_ranks_by_similarity(sample_chunks):
    store = InMemoryVectorStore()
    store.add(
        [
            EmbeddedChunk(chunk=sample_chunks[0], embedding=[1.0, 0.0, 0.0]),
            EmbeddedChunk(chunk=sample_chunks[1], embedding=[0.0, 1.0, 0.0]),
        ]
    )

    results = store.search([0.9, 0.1, 0.0], role=Role.IT, top_k=2)

    assert results[0].chunk.chunk_id == "hr_handbook-0"
    assert results[0].score > results[1].score


def test_search_excludes_chunks_not_visible_to_role(sample_chunks):
    store = InMemoryVectorStore()
    store.add(
        [
            EmbeddedChunk(chunk=sample_chunks[0], embedding=[1.0, 0.0, 0.0]),  # visible to all
            EmbeddedChunk(chunk=sample_chunks[2], embedding=[1.0, 0.0, 0.0]),  # legal only
        ]
    )

    employee_results = store.search([1.0, 0.0, 0.0], role=Role.EMPLOYEE, top_k=10)
    legal_results = store.search([1.0, 0.0, 0.0], role=Role.LEGAL, top_k=10)

    assert [r.chunk.chunk_id for r in employee_results] == ["hr_handbook-0"]
    assert {r.chunk.chunk_id for r in legal_results} == {"hr_handbook-0", "anti_corruption_policy-0"}


def test_rbac_filter_excludes_even_a_perfect_score_match(sample_chunks):
    """A restricted chunk must never surface for an unauthorized role, even
    when it's the best possible vector match — the filter runs before ranking."""
    store = InMemoryVectorStore()
    store.add([EmbeddedChunk(chunk=sample_chunks[1], embedding=[1.0, 0.0, 0.0])])  # IT only

    results = store.search([1.0, 0.0, 0.0], role=Role.EMPLOYEE, top_k=10)

    assert results == []


def test_save_and_load_roundtrip(tmp_path, sample_chunks):
    store = InMemoryVectorStore()
    store.add([EmbeddedChunk(chunk=sample_chunks[0], embedding=[0.1, 0.2, 0.3])])
    path = tmp_path / "index.json"
    store.save(path)

    loaded = InMemoryVectorStore.load(path)

    assert not loaded.is_empty()
    results = loaded.search([0.1, 0.2, 0.3], role=Role.EMPLOYEE, top_k=1)
    assert results[0].chunk.chunk_id == "hr_handbook-0"


def test_load_missing_file_returns_empty_store(tmp_path):
    store = InMemoryVectorStore.load(tmp_path / "does_not_exist.json")
    assert store.is_empty()
