"""Contradiction handling: the CONTRADICTED (own-goal) verdict.

WHY THIS MODULE EXISTS
----------------------
The base graph pipeline scores each pleaded point on a one-sided scale:
``strong`` / ``medium`` / ``weak`` / ``unsupported``. That scale answers "how
well is this point evidenced?" but it has no concept of evidence that actively
works *against* the pleaded case. In litigation that is the most dangerous
situation of all: a document in your own bundle that defeats a point you have
pleaded (an "own-goal"), or a later signed document that supersedes the term you
are relying on.

This module adds that missing concept. The pipeline already surfaces, for every
claim, a list of ``challenging_evidence`` (findings that cut against the point)
alongside its ``supporting_evidence``. We read that challenging evidence and, on
a plainly-stated rule, promote a weakly-evidenced point to CONTRADICTED instead
of merely "weak". The result is the four-way verdict vocabulary the front end
renders.

THE RULE (read this and you understand the module)
--------------------------------------------------
Given the pipeline's verdict for a point, its robustness score (0..100), its
supporting evidence and its challenging evidence:

  1. CONTRADICTED  - the point is unsupported or weak AND there is a decisive
                     opposing or superseding document (a challenging finding that
                     scores at or above the decisive threshold, or a CONTRADICTS
                     edge from a document the point itself cites) that outweighs
                     whatever support exists. This is the own-goal.
  2. NOT_ADDRESSED - the point is unsupported AND there is no evidence at all,
                     neither for nor against. Nothing in the bundle speaks to it.
  3. SUPPORTED     - the pipeline rated the point strong, or it is robustly
                     evidenced (robustness high) with real supporting evidence.
  4. UNVERIFIED    - everything else: asserted, partly evidenced, but not proven
                     and not contradicted.

The mapper calls :func:`classify_verdict` once per pleaded point to convert the
pipeline's verdict into this vocabulary.
"""
from __future__ import annotations

# A challenging finding at or above this score is treated as decisive: strong
# enough, on its own, to defeat a weakly-evidenced point. (Scores are 0..1.)
DECISIVE_CHALLENGE_SCORE = 0.6

# A point whose robustness is below this is too weak to stand against any
# decisive challenge, regardless of how the individual scores compare.
WEAK_ROBUSTNESS = 50

# A point at or above this robustness, with real supporting evidence, is treated
# as SUPPORTED even if the pipeline did not label it "strong".
SUPPORTED_ROBUSTNESS = 66

VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_CONTRADICTED = "CONTRADICTED"
VERDICT_NOT_ADDRESSED = "NOT_ADDRESSED"
VERDICT_UNVERIFIED = "UNVERIFIED"


def _scores(findings) -> list[float]:
    """Pull the numeric ``score`` off each finding (missing score -> 0.0)."""
    out: list[float] = []
    for f in findings or []:
        s = f.get("score")
        out.append(float(s) if s is not None else 0.0)
    return out


def classify_verdict(report: dict | None,
                     contradict_edge_score: float | None = None) -> str:
    """Map a pipeline claim report to the front-end verdict vocabulary.

    Parameters
    ----------
    report:
        One claim's pipeline report. Relevant keys: ``verdict`` (strong / medium
        / weak / unsupported), ``robustness_score`` (0..100),
        ``supporting_evidence`` and ``challenging_evidence`` (lists of findings,
        each with an optional ``score`` in 0..1).
    contradict_edge_score:
        Optional. Set when a document the point cites is itself the source of a
        CONTRADICTS edge in the graph. It is treated as a decisive challenge.

    Returns one of: SUPPORTED, CONTRADICTED, NOT_ADDRESSED, UNVERIFIED.
    """
    # No report at all: we cannot say anything beyond "asserted but unconfirmed".
    if not report:
        return VERDICT_UNVERIFIED

    robustness = int(report.get("robustness_score", 0) or 0)
    pipeline_verdict = (report.get("verdict") or "").lower()
    supporting = report.get("supporting_evidence") or []
    challenging = report.get("challenging_evidence") or []

    # Strength of the strongest challenge vs the strongest support. The point's
    # own robustness (as a 0..1 value) is folded in on the support side so that a
    # robustly-evidenced point is not toppled by a single mediocre challenge.
    challenge_scores = _scores(challenging)
    if contradict_edge_score is not None:
        challenge_scores.append(contradict_edge_score)
    support_scores = _scores(supporting) + [robustness / 100.0]

    # Is there a challenge strong enough to be decisive on its own?
    decisive_challenge = (
        any(s >= DECISIVE_CHALLENGE_SCORE for s in _scores(challenging))
        or contradict_edge_score is not None
    )
    strongest_challenge = max(challenge_scores or [0.0])
    strongest_support = max(support_scores or [0.0])

    # The challenge "wins" if it is at least as strong as the support, or if the
    # point is simply too weak to stand (robustness below the weak floor).
    challenge_outweighs_support = (
        strongest_challenge >= strongest_support or robustness < WEAK_ROBUSTNESS
    )

    # 1. CONTRADICTED: a decisive opposing/superseding document that outweighs
    #    the support. The point is an own-goal.
    if decisive_challenge and challenge_outweighs_support:
        return VERDICT_CONTRADICTED

    # 2. SUPPORTED: pipeline said "strong", or robust with real support.
    if pipeline_verdict == "strong" or (robustness >= SUPPORTED_ROBUSTNESS and supporting):
        return VERDICT_SUPPORTED

    # 3. NOT_ADDRESSED: unsupported with nothing in the bundle either way.
    if pipeline_verdict == "unsupported" and not supporting and not challenging:
        return VERDICT_NOT_ADDRESSED

    # 4. UNVERIFIED: asserted but neither proven nor contradicted.
    return VERDICT_UNVERIFIED
