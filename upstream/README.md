# Upstream submission drafts — Loom parser

Drafts for `WeaveMindAI/weft`, kept as the record of what was submitted.

**Status: submitted 2026-08-19 as [WeaveMindAI/weft#16](https://github.com/WeaveMindAI/weft/pull/16)**
from branch `fix/loom-attribute-classifier` on [the fork](https://github.com/JeremyGracey-AI/weft).
The PR body is `PR-DRAFT.md` below, near-verbatim. `ISSUE-DRAFT.md` was the alternative
route and went unused; it is kept because it states the bug without the patch, which is
the more portable description.

These were staged in public *before* submission so the review happened in the open rather
than after the fact.

| File | What it is |
|---|---|
| `ISSUE-DRAFT.md` | Issue text, if the report goes in as an issue |
| `PR-DRAFT.md` | PR title and body, plus the fork-and-push commands |
| `0001-loom-attribute-classifier.patch` | The change itself, `git am`-applicable |
| `DISCORD-REPLY-DRAFT.md` | Reply to Quentin's 2026-08-20 questions on the mvp runtime and the three weft dialects |

## The change

Two silent failures in `dashboard/src/lib/ai/loom-parser.ts`, both from one
substring test (`t.includes(':')`) used to split attributes from positional content:

1. A positional string containing a colon is classified as an attribute and split at
   `indexOf(':')` — `text "Runs 9:00 to 17:00"` loses its content entirely.
2. A `key="value"` token matches no colon and is absorbed into body text — which is how
   `title="Verify evidence"` shipped to visitors of this project's own demo.

The patch classifies on `^[A-Za-z][A-Za-z0-9_.-]*:` and raises a `LoomParseError` naming
the key on a bare `key=`. Same fix covers `parseBrick` and `parsePhase`.

## Verification

Applied to `WeaveMindAI/weft` @ `0f5c2cb`:

- New `loom-parser.test.ts`: 9 tests. **6 fail on clean `main`**, all 9 pass with the patch.
  The other 3 are regression guards for behavior that already worked.
- `pnpm -C dashboard check` — 4850 files, 0 errors, 0 warnings.
- Full `vitest run` — 263 pre-existing failures on `main` *and* on the branch, all
  catalog-dependent (`scripts/catalog-link.sh` not run). Delta: +9 passing, 0 new failures.

Reproduction with no account and no clone: [`loom-parser-repro.mjs`](../loom-parser-repro.mjs)
transcribes the three parser functions verbatim from `main`. `node loom-parser-repro.mjs`.

Background and the full finding list: [`UPSTREAM-REPORT.md`](../UPSTREAM-REPORT.md).

## Before submitting

`weft`'s CONTRIBUTING.md: *"No AI-generated slop. If an AI wrote your PR, read it
yourself first."* These drafts were AI-assisted. Every claim is cited to code or to
executed output so it can be checked — and it should be, by a human, first.
