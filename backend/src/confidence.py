"""Agreement-calibrated confidence math — disagreement = quantified uncertainty.

The trustworthy-AI core of the ensemble panel (brick #3b). When several
independent judges vote on the same pleaded proposition, the *spread* of their
verdicts is itself the signal: unanimity earns high confidence, a split earns
low confidence. This module turns a list of verdict strings (or ``Judgement``s)
into calibrated numbers — vote distribution, normalised entropy, vote margin,
an agreement label, a deterministic plurality winner, and a single blended
``panel_confidence`` in ``[0, 1]``. Pure, deterministic, dependency-light: no
LLM, no judges, no I/O. The system flags where it is unsure instead of bluffing
(the Luminance-style confidence angle).
"""
from __future__ import annotations

import math
from typing import Iterable

from .models import VERDICTS

__all__ = [
    "vote_distribution",
    "normalized_entropy",
    "margin",
    "agreement_label",
    "panel_confidence",
    "plurality_verdict",
    "summarize",
]


def _priority(verdict: str) -> int:
    """Tie-break rank: lower wins. Canonical order is ``models.VERDICTS``
    (SUPPORTED > CONTRADICTED > NOT_ADDRESSED > UNVERIFIED); unknown verdicts
    rank last so the tie-break stays total and deterministic."""
    try:
        return VERDICTS.index(verdict)
    except ValueError:
        return len(VERDICTS)


def vote_distribution(verdicts: list[str]) -> dict[str, int]:
    """Count of each observed verdict, ordered by canonical priority (then
    alphabetically) so the mapping is deterministic."""
    counts: dict[str, int] = {}
    for v in verdicts:
        counts[v] = counts.get(v, 0) + 1
    return {v: counts[v] for v in sorted(counts, key=lambda v: (_priority(v), v))}


def normalized_entropy(verdicts: list[str]) -> float:
    """Shannon entropy of the verdict mix, normalised to ``[0, 1]``.

    ``0.0`` when the panel is unanimous, ``1.0`` when it is maximally split
    across the observed verdicts. The log base is the number of *observed*
    categories ``k`` (so a clean 2-way split and a clean 3-way split both read
    1.0). Guards: ``n <= 1`` or a single category -> ``0.0``.
    """
    n = len(verdicts)
    if n <= 1:
        return 0.0
    counts = list(vote_distribution(verdicts).values())
    k = len(counts)
    if k <= 1:
        return 0.0
    h = 0.0
    for c in counts:
        p = c / n
        h -= p * math.log(p)
    return min(1.0, max(0.0, h / math.log(k)))


def margin(verdicts: list[str]) -> float:
    """Top share minus runner-up share, in ``[0, 1]``. ``1.0`` when one verdict
    holds every vote; ``0.0`` on an exact top tie."""
    n = len(verdicts)
    if n == 0:
        return 0.0
    counts = sorted(vote_distribution(verdicts).values(), reverse=True)
    top = counts[0] / n
    second = counts[1] / n if len(counts) > 1 else 0.0
    return top - second


def agreement_label(verdicts: list[str]) -> str:
    """Crisp label in {"unanimous", "majority", "split", "tie"}:

    * ``unanimous`` — every judge returned the same verdict.
    * ``tie``       — two or more verdicts share the top vote count.
    * ``majority``  — a unique top verdict held by a strict majority (> n/2).
    * ``split``     — a unique plurality winner but no majority (e.g. 2-1-1).
    """
    n = len(verdicts)
    if n == 0:
        return "split"
    dist = vote_distribution(verdicts)
    if len(dist) == 1:
        return "unanimous"
    top = max(dist.values())
    n_top = sum(1 for c in dist.values() if c == top)
    if n_top >= 2:
        return "tie"
    if top > n / 2:
        return "majority"
    return "split"


def panel_confidence(verdicts: list[str]) -> float:
    """Single calibrated confidence in ``[0, 1]``, high on agreement and low on
    disagreement. Blends inverse normalised entropy with the vote margin, equal
    weight: ``0.5 * (1 - entropy) + 0.5 * margin``. Unanimous -> 1.0; an even
    split -> 0.0. Monotonic: more-agreeing inputs score strictly higher."""
    if not verdicts:
        return 0.0
    conf = 0.5 * (1.0 - normalized_entropy(verdicts)) + 0.5 * margin(verdicts)
    return min(1.0, max(0.0, conf))


def plurality_verdict(verdicts: list[str]) -> str:
    """The winning verdict: most votes wins, ties broken by canonical priority
    (SUPPORTED > CONTRADICTED > NOT_ADDRESSED > UNVERIFIED). Empty input ->
    ``"UNVERIFIED"`` (the honest default)."""
    if not verdicts:
        return "UNVERIFIED"
    dist = vote_distribution(verdicts)
    return max(dist, key=lambda v: (dist[v], -_priority(v)))


def _verdicts_of(judgements: Iterable) -> list[str]:
    return [getattr(j, "verdict", j) for j in judgements]


def summarize(judgements: list) -> dict:
    """Roll a list of ``Judgement``s into the panel summary dict::

        {winner, votes, entropy, margin, confidence, label,
         dissent: [(backend, verdict), ...]}

    ``dissent`` lists the members whose verdict differs from the winner.
    """
    verdicts = _verdicts_of(judgements)
    winner = plurality_verdict(verdicts)
    return {
        "winner": winner,
        "votes": vote_distribution(verdicts),
        "entropy": normalized_entropy(verdicts),
        "margin": margin(verdicts),
        "confidence": panel_confidence(verdicts),
        "label": agreement_label(verdicts),
        "dissent": [
            (getattr(j, "backend", ""), j.verdict)
            for j in judgements
            if getattr(j, "verdict", None) != winner
        ],
    }
