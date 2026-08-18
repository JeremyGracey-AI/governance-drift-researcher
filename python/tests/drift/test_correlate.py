from __future__ import annotations

from datetime import UTC, date, datetime

from governance_drift.correlate import correlate
from governance_drift.models import ChangeEvent, Evidence, Extraction, InventoryEntry


def _evidence(path: str) -> Evidence:
    return Evidence(
        source_uri="file://fixture",
        content_sha256="0" * 64,
        retrieved_at=datetime(2026, 8, 16, tzinfo=UTC),
        field_path=path,
        extraction=Extraction.STRUCTURED,
    )


def _change(subject: str) -> ChangeEvent:
    return ChangeEvent(
        kind="model-retirement",
        subject=subject,
        effective=date(2026, 11, 1),
        detail="retiring",
        evidence=_evidence("$.data[0]"),
    )


def _entry(agent_id: str, *models: str) -> InventoryEntry:
    return InventoryEntry(
        agent_id=agent_id,
        owner="owner@example.invalid",
        models=models,
        connectors=(),
        evidence=_evidence("$.agents[0]"),
    )


def test_matches_every_agent_pinning_the_subject():
    result = correlate(
        (_change("gpt-4o-2024-08-06"),),
        (
            _entry("a", "gpt-4o-2024-08-06"),
            _entry("b", "gpt-4o-mini-2024-07-18"),
            _entry("c", "gpt-4o-2024-08-06", "gpt-4o-mini-2024-07-18"),
        ),
    )

    assert len(result) == 1
    assert [e.agent_id for e in result[0].affected] == ["a", "c"]


def test_changes_with_no_affected_agents_are_dropped():
    result = correlate((_change("some-other-model"),), (_entry("a", "gpt-4o"),))

    assert result == ()


def test_no_changes_yields_nothing():
    assert correlate((), (_entry("a", "gpt-4o"),)) == ()
