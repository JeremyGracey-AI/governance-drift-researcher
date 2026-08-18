from __future__ import annotations

import pytest

from governance_drift.paths import FieldPathError, resolve

PAYLOAD = {
    "data": [
        {"id": "gpt-4o", "meta": {"status": "retiring"}},
        {"id": "gpt-4o-mini", "meta": {"status": "ga"}},
    ],
    "count": 2,
}


def test_resolves_a_nested_index_path():
    assert resolve(PAYLOAD, "$.data[0].meta.status") == "retiring"


def test_resolves_a_top_level_key():
    assert resolve(PAYLOAD, "$.count") == 2


def test_resolves_the_root():
    assert resolve(PAYLOAD, "$") is PAYLOAD


def test_missing_key_raises():
    with pytest.raises(FieldPathError, match="nope"):
        resolve(PAYLOAD, "$.nope")


def test_index_out_of_range_raises():
    with pytest.raises(FieldPathError, match=r"\[9\]"):
        resolve(PAYLOAD, "$.data[9].id")


def test_indexing_a_mapping_raises():
    with pytest.raises(FieldPathError):
        resolve(PAYLOAD, "$.count[0]")


def test_malformed_path_raises():
    with pytest.raises(FieldPathError, match="must start"):
        resolve(PAYLOAD, "data[0]")


def test_reading_a_key_from_a_non_mapping_raises():
    with pytest.raises(FieldPathError, match="non-mapping"):
        resolve(PAYLOAD, "$.count.x")
