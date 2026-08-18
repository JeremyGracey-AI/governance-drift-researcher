from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from governance_drift.cli import main

if TYPE_CHECKING:
    import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _args(out: Path, *, with_tenant: bool) -> list[str]:
    args = [
        "scan",
        "--inventory",
        str(FIXTURES / "inventory_approved.yaml"),
        "--foundry",
        str(FIXTURES / "foundry_models.json"),
        "--out",
        str(out),
        "--today",
        "2026-08-16",
    ]
    if with_tenant:
        args += ["--tenant", str(FIXTURES / "tenant_observed.json")]
    return args


def test_scan_writes_both_artifacts_and_exits_nonzero_on_findings(tmp_path: Path):
    code = main(_args(tmp_path, with_tenant=True))

    report = tmp_path / "2026-08-16-drift.md"
    sarif = tmp_path / "findings.sarif"

    assert code == 1
    assert report.exists()
    assert sarif.exists()

    text = report.read_text(encoding="utf-8")
    assert "gpt-4o-2024-08-06" in text
    assert "shadow-bot" in text

    doc = json.loads(sarif.read_text(encoding="utf-8"))
    rule_ids = {r["ruleId"] for r in doc["runs"][0]["results"]}
    assert rule_ids == {"drift/model-retirement", "drift/unapproved-agent"}


def test_scan_without_tenant_states_the_coverage_gap(tmp_path: Path):
    main(_args(tmp_path, with_tenant=False))

    text = (tmp_path / "2026-08-16-drift.md").read_text(encoding="utf-8")

    assert "tenant adapter not configured" in text
    assert "shadow-bot" not in text


def test_scan_records_hashes_for_the_next_run(tmp_path: Path):
    main(_args(tmp_path, with_tenant=True))

    hashes = json.loads((tmp_path / "hashes.json").read_text(encoding="utf-8"))

    assert any(key.endswith("#$.data[0]") for key in hashes)


def test_second_run_with_unchanged_sources_reports_no_change(tmp_path: Path):
    main(_args(tmp_path, with_tenant=True))
    main(_args(tmp_path, with_tenant=True))

    text = (tmp_path / "2026-08-16-drift.md").read_text(encoding="utf-8")

    assert "No cited source changed since the previous report." in text


def test_clean_inventory_exits_zero(tmp_path: Path):
    inventory = tmp_path / "empty.yaml"
    inventory.write_text("agents: []\n", encoding="utf-8")

    code = main(
        [
            "scan",
            "--inventory",
            str(inventory),
            "--foundry",
            str(FIXTURES / "foundry_models.json"),
            "--out",
            str(tmp_path),
            "--today",
            "2026-08-16",
        ]
    )

    assert code == 0
    assert "No drift detected" in (tmp_path / "2026-08-16-drift.md").read_text(
        encoding="utf-8"
    )


def test_malformed_prior_hashes_are_ignored(tmp_path: Path):
    (tmp_path / "hashes.json").write_text("[]", encoding="utf-8")

    code = main(_args(tmp_path, with_tenant=True))

    assert code == 1


def test_second_run_with_a_changed_source_annotates_the_report(tmp_path: Path):
    foundry = tmp_path / "foundry.json"
    foundry.write_text(
        (FIXTURES / "foundry_models.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    args = [
        "scan",
        "--inventory",
        str(FIXTURES / "inventory_approved.yaml"),
        "--foundry",
        str(foundry),
        "--out",
        str(out),
        "--today",
        "2026-08-16",
    ]

    main(args)
    foundry.write_text(
        foundry.read_text(encoding="utf-8").replace("2026-11-01", "2026-12-01"),
        encoding="utf-8",
    )
    main(args)

    text = (out / "2026-08-16-drift.md").read_text(encoding="utf-8")

    assert "Sources changed since the previous report:" in text
    assert foundry.as_uri() in text


def test_relative_input_paths_are_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(FIXTURES.parent.parent)

    code = main(
        [
            "scan",
            "--inventory",
            "tests/fixtures/inventory_approved.yaml",
            "--foundry",
            "tests/fixtures/foundry_models.json",
            "--out",
            str(tmp_path),
            "--today",
            "2026-08-16",
        ]
    )

    assert code == 1
