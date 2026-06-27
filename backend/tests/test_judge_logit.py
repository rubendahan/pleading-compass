"""Offline tests for the logit-confidence judge (NVIDIA Nemotron angle).

No GPU, no model: we inject a fake logits function and assert the judge reads the
four-way verdict distribution correctly (argmax verdict + calibrated confidence), plus
the pure confidence math. The real path loads Nemotron weights locally and reads model
logits over single-token A/B/C/D labels; here we mock that seam.
"""
from __future__ import annotations

from src.answer_key import selftest_key
from src.ingest import load_bundle
from src.judges import logit
from src.judges.stub import make_judge as stub_make_judge
from src.pleadings import seed_propositions

BUNDLE = "data/selftest/bundle"


def test_logit_confidence_pure_math():
    r = logit.logit_confidence([10.0, 0.0, 0.0, 0.0])     # near-certain SUPPORTED
    assert r["verdict"] == "SUPPORTED"
    assert r["confidence"] > 0.99
    assert r["entropy"] < 0.01
    u = logit.logit_confidence([1.0, 1.0, 1.0, 1.0])      # uniform = max uncertainty
    assert abs(u["confidence"] - 0.25) < 1e-6
    assert u["entropy"] > 0.99
    assert abs(u["margin"]) < 1e-9


def test_logit_judge_reads_the_distribution():
    fake = lambda prompt: [0.5, 4.0, 0.2, 0.1]            # favours CONTRADICTED (label B)
    key = selftest_key()
    bundle = load_bundle(BUNDLE)
    judge = logit.make_judge(logits_fn=fake, key=key)
    j = judge(seed_propositions()[0], bundle)
    assert j.verdict == "CONTRADICTED"
    assert j.backend.startswith("logit")
    assert 0.0 <= j.confidence <= 1.0
    assert "dist" in j.extra and "entropy" in j.extra and "margin" in j.extra


def test_logit_judge_defers_to_stub_offline():
    key = selftest_key()
    bundle = load_bundle(BUNDLE)
    judge = logit.make_judge(force_stub=True, key=key)   # no logits_fn, no GPU -> stub
    stub = stub_make_judge(key=key)
    for p in seed_propositions():
        assert judge(p, bundle).verdict == stub(p, bundle).verdict
