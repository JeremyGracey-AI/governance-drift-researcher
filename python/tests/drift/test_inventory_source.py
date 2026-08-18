from __future__ import annotations

from pathlib import Path

import pytest

from governance_drift.models import Extraction
from governance_drift.sources.fetch import file_fetcher
from governance_drift.sources.inventory import InventoryFormatError, YamlInventorySource

FIXTURE = Path(__file__).parent.parent / "fixtures" / "inventory_approved.yaml"


def test_parses_every_agent():
    entries = YamlInventorySource(file_fetcher(FIXTURE)).entries()

    assert [e.agent_id for e in entries] == ["finance-copilot", "hr-bot"]
    assert entries[0].models == ("gpt-4o-2024-08-06",)
    assert entries[0].connectors == ("sharepoint",)
    assert entries[1].connectors == ()


def test_each_entry_cites_a_resolvable_index_path():
    entries = YamlInventorySource(file_fetcher(FIXTURE)).entries()

    assert entries[0].evidence.field_path == "$.agents[0]"
    assert entries[1].evidence.field_path == "$.agents[1]"
    assert entries[0].evidence.extraction is Extraction.STRUCTURED
    assert len(entries[0].evidence.content_sha256) == 64


def test_empty_agents_list_yields_no_entries(tmp_path: Path):
    target = tmp_path / "empty.yaml"
    target.write_text("agents: []\n", encoding="utf-8")

    assert YamlInventorySource(file_fetcher(target)).entries() == ()


def test_missing_agents_key_raises(tmp_path: Path):
    target = tmp_path / "bad.yaml"
    target.write_text("something_else: 1\n", encoding="utf-8")

    with pytest.raises(InventoryFormatError, match="agents"):
        YamlInventorySource(file_fetcher(target)).entries()


def test_agent_missing_a_required_field_raises(tmp_path: Path):
    target = tmp_path / "bad.yaml"
    target.write_text("agents:\n  - owner: nobody\n", encoding="utf-8")

    with pytest.raises(InventoryFormatError, match="agent_id"):
        YamlInventorySource(file_fetcher(target)).entries()


def test_non_list_agents_raises(tmp_path: Path):
    target = tmp_path / "bad.yaml"
    target.write_text("agents: 5\n", encoding="utf-8")

    with pytest.raises(InventoryFormatError, match="list"):
        YamlInventorySource(file_fetcher(target)).entries()


def test_non_mapping_agent_raises(tmp_path: Path):
    target = tmp_path / "bad.yaml"
    target.write_text("agents:\n  - 3\n", encoding="utf-8")

    with pytest.raises(InventoryFormatError, match="mapping"):
        YamlInventorySource(file_fetcher(target)).entries()


def test_absent_models_and_connectors_keys_default_to_empty(tmp_path: Path):
    target = tmp_path / "minimal.yaml"
    target.write_text("agents:\n  - agent_id: a\n    owner: o\n", encoding="utf-8")

    entries = YamlInventorySource(file_fetcher(target)).entries()

    assert entries[0].models == ()
    assert entries[0].connectors == ()


def test_non_list_models_raises(tmp_path: Path):
    target = tmp_path / "bad.yaml"
    target.write_text(
        "agents:\n  - agent_id: a\n    owner: o\n    models: nope\n",
        encoding="utf-8",
    )

    with pytest.raises(InventoryFormatError, match="expected a list"):
        YamlInventorySource(file_fetcher(target)).entries()
