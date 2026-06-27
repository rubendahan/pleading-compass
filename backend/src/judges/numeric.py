"""Numeric/temporal consistency judge ("Z3") — formal logic, narrowly applied.

Judge "Z3" of the bake-off. A bonus that complements the text judges: instead
of reasoning in prose, the LLM is asked to extract only *well-typed* NUMERIC and
TEMPORAL facts relevant to the proposition (entity, metric, value/date, source
anchor, verbatim quote). Those facts are loaded into an SMT solver (z3): one
``Real`` variable per ``(entity, metric)`` constrained ``== value``. If the
conjunction is UNSAT — i.e. two facts assert different values for the same
entity/metric — the facts are arithmetically incompatible -> CONTRADICTED,
citing BOTH source anchors. Consistent numeric facts -> SUPPORTED. No numeric
facts -> UNVERIFIED (out of this judge's scope; the text judges decide).

This is deliberately high-precision and non-fragile: it only ever fires on hard
typed contradictions a solver can prove, and degrades gracefully (no key, no
z3, any error -> the deterministic offline stub or an honest UNVERIFIED).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from . import base, stub
from .. import llm
from ..models import Bundle, Contradiction, EvidenceItem, Judgement, Proposition

_SYSTEM = (
    "You are a litigation analyst extracting FORMAL numeric/temporal facts for a "
    "solver. From the bundle, extract ONLY well-typed numeric or temporal facts "
    "that bear on the single pleaded proposition. Each fact must name the entity "
    "it measures, the metric, a numeric value (or an ISO date for temporal "
    "facts), its source doc_id/para, and a quote copied VERBATIM from that "
    "paragraph. Two facts about the same (entity, metric) with different values "
    "are a contradiction the solver will catch — so keep entity/metric labels "
    "consistent across facts that describe the same thing.\n"
    "Return ONLY JSON of this exact shape (empty list if there are no numeric "
    "facts):\n"
    '{"facts":[{"entity":"branch shortfall","metric":"amount","value":1000.0,'
    '"unit":"GBP","date":"2015-06-01","doc_id":"03","para":2,'
    '"quote":"<verbatim>"}]}\n'
    "Never invent or paraphrase a quote; never invent figures. Use \"date\" "
    "(ISO YYYY-MM-DD) instead of \"value\" for temporal facts. Empty \"facts\" "
    "if the proposition raises no numeric/temporal question."
)


@dataclass
class _Fact:
    entity: str
    metric: str
    value: float          # numeric value, or a date rendered to an ordinal
    doc_id: str
    para: int
    quote: str


def _date_ordinal(raw: object) -> Optional[float]:
    """ISO ``YYYY-MM-DD`` -> day ordinal (so dates compare as numbers), else None."""
    try:
        return float(date.fromisoformat(str(raw)).toordinal())
    except (TypeError, ValueError):
        return None


def _facts(data: dict, bundle: Bundle) -> list[_Fact]:
    """Validate the model's facts: typed value, real anchor, verbatim quote."""
    out: list[_Fact] = []
    for f in (data.get("facts") or []):
        entity = str(f.get("entity", "")).strip().lower()
        metric = str(f.get("metric", "")).strip().lower()
        if not entity or not metric:
            continue
        raw_value = f.get("value")
        value = None if raw_value is None else _to_float(raw_value)
        if value is None:
            value = _date_ordinal(f.get("date"))
        if value is None:
            continue
        doc_id = str(f.get("doc_id", "")).strip()
        try:
            para = int(f.get("para"))
        except (TypeError, ValueError):
            continue
        quote = str(f.get("quote", "") or "").strip()
        if not bundle.get(doc_id) or not base.verbatim_ok(quote, bundle, doc_id):
            continue                                   # drop hallucinated quote
        out.append(_Fact(entity, metric, value, doc_id, para, quote))
    return out


def _to_float(raw: object) -> Optional[float]:
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _evidence(fact: _Fact, bundle: Bundle, polarity: str) -> EvidenceItem:
    doc = bundle.get(fact.doc_id)
    etype = base.infer_evidence_type(doc)
    return EvidenceItem(fact.doc_id, fact.para, fact.quote, polarity, etype,
                        base.weight_for(etype, polarity))


def _conflict(group: list[_Fact]) -> Optional[tuple[_Fact, _Fact]]:
    """First pair in *group* whose values differ (the UNSAT witnesses)."""
    for i in range(len(group)):
        for j in range(i + 1, len(group)):
            if abs(group[i].value - group[j].value) > 1e-9:
                return group[i], group[j]
    return None


def _solve(proposition: Proposition, bundle: Bundle, data: dict, z3,
           *, backend: str) -> Judgement:
    facts = _facts(data, bundle)
    if not facts:
        return Judgement(proposition.id, "UNVERIFIED", 0.3, [], [],
                         single_source=False, burden=proposition.burden,
                         backend=backend,
                         extra={"note": "no numeric/temporal facts in scope"})

    # One shared Real per (entity, metric); each fact pins it to its value. A
    # clash of values for the same key makes the conjunction UNSAT — a proven
    # inconsistency the solver, not the prose, decides.
    solver = z3.Solver()
    groups: dict[tuple[str, str], list[_Fact]] = {}
    variables: dict[tuple[str, str], object] = {}
    for f in facts:
        key = (f.entity, f.metric)
        groups.setdefault(key, []).append(f)
        var = variables.setdefault(key, z3.Real(f"{f.entity}|{f.metric}"))
        solver.add(var == f.value)

    if solver.check() == z3.unsat:
        for key, group in groups.items():
            pair = _conflict(group)
            if pair is None:
                continue
            a, b = pair
            ref_a, ref_b = base.make_anchor(a.doc_id, a.para), base.make_anchor(b.doc_id, b.para)
            note = (f"Incompatible {key[1]} for '{key[0]}': "
                    f"{a.value:g} ({ref_a}) vs {b.value:g} ({ref_b}).")
            evidence = [_evidence(a, bundle, "contradict"), _evidence(b, bundle, "contradict")]
            return Judgement(proposition.id, "CONTRADICTED", 0.9, evidence,
                             [Contradiction(ref_a, ref_b, note)],
                             single_source=base.is_single_source(evidence),
                             burden=proposition.burden, backend=backend,
                             extra={"note": note})

    # Consistent numeric facts on the record affirm the proposition's numbers.
    evidence = [_evidence(f, bundle, "support") for f in facts]
    return Judgement(proposition.id, "SUPPORTED", 0.8, evidence, [],
                     single_source=base.is_single_source(evidence),
                     burden=proposition.burden, backend=backend)


def make_judge(*, force_stub: bool = False, model: Optional[str] = None,
               key=None) -> base.JudgeFn:
    """Return a ``judge(proposition, bundle)`` closure binding *model*/*force_stub*.
    Offline / on error it defers to the stub bound to the same answer *key*."""
    fallback = stub.make_judge(key=key)

    def _judge(proposition: Proposition, bundle: Bundle) -> Judgement:
        if force_stub or llm.active_backend() == "offline stub":
            return fallback(proposition, bundle)
        try:
            import z3
        except ImportError:
            return Judgement(proposition.id, "UNVERIFIED", 0.2, [], [],
                             single_source=False, burden=proposition.burden,
                             backend="numeric (z3 unavailable)",
                             extra={"note": "z3-solver not installed"})
        try:
            text, label = llm.chat(_SYSTEM, _user_prompt(proposition, bundle), model=model)
            return _solve(proposition, bundle, llm.parse_json(text), z3, backend=label)
        except Exception:
            return fallback(proposition, bundle)

    return _judge


def _user_prompt(proposition: Proposition, bundle: Bundle) -> str:
    return (
        f"PLEADED PROPOSITION\n"
        f"id: {proposition.id}\n"
        f"party: {proposition.party}\n"
        f"kind: {proposition.kind}\n"
        f"text: {proposition.text}\n\n"
        f"BUNDLE\n{bundle.full_text()}"
    )


def judge(proposition: Proposition, bundle: Bundle) -> Judgement:
    """Module-level convenience judge with default binding."""
    return make_judge()(proposition, bundle)
