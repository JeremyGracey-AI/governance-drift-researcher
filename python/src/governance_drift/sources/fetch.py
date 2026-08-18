"""Retrieval, hashing, and timestamping — the fixture/live swap point.

Every source takes a ``Fetcher``. Tests pass ``file_fetcher``; production
passes ``http_fetcher``. Nothing downstream knows the difference.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from pathlib import Path

    import httpx


class Fetched(NamedTuple):
    """One retrieved payload with its provenance.

    Attributes:
        uri: Where it came from.
        raw: The exact bytes retrieved.
        retrieved_at: Timezone-aware UTC retrieval time.
        content_sha256: Hex digest of ``raw``.
    """

    uri: str
    raw: bytes
    retrieved_at: datetime
    content_sha256: str


Fetcher = Callable[[], Fetched]


def _wrap(uri: str, raw: bytes) -> Fetched:
    """Attach provenance to retrieved bytes.

    Args:
        uri: Where the bytes came from.
        raw: The bytes.

    Returns:
        The wrapped payload.
    """
    return Fetched(
        uri=uri,
        raw=raw,
        retrieved_at=datetime.now(tz=UTC),
        content_sha256=hashlib.sha256(raw).hexdigest(),
    )


def file_fetcher(path: Path) -> Fetcher:
    """Build a fetcher that reads a local file.

    Args:
        path: File to read.

    Returns:
        A fetcher closing over ``path``.
    """

    def fetch() -> Fetched:
        return _wrap(path.as_uri(), path.read_bytes())

    return fetch


def http_fetcher(url: str, client: httpx.Client) -> Fetcher:
    """Build a fetcher that GETs ``url``.

    Args:
        url: Endpoint to retrieve.
        client: Caller-owned client; its lifecycle is not managed here.

    Returns:
        A fetcher closing over ``url`` and ``client``.
    """

    def fetch() -> Fetched:
        response = client.get(url)
        response.raise_for_status()
        return _wrap(url, response.content)

    return fetch
