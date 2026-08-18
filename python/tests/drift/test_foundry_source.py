from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from governance_drift.sources.fetch import file_fetcher
from governance_drift.sources.foundry import FoundryFormatError, FoundrySource

FIXTURE = Path(__file__).parent.parent / "fixtures" / "foundry_models.json"


def test_emits_only_lifecycle_affected_models():
    changes = FoundrySource(file_fetcher(FIXTURE)).changes()

    assert [c.subject for c in changes] == [
        "gpt-4o-2024-08-06",
        "text-embedding-ada-002",
    ]


def test_dated_retirement_carries_its_date_and_path():
    changes = FoundrySource(file_fetcher(FIXTURE)).changes()

    assert changes[0].kind == "model-retirement"
    assert changes[0].effective == date(2026, 11, 1)
    assert changes[0].evidence.field_path == "$.data[0]"
    assert "gpt-4o-2024-11-20" in changes[0].detail


def test_undated_deprecation_has_no_effective_date():
    changes = FoundrySource(file_fetcher(FIXTURE)).changes()

    assert changes[1].effective is None


def test_missing_data_key_raises(tmp_path: Path):
    target = tmp_path / "bad.json"
    target.write_text("{}", encoding="utf-8")

    with pytest.raises(FoundryFormatError, match="data"):
        FoundrySource(file_fetcher(target)).changes()


def test_unparseable_date_raises(tmp_path: Path):
    target = tmp_path / "bad.json"
    target.write_text(
        '{"data": [{"id": "m", "version": "1", "lifecycleStatus": "retiring",'
        ' "deprecationDate": "not-a-date"}]}',
        encoding="utf-8",
    )

    with pytest.raises(FoundryFormatError, match="deprecationDate"):
        FoundrySource(file_fetcher(target)).changes()


def test_non_array_data_raises(tmp_path: Path):
    target = tmp_path / "bad.json"
    target.write_text('{"data": 5}', encoding="utf-8")

    with pytest.raises(FoundryFormatError, match="array"):
        FoundrySource(file_fetcher(target)).changes()


def test_non_object_model_raises(tmp_path: Path):
    target = tmp_path / "bad.json"
    target.write_text('{"data": [3]}', encoding="utf-8")

    with pytest.raises(FoundryFormatError, match="object"):
        FoundrySource(file_fetcher(target)).changes()
