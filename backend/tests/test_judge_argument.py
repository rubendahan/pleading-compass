"""Offline test for the argument-graph judge (judge C).

Runs with NO API key: we monkeypatch ``src.llm`` so the judge takes its live
(non-stub) path against a canned argument structure. Asserts the verdict is
DERIVED from the grounds/rebuttals graph (not a trusted label), that a single
ground reads as single-source risk, and that the drawable ``argument_graph``
lands in ``j.extra``.
"""
from __future__ import annotations

import json

from src import llm
from src.ingest import load_bundle
from src.judges import argument
from src.pleadings import seed_propositions

BUNDLE = "data/selftest/bundle"

# A REAL verbatim sentence copied from doc 04 ¶2 (the Fujitsu engineer's WS).
_REAL_QUOTE = (
    "Support staff at the Centre were able to insert and edit balancing "
    "transactions directly into a branch account remotely, in order to correct "
    "discrepancies identified in the data."
)


def _props():
    return {p.id: p for p in seed_propositions()}


def _patch(monkeypatch, canned: str) -> None:
    monkeypatch.setattr(llm, "active_backend", lambda *a, **k: "anthropic")
    monkeypatch.setattr(llm, "chat", lambda system, user, **kw: (canned, "anthropic:test"))


def test_argument_grounds_only_is_supported(monkeypatch):
    # P2: one ground, no rebuttals -> graph derives SUPPORTED, single-source.
    canned = json.dumps({
        "confidence": 0.9,
        "grounds": [{"doc_id": "04", "para": 2, "quote": _REAL_QUOTE}],
        "rebuttals": [],
        "contradictions": [],
    })
    _patch(monkeypatch, canned)

    bundle = load_bundle(BUNDLE)
    j = argument.make_judge(model="test")(_props()["P2"], bundle)

    assert j.verdict == "SUPPORTED"
    assert j.single_source is True
    assert len(j.evidence) == 1
    assert j.evidence[0].polarity == "support"
    assert j.backend == "anthropic:test"

    assert "argument_graph" in j.extra
    graph = j.extra["argument_graph"]
    assert len(graph["nodes"]) >= 1
    assert any(n.get("kind") == "proposition" for n in graph["nodes"])
    assert any(e.get("label") == "support" for e in graph["edges"])


def test_argument_silent_bundle_is_not_addressed(monkeypatch):
    # G1: a constructed gap — no grounds, no rebuttals -> NOT_ADDRESSED, no evidence.
    canned = json.dumps({
        "confidence": 0.0,
        "grounds": [],
        "rebuttals": [],
        "contradictions": [],
    })
    _patch(monkeypatch, canned)

    bundle = load_bundle(BUNDLE)
    j = argument.make_judge(model="test")(_props()["G1"], bundle)

    assert j.verdict == "NOT_ADDRESSED"
    assert j.evidence == []
