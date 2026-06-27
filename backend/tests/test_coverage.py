"""Coverage report — quantified search proof behind a NOT_ADDRESSED verdict.

Runs on the self-test bundle (always present), so no API key / real CMS data is
needed. Answer key in ``data/selftest/propositions.py`` GOLD:
  * G1 — NOT_ADDRESSED, a CONSTRUCTED gap pleaded NOWHERE in the bundle (the
    clean "genuine absence" case: nothing in the bundle should match it);
  * P1 — SUPPORTED, a proposition the bundle plainly engages with.

The threshold should let an engaged proposition cross while the genuine gap
does not. Assertions are relative/ordering where possible, not brittle floats.
"""
from __future__ import annotations

from src import coverage
from src.ingest import load_bundle
from src.pleadings import seed_propositions

BUNDLE = "data/selftest/bundle"

GAP = "G1"          # GOLD: NOT_ADDRESSED, pleaded nowhere — the genuine absence
SUPPORTED = "P1"    # GOLD: SUPPORTED — the bundle engages with this one


def _setup():
    bundle = load_bundle(BUNDLE)
    props = {p.id: p for p in seed_propositions()}
    return bundle, props


def test_genuine_gap_does_not_cross_threshold():
    bundle, props = _setup()
    rep = coverage.coverage_report(props[GAP], bundle)
    assert rep.crossed is False
    assert rep.paras_inspected > 0
    assert rep.max_similarity < rep.threshold
    assert len(rep.queries) >= 2


def test_supported_proposition_crosses_threshold():
    bundle, props = _setup()
    rep = coverage.coverage_report(props[SUPPORTED], bundle)
    assert rep.crossed is True
    assert rep.max_similarity >= rep.threshold


def test_supported_outscores_the_gap():
    bundle, props = _setup()
    sup = coverage.coverage_report(props[SUPPORTED], bundle)
    gap = coverage.coverage_report(props[GAP], bundle)
    # Relative invariant: an engaged proposition must out-match a genuine gap.
    assert sup.max_similarity > gap.max_similarity


def test_render_contains_prop_id_and_comparison():
    bundle, props = _setup()
    rep = coverage.coverage_report(props[GAP], bundle)
    line = coverage.render_coverage(rep)
    assert isinstance(line, str) and line
    assert GAP in line
    assert "<" in line          # the gap did not cross → "<" comparison shown


def test_top_hits_are_ranked_and_consistent():
    bundle, props = _setup()
    rep = coverage.coverage_report(props[SUPPORTED], bundle, k=5)
    assert len(rep.top_hits) <= 5
    scores = [s for _anchor, s in rep.top_hits]
    assert scores == sorted(scores, reverse=True)        # descending
    anchors = [a for a, _s in rep.top_hits]
    assert len(anchors) == len(set(anchors))             # unique anchors
    # best_anchor / max_similarity agree with the top of top_hits
    # (top_hits scores are rounded for display, so compare at that precision).
    assert rep.best_anchor == rep.top_hits[0][0]
    assert round(rep.max_similarity, 4) == rep.top_hits[0][1]
