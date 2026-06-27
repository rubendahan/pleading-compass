"""Judge protocol + shared helpers.

Every judge is a callable ``judge(proposition, bundle) -> Judgement``. These
helpers keep judges honest and consistent: anchors ("04¶3"), verbatim checking
(drop hallucinated quotes), evidence typing/weighting, single-source risk.
"""
from __future__ import annotations

import re
from typing import Callable

from ..models import (Bundle, Contradiction, Document, EvidenceItem, Judgement,
                      Proposition, VERDICTS)

JudgeFn = Callable[[Proposition, Bundle], Judgement]

_TYPE_BY_DOC = {
    "witness": "witness_recollection",
    "expert": "expert_opinion",
    "correspondence": "correspondence",
    "contract": "contemporaneous_doc",
    "pleading": "contemporaneous_doc",
}
_HIGH = {"contemporaneous_doc", "admission", "correspondence"}
_MEDIUM = {"expert_opinion", "witness_recollection"}


def make_anchor(doc_id: str, para: int) -> str:
    return f"{doc_id}¶{para}"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def verbatim_ok(quote: str, bundle: Bundle, doc_id: str) -> bool:
    """True if *quote* appears (normalised) in document *doc_id*."""
    if not quote:
        return False
    doc = bundle.get(doc_id)
    if not doc:
        return False
    hay = _norm(" ".join(p.text for p in doc.paras))
    return _norm(quote) in hay


def infer_evidence_type(doc: Document) -> str:
    return _TYPE_BY_DOC.get(doc.doc_type, "contemporaneous_doc")


def weight_for(ev_type: str, polarity: str) -> str:
    if ev_type in _HIGH:
        return "high"
    if ev_type in _MEDIUM:
        return "medium"
    return "low"


def is_single_source(evidence: list[EvidenceItem]) -> bool:
    docs = {e.doc_id for e in evidence if e.polarity == "support"}
    return len(docs) == 1


def build_judgement(proposition: Proposition, bundle: Bundle, data: dict, *,
                    backend: str) -> Judgement:
    """Map the shared judge JSON contract -> Judgement.

    Drops any quote that is not verbatim in its cited document (anti-
    hallucination), fills evidence type/weight, computes single-source risk,
    and stamps the proposition's burden. Used by all LLM judges so they map
    output identically.
    """
    verdict = str(data.get("verdict", "UNVERIFIED")).upper()
    if verdict not in VERDICTS:
        verdict = "UNVERIFIED"

    evidence: list[EvidenceItem] = []
    for e in data.get("evidence", []) or []:
        doc_id = str(e.get("doc_id", "")).strip()
        try:
            para = int(e.get("para"))
        except (TypeError, ValueError):
            continue
        quote = str(e.get("quote", "") or "").strip()
        doc = bundle.get(doc_id)
        if not doc or not verbatim_ok(quote, bundle, doc_id):
            continue
        polarity = e.get("polarity") or ("contradict" if verdict == "CONTRADICTED" else "support")
        etype = infer_evidence_type(doc)
        evidence.append(EvidenceItem(doc_id, para, quote, polarity, etype, weight_for(etype, polarity)))

    contradictions = [
        Contradiction(str(c.get("ref_a", "")), str(c.get("ref_b", "")), str(c.get("note", "")))
        for c in (data.get("contradictions", []) or [])
        if c.get("ref_a") and c.get("ref_b")
    ]
    try:
        confidence = float(data.get("confidence", 0.5) or 0.5)
    except (TypeError, ValueError):
        confidence = 0.5

    return Judgement(proposition.id, verdict, confidence, evidence, contradictions,
                     single_source=is_single_source(evidence), burden=proposition.burden,
                     backend=backend)
