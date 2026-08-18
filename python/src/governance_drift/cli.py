"""Command-line entry point.

Writes three artifacts into ``--out``: a timestamped Markdown report, a SARIF
log, and ``hashes.json`` — the digests that let the *next* run perform verify
check (b).
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, cast

import yaml

from governance_drift.detectors.model_retirement import ModelRetirementDetector
from governance_drift.detectors.unapproved_agent import UnapprovedAgentDetector
from governance_drift.render.markdown import MarkdownRenderer
from governance_drift.render.sarif import SarifRenderer
from governance_drift.sources.fetch import file_fetcher
from governance_drift.sources.foundry import FoundrySource
from governance_drift.sources.inventory import YamlInventorySource
from governance_drift.sources.tenant import TenantSource
from governance_drift.verify import hash_key, verify

if TYPE_CHECKING:
    from collections.abc import Sequence

    from governance_drift.models import Finding

HASHES_FILE = "hashes.json"


def _parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        The parser.
    """
    parser = argparse.ArgumentParser(prog="govdrift")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="Scan for governance drift")
    scan.add_argument("--inventory", type=Path, default=Path("inventory.yaml"))
    scan.add_argument("--foundry", type=Path, required=True)
    scan.add_argument("--tenant", type=Path, default=None)
    scan.add_argument("--out", type=Path, default=Path("reports"))
    scan.add_argument("--today", type=date.fromisoformat, default=None)
    return parser


def _prior_hashes(out: Path) -> dict[str, str]:
    """Load digests recorded by the previous run.

    Args:
        out: The output directory.

    Returns:
        The mapping, empty on the first run.
    """
    path = out / HASHES_FILE
    if not path.exists():
        return {}
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return {}
    typed = cast("dict[str, object]", loaded)
    return {key: str(value) for key, value in typed.items()}


def _scan(args: argparse.Namespace) -> int:
    """Run a scan and write artifacts.

    Args:
        args: Parsed arguments.

    Returns:
        ``1`` if any finding survived verification, else ``0``.
    """
    # Resolved because Path.as_uri() — the evidence source_uri — rejects
    # relative paths, and the scheduled workflow passes relative ones.
    inventory_path: Path = args.inventory.resolve()
    foundry_path: Path = args.foundry.resolve()
    tenant_arg: Path | None = args.tenant
    tenant_path: Path | None = tenant_arg.resolve() if tenant_arg else None
    out: Path = args.out
    # A calendar date with no clock is exactly what the default needs.
    today: date = args.today or date.today()  # noqa: DTZ011

    out.mkdir(parents=True, exist_ok=True)

    approved = YamlInventorySource(file_fetcher(inventory_path)).entries()
    changes = FoundrySource(file_fetcher(foundry_path)).changes()
    tenant = TenantSource(file_fetcher(tenant_path) if tenant_path else None)
    observed = tenant.entries()

    candidates: list[Finding] = []
    candidates.extend(
        ModelRetirementDetector(today).detect(changes, approved, observed)
    )
    candidates.extend(UnapprovedAgentDetector().detect(changes, approved, observed))

    payloads: dict[str, object] = {
        inventory_path.as_uri(): _load_yaml(inventory_path),
        foundry_path.as_uri(): json.loads(foundry_path.read_bytes()),
    }
    if tenant_path is not None:
        payloads[tenant_path.as_uri()] = json.loads(tenant_path.read_bytes())

    result = verify(candidates, payloads, _prior_hashes(out))

    report = MarkdownRenderer(
        run_date=today,
        tenant_configured=tenant.configured,
        dropped=result.dropped,
        changed_sources=result.changed_sources,
    ).render(result.kept)
    (out / f"{today.isoformat()}-drift.md").write_text(report, encoding="utf-8")
    (out / "findings.sarif").write_text(
        SarifRenderer().render(result.kept), encoding="utf-8"
    )

    digests = {
        hash_key(ev): ev.content_sha256 for f in result.kept for ev in f.evidence
    }
    (out / HASHES_FILE).write_text(
        json.dumps(digests, indent=2, sort_keys=True), encoding="utf-8"
    )

    return 1 if result.kept else 0


def _load_yaml(path: Path) -> object:
    """Decode a YAML file for verification.

    Args:
        path: The file.

    Returns:
        The decoded document.
    """
    decoded: object = yaml.safe_load(path.read_bytes())
    return decoded


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Arguments, or ``None`` to read ``sys.argv``.

    Returns:
        Process exit code.
    """
    args = _parser().parse_args(argv)
    return _scan(args)
