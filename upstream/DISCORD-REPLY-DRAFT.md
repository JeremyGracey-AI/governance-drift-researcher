# Discord reply draft — answering Quentin, 2026-08-20

Context: Quentin Feuillade--Montixi replied in the WeaveMind Discord (#share-your-workflow) to the
2026-08-18 field-report post, asking two things:

1. *"For the mvp branch, did you have any issues?"*
2. *"The mvp and the weavemind cloud are running on two completely different engines and there is
   quite a lot of difference in the language itself too, so I am a bit surprised if you managed to
   run it with the same weft code. Where should I look at for the issue you had on the runtime?"*

He is right about the second one: it was **not** the same weft code. Three variants. Verified before
drafting:

| | mvp branch (`main.weft`) | kind cluster (`main.run-variant.weft`) | Cloud |
|---|---|---|---|
| LLM | `OpenRouterProvider`, `OpenAIProvider`, `LlmParams`, `LlmModerate` | dropped entirely | `LlmConfig` |
| HTTP | `HttpRequest` | `HttpRequest` | none — `ExecPython` + `urllib.request.urlopen` |
| Toggle | — | — | `Boolean` |
| Size | 322 lines | 301 lines | 13,223 chars, cloud-only |

---

## Reply text

Thanks — and you're right to be surprised, it wasn't the same weft code. Three variants, which I
think corroborates what you're saying about the engines.

**mvp branch** (`main.weft`, in the repo): `OpenRouterProvider` / `OpenAIProvider` / `LlmParams` /
`LlmModerate`, and `HttpRequest` for the Semantic Scholar call. The type/wiring compiler was the
best part of the whole exercise — 13 validation passes, Levenshtein did-you-mean, and it caught a
real bug in my port on first compile: `HttpRequest.body: JsonDict | String` refused into a
`JsonDict` port, which is exactly the non-JSON error-page case my original Python client would have
crashed on at runtime.

**Cloud**: rejected every one of those. `LlmConfig` instead of the provider/params pair, no
`HttpRequest` at all — I rewrote the S2 fetch as `ExecPython` with `urllib.request.urlopen`, which
is incidentally how I found that Cloud ExecPython has network egress (I got a 429 from S2, not a
block — worth documenting, since it's also the soft underbelly of the taint-analysis story).

**kind cluster**: `main.run-variant.weft`, also committed — the LLM tail dropped entirely, since
provider creds need the editor.

On the mvp runtime, three things, all in
[UPSTREAM-REPORT.md § Runtime findings](https://github.com/JeremyGracey-AI/governance-drift-researcher/blob/main/UPSTREAM-REPORT.md)
with fuller transcripts in EVALUATION.md § Runtime addendum:

1. Registering during the daemon's initial rollout orphaned an execution — "running, in flight", no
   worker, driven by nobody — when the dispatcher pod got replaced.
2. Cancelling that orphan enqueued a poisoned `storage_sweep` row that retried a "transient
   broker/control-plane fault" every 20s **through daemon restarts**, 503ing project management.
   Manual `DELETE FROM storage_sweep` was the only recovery I found. Durable state cutting both ways.
3. The full platform plus a worker image doesn't fit Docker Desktop's default ~7.7GB VM. Worker
   died, reaper's `kill_pod` failed, in-cluster API went unreachable, all control-plane pods
   restarted together. 16GB didn't save it locally either — kind networking went stale across
   Docker restarts.

Separately, and probably more actionable: I hit a Loom parser bug in my own published page and sent
a PR — https://github.com/WeaveMindAI/weft/pull/16. `parseBrick` splits attributes from positional
content with `t.includes(':')`, so `title="x"` gets absorbed into body text with no error at any
stage (mine rendered raw markup to visitors for a day), and any positional string containing a colon
gets destroyed — `text "Runs 9:00 to 17:00"` comes back with `content: undefined`. Nine tests, six
fail on main.

Genuinely impressed with the compile layer, by the way. "If it compiles, the architecture is sound"
is the part I keep coming back to for other projects — looking forward to seeing where it goes.

---

## Notes on the drafting

- Leads with compiler praise **before** the runtime problems. He asked "did you have any issues";
  the honest answer is that the compile layer was excellent and the runtime wasn't. Burying the
  good half would read as a hit piece.
- Confirms his instinct on the dialects rather than defending the original post's "across all three
  surfaces" phrasing. He is correct, and saying so plainly is cheaper than hedging.
- The Loom PR is one paragraph at the end and flagged as separate — he asked about the mvp runtime,
  so leading with a different bug would be hijacking his question. But he also asked "where should I
  look", and #16 is the thing he could merge today.
