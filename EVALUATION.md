# Porting a governed agent pipeline to Weft: an evaluation

**Subject:** [Weft](https://github.com/WeaveMindAI/weft), `mvp` branch, evaluated 2026-08-18
(pre-release; the README says August 2026 release and asks for exactly this kind of feedback).
**Method:** port a real, working governed pipeline — the author's drift-researcher (agent-lab, private reference implementation)
(sources → detectors → evidence check → report → human gate) — plus a live enrichment path
(Semantic Scholar → LLM), and evaluate the language against its own published claims and
design principles. The port was authored by an AI from the repo's docs alone, which is the
language's own stated author model ("the author is an AI with a prompt, not a human with a
manual" — `docs/design-principles.md`).
**Scope honestly stated:** this evaluates the *compile layer* — language, type system,
catalog, validation — where Weft's differentiating claims live. Runtime execution (durable
journal, HumanQuery suspension, the kind-cluster dispatcher) is **not evaluated here**.

## The port

[`main.weft`](main.weft): ~20 nodes, one per Python module of the original —
three source parsers, two detectors, the evidence-check verifier (findings citing
unresolvable field paths are dropped), the Markdown renderer with its coverage-gap
statement, a Semantic Scholar search feeding an LLM migration-impact note, and a
`HumanQuery` → `Gate` publish gate ("agents propose, humans promote"). Compiles to a worker
image in one command.

What mapped beautifully:

- **Null propagation as governance flow.** "No retirement findings → skip the whole
  enrichment branch" is zero lines of code: the S2 query node emits nothing and the branch
  structurally skips. The Python version needs explicit conditionals.
- **The human gate is a first-class node.** `HumanQuery` + `Gate` is the
  propose/promote pattern as *vocabulary*, not convention.
- **The type system caught a real bug on the first compile.** `HttpRequest.body` is
  `JsonDict | String` (APIs answer errors with non-JSON bodies); wiring it into a
  `JsonDict` port was refused with a message that named the fix. The original Python
  client would have thrown at runtime on that exact path. This is their design-principle
  bucket (b) — "refused loudly, naming the fix, before anything runs" — working as
  specified.

What fought back:

- **`ExecPython` is stdlib-only** — no dependency mechanism. The inventory fixture had to
  become JSON because there is no `yaml`. Any real port of Python logic hits this wall
  immediately.
- **No Template node**; string assembly happens in `ExecPython` f-strings, which turns
  every prompt into opaque code the graph can't see (relevant below).
- **Docs/code drift, pre-release but worth flagging:** `docs/getting-started.md` promises
  a "subprocess worker backend and sqlite journal, no cloud, no docker" path; the shipped
  `weft daemon start` help says it "ensures the kind cluster, ingress, images." And the
  README's "your program is a native binary, not a graph being interpreted" is half-true:
  node implementations are natively compiled, but the topology is a JSON
  `ProjectDefinition` fetched per execution and walked by a generic engine
  (`crates/weft-compiler/src/codegen.rs:14-40`, `crates/weft-engine/src/lib.rs:1-5`).

## The headline claim, tested

The launch post and README claim the compiler catches architectural risk:
"It can flag user input reaching a model with no filter" (README, "What the compiler
buys you") — and flatly, in the "it's a cage" paragraph: "The compiler won't let the AI …
send unfiltered user input straight into a model."

**Finding 1 — the capability is not implemented.** The mvp validation pass
(`crates/weft-compiler/src/validate.rs`, 13 checks) contains type, wiring, config, graph-
shape, loop, and trigger rules — no taint tracking, no filter requirement, in mvp or v1.
Empirically: this port wires Semantic Scholar abstracts — arbitrary untrusted web text —
through an `ExecPython` prompt builder straight into `LlmInference.prompt`, and the stock
compiler accepts it without a diagnostic (`eval/transcript-rule-firing.txt`, §1).
The hedged phrasing ("it's the place to enforce") is accurate; the flat assertion is
aspirational.

**Finding 2 — a useful version is 30 lines of shipped machinery away.** Weft already has
a declarative per-node rule system with a closed condition grammar, including
`input_source_type` (`crates/weft-core/src/node.rs`, evaluated at `validate.rs:236-303`)
— used by zero catalog files today. This patch (`eval/unfiltered-prompt-rule.patch`) adds
one rule to `LlmInference`: a wired `prompt` must come from a `Gate` or `Text` node.
Result, with transcripts:

- the unfiltered S2 edge is now **refused at compile time** with a prescriptive message
  (transcript §2);
- the corrected graph — corpus → `LlmModerate` → `Gate` → prompt — **compiles green**
  (transcript §3), so the rule admits the intended pattern rather than rejecting
  everything.

No engine changes; the rule rides the catalog. And because `weft new` copies the catalog
into each project (`nodes/base_catalog/`), an organization can ship a hardened catalog as
*policy* — governance distributed with the vocabulary. That deployment story deserves a
line in their docs; it may be the most enterprise-relevant property the design already has.

**Finding 3 — the precise distance between the demo and the claim.** `input_source_type`
sees only the *direct* upstream node. Two consequences: it over-approximates (any
`ExecPython` source is flagged, trusted or not), and it can be laundered — a `Gate` whose
`value` input carries unmoderated text passes the rule while the text remains unfiltered.
Real enforcement of the README's sentence needs *transitive provenance*: label sources
(HTTP bodies, web search, email) untrusted, propagate through edges, and require a
sanitizing node type on every untrusted→LLM path. The compiler already computes
whole-graph reachability for cycle/output analysis, so the traversal machinery exists;
what's missing is a taint lattice over it and a `provenance`-aware condition in the rule
grammar. That is a well-scoped feature, not a research problem — but until it exists,
"the compiler won't let you" should read "the compiler can be taught to."

## Verdict

The unglamorous claims are the true ones. The type system, port resolution, loop rules,
and error messages are genuinely excellent — closer to a mature compiler's UX than to a
proof of concept, and they caught a real bug in this port before first run. The glamorous
claim — architectural security analysis — is not yet real, but the design has already
paid for the mechanism that makes a first version nearly free, and this evaluation ships
that version as a working patch. For the governed-composition thesis this work belongs to, Weft is the strongest evidence yet that "enforce in structure, not
in prose" can live in a language — and a reminder that the enforcement is only as real
as the code behind the claim.

## Reproduce

```bash
git clone -b mvp https://github.com/WeaveMindAI/weft && cd weft
cargo build -p weft-cli --release
# Weft's builtin catalog is O'Saasy-licensed, so it is not vendored here.
# Recreate a scaffold and drop this project's files into it:
weft new drift-researcher-weft && cd drift-researcher-weft
cp -R /path/to/this/dir/{main.weft,fixtures,eval} .
patch -p1 -d nodes/base_catalog/../.. < eval/unfiltered-prompt-rule.patch  # or apply to nodes/base_catalog/ai/llm/infer/metadata.json by hand
../weft/target/release/weft build            # green (moderated graph)
# revert main.weft's moderation gate to a direct edge -> the rule fires
# remove the rule from the catalog copy -> the same edge compiles silently
```

## Runtime addendum (2026-08-18, late-night attempt)

We tried to run the compiled graph on the local kind-cluster dispatcher. Four findings, in
the order the night delivered them; all from a MacBook-class host with Docker Desktop's
default ~7.7 GB VM:

1. **The mvp daemon is Kubernetes-first, contradicting its own getting-started doc.**
   `weft daemon start` builds a kind cluster, ingress, envoy gateway, Postgres, and a
   broker — the promised docker-free subprocess+sqlite path does not exist in the shipped
   mvp CLI.
2. **Pod-swap orphan.** Registering + running during the daemon's initial rollout landed
   the execution on a dispatcher pod that was immediately replaced; the execution row
   survived in Postgres as "running, in flight" with no worker, driven by nobody.
3. **A poisoned terminate sweep survives restarts.** Cancelling that orphan enqueued a
   cleanup in `storage_sweep` that retried a "transient broker/control-plane fault" every
   20 s, indefinitely, through daemon restarts (durable state cutting both ways), while
   the control plane answered 503 to project management calls. Manual
   `DELETE FROM storage_sweep` was the only recovery we found.
4. **Resource floor.** With the sweep cleared, the worker pod (a full Rust+PyO3 image)
   spawned and died under VM memory pressure; the reaper's `kill_pod` failed; the in-
   cluster API server became intermittently unreachable and all control-plane pods
   restarted together. The platform (Postgres + broker + dispatcher + envoy + ingress +
   object store + worker) does not fit a default Docker Desktop VM alongside its own
   BuildKit cache.

None of this contradicts the compile-layer verdict — but it sharpens the overall one: the
language and compiler are further along than the launch material's modest tone suggests,
and the runtime platform is earlier than its confident tone suggests. Next attempt:
raise the Docker VM to 12-16 GB and rerun; the graph itself is compiled, registered, and
ready. The run-variant `main.weft` used for this attempt swaps the LLM/moderation tail
(needs editor-configured credentials) for a Semantic Scholar literature appendix and ends
at the HumanQuery publish gate — durable suspension is the demo, when the platform holds.

## Cloud-run addendum (2026-08-18, ~03:00): the graph ran end to end on WeaveMind Cloud

After the local kind cluster proved unrunnable on a laptop VM, the same pipeline was ported
to app.weavemind.ai's Builder and **executed end to end** (project "Governance Drift
Researcher", execution 1d1dba5a…, cost $0.03). Findings from the working system:

1. **The cloud runs a different dialect than the mvp branch.** No `OpenRouterProvider` /
   `LlmParams` / `HttpRequest` in the cloud catalog; LLM wiring goes through `LlmConfig`.
   Three Wefts now exist (main-v1, mvp, cloud) and none fully agree.
2. **The Builder's editor parser accepts syntax the cloud compiler rejects.** Triple-backtick
   multi-line `Text.value` config parsed and rendered as a graph in the editor, then failed
   server-side at run start ("Invalid node syntax"). The two-views-one-truth story has a
   third, disagreeing party at execution time. (Also: the docs' secondary human-task surface,
   `/tasks/<executionId>`, rejects its documented parameters; the browser extension is the
   only working way to answer a HumanQuery.)
3. **What ran, ran honestly.** All 15 compute nodes completed: detectors produced the exact
   expected findings (gpt-4o-2024-08-06 HIGH severity at 77 days; shadow-bot unapproved),
   the evidence check kept both, the Semantic Scholar call reached the API and got 429-rate-
   limited (cloud ExecPython *does* have network egress; my inline urllib had no backoff —
   the client library this port is based on exists precisely because of that), and the LLM,
   told to use ONLY the literature, correctly reported that no literature was available
   rather than fabricating. The rendered report suspended at the HumanQuery publish gate.
4. **The human gate is structurally human.** The pending approval can only be submitted
   from the browser extension by a signed-in person — no API, no URL, no way for the
   agent driving the browser to approve its own report. Accidental or not, that is
   "agents propose, humans promote" enforced by the platform's own architecture, and it is
   the strongest single piece of evidence in this evaluation that the governed-composition
   bet (Scout Compass's founding invariant: agents propose, humans promote) can live in a
   language runtime rather than in convention.
