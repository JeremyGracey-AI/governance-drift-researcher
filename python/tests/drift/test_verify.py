from __future__ import annotations

from datetime import UTC, datetime

from governance_drift.models import (
    Evidence,
    Extraction,
    Finding,
    InventoryEntry,
    ProposedAction,
    Severity,
)
from governance_drift.verify import hash_key, verify

PAYLOAD = {"data": [{"id": "gpt-4o"}]}


def _evidence(path: str, digest: str = "a" * 64) -> Evidence:
    return Evidence(
        source_uri="file://fixture",
        content_sha256=digest,
        retrieved_at=datetime(2026, 8, 16, tzinfo=UTC),
        field_path=path,
        extraction=Extraction.STRUCTURED,
    )


def _finding(evidence: Evidence) -> Finding:
    return Finding(
        rule_id="drift/model-retirement",
        severity=Severity.HIGH,
        summary="something",
        affected=(
            InventoryEntry(
                agent_id="a",
                owner="o@example.invalid",
                models=(),
                connectors=(),
                evidence=evidence,
            ),
        ),
        evidence=(evidence,),
        next_action=ProposedAction(description="x", diff=None),
    )


def test_resolvable_evidence_is_kept():
    result = verify(
        (_finding(_evidence("$.data[0].id")),), {"file://fixture": PAYLOAD}, {}
    )

    assert len(result.kept) == 1
    assert result.dropped == 0
    assert result.changed_sources == ()


def test_unresolvable_field_path_drops_the_finding_and_counts_it():
    result = verify(
        (_finding(_evidence("$.data[9].id")),), {"file://fixture": PAYLOAD}, {}
    )

    assert result.kept == ()
    assert result.dropped == 1


def test_missing_payload_for_a_source_drops_the_finding():
    result = verify((_finding(_evidence("$.data[0].id")),), {}, {})

    assert result.kept == ()
    assert result.dropped == 1


def test_changed_source_hash_annotates_but_keeps():
    evidence = _evidence("$.data[0].id", digest="b" * 64)
    prior = {hash_key(evidence): "a" * 64}

    result = verify((_finding(evidence),), {"file://fixture": PAYLOAD}, prior)

    assert len(result.kept) == 1
    assert result.dropped == 0
    assert result.changed_sources == ("file://fixture#$.data[0].id",)


def test_matching_prior_hash_is_not_annotated():
    evidence = _evidence("$.data[0].id")
    prior = {hash_key(evidence): "a" * 64}

    result = verify((_finding(evidence),), {"file://fixture": PAYLOAD}, prior)

    assert result.changed_sources == ()


def test_unseen_source_is_not_annotated_as_changed():
    result = verify(
        (_finding(_evidence("$.data[0].id")),), {"file://fixture": PAYLOAD}, {}
    )

    assert result.changed_sources == ()
