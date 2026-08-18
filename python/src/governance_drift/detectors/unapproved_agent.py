"""Detect agents running in the tenant that the baseline never approved."""

from __future__ import annotations

from typing import TYPE_CHECKING

from governance_drift.models import Finding, ProposedAction, Severity

if TYPE_CHECKING:
    from collections.abc import Sequence

    from governance_drift.models import ChangeEvent, InventoryEntry


class UnapprovedAgentDetector:
    """Flags observed agents with no approved counterpart.

    Severity is always HIGH: an agent running outside the approved baseline
    is a governance violation by definition, independent of what it does.
    """

    rule_id = "drift/unapproved-agent"

    def detect(
        self,
        changes: Sequence[ChangeEvent],  # noqa: ARG002
        approved: Sequence[InventoryEntry],
        observed: Sequence[InventoryEntry],
    ) -> tuple[Finding, ...]:
        """Compute ``observed - approved``.

        Args:
            changes: Unused by this rule; part of the Detector protocol.
            approved: The approved baseline.
            observed: What the tenant is actually running.

        Returns:
            One finding per unapproved agent, or ``()``.
        """
        known = {entry.agent_id for entry in approved}
        rogue = tuple(entry for entry in observed if entry.agent_id not in known)
        if not rogue:
            return ()
        names = ", ".join(entry.agent_id for entry in rogue)
        summary = (
            f"{len(rogue)} agent(s) running outside the approved baseline: {names}"
        )
        return (
            Finding(
                rule_id=self.rule_id,
                severity=Severity.HIGH,
                summary=summary,
                affected=rogue,
                evidence=tuple(entry.evidence for entry in rogue),
                next_action=ProposedAction(
                    description=(
                        "Review each agent, then either add it to inventory.yaml "
                        "in a reviewed pull request or decommission it"
                    ),
                    diff=None,
                ),
            ),
        )
