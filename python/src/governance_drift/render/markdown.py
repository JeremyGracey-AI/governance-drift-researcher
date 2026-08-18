"""Render findings as the human-readable, git-committed audit artifact."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date

    from governance_drift.models import Finding


class MarkdownRenderer:
    """Serializes findings plus the run context that qualifies them."""

    def __init__(
        self,
        run_date: date,
        *,
        tenant_configured: bool,
        dropped: int,
        changed_sources: Sequence[str],
    ) -> None:
        """Store run context.

        Args:
            run_date: The date the scan ran.
            tenant_configured: Whether a tenant adapter was supplied.
            dropped: Findings dropped by verify check (a).
            changed_sources: Sources whose digest moved since the last run.
        """
        super().__init__()
        self._run_date = run_date
        self._tenant_configured = tenant_configured
        self._dropped = dropped
        self._changed_sources = tuple(changed_sources)

    def render(self, findings: Sequence[Finding]) -> str:
        """Render the report.

        Args:
            findings: Verified findings.

        Returns:
            The Markdown document.
        """
        lines = [f"# Governance drift — {self._run_date.isoformat()}", ""]
        lines.extend(self._context())
        ordered = sorted(findings, key=lambda f: f.severity.rank)
        if not ordered:
            lines.extend(["## Findings", "", "No drift detected.", ""])
        else:
            lines.append("## Findings")
            lines.append("")
            for finding in ordered:
                lines.extend(self._finding(finding))
        return "\n".join(lines)

    def _context(self) -> list[str]:
        """Render the run-context block.

        Returns:
            Lines describing coverage and verification outcomes.
        """
        lines = ["## Run context", ""]
        if not self._tenant_configured:
            lines.append(
                "- **Coverage gap:** tenant adapter not configured — "
                "vendor-side findings only. Absence of tenant findings does "
                "not mean the tenant is clean."
            )
        else:
            lines.append("- Tenant adapter configured; both sides scanned.")
        lines.append(f"- Findings dropped by evidence check: {self._dropped}")
        if self._changed_sources:
            lines.append("- Sources changed since the previous report:")
            lines.extend(f"  - `{key}`" for key in self._changed_sources)
        else:
            lines.append("- No cited source changed since the previous report.")
        lines.append("")
        return lines

    def _finding(self, finding: Finding) -> list[str]:
        """Render one finding.

        Args:
            finding: The finding.

        Returns:
            Lines for this finding.
        """
        lines = [
            f"### {finding.severity.upper()} · {finding.rule_id}",
            "",
            finding.summary,
            "",
            f"**Affected ({len(finding.affected)}):**",
            "",
        ]
        lines.extend(
            f"- `{entry.agent_id}` — owner {entry.owner} "
            f"(`{entry.evidence.source_uri}` at `{entry.evidence.field_path}`)"
            for entry in finding.affected
        )
        lines.extend(["", "**Evidence:**", ""])
        lines.extend(
            f"- `{ev.source_uri}` at `{ev.field_path}` "
            f"— sha256 `{ev.content_sha256[:12]}…`, retrieved "
            f"{ev.retrieved_at.isoformat()}, extraction `{ev.extraction}`"
            for ev in finding.evidence
        )
        lines.extend(
            [
                "",
                (
                    f"**Safest next action — PROPOSED, not applied:** "
                    f"{finding.next_action.description}"
                ),
                "",
            ]
        )
        return lines
