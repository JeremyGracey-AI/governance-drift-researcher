"""Read model lifecycle state from the Azure AI Foundry Models API.

The Foundry retirement documentation directs readers to query the Models API
rather than trust the static docs page, so this reads ``lifecycleStatus`` and
``deprecationDate`` as typed fields. Nothing here interprets prose, which is
why v1 needs no model in the loop.
"""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING, Final, cast

from governance_drift.models import ChangeEvent, Evidence, Extraction

if TYPE_CHECKING:
    from governance_drift.sources.fetch import Fetched, Fetcher

#: Lifecycle values that mean an inventory entry pinning the model is at risk.
AFFECTED_STATUSES: Final = frozenset({"retiring", "deprecated", "retired"})


class FoundryFormatError(Exception):
    """Raised when a Foundry payload does not match the expected shape."""


def _effective(raw: object, index: int) -> date | None:
    """Parse an optional ISO deprecation date.

    Args:
        raw: The parsed value, possibly ``None``.
        index: Position in ``data``, for error messages.

    Returns:
        The date, or ``None`` when undated.

    Raises:
        FoundryFormatError: If present but unparseable.
    """
    if raw is None:
        return None
    try:
        return date.fromisoformat(str(raw))
    except ValueError as exc:
        msg = f"data[{index}] has an unparseable deprecationDate: {raw!r}"
        raise FoundryFormatError(msg) from exc


class FoundrySource:
    """Emits model-retirement change events."""

    def __init__(self, fetch: Fetcher) -> None:
        """Store the fetcher.

        Args:
            fetch: Retrieves the Models API payload.
        """
        super().__init__()
        self._fetch = fetch

    def changes(self) -> tuple[ChangeEvent, ...]:
        """Parse every lifecycle-affected model.

        Returns:
            One event per affected model, in payload order.

        Raises:
            FoundryFormatError: If the payload shape is wrong.
        """
        fetched: Fetched = self._fetch()
        document: object = json.loads(fetched.raw)
        if not isinstance(document, dict) or "data" not in document:
            msg = "Foundry payload must be an object with a 'data' array"
            raise FoundryFormatError(msg)
        typed = cast("dict[str, object]", document)
        data: object = typed["data"]
        if not isinstance(data, list):
            msg = "'data' must be an array"
            raise FoundryFormatError(msg)
        listed = cast("list[object]", data)

        events: list[ChangeEvent] = []
        for index, raw in enumerate(listed):
            event = self._event(raw, index, fetched)
            if event is not None:
                events.append(event)
        return tuple(events)

    def _event(self, raw: object, index: int, fetched: Fetched) -> ChangeEvent | None:
        """Build one event, or ``None`` when the model is unaffected.

        Args:
            raw: The model object.
            index: Position in ``data``.
            fetched: Provenance for the whole payload.

        Returns:
            The event, or ``None``.

        Raises:
            FoundryFormatError: If the model is not an object.
        """
        if not isinstance(raw, dict):
            msg = f"data[{index}] must be an object"
            raise FoundryFormatError(msg)
        typed = cast("dict[str, object]", raw)
        status = str(typed.get("lifecycleStatus", ""))
        if status not in AFFECTED_STATUSES:
            return None

        subject = f"{typed.get('id', '')}-{typed.get('version', '')}"
        replacement = typed.get("replacement")
        detail = f"lifecycleStatus={status}"
        if replacement is not None:
            detail = f"{detail}; replacement={replacement}"

        return ChangeEvent(
            kind="model-retirement",
            subject=subject,
            effective=_effective(typed.get("deprecationDate"), index),
            detail=detail,
            evidence=Evidence(
                source_uri=fetched.uri,
                content_sha256=fetched.content_sha256,
                retrieved_at=fetched.retrieved_at,
                field_path=f"$.data[{index}]",
                extraction=Extraction.STRUCTURED,
            ),
        )
