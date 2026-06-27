"""Offline test for the numeric/temporal ("Z3") judge.

Runs with NO API key and skips entirely if z3 is unavailable. We monkeypatch
``src.llm`` so the judge takes its live (non-stub) path against a canned model
response, then assert the SMT solver catches an arithmetic contradiction and
that the empty-facts case is honestly UNVERIFIED. The canned quotes are copied
VERBATIM from doc 03 (the subpostmaster's witness statement) so they survive
``base.verbatim_ok``.
"""
from __future__ import annotations

import json

import pytest

z3 = pytest.importorskip("z3")  # skip if the solver is not installed

from src import llm
from src.ingest import load_bundle
from src.judges import numeric
from src.models import Proposition

BUNDLE = "data/selftest/bundle"

# Two REAL verbatim substrings of doc 03 — the apparent shortfall vs. the real loss.
_QUOTE_APPARENT = "sometimes of several thousand pounds"          # 03 ¶2
_QUOTE_REAL = "No cash was ever in fact missing from my branch"   # 03 ¶3

_PROP = Proposition(
    "P1", "Horizon shortfalls did not reflect any real loss.",
    "claimant", "allegation", "claimant",
)

# Same (entity, metric) pinned to two incompatible values -> UNSAT -> CONTRADICTED.
_CONTRADICTORY = json.dumps({"facts": [
    {"entity": "branch shortfall", "metric": "amount", "value": 5000.0,
     "unit": "GBP", "doc_id": "03", "para": 2, "quote": _QUOTE_APPARENT},
    {"entity": "branch shortfall", "metric": "amount", "value": 0.0,
     "unit": "GBP", "doc_id": "03", "para": 3, "quote": _QUOTE_REAL},
]})

_EMPTY = json.dumps({"facts": []})


def _patch(monkeypatch, payload: str) -> None:
    monkeypatch.setattr(llm, "active_backend", lambda *a, **k: "anthropic")
    monkeypatch.setattr(llm, "chat", lambda system, user, **kw: (payload, "anthropic:test"))


def test_numeric_contradiction_cites_both_anchors(monkeypatch):
    _patch(monkeypatch, _CONTRADICTORY)
    bundle = load_bundle(BUNDLE)
    j = numeric.make_judge(model="test")(_PROP, bundle)

    assert j.verdict == "CONTRADICTED"
    assert j.backend == "anthropic:test"

    # The contradiction's two refs cover BOTH source anchors.
    assert len(j.contradictions) == 1
    c = j.contradictions[0]
    assert {c.ref_a, c.ref_b} == {"03¶2", "03¶3"}

    # Both incompatible facts surface as 'contradict' evidence on the same anchors.
    anchors = {f"{e.doc_id}¶{e.para}" for e in j.evidence}
    assert {"03¶2", "03¶3"} <= anchors
    assert all(e.polarity == "contradict" for e in j.evidence)


def test_numeric_no_facts_is_unverified(monkeypatch):
    _patch(monkeypatch, _EMPTY)
    bundle = load_bundle(BUNDLE)
    j = numeric.make_judge(model="test")(_PROP, bundle)

    assert j.verdict == "UNVERIFIED"
    assert j.evidence == []
    assert j.contradictions == []
