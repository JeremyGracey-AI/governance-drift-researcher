from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from governance_drift.detectors.model_retirement import ModelRetirementDetector
from governance_drift.models import (
    ChangeEvent,
    Evidence,
    Extraction,
    InventoryEntry,
    Severity,
)

TODAY = date(2026, 8, 16)


def _evidence() -> Evidence:
    return Evidence(
        source_uri="file://fixture",
        content_sha256="0" * 64,
        retrieved_at=datetime(2026, 8, 16, tzinfo=UTC),
        field_path="$.data[0]",
        extraction=Extraction.STRUCTURED,
    )


def _change(effective: date | None) -> ChangeEvent:
    return ChangeEvent(
        kind="model-retirement",
        subject="gpt-4o-2024-08-06",
        effective=effective,
        detail="lifecycleStatus=retiring; replacement=gpt-4o-2024-11-20",
        evidence=_evidence(),
    )


def _entry() -> InventoryEntry:
    return InventoryEntry(
        agent_id="finance-copilot",
        owner="fin-eng@example.invalid",
        models=("gpt-4o-2024-08-06",),
        connectors=(),
        evidence=_evidence(),
    )


@pytest.mark.parametrize(
    ("effective", "expected"),
    [
        (date(2026, 7, 1), Severity.CRITICAL),
        (date(2026, 9, 1), Severity.CRITICAL),
        (date(2026, 11, 1), Severity.HIGH),
        (date(2027, 1, 1), Severity.MEDIUM),
        (date(2028, 1, 1), Severity.INFO),
        (None, Severity.LOW),
    ],
)
def test_severity_scales_with_time_remaining(
    effective: date | None, expected: Severity
):
    findings = ModelRetirementDetector(TODAY).detect(
        (_change(effective),), (_entry(),), ()
    )

    assert findings[0].severity is expected


def test_finding_names_affected_agents_and_cites_both_sides():
    findings = ModelRetirementDetector(TODAY).detect(
        (_change(date(2026, 11, 1)),), (_entry(),), ()
    )

    assert len(findings) == 1
    assert findings[0].rule_id == "drift/model-retirement"
    assert findings[0].affected[0].agent_id == "finance-copilot"
    assert len(findings[0].evidence) == 2
    assert "gpt-4o-2024-08-06" in findings[0].summary


def test_next_action_is_a_proposal_with_no_diff():
    findings = ModelRetirementDetector(TODAY).detect(
        (_change(date(2026, 11, 1)),), (_entry(),), ()
    )

    assert findings[0].next_action.diff is None
    assert "gpt-4o-2024-11-20" in findings[0].next_action.description


def test_unused_model_produces_no_finding():
    other = InventoryEntry(
        agent_id="hr-bot",
        owner="people-ops@example.invalid",
        models=("gpt-4o-mini-2024-07-18",),
        connectors=(),
        evidence=_evidence(),
    )

    assert ModelRetirementDetector(TODAY).detect((_change(None),), (other,), ()) == ()


def test_change_without_replacement_proposes_choosing_one():
    change = ChangeEvent(
        kind="model-retirement",
        subject="gpt-4o-2024-08-06",
        effective=None,
        detail="lifecycleStatus=deprecated",
        evidence=_evidence(),
    )

    findings = ModelRetirementDetector(TODAY).detect((change,), (_entry(),), ())

    assert "Choose a supported replacement" in findings[0].next_action.description


def test_past_retirement_is_worded_as_days_ago():
    findings = ModelRetirementDetector(TODAY).detect(
        (_change(date(2026, 7, 1)),), (_entry(),), ()
    )

    assert "days ago" in findings[0].summary
