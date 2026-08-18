from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import governance_drift.protocols as _  # noqa: F401
from governance_drift.models import (
    Evidence,
    Extraction,
    Finding,
    ProposedAction,
    Severity,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from governance_drift.models import ChangeEvent, InventoryEntry
    from governance_drift.protocols import (
        ChangeSource,
        Detector,
        InventorySource,
        Renderer,
    )


def _evidence() -> Evidence:
    return Evidence(
        source_uri="file://fixture",
        content_sha256="0" * 64,
        retrieved_at=datetime(2026, 8, 16, tzinfo=UTC),
        field_path="$.data[0]",
        extraction=Extraction.STRUCTURED,
    )


class _Source:
    def changes(self) -> Sequence[ChangeEvent]:
        return ()


class _Inventory:
    def entries(self) -> Sequence[InventoryEntry]:
        return ()


class _Detector:
    rule_id = "drift/example"

    def detect(
        self,
        changes: Sequence[ChangeEvent],
        approved: Sequence[InventoryEntry],
        observed: Sequence[InventoryEntry],
    ) -> Sequence[Finding]:
        return (
            Finding(
                rule_id=self.rule_id,
                severity=Severity.INFO,
                summary="none",
                affected=(),
                evidence=(_evidence(),),
                next_action=ProposedAction(description="nothing", diff=None),
            ),
        )


class _Renderer:
    def render(self, findings: Sequence[Finding]) -> str:
        return f"{len(findings)}"


def test_structural_implementations_satisfy_the_protocols():
    source: ChangeSource = _Source()
    inventory: InventorySource = _Inventory()
    detector: Detector = _Detector()
    renderer: Renderer = _Renderer()

    assert source.changes() == ()
    assert inventory.entries() == ()
    findings = detector.detect((), (), ())
    assert len(findings) == 1
    assert renderer.render(findings) == "1"
