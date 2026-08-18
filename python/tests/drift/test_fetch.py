from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import httpx
import pytest

from governance_drift.sources.fetch import file_fetcher, http_fetcher

if TYPE_CHECKING:
    from pathlib import Path


def test_file_fetcher_reads_bytes_and_hashes_them(tmp_path: Path):
    target = tmp_path / "payload.json"
    target.write_bytes(b'{"data": []}')

    fetched = file_fetcher(target)()

    assert fetched.raw == b'{"data": []}'
    assert fetched.content_sha256 == hashlib.sha256(b'{"data": []}').hexdigest()
    assert fetched.uri == target.as_uri()
    assert fetched.retrieved_at.tzinfo is not None


def test_file_fetcher_raises_for_a_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        file_fetcher(tmp_path / "absent.json")()


def test_http_fetcher_returns_body_and_hash():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/models"
        return httpx.Response(200, content=b'{"data": [1]}')

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetched = http_fetcher("https://example.invalid/models", client)()

    assert fetched.raw == b'{"data": [1]}'
    assert fetched.content_sha256 == hashlib.sha256(b'{"data": [1]}').hexdigest()
    assert fetched.uri == "https://example.invalid/models"


def test_http_fetcher_raises_on_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(httpx.HTTPStatusError),
    ):
        http_fetcher("https://example.invalid/models", client)()
