from __future__ import annotations

import pytest

from policyiq.models import DocumentChunk, Role


@pytest.fixture()
def sample_chunks() -> list[DocumentChunk]:
    return [
        DocumentChunk(
            chunk_id="hr_handbook-0",
            doc_id="hr_handbook",
            doc_title="Employee Handbook",
            text="Full-time employees accrue 1.75 days of paid time off per month, totaling 21 days per year.",
            visible_to=[Role.EMPLOYEE, Role.HR, Role.IT, Role.LEGAL, Role.FINANCE],
        ),
        DocumentChunk(
            chunk_id="it_security_policy-0",
            doc_id="it_security_policy",
            doc_title="IT Security Policy",
            text="Tier 1 incidents require containment to begin within 15 minutes of detection.",
            visible_to=[Role.IT],
        ),
        DocumentChunk(
            chunk_id="anti_corruption_policy-0",
            doc_id="anti_corruption_policy",
            doc_title="Anti-Corruption and Anti-Bribery Policy",
            text="Gifts to a business partner are permitted up to $100 in value per occasion.",
            visible_to=[Role.LEGAL],
        ),
    ]
