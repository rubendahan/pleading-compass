"""Unit tests for the agreement-calibrated confidence math (brick #3b).

Pure functions, no judges, no I/O. The guiding principle under test:
disagreement = quantified uncertainty — unanimity reads ~1.0, an even split
reads ~0.0, and confidence is monotone in agreement.
"""
from __future__ import annotations

from src import confidence

S = "SUPPORTED"
C = "CONTRADICTED"
N = "NOT_ADDRESSED"
U = "UNVERIFIED"


def test_unanimous_is_certain():
    verdicts = [S, S, S, S]
    assert confidence.normalized_entropy(verdicts) == 0.0
    assert confidence.margin(verdicts) == 1.0
    assert confidence.agreement_label(verdicts) == "unanimous"
    assert confidence.panel_confidence(verdicts) >= 0.99   # near 1.0
    assert confidence.plurality_verdict(verdicts) == S
    assert confidence.vote_distribution(verdicts) == {S: 4}


def test_even_split_is_uncertain():
    verdicts = [S, C]
    assert confidence.normalized_entropy(verdicts) >= 0.99  # ~1.0, maximally split
    assert confidence.panel_confidence(verdicts) <= 0.01    # low confidence
    assert confidence.agreement_label(verdicts) in {"split", "tie"}


def test_panel_confidence_is_monotonic_in_agreement():
    # Strictly higher for more-agreeing inputs (real verdict strings).
    c_unanimous = confidence.panel_confidence([S, S, S, S])
    c_three_one = confidence.panel_confidence([S, S, S, C])
    c_two_two = confidence.panel_confidence([S, S, C, C])
    assert c_unanimous > c_three_one > c_two_two
    assert 0.0 <= c_two_two and c_unanimous <= 1.0


def test_plurality_tie_break_is_deterministic():
    # 1-1 tie: canonical priority SUPPORTED > CONTRADICTED resolves to SUPPORTED,
    # regardless of input order.
    assert confidence.plurality_verdict([C, S]) == S
    assert confidence.plurality_verdict([S, C]) == S
    # NOT_ADDRESSED vs CONTRADICTED tie -> CONTRADICTED (earlier in VERDICTS).
    assert confidence.plurality_verdict([N, C]) == C
    # A clear plurality is unaffected by the tie-break.
    assert confidence.plurality_verdict([U, U, S]) == U


def test_labels_majority_and_split():
    assert confidence.agreement_label([S, S, S, C]) == "majority"   # 75% > 50%
    assert confidence.agreement_label([S, S, C, C]) == "tie"        # top tie
    assert confidence.agreement_label([S, S, C, N]) == "split"      # plurality, no majority


def test_summarize_shape_and_dissent():
    class _J:
        def __init__(self, backend, verdict):
            self.backend = backend
            self.verdict = verdict

    judgements = [_J("a", S), _J("b", S), _J("c", C)]
    out = confidence.summarize(judgements)
    assert out["winner"] == S
    assert out["votes"] == {S: 2, C: 1}
    assert out["label"] == "majority"
    assert 0.0 < out["confidence"] < 1.0
    assert out["dissent"] == [("c", C)]
    assert set(out) == {"winner", "votes", "entropy", "margin", "confidence", "label", "dissent"}
