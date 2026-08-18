"""The two evidence checks from the design spec, §8.1.

Re-hashing a payload inside the run that fetched it proves nothing — the
digest was computed from those same bytes moments earlier. So the two checks
here are deliberately different in kind:

(a) Field-path resolution, intra-run. Does the cited path actually exist in
    the payload the finding came from? This catches a detector citing a path
    that is not there. Failure drops the finding.

(b) Source change, cross-run. Does the digest differ from the one the
    previous report recorded for this same source and path? That means the
    upstream source moved under a finding already published. This annotates;
    it never drops, because a changed source is information.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from governance_drift.paths import FieldPathError, resolve

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from governance_drift.models import Evidence, Finding


@dataclass(frozen=True, slots=True)
class VerifyResult:
    """Outcome of verification.

    Attributes:
        kept: Findings that survived check (a).
        dropped: How many findings failed check (a).
        changed_sources: ``hash_key`` values whose digest moved since the
            previous run.
    """

    kept: tuple[Finding, ...]
    dropped: int
    changed_sources: tuple[str, ...]


def hash_key(evidence: Evidence) -> str:
    """Build the stable key under which a digest is recorded across runs.

    Args:
        evidence: The citation.

    Returns:
        ``"{source_uri}#{field_path}"``.
    """
    return f"{evidence.source_uri}#{evidence.field_path}"


def _resolves(evidence: Evidence, payloads: Mapping[str, object]) -> bool:
    """Run check (a) for one citation.

    Args:
        evidence: The citation.
        payloads: Decoded payloads keyed by source URI.

    Returns:
        Whether the cited path resolves.
    """
    if evidence.source_uri not in payloads:
        return False
    try:
        resolve(payloads[evidence.source_uri], evidence.field_path)
    except FieldPathError:
        return False
    return True


def verify(
    findings: Sequence[Finding],
    payloads: Mapping[str, object],
    prior_hashes: Mapping[str, str],
) -> VerifyResult:
    """Apply both checks.

    Args:
        findings: Candidate findings.
        payloads: Decoded payloads keyed by source URI.
        prior_hashes: Digests recorded by the previous run, keyed by
            :func:`hash_key`.

    Returns:
        The kept findings, the drop count, and any changed sources.
    """
    kept: list[Finding] = []
    dropped = 0
    changed: list[str] = []

    for finding in findings:
        if not all(_resolves(ev, payloads) for ev in finding.evidence):
            dropped += 1
            continue
        kept.append(finding)
        for ev in finding.evidence:
            key = hash_key(ev)
            previous = prior_hashes.get(key)
            if previous is not None and previous != ev.content_sha256:
                changed.append(key)

    return VerifyResult(
        kept=tuple(kept),
        dropped=dropped,
        changed_sources=tuple(dict.fromkeys(changed)),
    )
