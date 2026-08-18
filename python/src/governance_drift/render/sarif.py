"""Render findings as SARIF 2.1.0 for Defender, Sentinel, or code scanning."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Final

from governance_drift.models import Severity

if TYPE_CHECKING:
    from collections.abc import Sequence

    from governance_drift.models import Finding

#: SARIF has three actionable levels; map our five onto them.
LEVELS: Final[dict[Severity, str]] = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "note",
}

_INFO_URI: Final = "https://github.com/JeremyGracey-AI/governance-drift-researcher"


class SarifRenderer:
    """Serializes findings as a SARIF log."""

    def render(self, findings: Sequence[Finding]) -> str:
        """Render the SARIF document.

        Args:
            findings: Verified findings.

        Returns:
            Pretty-printed SARIF JSON.
        """
        document: dict[str, Any] = {
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "governance-drift",
                            "informationUri": _INFO_URI,
                            "rules": self._rules(findings),
                        }
                    },
                    "results": [self._result(f) for f in findings],
                }
            ],
        }
        return json.dumps(document, indent=2, sort_keys=True)

    def _rules(self, findings: Sequence[Finding]) -> list[dict[str, Any]]:
        """Build the deduplicated rule list.

        Args:
            findings: Verified findings.

        Returns:
            One descriptor per distinct rule id.
        """
        seen = dict.fromkeys(f.rule_id for f in findings)
        return [{"id": rule_id, "name": rule_id} for rule_id in seen]

    def _result(self, finding: Finding) -> dict[str, Any]:
        """Build one SARIF result.

        Args:
            finding: The finding.

        Returns:
            The result object.
        """
        return {
            "ruleId": finding.rule_id,
            "level": LEVELS[finding.severity],
            "message": {"text": finding.summary},
            "properties": {
                "severity": str(finding.severity),
                "affected": [entry.agent_id for entry in finding.affected],
                "nextAction": finding.next_action.description,
                "nextActionApplied": False,
                "provenance": [
                    {
                        "sourceUri": ev.source_uri,
                        "fieldPath": ev.field_path,
                        "contentSha256": ev.content_sha256,
                        "retrievedAt": ev.retrieved_at.isoformat(),
                        "extraction": str(ev.extraction),
                    }
                    for ev in finding.evidence
                ],
            },
        }
