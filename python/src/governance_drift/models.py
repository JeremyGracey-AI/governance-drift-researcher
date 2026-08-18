"""Frozen data types for the drift researcher.

Every type here is immutable. Behavior lives in the modules that consume them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date, datetime


class Extraction(StrEnum):
    """How a cited value was obtained.

    Recording this on the artifact keeps the audit trail from overstating
    certainty once prose extraction lands in v2.
    """

    STRUCTURED = "structured"
    LLM = "llm"


class Severity(StrEnum):
    """Finding severity, declared most-severe first."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def rank(self) -> int:
        """Sort key derived from declaration order.

        Returns:
            ``0`` for the most severe member, ascending.
        """
        return list(Severity).index(self)


@dataclass(frozen=True, slots=True)
class Evidence:
    """A machine-checkable citation.

    Attributes:
        source_uri: Where the payload came from.
        content_sha256: Hash of the exact bytes retrieved.
        retrieved_at: Timezone-aware UTC retrieval time.
        field_path: Index path into the payload, e.g. ``$.data[0].id``.
        extraction: Whether the value was read from a typed field or inferred.
    """

    source_uri: str
    content_sha256: str
    retrieved_at: datetime
    field_path: str
    extraction: Extraction


@dataclass(frozen=True, slots=True)
class ChangeEvent:
    """Something the vendor changed.

    Attributes:
        kind: Detector-facing category, e.g. ``model-retirement``.
        subject: The thing that changed, e.g. a model id.
        effective: When it takes effect, if dated.
        detail: Human-readable description.
        evidence: The citation proving it.
    """

    kind: str
    subject: str
    effective: date | None
    detail: str
    evidence: Evidence


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    """One agent, either approved or observed.

    Attributes:
        agent_id: Stable identifier.
        owner: Accountable party.
        models: Model ids this agent pins.
        connectors: Connector ids this agent uses.
        evidence: The citation proving the entry.
    """

    agent_id: str
    owner: str
    models: tuple[str, ...]
    connectors: tuple[str, ...]
    evidence: Evidence


@dataclass(frozen=True, slots=True)
class ProposedAction:
    """The safest next action. Never applied by this system.

    ``diff`` is always ``None`` in v1: producing one requires knowing which
    file pins the model, which is the rung-3 repo scan the spec puts out of
    scope. The field exists so renderers and the SARIF schema stay stable.

    Attributes:
        description: What a human should consider doing.
        diff: A suggested patch, or ``None``.
    """

    description: str
    diff: str | None


@dataclass(frozen=True, slots=True)
class Finding:
    """A verified drift finding.

    Attributes:
        rule_id: Stable rule identifier, e.g. ``drift/model-retirement``.
        severity: How urgent.
        summary: One-line description.
        affected: Inventory entries this applies to.
        evidence: Citations supporting the claim.
        next_action: The proposal.
    """

    rule_id: str
    severity: Severity
    summary: str
    affected: tuple[InventoryEntry, ...]
    evidence: tuple[Evidence, ...]
    next_action: ProposedAction
