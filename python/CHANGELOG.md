# Changelog

All notable changes to `governance-drift` are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-08-19

### Fixed

- **Corrected an inaccurate capability claim in the README.** The install block
  advertised the `[http]` extra as "live Foundry/tenant HTTP sources", which read as a
  `govdrift scan` feature. It is not one: every `scan` argument is typed `Path` and all
  three sources are constructed with `file_fetcher`. The extra installs `httpx` and
  exposes `http_fetcher(url, client)` as a building block for consumers who construct
  sources in Python. The README now states that scope explicitly and notes that a URL
  branch for the CLI is not shipped yet.

### Added

- This changelog.

## [0.1.0] - 2026-08-18

Initial release, extracted from the private reference implementation.

- `govdrift scan` — file-based governance drift detection over an approved inventory
  (YAML), an Azure AI Foundry model-lifecycle payload (JSON), and an optional observed
  tenant payload (JSON).
- Detectors: model retirement (severity scales with days remaining — <=30 critical,
  <=90 high, <=180 medium) and unapproved agents (HIGH by definition).
- Evidence verification: every finding's cited JSON field path is re-resolved against
  the payload it came from before the report is written; findings citing an unresolvable
  path are dropped and counted. Cross-run content digests annotate changed sources
  without dropping their findings.
- Output: Markdown report carrying coverage gaps and the drop count, SARIF 2.1.0 for
  Defender / Sentinel / GitHub code scanning, and `hashes.json` for cross-run tracking.
- Exit code 1 when any finding survives verification, so it doubles as a CI gate.

[0.1.1]: https://github.com/JeremyGracey-AI/governance-drift-researcher/releases/tag/v0.1.1
[0.1.0]: https://github.com/JeremyGracey-AI/governance-drift-researcher/releases/tag/v0.1.0
