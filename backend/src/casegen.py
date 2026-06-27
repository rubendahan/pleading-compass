"""Procedural case generator — synthetic scenarios for property-based stress testing.

Generates litigation-shaped instances (coherence clusters, numeric disputes, verdict
panels) from a SEEDED RNG, fully deterministically and with ZERO LLM tokens. Used by
``tests/test_properties.py`` to throw thousands of adversarial cases at the deterministic
engine and check invariants, instead of relying on one hand-built bundle.

The shapes mirror the real engine's contracts (``coherence.CoherenceClaim/Edge/Cluster``,
``numeric_check.DisputedPair``, ``models.VERDICTS``), so a generated case exercises exactly
the same code paths as the Meridian bundle.
"""
from __future__ import annotations

import random

from .coherence import CoherenceClaim, CoherenceCluster, CoherenceEdge
from .models import VERDICTS

# Source-type -> weight, mirroring coherence.SOURCE_WEIGHTS' hierarchy.
_BUNDLE_SOURCES = {
    "witness_statement": 2.0, "solicitor_letter": 1.5, "contemporaneous_email": 4.0,
    "expert_report": 4.0, "defect_log": 4.5, "change_order": 5.0,
    "acceptance_certificate": 5.0,
}
_HARD_RELATIONS = ("contradicts", "supersedes")
_SOFT_RELATIONS = ("supports", "caps", "qualifies", "attacks", "legal_bar")


def _claim(i: int, polarity: str, source_type: str, weight: float) -> CoherenceClaim:
    return CoherenceClaim(
        id=f"c{i}", issue="GEN", text=f"generated claim {i}",
        proposition_id=(f"P{i}" if polarity == "pleading" else None),
        source_doc=(None if source_type == "absence" else f"{10 + i % 80:02d}"),
        source_para=str(1 + i % 30), quote=None, source_type=source_type,
        weight=weight, polarity=polarity,
    )


def random_cluster(rng: random.Random, *, max_claims: int = 8, max_edges: int = 10) -> CoherenceCluster:
    """A random cluster: 1..max_claims claims of mixed polarity/weight, and a handful of
    hard/soft edges between distinct claims (no self-loops)."""
    n = rng.randint(1, max_claims)
    claims = []
    for i in range(n):
        polarity = rng.choices(["pleading", "bundle", "legal_overlay"], weights=[3, 5, 2])[0]
        if polarity == "pleading":
            st, w = "pleading", 1.0
        elif polarity == "legal_overlay":
            st, w = "legal_clause", 4.0
        else:
            st = rng.choice(list(_BUNDLE_SOURCES))
            w = _BUNDLE_SOURCES[st]
        claims.append(_claim(i, polarity, st, w))

    edges = []
    if n >= 2:
        for _ in range(rng.randint(0, max_edges)):
            a, b = rng.sample(range(n), 2)
            hard = rng.random() < 0.55
            rel = rng.choice(_HARD_RELATIONS if hard else _SOFT_RELATIONS)
            edges.append(CoherenceEdge(f"c{a}", f"c{b}", rel, hard, "generated edge", "gen"))
    return CoherenceCluster(issue="GEN", claims=claims, edges=edges)


def dominated_pleading(rng: random.Random):
    """Archetype with a known outcome: a pleaded claim (weight 1) hard-contradicted by a
    strictly heavier evidence claim. Returns ``(cluster, {ids that must be rejected})``.

    Padded with random non-conflicting filler claims so the solver still has to do work.
    """
    ev_src = rng.choice([s for s, w in _BUNDLE_SOURCES.items() if w > 1.0])
    pleaded = _claim(0, "pleading", "pleading", 1.0)
    evidence = _claim(1, "bundle", ev_src, _BUNDLE_SOURCES[ev_src])
    claims = [pleaded, evidence]
    edges = [CoherenceEdge("c1", "c0", "contradicts", True, "heavier evidence rebuts pleading", "gen")]
    for i in range(2, 2 + rng.randint(0, 4)):           # inert filler (no edges)
        claims.append(_claim(i, "bundle", rng.choice(list(_BUNDLE_SOURCES)),
                             _BUNDLE_SOURCES[rng.choice(list(_BUNDLE_SOURCES))]))
    return CoherenceCluster(issue="GEN", claims=claims, edges=edges), {"c0"}


def random_numeric_pair(rng: random.Random):
    """A random pleaded-vs-evidence numeric pair, roughly half consistent / half not."""
    from .numeric_check import DisputedPair
    pleaded = round(rng.uniform(1.0, 1_000_000.0), 2)
    if rng.random() < 0.5:                               # consistent: within ~1%
        evidence = pleaded + rng.choice([-1, 1]) * rng.uniform(0.0, pleaded * 0.01)
    else:                                                # contradictory: far apart
        evidence = pleaded + rng.choice([-1, 1]) * rng.uniform(pleaded * 0.2, pleaded * 2.0)
    tol = rng.uniform(0.0, pleaded * 0.05)
    return DisputedPair("gen", "entity", "metric", pleaded, round(evidence, 2),
                        "02¶1", "03¶1", round(tol, 2))


def random_verdicts(rng: random.Random, *, k_max: int = 7) -> list[str]:
    """A random panel of verdicts (each one of VERDICTS), length 1..k_max."""
    return [rng.choice(VERDICTS) for _ in range(rng.randint(1, k_max))]
