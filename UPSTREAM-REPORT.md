# Field report: first external port of a production-shaped pipeline to Weft

*Prepared 2026-08-18 for the WeaveMind team. Companion artifacts: the ported project
("Governance Drift Researcher", ran end-to-end on Cloud, execution 1d1dba5a…), a
declarative-rule patch, and reproduction transcripts. Full evaluation: EVALUATION.md in this repository.*

Your README asks for exactly this kind of feedback, so: I ported a real governance
pipeline (drift detection: sources → detectors → evidence verification → LLM enrichment →
human publish gate, ~20 nodes) to Weft across all three surfaces — the mvp branch compiler,
a local kind cluster, and Cloud — in one night. Here is everything I hit, ordered by what
I'd want to know first if I were you.

## What's genuinely excellent

1. **The mvp type/wiring compiler is beyond PoC grade.** 13 validation passes, Levenshtein
   did-you-mean, prescriptive errors. It caught a real bug in my port on first compile:
   `HttpRequest.body: JsonDict | String` refused into a `JsonDict` port — the non-JSON
   error-page case my original Python client would have crashed on at runtime.
2. **Null propagation as control flow maps beautifully to governance logic.** "No findings →
   skip enrichment" was zero lines. The HumanQuery/Gate publish gate is the
   agents-propose-humans-promote pattern as first-class vocabulary.
3. **The human gate is structurally human on Cloud.** There is no API or URL by which the
   agent that built and ran the project can approve its own output; submission requires a
   minted extension token surface. Whether by design or accident, that is a real
   governance property — I'd document it as a feature.
4. **Per-project catalog vendoring (`weft new` → `nodes/base_catalog/`) is an enterprise
   policy-distribution story** you aren't telling: an org can ship a hardened catalog and
   every project inherits its rules.

## The headline claim needs code or softer wording

README (the "cage" paragraph) says the compiler "won't let the AI … send unfiltered user
input straight into a model." **That analysis doesn't exist in mvp or v1** (validate.rs has
no taint/filter machinery; the hedged phrasing in "What the compiler buys you" is the
accurate one). Empirically: my port wires web-fetched abstracts through a code node into
`LlmInference.prompt` and compiles silently.

**But you've already built the mechanism that makes a first version nearly free.** The
declarative rule grammar's `input_source_type` condition (weft-core/src/node.rs, evaluated
at validate.rs:236-303) is used by zero catalog files today. The attached ~30-line
metadata-only patch (eval/unfiltered-prompt-rule.patch) adds one rule to LlmInference:
wired prompts must come from a Gate or Text node. It refuses my unfiltered edge with a
prescriptive message and admits the corrected LlmModerate → Gate → prompt graph.
Transcripts included. Honest limitation: single-hop, launderable through a Gate whose
value is untrusted — real enforcement needs transitive provenance over the graph traversal
you already run for cycle/reachability analysis. Well-scoped feature, not research.

## Dialect and docs drift (three Wefts exist)

- Cloud rejects mvp-isms (`OpenRouterProvider`, `LlmParams`, `HttpRequest`); mvp rejects
  cloud-isms (`LlmConfig`). Expected pre-release — but the Builder's *editor parser accepts
  syntax the Cloud compiler rejects at run start* (triple-backtick `Text.value` config
  parsed, rendered as a graph, then "Invalid node syntax" server-side). The two-views
  promise has a third, disagreeing party at execution time.
- docs/getting-started.md promises a "subprocess worker + sqlite, no docker" path; the
  shipped mvp daemon requires a kind cluster.
- The docs' secondary human-task surface (`/tasks/<executionId>`) rejects its documented
  parameters; the working URL needs the task-scoped execution id, nodeId, AND an extension
  token (found by reading extension-browser-v1/src).
- "Transpiles to Rust: a native binary, not a graph being interpreted" is half-true: node
  impls are native; topology is a JSON ProjectDefinition fetched per execution and walked
  by the engine.

## Runtime findings (local kind cluster, Docker Desktop VM)

1. Registering during the daemon's initial rollout orphaned an execution ("running, in
   flight," no worker, driven by nobody) when the dispatcher pod was replaced.
2. Cancelling that orphan enqueued a poisoned `storage_sweep` row that retried a
   "transient broker/control-plane fault" every 20s **through daemon restarts** (durable
   state cutting both ways), 503ing project management; manual `DELETE FROM storage_sweep`
   was the only recovery I found.
3. The full platform + a worker image doesn't fit Docker Desktop's default ~7.7GB VM;
   worker died, reaper's kill_pod failed, in-cluster API went unreachable, all control-plane
   pods restarted together. (16GB VM didn't save it locally; kind networking went stale
   across Docker restarts.)
4. Cloud ExecPython has network egress (my S2 call got a 429, not a block) — worth
   documenting, since it's also the taint-analysis story's soft underbelly.

## Addendum (2026-08-19): the Loom half has none of the compile layer's rigor

Everything above concerns Weft. This section concerns **Loom** and the Builder/publish
pipeline, and it is a different story — routing note, since the two are easy to conflate.

For a day, my published app rendered its own markup to visitors as body copy:

```
title="Verify evidence" Every finding is checked against its source data by
SHA-256 hash and JSON path before it reaches the report.
```

Line 42 of the runner page used `title=` where Loom wants `title:`. One of the file's
seven `title` attributes; a scan after the fix returned zero `=` separators anywhere in
the file, so it was the only one. The card also silently lost its heading.

1. **The Loom parser fails silently into content.** A malformed `attr="value"` raised no
   error in the editor, on save, at publish, or at render — it was consumed as the
   element's positional body string and shipped. This is the mirror image of the Builder
   parser finding above: there, the editor accepted what the Cloud compiler rejected;
   here, nothing rejects it at all. The contrast with Weft is the part I'd act on: your
   mvp compiler has 13 validation passes and Levenshtein did-you-mean; Loom has no
   diagnostic for this. **A parse error on `attr=` inside a Loom element, suggesting
   `attr:`, would have caught it at keystroke time.**

2. **The error is predictable, not incidental.** Loom is markup-shaped — nested elements
   with quoted attributes — and uses the one separator markup never uses. HTML, JSX and
   XML all bind attributes with `=`; so does Weft at the outer level
   (`runDate = Text { value: "..." }`), in the same project, 338 lines to Loom's 48.
   Anyone fluent in either neighbour will produce `=` here. The loom in question was
   generated by your own Tangle Runner Page Builder across several rounds, which is the
   sharpest version of the point: the platform's own author model makes this mistake.

3. **Deployments diverge from their builder with no indicator.** I fixed line 42 in the
   builder project, saved, and the public endpoint still served the broken loom — the two
   scopes hold independent frozen copies. Nothing in the UI says a deployment is stale: no
   badge, no "republish needed", no diff. I only caught it because I verified against
   `api/v1/publish/by-user/...` rather than the logged-in view. An author who fixes a bug
   in the obvious place will reasonably believe it shipped.

4. **Opening a deployment scope started a billable run I did not request.** It behaved
   correctly — suspended at the human gate, published nothing — but navigation should not
   spend credits.

5. **Public metadata defaults are poor.** The deployment's public name defaulted to
   `Untitled Project`, and its SEO description appears seeded from an assistant chat turn
   ("I added three additional fields into the configuration..."). Publishing should require
   a name and should not promote conversational text into public metadata.

6. **Loom has no version-controlled representation.** Weft lives in this repo; Loom lived
   only in the cloud project, so it never passed review, diff, or CI — which is exactly why
   a one-character error survived to production in a repo where the Weft half is
   compiler-validated. I have now mirrored it here as `runner-page.loom` and
   `runner-layout.loom`, exported from the publish endpoint, but that is a workaround for a
   missing export/import path, not a fix.

Worth saying plainly, since it is the most useful data point in this report: this is a
*governance drift* researcher whose own interface layer drifted, silently, outside every
governed surface it exists to demonstrate. The Weft half was version-controlled and
compiler-checked and was fine. The Loom half was generated, never diffed, never validated,
and shipped broken. The gap between those two halves is the finding.

Reproduction, derived from the observed instance (a minimal isolated case was not run, to
avoid throwaway deployments on a live account): write any Loom element with a valid
attribute and a positional body string, change one separator from `:` to `=`, save, publish,
and load the public URL. Expected: a parse error naming the line. Actual: the literal text
`attr="value"` in the rendered body.

## Context

The port was authored by an AI from your docs alone — your own stated author model — and
the compile-layer experience largely delivers on it. Happy to share the project export,
open issues for any subset of this, or PR the rule patch. The pipeline this ports is the
reference implementation in this repo; the evaluation with all transcripts is EVALUATION.md.
