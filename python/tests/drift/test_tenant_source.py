from __future__ import annotations

from pathlib import Path

import pytest

from governance_drift.sources.fetch import file_fetcher
from governance_drift.sources.tenant import TenantFormatError, TenantSource

FIXTURE = Path(__file__).parent.parent / "fixtures" / "tenant_observed.json"


def test_parses_observed_agents():
    source = TenantSource(file_fetcher(FIXTURE))
    entries = source.entries()

    assert source.configured is True
    assert [e.agent_id for e in entries] == ["finance-copilot", "hr-bot", "shadow-bot"]
    assert entries[2].connectors == ("sharepoint", "email")


def test_entries_cite_resolvable_paths():
    entries = TenantSource(file_fetcher(FIXTURE)).entries()
    assert entries[2].evidence.field_path == "$.value[2]"


def test_unconfigured_source_degrades_to_empty():
    source = TenantSource(None)

    assert source.configured is False
    assert source.entries() == ()


def test_malformed_payload_raises(tmp_path: Path):
    target = tmp_path / "bad.json"
    target.write_text('{"nope": []}', encoding="utf-8")

    with pytest.raises(TenantFormatError, match="value"):
        TenantSource(file_fetcher(target)).entries()


def test_non_array_value_raises(tmp_path: Path):
    target = tmp_path / "bad.json"
    target.write_text('{"value": 5}', encoding="utf-8")

    with pytest.raises(TenantFormatError, match="array"):
        TenantSource(file_fetcher(target)).entries()


def test_non_object_agent_raises(tmp_path: Path):
    target = tmp_path / "bad.json"
    target.write_text('{"value": [3]}', encoding="utf-8")

    with pytest.raises(TenantFormatError, match="object"):
        TenantSource(file_fetcher(target)).entries()


def test_agent_missing_id_raises(tmp_path: Path):
    target = tmp_path / "bad.json"
    target.write_text('{"value": [{"owner": "x"}]}', encoding="utf-8")

    with pytest.raises(TenantFormatError, match="id"):
        TenantSource(file_fetcher(target)).entries()


def test_absent_models_and_connectors_keys_default_to_empty(tmp_path: Path):
    target = tmp_path / "minimal.json"
    target.write_text('{"value": [{"id": "a"}]}', encoding="utf-8")

    entries = TenantSource(file_fetcher(target)).entries()

    assert entries[0].models == ()
    assert entries[0].connectors == ()
    assert entries[0].owner == "unknown"


def test_non_array_models_raises(tmp_path: Path):
    target = tmp_path / "bad.json"
    target.write_text('{"value": [{"id": "a", "models": "nope"}]}', encoding="utf-8")

    with pytest.raises(TenantFormatError, match="expected an array"):
        TenantSource(file_fetcher(target)).entries()
