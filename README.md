# Governance Drift Researcher

**A deterministic drift researcher that answers: what changed in the approved AI-agent
landscape, what is affected, what evidence supports it, and what is the safest next
action — and publishes nothing until a human approves.**

Every organization running AI agents has an approved baseline (which agents, which
models, which connectors) and a reality that drifts away from it: vendors retire models
that production agents still pin; agents appear that nobody approved. This pipeline
detects that drift and reports it under rules that make the report *trustworthy*:

- **Every finding carries verifiable evidence** — source URI, JSON field path, and the
  content hash of the exact bytes it was derived from.
- **Findings that can't be re-verified are dropped**, and the report says how many.
- **Coverage gaps are stated, not hidden** — "absence of tenant findings does not mean
  the tenant is clean."
- **Nothing publishes without human sign-off.** The pipeline suspends at an approval
  gate; a human reads the draft, approves or rejects, and the decision (with notes) is
  in the audit trail. *Agents propose, humans promote.*

![The pipeline as a live graph](images/1-builder-graph-run-live.jpg)

## Try it

**[Clone it on WeaveMind Cloud →](https://app.weavemind.ai/community/9be42678-5f9f-42ae-8ca8-0c0b1ee623d3)**
(community gallery, by `gracey_dev`) — one click into your own projects. A full run costs about **$0.03**. This repo carries the
same program as source: [`main.weft`](main.weft) (~20 nodes, Weft mvp dialect;
[`main.run-variant.weft`](main.run-variant.weft) is the credential-free variant).

**Or run it as a Python CLI** — `pip install governance-drift`, then `govdrift scan` emits
SARIF straight into GitHub code scanning. See [`python/`](python/).

## How it works

```
foundry feed ─┐
inventory ────┼→ parsers → detectors ──→ evidence check ──→ report renderer ─→ HUMAN ─→ gate ─→ publish
tenant feed ──┘   (model retirement,      (re-resolve every    (coverage gaps,   approval
                   unapproved agents)      cited field path;     severity-ranked
                                           drop what fails)      findings)
                        Semantic Scholar ─→ LLM migration note ──↗
```

- **Detectors**: model-retirement (severity from days-to-retirement: ≤30 critical,
  ≤90 high, ≤180 medium) and unapproved-agent (anything observed outside the baseline
  is HIGH by definition).
- **Enrichment**: literature context from the Semantic Scholar API feeds an LLM that
  drafts a migration-impact note — instructed to treat retrieved text as data, never
  instructions, and observed (in the live run) refusing to fabricate when the literature
  fetch failed.
- **The human gate is structural.** On WeaveMind Cloud there is no API by which the agent
  that built the pipeline can approve its own report — submission requires a
  human-held surface. Governance enforced by architecture, not by prompt.

![All nodes green, suspended at the human gate](images/2-execution-all-nodes-human-gate.jpg)
![The approval form holding the drafted report](images/3-approval-form-with-report.jpg)

The reference implementation (pure Python, same detectors and evidence rules, marimo
notebook + test suite) lives in the author's agent-lab; this is its first port to a
coordination language.

## Field report: what we learned porting this to Weft

This pipeline is also the vehicle for the **first external evaluation of
[Weft](https://github.com/WeaveMindAI/weft)** (pre-release), written the same way the
pipeline writes its reports — claims with evidence, failures with root causes:

- **[WHAT-IS-WEFT.md](WHAT-IS-WEFT.md)** — two-minute primer on the language.
- **[EVALUATION.md](EVALUATION.md)** — the full evaluation: a compile layer that caught a
  real bug on first compile; the flagship "unfiltered input → model" claim tested (not
  implemented — so we implemented it: a [~30-line rule patch](eval/unfiltered-prompt-rule.patch)
  that refuses the unfiltered edge and admits the moderated one, with
  [transcripts](eval/transcript-rule-firing.txt)); three coexisting dialects; four
  runtime findings from a local cluster; and the end-to-end Cloud run behind the
  screenshots above.
- **[UPSTREAM-REPORT.md](UPSTREAM-REPORT.md)** — the findings as prepared for the
  WeaveMind team, strengths first.

*Method: claims carry evidence (file:line citations, committed transcripts, screenshots
of live runs); failures are reported with root causes; the subject is measured against
its own published claims. Weft is O'Saasy-licensed; its catalog is deliberately not
vendored here — `weft new` regenerates it.*
