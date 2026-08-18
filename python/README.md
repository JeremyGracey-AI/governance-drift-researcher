# governance-drift

**Deterministic AI-agent governance drift detection — evidence-backed findings, stated
coverage gaps, and SARIF output for CI.**

Your organization has an approved baseline of AI agents (which agents, which models, which
connectors) and a reality that drifts from it: vendors retire models that production agents
still pin; agents appear that nobody approved. `governance-drift` detects that drift and
reports it under rules that make the report *trustworthy* — every finding carries a source
URI, JSON field path, and content hash; findings that can't be re-verified are dropped; and
coverage gaps are stated rather than hidden.

This is the Python reference implementation. The same pipeline also runs as a
[Weft graph on WeaveMind Cloud](https://github.com/JeremyGracey-AI/governance-drift-researcher)
(clonable, ~$0.03/run) with a human approval gate.

## Install

```bash
pip install governance-drift          # file-based scan (pyyaml only)
pip install "governance-drift[http]"  # + live Foundry/tenant HTTP sources
```

## Scan

```bash
govdrift scan \
  --inventory approved.yaml \
  --foundry   foundry_models.json \
  --tenant    tenant_observed.json \
  --out       out/
```

Writes `out/<date>-drift.md` (human report), `out/findings.sarif` (SARIF 2.1.0), and
`out/hashes.json` (cross-run source-change tracking). Exit code is `1` if any finding
survived verification, else `0` — so it doubles as a CI gate.

## Governance drift as a GitHub code-scanning check

`govdrift` emits SARIF, which GitHub ingests natively. Drop this in a workflow to turn
unapproved-agent and retired-model findings into code-scanning alerts:

```yaml
- run: govdrift scan --inventory approved.yaml --foundry foundry.json --out out/
  continue-on-error: true          # let SARIF upload run even when drift is found
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: out/findings.sarif
```

## What it checks

- **Model retirement** — a vendor-retiring/deprecated model that an approved agent still
  pins. Severity scales with days remaining (≤30 critical, ≤90 high, ≤180 medium).
- **Unapproved agents** — anything observed in the tenant that isn't in the approved
  baseline. HIGH by definition.

Every finding's evidence is re-resolved against the payload it came from before the report
is written; a finding citing an unresolvable path is dropped and counted. Adapters are
small classes implementing `ChangeSource` / `InventorySource` — Azure AI Foundry model
lifecycle and inventory/tenant JSON-YAML ship today; add your own in ~40 lines.

## License

MIT © Jeremy Gracey
