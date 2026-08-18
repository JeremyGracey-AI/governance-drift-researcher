"""Join vendor changes to the agents they affect.

This is the product thesis in one function: a change nobody uses is noise,
and an agent nobody changed is fine. Only their intersection is a finding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from governance_drift.models import ChangeEvent, InventoryEntry


@dataclass(frozen=True, slots=True)
class Correlation:
    """A change and the inventory entries it affects.

    Attributes:
        change: The vendor-side change.
        affected: Entries pinning the changed subject. Never empty.
    """

    change: ChangeEvent
    affected: tuple[InventoryEntry, ...]


def correlate(
    changes: Sequence[ChangeEvent],
    inventory: Sequence[InventoryEntry],
) -> tuple[Correlation, ...]:
    """Pair each change with the entries it affects.

    Args:
        changes: Vendor-side changes.
        inventory: Approved agents.

    Returns:
        One correlation per change that affects at least one entry. Changes
        affecting nothing are dropped.
    """
    results: list[Correlation] = []
    for change in changes:
        affected = tuple(entry for entry in inventory if change.subject in entry.models)
        if affected:
            results.append(Correlation(change=change, affected=affected))
    return tuple(results)
