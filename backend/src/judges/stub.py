"""Deterministic offline judge — keyed on a labelled GOLD answer key.

Default key is the synthetic Bates self-test (so the whole pipeline + UI + bake-off
run with no API key, and ``from src.judges.stub import judge`` keeps working).
``make_judge(key=...)`` binds the judge to any answer key (e.g. the real CMS bundle),
which lets the demo reproduce the labelled analysis offline and validates the scorer
on real anchors. Honest ("UNVERIFIED") for any proposition outside the key.
"""
from __future__ import annotations

from typing import Optional

from . import base
from ..models import Bundle, Contradiction, EvidenceItem, Judgement, Proposition

_BACKEND = "stub (offline)"


def _build(proposition: Proposition, bundle: Bundle, gold: dict, pleaded_at: dict) -> Judgement:
    g = gold.get(proposition.id)
    if g is None:
        return Judgement(proposition.id, "UNVERIFIED", 0.2, [], [],
                         single_source=False, burden=proposition.burden, backend=_BACKEND)

    verdict = g["verdict"]
    polarity = "contradict" if verdict == "CONTRADICTED" else "support"
    evidence: list[EvidenceItem] = []
    for doc_id, para in g.get("evidence", []):
        doc = bundle.get(doc_id)
        p = doc.para(para) if doc else None
        if not p:
            continue
        etype = base.infer_evidence_type(doc)
        evidence.append(EvidenceItem(doc_id, para, p.text, polarity, etype,
                                     base.weight_for(etype, polarity)))

    contradictions: list[Contradiction] = []
    own_at = pleaded_at.get(proposition.id)
    # A contradicted pleaded allegation: pleaded paragraph vs the contradicting evidence.
    if verdict == "CONTRADICTED" and evidence and own_at:
        pleaded = base.make_anchor(*own_at)
        ev = base.make_anchor(evidence[0].doc_id, evidence[0].para)
        contradictions.append(Contradiction(
            pleaded, ev, g.get("note") or f"Pleaded case contradicted by the evidence at {ev}."))
    # An opposing pleaded proposition (e.g. claimant allegation vs a defence point).
    for other in g.get("contradicts", []):
        other_at = pleaded_at.get(other)
        if other_at and evidence and verdict != "CONTRADICTED":
            ev = base.make_anchor(evidence[0].doc_id, evidence[0].para)
            other_anchor = base.make_anchor(*other_at)
            contradictions.append(Contradiction(
                ev, other_anchor,
                f"Supported by {ev} but denied in the pleading at {other_anchor}."))

    single = g.get("single_source", base.is_single_source(evidence))
    confidence = 0.95 if evidence else (0.9 if verdict == "NOT_ADDRESSED" else 0.4)
    j = Judgement(proposition.id, verdict, confidence, evidence, contradictions,
                  single_source=single, burden=proposition.burden, backend=_BACKEND)
    if g.get("note"):
        j.extra["note"] = g["note"]
    lr = g.get("legal_risk")
    if lr and lr != "NONE":
        j.extra["legal_risk"] = lr      # second axis: legal defeat vs evidential outcome
    return j


def make_judge(*, force_stub: bool = False, model: Optional[str] = None, key=None):
    """Return a stub judge bound to *key* (an ``answer_key.AnswerKey``); defaults to
    the self-test key for backward compatibility."""
    if key is None:
        from ..answer_key import selftest_key
        key = selftest_key()
    return lambda proposition, bundle: _build(proposition, bundle, key.gold, key.pleaded_at)


def judge(proposition: Proposition, bundle: Bundle) -> Judgement:
    """Module-level default judge, bound to the self-test GOLD (back-compat)."""
    from data.selftest.propositions import GOLD, PLEADED_AT
    return _build(proposition, bundle, GOLD, PLEADED_AT)
