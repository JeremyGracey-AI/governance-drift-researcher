"""Read observed tenant agents.

Optional at runtime. With no fetcher configured this yields nothing and
reports ``configured is False``, so a report can distinguish "no drift" from
"never looked".
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from governance_drift.models import Evidence, Extraction, InventoryEntry

if TYPE_CHECKING:
    from governance_drift.sources.fetch import Fetched, Fetcher


class TenantFormatError(Exception):
    """Raised when a tenant payload does not match the expected shape."""


def _strings(value: object) -> tuple[str, ...]:
    """Coerce an optional JSON array into a tuple of strings.

    Args:
        value: The parsed value, possibly ``None``.

    Returns:
        The strings, empty if ``value`` is ``None``.

    Raises:
        TenantFormatError: If ``value`` is neither ``None`` nor an array.
    """
    if value is None:
        return ()
    if not isinstance(value, list):
        msg = f"expected an array, got {type(value).__name__}"
        raise TenantFormatError(msg)
    items = cast("list[object]", value)
    return tuple(str(item) for item in items)


class TenantSource:
    """Parses observed tenant agents, or degrades to empty."""

    def __init__(self, fetch: Fetcher | None) -> None:
        """Store the optional fetcher.

        Args:
            fetch: Retrieves the tenant payload, or ``None`` when the adapter
                is not configured.
        """
        super().__init__()
        self._fetch = fetch

    @property
    def configured(self) -> bool:
        """Whether a tenant fetcher was supplied."""
        return self._fetch is not None

    def entries(self) -> tuple[InventoryEntry, ...]:
        """Parse every observed agent.

        Returns:
            One entry per agent, or ``()`` when unconfigured.

        Raises:
            TenantFormatError: If the payload shape is wrong.
        """
        if self._fetch is None:
            return ()
        fetched: Fetched = self._fetch()
        document: object = json.loads(fetched.raw)
        if not isinstance(document, dict) or "value" not in document:
            msg = "tenant payload must be an object with a 'value' array"
            raise TenantFormatError(msg)
        typed = cast("dict[str, object]", document)
        value: object = typed["value"]
        if not isinstance(value, list):
            msg = "'value' must be an array"
            raise TenantFormatError(msg)
        listed = cast("list[object]", value)
        return tuple(
            self._entry(raw, index, fetched) for index, raw in enumerate(listed)
        )

    def _entry(self, raw: object, index: int, fetched: Fetched) -> InventoryEntry:
        """Build one entry.

        Args:
            raw: The agent object.
            index: Position in the array.
            fetched: Provenance for the whole payload.

        Returns:
            The entry.

        Raises:
            TenantFormatError: If the agent is not an object or lacks an id.
        """
        if not isinstance(raw, dict):
            msg = f"value[{index}] must be an object"
            raise TenantFormatError(msg)
        typed = cast("dict[str, object]", raw)
        if "id" not in typed:
            msg = f"value[{index}] is missing required field 'id'"
            raise TenantFormatError(msg)
        return InventoryEntry(
            agent_id=str(typed["id"]),
            owner=str(typed.get("owner", "unknown")),
            models=_strings(typed.get("models")),
            connectors=_strings(typed.get("connectors")),
            evidence=Evidence(
                source_uri=fetched.uri,
                content_sha256=fetched.content_sha256,
                retrieved_at=fetched.retrieved_at,
                field_path=f"$.value[{index}]",
                extraction=Extraction.STRUCTURED,
            ),
        )
