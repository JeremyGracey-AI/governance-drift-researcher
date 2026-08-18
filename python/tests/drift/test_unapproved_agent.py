from __future__ import annotations

from datetime import UTC, datetime

from governance_drift.detectors.unapproved_agent import UnapprovedAgentDetector
from governance_drift.models import Evidence, Extraction, InventoryEntry, Severity


def _entry(agent_id: str) -> InventoryEntry:
    return InventoryEntry(
        agent_id=agent_id,
        owner="owner@example.invalid",
        models=("gpt-4o-2024-08-06",),
        connectors=(),
        evidence=Evidence(
            source_uri="file://fixture",
            content_sha256="0" * 64,
            retrieved_at=datetime(2026, 8, 16, tzinfo=UTC),
            field_path="$.value[0]",
            extraction=Extraction.STRUCTURED,
        ),
    )


def test_flags_observed_agents_absent_from_the_baseline():
    findings = UnapprovedAgentDetector().detect(
        (),
        (_entry("finance-copilot"), _entry("hr-bot")),
        (_entry("finance-copilot"), _entry("hr-bot"), _entry("shadow-bot")),
    )

    assert len(findings) == 1
    assert findings[0].rule_id == "drift/unapproved-agent"
    assert findings[0].severity is Severity.HIGH
    assert findings[0].affected[0].agent_id == "shadow-bot"
    assert "shadow-bot" in findings[0].summary


def test_matching_inventories_produce_nothing():
    approved = (_entry("finance-copilot"),)

    assert UnapprovedAgentDetector().detect((), approved, approved) == ()


def test_unconfigured_tenant_produces_nothing():
    assert UnapprovedAgentDetector().detect((), (_entry("a"),), ()) == ()


def test_approved_agents_missing_from_the_tenant_are_not_flagged():
    findings = UnapprovedAgentDetector().detect(
        (), (_entry("a"), _entry("b")), (_entry("a"),)
    )

    assert findings == ()
