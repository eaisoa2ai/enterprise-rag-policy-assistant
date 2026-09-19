import pytest

from policyiq.guardrails import check_citations_exist, check_groundedness
from policyiq.models import Citation

OVERLAP_FLOOR = 0.35


def test_grounded_answer_has_no_violations(sample_chunks):
    hr_chunk = sample_chunks[0]
    citations = [Citation(doc_id=hr_chunk.doc_id, doc_title=hr_chunk.doc_title, chunk_id=hr_chunk.chunk_id)]
    answer = "Employees accrue 1.75 days of paid time off per month, totaling 21 days per year."

    violations = check_groundedness(answer, citations, [hr_chunk], OVERLAP_FLOOR)

    assert violations == []


def test_fabricated_answer_with_low_overlap_is_flagged(sample_chunks):
    hr_chunk = sample_chunks[0]
    citations = [Citation(doc_id=hr_chunk.doc_id, doc_title=hr_chunk.doc_title, chunk_id=hr_chunk.chunk_id)]
    answer = "Employees receive unlimited vacation and a company car after one year of tenure."

    violations = check_groundedness(answer, citations, [hr_chunk], OVERLAP_FLOOR)

    assert any("overlap" in v.lower() for v in violations)


def test_answer_with_no_citations_is_flagged(sample_chunks):
    violations = check_groundedness("Some answer text here.", [], sample_chunks, OVERLAP_FLOOR)
    assert any("no citations" in v.lower() for v in violations)


def test_empty_answer_is_flagged(sample_chunks):
    hr_chunk = sample_chunks[0]
    citations = [Citation(doc_id=hr_chunk.doc_id, doc_title=hr_chunk.doc_title, chunk_id=hr_chunk.chunk_id)]

    violations = check_groundedness("   ", citations, [hr_chunk], OVERLAP_FLOOR)

    assert violations != []


def test_citation_to_chunk_not_retrieved_is_flagged(sample_chunks):
    hr_chunk = sample_chunks[0]
    fake_citation = Citation(doc_id="ghost", doc_title="Ghost Doc", chunk_id="ghost-99")

    violations = check_citations_exist([fake_citation], [hr_chunk])

    assert len(violations) == 1
    assert "ghost-99" in violations[0]


def test_citation_to_a_real_retrieved_chunk_passes(sample_chunks):
    hr_chunk = sample_chunks[0]
    citation = Citation(doc_id=hr_chunk.doc_id, doc_title=hr_chunk.doc_title, chunk_id=hr_chunk.chunk_id)

    assert check_citations_exist([citation], [hr_chunk]) == []


@pytest.mark.parametrize("overlap_floor", [0.0, 0.35, 0.9])
def test_overlap_floor_is_configurable(sample_chunks, overlap_floor):
    hr_chunk = sample_chunks[0]
    citations = [Citation(doc_id=hr_chunk.doc_id, doc_title=hr_chunk.doc_title, chunk_id=hr_chunk.chunk_id)]
    # Shares exactly one significant word ("employees") with the source.
    answer = "Employees also get a free gym membership and catered lunch every day."

    violations = check_groundedness(answer, citations, [hr_chunk], overlap_floor)

    if overlap_floor == 0.0:
        assert violations == []
    else:
        assert any("overlap" in v.lower() for v in violations)
