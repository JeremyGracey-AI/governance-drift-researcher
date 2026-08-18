"""Structural interfaces for every swappable part of the pipeline.

Implementations satisfy these by shape; nothing inherits from them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from governance_drift.models import ChangeEvent, Evidence, Finding, InventoryEntry


class ChangeSource(Protocol):
    """Yields vendor-side change events."""

    def changes(self) -> Sequence[ChangeEvent]:
        """Return every change this source knows about."""
        ...


class InventorySource(Protocol):
    """Yields agent inventory entries, approved or observed."""

    def entries(self) -> Sequence[InventoryEntry]:
        """Return every inventory entry this source knows about."""
        ...


class Detector(Protocol):
    """Turns changes and inventory into findings."""

    rule_id: str

    def detect(
        self,
        changes: Sequence[ChangeEvent],
        approved: Sequence[InventoryEntry],
        observed: Sequence[InventoryEntry],
    ) -> Sequence[Finding]:
        """Return findings for this rule."""
        ...


class Renderer(Protocol):
    """Serializes findings to a single output document."""

    def render(self, findings: Sequence[Finding]) -> str:
        """Return the rendered document."""
        ...


class Extractor(Protocol):
    """v2 seam: prose to structured change events.

    Unimplemented in v1. Outputs must carry ``Extraction.LLM``.
    """

    def extract(self, text: str, evidence: Evidence) -> Sequence[ChangeEvent]:
        """Return change events found in ``text``."""
        ...


class Judge(Protocol):
    """v2 seam: verify a finding's claim against its cited evidence span.

    Unimplemented in v1. Meaningful only for ``Extraction.LLM`` findings; a
    structured finding is already proven by its field path.
    """

    def supports(self, finding: Finding, span: str) -> bool:
        """Return whether ``span`` supports ``finding``."""
        ...
