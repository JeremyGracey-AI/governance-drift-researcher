"""Read the approved baseline from YAML.

This module reads. It never writes — that is the structural enforcement of
"agents propose, humans promote".
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import yaml

from governance_drift.models import Evidence, Extraction, InventoryEntry

if TYPE_CHECKING:
    from governance_drift.sources.fetch import Fetched, Fetcher


class InventoryFormatError(Exception):
    """Raised when an inventory document does not match the expected shape."""


def _require(raw: dict[str, object], key: str, index: int) -> object:
    """Read a required key from an agent mapping.

    Args:
        raw: The agent mapping.
        key: The key to read.
        index: Position in the ``agents`` list, for error messages.

    Returns:
        The value.

    Raises:
        InventoryFormatError: If the key is absent.
    """
    if key not in raw:
        msg = f"agents[{index}] is missing required field {key!r}"
        raise InventoryFormatError(msg)
    return raw[key]


def _strings(value: object) -> tuple[str, ...]:
    """Coerce an optional YAML list into a tuple of strings.

    Args:
        value: The parsed value, possibly ``None``.

    Returns:
        The strings, empty if ``value`` is ``None``.

    Raises:
        InventoryFormatError: If ``value`` is neither ``None`` nor a list.
    """
    if value is None:
        return ()
    if not isinstance(value, list):
        msg = f"expected a list, got {type(value).__name__}"
        raise InventoryFormatError(msg)
    items = cast("list[object]", value)
    return tuple(str(item) for item in items)


class YamlInventorySource:
    """Parses an inventory document into :class:`InventoryEntry` values."""

    def __init__(self, fetch: Fetcher) -> None:
        """Store the fetcher.

        Args:
            fetch: Retrieves the YAML document.
        """
        super().__init__()
        self._fetch = fetch

    def entries(self) -> tuple[InventoryEntry, ...]:
        """Parse every agent in the document.

        Returns:
            One entry per agent, each citing its index path.

        Raises:
            InventoryFormatError: If the document shape is wrong.
        """
        fetched: Fetched = self._fetch()
        document: object = yaml.safe_load(fetched.raw)
        if not isinstance(document, dict) or "agents" not in document:
            msg = "inventory document must be a mapping with an 'agents' key"
            raise InventoryFormatError(msg)
        typed = cast("dict[str, object]", document)
        agents: object = typed["agents"]
        if not isinstance(agents, list):
            msg = "'agents' must be a list"
            raise InventoryFormatError(msg)
        listed = cast("list[object]", agents)
        return tuple(
            self._entry(raw, index, fetched) for index, raw in enumerate(listed)
        )

    def _entry(self, raw: object, index: int, fetched: Fetched) -> InventoryEntry:
        """Build one entry.

        Args:
            raw: The agent mapping.
            index: Position in the list.
            fetched: Provenance for the whole document.

        Returns:
            The entry.

        Raises:
            InventoryFormatError: If the agent is not a mapping or lacks fields.
        """
        if not isinstance(raw, dict):
            msg = f"agents[{index}] must be a mapping"
            raise InventoryFormatError(msg)
        typed = cast("dict[str, object]", raw)
        return InventoryEntry(
            agent_id=str(_require(typed, "agent_id", index)),
            owner=str(_require(typed, "owner", index)),
            models=_strings(typed.get("models")),
            connectors=_strings(typed.get("connectors")),
            evidence=Evidence(
                source_uri=fetched.uri,
                content_sha256=fetched.content_sha256,
                retrieved_at=fetched.retrieved_at,
                field_path=f"$.agents[{index}]",
                extraction=Extraction.STRUCTURED,
            ),
        )
