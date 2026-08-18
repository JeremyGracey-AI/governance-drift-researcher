from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

import pytest

from governance_drift.models import (
    ChangeEvent,
    Evidence,
    Extraction,
    Finding,
    InventoryEntry,
    ProposedAction,
    Severity,
)


def _evidence() -> Evidence:
    return Evidence(
        source_uri="https://example.invalid/models",
        content_sha256="0" * 64,
        retrieved_at=datetime(2026, 8, 16, tzinfo=UTC),
        field_path="$.data[0].deprecationDate",
        extraction=Extraction.STRUCTURED,
    )


def test_severity_rank_orders_most_severe_first():
    assert Severity.CRITICAL.rank == 0
    assert Severity.CRITICAL.rank < Severity.HIGH.rank < Severity.INFO.rank


def test_severity_is_a_string():
    assert Severity.HIGH == "high"


def test_evidence_is_frozen():
    ev = _evidence()
    with pytest.raises(FrozenInstanceError):
        ev.source_uri = "changed"  # type: ignore[misc]


def test_change_event_holds_its_evidence():
    ev = _evidence()
    change = ChangeEvent(
        kind="model-retirement",
        subject="gpt-4o-2024-08-06",
        effective=date(2026, 11, 1),
        detail="retiring",
        evidence=ev,
    )
    assert change.evidence is ev
    assert change.effective == date(2026, 11, 1)


def test_finding_carries_affected_entries_and_a_proposal():
    ev = _evidence()
    entry = InventoryEntry(
        agent_id="finance-copilot",
        owner="fin-eng@example.invalid",
        models=("gpt-4o-2024-08-06",),
        connectors=(),
        evidence=ev,
    )
    finding = Finding(
        rule_id="drift/model-retirement",
        severity=Severity.HIGH,
        summary="gpt-4o retires in 77 days",
        affected=(entry,),
        evidence=(ev,),
        next_action=ProposedAction(description="pin to gpt-4o-2024-11-20", diff=None),
    )
    assert finding.affected[0].agent_id == "finance-copilot"
    assert finding.next_action.diff is None
