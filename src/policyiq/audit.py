"""Append-only audit trail. Every query writes one JSONL entry — same
pattern as outreach-iq and ClaimSight: agent name, timestamp, input summary,
output, and the review decision taken.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from policyiq.config import PROJECT_ROOT

AUDIT_LOG_PATH = PROJECT_ROOT / "logs" / "audit_trail.jsonl"


def write_audit_entry(
    *,
    stage: str,
    input_summary: dict[str, Any],
    output: dict[str, Any],
    review_decision: str,
    warnings: list[str] | None = None,
) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "stage": stage,
        "input_summary": input_summary,
        "output": output,
        "review_decision": review_decision,
        "warnings": warnings or [],
    }
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def read_audit_trail() -> list[dict[str, Any]]:
    if not AUDIT_LOG_PATH.exists():
        return []
    lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]
