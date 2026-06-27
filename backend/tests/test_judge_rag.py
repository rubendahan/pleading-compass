"""Offline tests for the lexical-RAG judge (judge B)."""
from __future__ import annotations

import json

import src.llm as llm
from src.ingest import load_bundle
from src.judges import rag
from src.pleadings import seed_propositions

BUNDLE = "data/selftest/bundle"


def _props():
    return {p.id: p for p in seed_propositions()}


def test_retrieve_scores():
    b = load_bundle(BUNDLE)
    rows = rag.retrieve(_props()["P1"], b, k=3)
    assert len(rows) <= 3
    scores = [s for _, _, s in rows]
    assert scores == sorted(scores, reverse=True)        # non-increasing
    for doc_id, para, score in rows:
        assert isinstance(doc_id, str)
        assert isinstance(para, int)
        assert isinstance(score, float)


# Verbatim, copied from data/selftest/bundle/04_ws_fujitsu_engineer.md (para 2).
_QUOTE_04_2 = (
    "Support staff at the Centre were able to insert and edit balancing "
    "transactions directly into a branch account remotely, in order to "
    "correct discrepancies identified in the data."
)

_CANNED = json.dumps({
    "verdict": "SUPPORTED",
    "confidence": 0.9,
    "evidence": [
        {"doc_id": "04", "para": 2, "quote": _QUOTE_04_2, "polarity": "support"},
    ],
    "contradictions": [
        {"ref_a": "04¶2", "ref_b": "02¶3", "note": "Defence denies remote access."},
    ],
})


def test_judge_maps_canned(monkeypatch):
    b = load_bundle(BUNDLE)
    # Pretend a real backend is live, and feed the judge a canned model reply.
    monkeypatch.setattr(llm, "active_backend", lambda *a, **k: "anthropic")
    monkeypatch.setattr(llm, "chat", lambda system, user, **k: (_CANNED, "anthropic:test"))

    p2 = _props()["P2"]
    j = rag.make_judge()(p2, b)

    assert j.verdict == "SUPPORTED"
    assert j.evidence                                    # evidence non-empty
    ev = j.evidence[0]
    assert ev.doc_id == "04" and ev.para == 2            # anchored to a real para
    assert ev.quote == _QUOTE_04_2                       # verbatim survived the check
    assert j.backend == "anthropic:test"
    assert j.burden == p2.burden                         # burden stamped
