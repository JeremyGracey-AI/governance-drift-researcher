from __future__ import annotations

import json
from datetime import UTC, date, datetime

from governance_drift.models import (
    Evidence,
    Extraction,
    Finding,
    InventoryEntry,
    ProposedAction,
    Severity,
)
from governance_drift.render.markdown import MarkdownRenderer
from governance_drift.render.sarif import SarifRenderer


def _finding(severity: Severity = Severity.HIGH) -> Finding:
    evidence = Evidence(
        source_uri="https://example.invalid/models",
        content_sha256="c" * 64,
        retrieved_at=datetime(2026, 8, 16, tzinfo=UTC),
        field_path="$.data[0]",
        extraction=Extraction.STRUCTURED,
    )
    return Finding(
        rule_id="drift/model-retirement",
        severity=severity,
        summary="gpt-4o-2024-08-06 retires in 77 days",
        affected=(
            InventoryEntry(
                agent_id="finance-copilot",
                owner="fin-eng@example.invalid",
                models=("gpt-4o-2024-08-06",),
                connectors=(),
                evidence=evidence,
            ),
        ),
        evidence=(evidence,),
        next_action=ProposedAction(description="pin to gpt-4o-2024-11-20", diff=None),
    )


def _markdown(
    *,
    tenant_configured: bool = True,
    dropped: int = 0,
    changed_sources: tuple[str, ...] = (),
) -> MarkdownRenderer:
    return MarkdownRenderer(
        run_date=date(2026, 8, 16),
        tenant_configured=tenant_configured,
        dropped=dropped,
        changed_sources=changed_sources,
    )


def test_markdown_includes_summary_evidence_and_proposal():
    out = _markdown().render((_finding(),))

    assert "gpt-4o-2024-08-06 retires in 77 days" in out
    assert "finance-copilot" in out
    assert "https://example.invalid/models" in out
    assert "$.data[0]" in out
    assert "pin to gpt-4o-2024-11-20" in out
    assert "PROPOSED" in out


def test_markdown_sorts_most_severe_first():
    out = _markdown().render((_finding(Severity.LOW), _finding(Severity.CRITICAL)))

    assert out.index("CRITICAL") < out.index("LOW")


def test_markdown_states_when_the_tenant_adapter_was_unconfigured():
    out = _markdown(tenant_configured=False).render(())

    assert "tenant adapter not configured" in out


def test_markdown_reports_drops_and_changed_sources():
    out = _markdown(dropped=2, changed_sources=("https://x#$.a",)).render(())

    assert "2" in out
    assert "https://x#$.a" in out


def test_markdown_handles_no_findings():
    out = _markdown().render(())

    assert "No drift detected" in out


def test_sarif_is_valid_json_with_one_result_per_finding():
    out = SarifRenderer().render((_finding(),))
    doc = json.loads(out)

    assert doc["version"] == "2.1.0"
    run = doc["runs"][0]
    assert run["tool"]["driver"]["name"] == "governance-drift"
    assert len(run["results"]) == 1
    assert run["results"][0]["ruleId"] == "drift/model-retirement"
    assert run["results"][0]["level"] == "error"


def test_sarif_maps_severity_to_level():
    doc = json.loads(SarifRenderer().render((_finding(Severity.LOW),)))

    assert doc["runs"][0]["results"][0]["level"] == "note"


def test_sarif_carries_provenance_per_result():
    doc = json.loads(SarifRenderer().render((_finding(),)))
    props = doc["runs"][0]["results"][0]["properties"]

    assert props["provenance"][0]["sourceUri"] == "https://example.invalid/models"
    assert props["provenance"][0]["extraction"] == "structured"
