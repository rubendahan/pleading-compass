"""Offline tests for the ensemble panel judge (brick #3b).

No API key required. Two scenarios:

1. Unanimous offline — built with ``force_stub=True``, every member judge
   defers to the deterministic stub, so the panel reproduces the stub verdict
   with near-1.0 confidence and an "unanimous" label.
2. Dissent — fake member judges injected via the ``members`` seam return
   differing verdicts; the panel must pick the documented plurality winner, drop
   its confidence, and record the dissenters in ``extra``.
"""
from __future__ import annotations

from src.answer_key import selftest_key
from src.ingest import load_bundle
from src.judges import panel, stub
from src.models import Judgement
from src.pleadings import seed_propositions

BUNDLE = "data/selftest/bundle"


def _fake(backend: str, verdict: str):
    """A minimal injectable member judge returning a fixed verdict."""
    def _judge(proposition, bundle) -> Judgement:
        return Judgement(proposition.id, verdict, 0.9, [], [],
                         burden=proposition.burden, backend=backend)
    return _judge


def test_panel_unanimous_offline_matches_stub():
    key = selftest_key()
    bundle = load_bundle(BUNDLE)
    judge = panel.make_judge(force_stub=True, key=key)
    stub_judge = stub.make_judge(key=key)

    for prop in seed_propositions():
        pj = judge(prop, bundle)
        sj = stub_judge(prop, bundle)

        # Offline every member is the stub, so the panel is unanimous on its verdict.
        assert pj.verdict == sj.verdict
        assert pj.confidence >= 0.99                       # near 1.0
        assert pj.backend.startswith("panel(")
        assert pj.burden == prop.burden

        assert pj.extra["label"] == "unanimous"
        assert pj.extra["entropy"] == 0.0
        assert pj.extra["votes"] == {sj.verdict: len(pj.extra["members"])}
        assert pj.extra["dissent"] == []                   # nobody disagrees


def test_panel_dissent_picks_plurality_and_flags_uncertainty():
    bundle = load_bundle(BUNDLE)
    prop = seed_propositions()[0]

    # Two SUPPORTED vs one CONTRADICTED -> plurality SUPPORTED, but not unanimous.
    members = [
        _fake("fake-A", "SUPPORTED"),
        _fake("fake-B", "SUPPORTED"),
        _fake("fake-C", "CONTRADICTED"),
    ]
    judge = panel.make_judge(members=members)
    j = judge(prop, bundle)

    assert j.verdict == "SUPPORTED"                          # documented plurality winner
    assert j.backend == "panel(3)"
    assert 0.0 < j.confidence < 1.0                          # disagreement lowers confidence
    assert j.extra["label"] == "majority"
    assert j.extra["votes"] == {"SUPPORTED": 2, "CONTRADICTED": 1}
    assert j.extra["dissent"] == [("fake-C", "CONTRADICTED")]
    assert ("fake-A", "SUPPORTED", 0.9) in j.extra["members"]


def test_panel_tie_resolves_by_priority_and_drops_confidence():
    bundle = load_bundle(BUNDLE)
    prop = seed_propositions()[0]

    # 1-1 split: canonical priority SUPPORTED > CONTRADICTED breaks the tie.
    judge = panel.make_judge(members=[_fake("a", "CONTRADICTED"), _fake("b", "SUPPORTED")])
    j = judge(prop, bundle)

    assert j.verdict == "SUPPORTED"
    assert j.confidence <= 0.01                             # even split -> ~0
    assert j.extra["label"] in {"split", "tie"}
    assert ("a", "CONTRADICTED") in j.extra["dissent"]
