from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from policyiq.models import AgentOutput, QueryResult, Role


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_agent_output_rejects_out_of_range_confidence(confidence):
    with pytest.raises(ValidationError):
        AgentOutput(confidence=confidence, reasoning_summary="test")


@pytest.mark.parametrize("confidence", [0.0, 0.5, 1.0])
def test_agent_output_accepts_boundary_confidence(confidence):
    output = AgentOutput(confidence=confidence, reasoning_summary="test")
    assert output.confidence == confidence


def test_query_result_defaults_to_not_requiring_review():
    result = QueryResult(
        query_id="q1", question="test?", role=Role.EMPLOYEE, started_at=datetime.now(UTC)
    )
    assert result.requires_review is False
    assert result.answered is False
    assert result.errors == []


def test_role_values():
    assert {r.value for r in Role} == {"employee", "hr", "it", "legal", "finance"}
