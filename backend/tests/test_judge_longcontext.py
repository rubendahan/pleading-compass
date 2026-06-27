"""Offline test for the long-context judge.

Runs with NO API key: we monkeypatch ``src.llm`` so the judge takes its live
(non-stub) path against a canned model response. Asserts the shared
``build_judgement`` mapping holds — verdict, anti-hallucination (a fabricated
quote is dropped), single-source risk, contradictions, and burden.
"""
from __future__ import annotations

import json

from src import llm
from src.ingest import load_bundle
from src.judges import longcontext
from src.pleadings import seed_propositions

BUNDLE = "data/selftest/bundle"

# A REAL verbatim sentence copied from doc 04 ¶2 (the Fujitsu engineer's WS).
_REAL_QUOTE = (
    "Support staff at the Centre were able to insert and edit balancing "
    "transactions directly into a branch account remotely, in order to correct "
    "discrepancies identified in the data."
)
# A quote that appears in NO document in the bundle -> must be dropped.
_FAKE_QUOTE = (
    "Fujitsu confirmed in writing that remote access to branch accounts was "
    "never technically possible."
)

_CANNED = json.dumps({
    "verdict": "SUPPORTED",
    "confidence": 0.9,
    "evidence": [
        {"doc_id": "04", "para": 2, "quote": _REAL_QUOTE, "polarity": "support"},
        {"doc_id": "04", "para": 5, "quote": _FAKE_QUOTE, "polarity": "support"},
    ],
    "contradictions": [{"ref_a": "04¶2", "ref_b": "02¶3", "note": "x"}],
})


def _props():
    return {p.id: p for p in seed_propositions()}


def test_longcontext_supported_drops_fabricated_quote(monkeypatch):
    # Pretend an Anthropic backend is live, and return the canned JSON.
    monkeypatch.setattr(llm, "active_backend", lambda *a, **k: "anthropic")
    monkeypatch.setattr(llm, "chat", lambda system, user, **kw: (_CANNED, "anthropic:test"))

    bundle = load_bundle(BUNDLE)
    judge = longcontext.make_judge(model="test")
    j = judge(_props()["P2"], bundle)

    assert j.verdict == "SUPPORTED"
    assert len(j.evidence) == 1            # fabricated quote dropped by build_judgement
    assert j.evidence[0].quote == _REAL_QUOTE
    assert j.single_source is True
    assert len(j.contradictions) == 1
    assert j.burden == "claimant"
    assert j.backend == "anthropic:test"
