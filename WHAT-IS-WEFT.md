# What is Weft? (a primer for readers of this report)

*Original summary by the report author, reflecting Weft's pre-release state as observed
2026-08-18. The authoritative source is the official documentation at
[weavemind.ai/docs](https://weavemind.ai/docs) and the repo at
[github.com/WeaveMindAI/weft](https://github.com/WeaveMindAI/weft).*

**Weft** is an open-source *coordination language* for AI systems, built by
[WeaveMind](https://weavemind.ai) (founder Quentin Feuillade--Montixi). The core idea:
instead of orchestrating LLMs, humans, databases, and APIs with glue code in a
general-purpose language, you declare them as **typed nodes in a dataflow graph**, wire
their ports together, and let a compiler verify the whole architecture before anything
runs. A paired AI builder ("Tangle," cloud-only) writes Weft from plain language.

## The concepts you need for this report

- **Nodes and ports.** A program is node declarations plus connections
  (`target.input = source.output`). Nodes come from a catalog: LLM inference and
  providers, code execution (embedded Python), HTTP, human forms, gates, messaging
  integrations, storage, triggers. Every port is typed; every connection is type-checked.
- **Compile-time architecture checking.** Type mismatches, unwired required inputs,
  cycles, malformed loop shapes, and config errors are refused before execution, usually
  with a message that names the fix. This is the layer our evaluation found genuinely
  strong — and also the layer whose most ambitious marketing claim (flagging unfiltered
  input flowing into a model) is not yet implemented; see the patch in this repo.
- **Branching by null propagation.** There is no if/else. A node whose required input is
  absent (null) is skipped, and the skip cascades down that branch. A **Gate** node closes
  its output when its `pass` input is false — that's how our human approval controls
  publication.
- **Groups and folding.** Any cluster of nodes can collapse into a single node with a
  typed interface, nested arbitrarily — the mechanism meant to keep large graphs legible.
- **Parallelism from types.** Wiring a `List[T]` into a port expecting `T` implicitly
  fans execution out per element and gathers results back (failed lanes become nulls).
- **Humans as nodes.** A `HumanQuery` node suspends the execution, presents a form
  (display fields, approve/reject buttons, text inputs), and resumes with the human's
  answers wired onto its output ports. Suspensions are durable — they survive restarts
  and can wait days.
- **Durable execution.** State is journaled; a crashed or evicted worker rebuilds from
  the journal. Node implementations are compiled Rust; the graph topology itself is data,
  interpreted by an engine inside the per-project worker.
- **Two views, one source.** The same program renders as dense code (for AI authors) and
  as an interactive graph (for humans), kept in sync by the editor.

## Surfaces, as of this writing

Three coexisting incarnations, which matters for reproducing this report: the inactive
`main` branch (v1), the actively rebuilt `mvp` branch (planned August 2026 release; what
our compile-layer evaluation targets), and **WeaveMind Cloud** (app.weavemind.ai, running
a v1-lineage dialect; where our end-to-end run happened). The three do not currently
accept the same source — details in [EVALUATION.md](EVALUATION.md).

## Why this report cares

Weft is the most complete attempt we've seen to move AI-system governance — who can feed
what to a model, what requires human sign-off, what is auditable — from convention and
prompts into a **language and compiler**. That is the bet under evaluation here: not
whether Weft is finished (it says itself it isn't), but whether "enforce in structure,
not in prose" survives contact with a real pipeline. Largely, it does.
