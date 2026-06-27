"""Argument-graph judge — Toulmin/Dung structure over LLM-extracted claims.

Judge "C" of the bake-off and the differentiator vs plain RAG. Instead of
trusting a model-emitted verdict *label*, this judge asks the model to extract
an argument *structure* for the proposition — GROUNDS (paragraphs whose
evidence supports it) and REBUTTALS (paragraphs whose evidence attacks it) —
then builds a small support/attack graph and DERIVES the verdict from the
graph. That buys explainability (a drawable graph in
``j.extra["argument_graph"]``) and honest load-bearing detection: a claim resting
on one paragraph shows up as a single support node / single-source risk.

Like every LLM judge it reuses ``base.build_judgement`` so verbatim filtering
(hallucinated quotes dropped) and single-source risk are computed identically,
and it falls back to the deterministic offline stub with no key / on any error.
"""
from __future__ import annotations

from typing import Optional

from . import base, stub
from .. import llm
from ..models import Bundle, EvidenceItem, Judgement, Proposition

_SYSTEM = (
    "You are an argumentation analyst building a Toulmin/Dung argument "
    "structure for ONE pleaded proposition over a bundle of documents (each "
    "shown as '### <doc_id> <title>' followed by numbered paragraphs '¶n').\n"
    "Identify GROUNDS — paragraphs whose evidence SUPPORTS the proposition — "
    "and REBUTTALS — paragraphs whose evidence ATTACKS it. Flag any direct "
    "contradiction between two paragraphs.\n"
    "Return ONLY JSON of this exact shape:\n"
    '{"confidence":0.0,'
    '"grounds":[{"doc_id":"04","para":2,"quote":"<verbatim sentence from that doc>"}],'
    '"rebuttals":[{"doc_id":"02","para":3,"quote":"<verbatim sentence from that doc>"}],'
    '"contradictions":[{"ref_a":"04¶2","ref_b":"02¶3","note":"..."}]}\n'
    "Rules: every quote MUST be copied verbatim from the cited document — never "
    "invent or paraphrase one. Leave grounds AND rebuttals EMPTY when the bundle "
    "is silent on the proposition. Do NOT emit a verdict label — the verdict is "
    "derived from the grounds/rebuttals graph, not asserted by you."
)


def _user_prompt(proposition: Proposition, bundle: Bundle) -> str:
    return (
        f"PLEADED PROPOSITION\n"
        f"id: {proposition.id}\n"
        f"party: {proposition.party}\n"
        f"kind: {proposition.kind}\n"
        f"text: {proposition.text}\n\n"
        f"BUNDLE\n{bundle.full_text()}"
    )


def _derive_verdict(supports: int, attacks: int) -> str:
    """Verdict from the support/attack graph (counts after verbatim filtering)."""
    if supports == 0 and attacks == 0:
        return "NOT_ADDRESSED"
    if attacks > supports:
        return "CONTRADICTED"
    return "SUPPORTED"


def _argument_graph(proposition: Proposition,
                    evidence: list[EvidenceItem]) -> dict:
    """A drawable support/attack graph: proposition node + one node per quote."""
    prop_id = f"prop:{proposition.id}"
    nodes: list[dict] = [
        {"id": prop_id, "kind": "proposition", "label": proposition.text}
    ]
    edges: list[dict] = []
    for e in evidence:
        anchor = base.make_anchor(e.doc_id, e.para)
        attack = e.polarity == "contradict"
        nodes.append({
            "id": anchor, "kind": "rebuttal" if attack else "ground",
            "doc_id": e.doc_id, "para": e.para, "quote": e.quote,
            "polarity": e.polarity, "weight": e.weight,
        })
        edges.append({
            "source": anchor, "target": prop_id,
            "label": "attack" if attack else "support",
        })
    return {"nodes": nodes, "edges": edges}


def make_judge(*, force_stub: bool = False,
               model: Optional[str] = None, key=None) -> base.JudgeFn:
    """Return a ``judge(proposition, bundle)`` closure binding *model*/*force_stub*.
    Offline / on error it defers to the stub bound to the same answer *key*."""
    fallback = stub.make_judge(key=key)

    def _judge(proposition: Proposition, bundle: Bundle) -> Judgement:
        if force_stub or llm.active_backend() == "offline stub":
            return fallback(proposition, bundle)
        try:
            text, label = llm.chat(_SYSTEM, _user_prompt(proposition, bundle),
                                    model=model)
            data = llm.parse_json(text)

            # Grounds support; rebuttals attack. Map onto the shared evidence
            # contract so build_judgement does verbatim filtering for us.
            evidence_in: list[dict] = []
            for g in data.get("grounds", []) or []:
                evidence_in.append({**g, "polarity": "support"})
            for r in data.get("rebuttals", []) or []:
                evidence_in.append({**r, "polarity": "contradict"})

            mapped = {
                "verdict": "UNVERIFIED",        # overridden from the graph below
                "confidence": data.get("confidence", 0.5),
                "evidence": evidence_in,
                "contradictions": data.get("contradictions", []),
            }
            j = base.build_judgement(proposition, bundle, mapped, backend=label)

            # Derive the verdict from the FILTERED graph, not a trusted label.
            supports = sum(1 for e in j.evidence if e.polarity == "support")
            attacks = sum(1 for e in j.evidence if e.polarity == "contradict")
            j.verdict = _derive_verdict(supports, attacks)
            j.single_source = base.is_single_source(j.evidence)
            j.extra["argument_graph"] = _argument_graph(proposition, j.evidence)
            return j
        except Exception:
            return fallback(proposition, bundle)

    return _judge


def judge(proposition: Proposition, bundle: Bundle) -> Judgement:
    """Module-level convenience judge with default binding."""
    return make_judge()(proposition, bundle)
