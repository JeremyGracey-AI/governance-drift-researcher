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

## Addendum (2026-08-19): Loom's positional fallback is silent, and it eats content

Everything above concerns Weft. This section concerns **Loom** — specifically
`dashboard/src/lib/ai/loom-parser.ts`, which is in this repository. The Rust compiler is not
implicated anywhere below; these are dashboard findings.

Noted up front so nobody wastes time: ROADMAP's "Centralize parsing and compilation in Rust"
covers this file, and `publish.rs:490-493` already says "the dashboard is the only place that
understands the loom syntax." Everything here is scoped to something small enough to survive
that migration, or to carry over as a test case.

A runnable reproduction is `loom-parser-repro.mjs` in this repo — `tokenizeLine`,
`parseAttributes`, and `parseBrick`'s classifier transcribed verbatim from `main`, with cases.
`node loom-parser-repro.mjs`.

### 1. `attr=` is silently demoted to body text

My published app rendered its own markup to visitors for a day:

```
title="Verify evidence" Every finding is checked against its source data by
SHA-256 hash and JSON path before it reaches the report.
```

Line 42 of the runner page had `title=` where Loom wants `title:`. The mechanism is
`parseBrick`, lines 766-773:

```ts
for (const t of rest) {
    if (t.includes(':') && !t.startsWith('[')) attrTokens.push(t);
    else if (t.startsWith('[') && t.endsWith(']')) attrTokens.push(t);
    else positional.push(parseQuotedString(t));
}
```

The classifier is a substring test for `:`. A token without one is not an error — it is
positional content, joined into `props.content`. So `title="Verify evidence"` became prose and
the card lost its heading. No diagnostic at edit, save, publish, or render.

`state.errors` and `LoomParseError` already exist and are used two lines up for
`Unknown brick` and for `does not accept child blocks`. The channel is there; this path just
does not use it.

### 2. Any positional string containing a colon is destroyed (higher severity)

This one I found reading the classifier, not from my own project, and it is worse. Because the
test is `t.includes(':')` rather than a structural check, a **positional** string with a colon
anywhere in it is classified as an attribute, and `parseAttributes` then splits it at
`indexOf(':')`. Verified output from the repro:

```
src      text "Docs: https://example.com"
content  undefined
props    {"\"Docs":" https://example.com\""}

src      text "Runs 9:00 to 17:00"
content  undefined
props    {"\"Runs 9":"00 to 17:00\""}

src      feature icon:"clock" title:"Scheduled" "Fires at 06:30 UTC"
props    {"icon":"clock","title":"Scheduled","\"Fires at 06":"30 UTC\""}
```

`content` is `undefined` in every case. The text does not render wrong — **it disappears**, and
a garbage attribute takes its place. Times, URLs, ratios, and any prose using a colon all hit
this. Your own quick-reference example `text "Paste your robotic draft below."` is one colon
away from vanishing.

Attribute *values* containing colons are fine (`subtitle:"Note: it is fast"` parses correctly),
because the first colon is the real separator. The bug is specific to positional strings.

### 3. The `=` mistake is predictable, not incidental

Loom is markup-shaped — nested elements, quoted attributes — and binds with `:` where HTML, JSX
and XML all use `=`. Weft itself uses `=` at the outer level (`runDate = Text { value: "..." }`),
in the same project, 338 lines to Loom's 48. The loom in question was generated by your own
Tangle Runner Page Builder across several rounds, which is the sharpest version of the point:
the platform's own author model makes this mistake, and nothing catches it.

### 4. Deployments diverge from the builder with no staleness indicator

To be clear about what is *not* the complaint: `publish.rs:202-219` shows a deployment is a
cloned `projects` row, and that is correct design — a live page should not mutate under visitors
because someone edited the builder.

The gap is that nothing surfaces the divergence. I fixed line 42 in the builder, saved, and the
public endpoint still served the broken loom. No staleness badge, no "republish needed", no
builder-vs-deployment diff. I only caught it because I verified against
`api/v1/publish/by-user/...` rather than the logged-in view. An author who fixes a bug in the
obvious place will reasonably believe it shipped.

### 5. Entering a deployment scope starts a billable run, every time

First reported here as a one-off. It is not: three for three, deterministic. Switching into the
deployment scope — via `Manage` on the deployment row, or the scope switcher — starts a pipeline
run with no confirmation. Each behaved correctly, suspending at the human gate and publishing
nothing, so the governance is sound. But navigating to look at a deployment should not spend the
owner's credits, and there is no way to inspect a live deployment without paying for a run.

### 6. The Overwrite button exists only in the scope where it is rejected

Re-publishing over an existing deployment is documented in `publish.rs:207-210` and works. Finding
it does not.

The deployment row carries an **Overwrite** button, but only when you are viewing the deployment
scope. Clicking it returns:

```
Cannot publish a deployment project. Publish its origin builder project instead.
```

From the builder scope, where publishing *is* permitted, that row shows `Manage | Pause | delete`
and no Overwrite at all. So the control is rendered exactly where the API refuses it and absent
where it would succeed — the same shape as findings 1 and 2, a UI offering an action the backend
will not honour, with nothing reconciling the two.

The path that does work is undiscoverable: go to the builder and, in the form headed **"Publish to
a new URL"**, retype the *existing* slug. That is the documented re-publish path, but the heading
says the opposite of what the action does, and the correct move is visually identical to the
mistake that forks a second deployment at a second URL. Worse, the slug field auto-fills from the
project name, so after renaming a project the prefilled value is a *different* slug than the live
one — the default is the fork, and the safe action requires knowing to overwrite it.

A rename of the Overwrite affordance, or surfacing it on the builder's deployment row where the
API accepts it, would cost very little.

### 7. Public metadata defaults, and a name that cannot be set where it is shown

The deployment's public name defaulted to `Untitled Project` and its SEO description was seeded
from an assistant chat turn ("I added three additional fields into the configuration..."). Both
were public for a day. Publishing should require a name and should not promote conversational text
into public metadata.

Fixing it surfaced a related constraint: `publish.rs:382` is `let project_name = builder.name;`
with no request override, while the line below it takes `req.description.or(project_description)`.
So a deployment's description can be set at publish time but its **name can only be changed by
renaming the builder project** — a rename of something the visitor never sees, in order to change
something they do. Both are now corrected on my deployment via the re-publish path above.

### Why I think this fits your stated direction rather than fighting it

CONTRIBUTING.md, "What not to do": **"Do not add silent fallbacks. Fail loud."** And under the
node design rules: "Surface errors loudly... No silent fallbacks, no guessed defaults for values
the user was supposed to provide." Findings 1 and 2 are that rule being broken in the Loom
parser. I am not proposing a new opinion, I am reporting a place where the code disagrees with
the documented one.

ROADMAP's "Explicit expand / gather" item is the same failure shape you have already decided how
to handle: an implicit mechanism that "AI writers (and humans) confuse", where the expected
behaviour "silently doesn't happen and produces wrong data", fixed by making it explicit and
erroring by default. Loom's positional fallback is that pattern in the dashboard. The same
remedy applies — require positional content to be unambiguous, and error on a bare
`key=value` token instead of absorbing it.

DESIGN.md, "Dense for AI generation": "If the AI keeps making the same mistake, the language
changes to make that mistake harder to express." This is a documented instance of exactly that,
with your own builder as the AI in question.

### Smallest fix that would have caught both

In `parseBrick`'s classifier, treat a bare unquoted token matching `^[a-zA-Z][\w-]*=` as an
error (`Did you mean 'key:'?`), and decide positional-vs-attribute on whether the token *starts*
with an identifier followed by `:` outside quotes, rather than on `includes(':')`. Both are
local to one function and would carry over as test cases when parsing moves to Rust.

Findings 1 and 2 are submitted as [WeaveMindAI/weft#16](https://github.com/WeaveMindAI/weft/pull/16),
with tests. Findings 3-7 are publish-pipeline and UX observations, deliberately kept out of that PR
since it is scoped to the parser — happy to open issues for any subset, or to leave them here.

## Context

The port was authored by an AI from your docs alone — your own stated author model — and
the compile-layer experience largely delivers on it. Happy to share the project export,
open issues for any subset of this, or PR the rule patch. The pipeline this ports is the
reference implementation in this repo; the evaluation with all transcripts is EVALUATION.md.
