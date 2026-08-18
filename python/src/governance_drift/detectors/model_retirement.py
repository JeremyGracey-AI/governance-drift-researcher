"""Detect approved agents pinning a model the vendor is retiring."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from governance_drift.correlate import correlate
from governance_drift.models import Finding, ProposedAction, Severity

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date

    from governance_drift.correlate import Correlation
    from governance_drift.models import ChangeEvent, InventoryEntry

#: Day thresholds, ascending, paired with the severity they trigger.
THRESHOLDS: Final[tuple[tuple[int, Severity], ...]] = (
    (30, Severity.CRITICAL),
    (90, Severity.HIGH),
    (180, Severity.MEDIUM),
)


def _severity(effective: date | None, today: date) -> Severity:
    """Grade urgency from time remaining.

    Args:
        effective: The retirement date, or ``None`` when undated.
        today: The reference date.

    Returns:
        The severity.
    """
    if effective is None:
        return Severity.LOW
    days = (effective - today).days
    for limit, severity in THRESHOLDS:
        if days <= limit:
            return severity
    return Severity.INFO


def _summary(correlation: Correlation, today: date) -> str:
    """Describe the correlation in one line.

    Args:
        correlation: The change and its affected agents.
        today: The reference date.

    Returns:
        The summary.
    """
    count = len(correlation.affected)
    subject = correlation.change.subject
    if correlation.change.effective is None:
        return (
            f"{subject} is deprecated with no retirement date; {count} agent(s) pin it"
        )
    days = (correlation.change.effective - today).days
    when = f"in {days} days" if days >= 0 else f"{abs(days)} days ago"
    return (
        f"{subject} retires {when} ({correlation.change.effective}); "
        f"{count} agent(s) pin it"
    )


def _replacement(detail: str) -> str | None:
    """Pull the replacement model id out of a change detail string.

    Args:
        detail: The change detail, e.g. ``"lifecycleStatus=retiring;
            replacement=gpt-4o-2024-11-20"``.

    Returns:
        The replacement id, or ``None`` when absent.
    """
    marker = "replacement="
    if marker not in detail:
        return None
    return detail.split(marker, 1)[1].strip()


class ModelRetirementDetector:
    """Flags approved agents pinning a retiring model."""

    rule_id = "drift/model-retirement"

    def __init__(self, today: date) -> None:
        """Store the reference date.

        Args:
            today: Reference date for urgency. Injected so runs are
                reproducible and no implicit clock read occurs.
        """
        super().__init__()
        self._today = today

    def detect(
        self,
        changes: Sequence[ChangeEvent],
        approved: Sequence[InventoryEntry],
        observed: Sequence[InventoryEntry],  # noqa: ARG002
    ) -> tuple[Finding, ...]:
        """Correlate retirements against the approved baseline.

        Args:
            changes: Vendor-side changes.
            approved: The approved baseline.
            observed: Unused by this rule; part of the Detector protocol.

        Returns:
            One finding per affected change.
        """
        return tuple(
            self._finding(correlation) for correlation in correlate(changes, approved)
        )

    def _finding(self, correlation: Correlation) -> Finding:
        """Build one finding.

        Args:
            correlation: The change and its affected agents.

        Returns:
            The finding.
        """
        replacement = _replacement(correlation.change.detail)
        action = (
            f"Pin affected agents to {replacement}"
            if replacement
            else f"Choose a supported replacement for {correlation.change.subject}"
        )
        return Finding(
            rule_id=self.rule_id,
            severity=_severity(correlation.change.effective, self._today),
            summary=_summary(correlation, self._today),
            affected=correlation.affected,
            evidence=(
                correlation.change.evidence,
                *(entry.evidence for entry in correlation.affected),
            ),
            next_action=ProposedAction(description=action, diff=None),
        )
