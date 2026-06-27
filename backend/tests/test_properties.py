"""Property-based / metamorphic stress tests — thousands of generated cases, zero tokens.

Instead of one cherry-picked bundle, we procedurally generate many adversarial scenarios
(``src/casegen.py``) and assert INVARIANTS that must always hold — no LLM, no API key, no
pre-labelled answer per case. Each invariant has an independent oracle:

  * solver  — accepted set is conflict-free AND its weight equals an independent exhaustive
              max-weight oracle; output is deterministic.
  * numeric — the z3 path and the pure-Python interval path agree on every random pair.
  * confidence — bounds hold, unanimity pins confidence to 1, plurality is the vote argmax.
  * coverage — the inspected-paragraph count is exact and ``crossed`` tracks the threshold.

A failure here is a real find: either a generator bug or an engine bug.
"""
from __future__ import annotations

import random

import pytest

from src import casegen, coherence, confidence, coverage, numeric_check
from src.ingest import load_bundle
from src.pleadings import seed_propositions

ITERS = 1500


# ----------------------------------------------------------------- oracles
def _hard_pairs(cluster):
    idx = {c.id: i for i, c in enumerate(cluster.claims)}
    return [(idx[e.source], idx[e.target]) for e in cluster.edges
            if e.hard and e.source in idx and e.target in idx]


def _max_weight_oracle(cluster):
    """Independent exhaustive maximum-weight conflict-free subset weight."""
    claims = cluster.claims
    n = len(claims)
    pairs = _hard_pairs(cluster)
    best = 0.0
    for mask in range(1 << n):
        if any((mask >> i & 1) and (mask >> j & 1) for i, j in pairs):
            continue
        w = sum(claims[i].weight for i in range(n) if mask >> i & 1)
        if w > best:
            best = w
    return best


def _accepted_weight(sol):
    return sum(c.weight for c in sol.accepted)


def _is_conflict_free(sol, cluster):
    acc = {c.id for c in sol.accepted}
    return all(not (e.source in acc and e.target in acc)
               for e in cluster.edges if e.hard)


# ----------------------------------------------------------------- solver
def test_solver_conflict_free_and_optimal():
    rng = random.Random(20260627)
    for _ in range(ITERS):
        cl = casegen.random_cluster(rng, max_claims=8)
        sol = coherence.solve_cluster(cl)
        assert _is_conflict_free(sol, cl)
        assert abs(_accepted_weight(sol) - _max_weight_oracle(cl)) < 1e-9
        # accepted and rejected exactly partition the claims
        assert {c.id for c in sol.accepted} | {c.id for c in sol.rejected} \
            == {c.id for c in cl.claims}
        assert len(sol.accepted) + len(sol.rejected) == len(cl.claims)


def test_solver_is_deterministic():
    rng = random.Random(101)
    for _ in range(400):
        cl = casegen.random_cluster(rng, max_claims=9)
        a = coherence.solve_cluster(cl)
        b = coherence.solve_cluster(cl)
        assert {c.id for c in a.accepted} == {c.id for c in b.accepted}


def test_solver_rejects_pleading_dominated_by_heavier_evidence():
    """Archetype: a pleaded claim hard-contradicted by a strictly heavier evidence claim
    is always rejected, and the evidence accepted."""
    rng = random.Random(7)
    for _ in range(500):
        cl, expect_rejected = casegen.dominated_pleading(rng)
        sol = coherence.solve_cluster(cl)
        rejected = {c.id for c in sol.rejected}
        assert expect_rejected <= rejected


# ----------------------------------------------------------------- numeric
def test_numeric_z3_and_interval_paths_agree():
    pytest.importorskip("z3")
    rng = random.Random(99)
    for _ in range(1000):
        pair = casegen.random_numeric_pair(rng)
        z = numeric_check.reconcile(pair, use_z3=True)
        i = numeric_check.reconcile(pair, use_z3=False)
        assert z.status == i.status
        assert z.solver == "z3" and i.solver == "interval"


# ----------------------------------------------------------------- confidence
def test_confidence_invariants():
    rng = random.Random(3)
    for _ in range(2000):
        vs = casegen.random_verdicts(rng)
        c = confidence.panel_confidence(vs)
        assert 0.0 <= c <= 1.0
        assert 0.0 <= confidence.normalized_entropy(vs) <= 1.0
        assert 0.0 <= confidence.margin(vs) <= 1.0
        # plurality winner is an argmax of the vote distribution
        dist = confidence.vote_distribution(vs)
        assert dist[confidence.plurality_verdict(vs)] == max(dist.values())
        # unanimity pins confidence to 1 and entropy to 0
        if len(set(vs)) == 1:
            assert c >= 0.999
            assert confidence.normalized_entropy(vs) == 0.0


def test_confidence_does_not_drop_when_a_dissenter_joins_the_majority():
    rng = random.Random(11)
    for _ in range(800):
        vs = casegen.random_verdicts(rng, k_max=6)
        win = confidence.plurality_verdict(vs)
        i = next((k for k, v in enumerate(vs) if v != win), None)
        if i is None:
            continue
        vs2 = list(vs)
        vs2[i] = win
        assert confidence.panel_confidence(vs2) >= confidence.panel_confidence(vs) - 1e-9


# ----------------------------------------------------------------- coverage
def test_coverage_invariants():
    bundle = load_bundle("data/selftest/bundle")
    props = seed_propositions()
    total = sum(1 for _ in bundle.iter_paras())
    rng = random.Random(5)
    for p in props:
        for _ in range(12):
            th = rng.uniform(0.1, 0.9)
            rep = coverage.coverage_report(p, bundle, threshold=th)
            assert rep.paras_inspected == total
            assert rep.crossed == (rep.max_similarity >= th)
            assert 0.0 <= rep.max_similarity <= 1.0
            assert len(rep.queries) >= 1
