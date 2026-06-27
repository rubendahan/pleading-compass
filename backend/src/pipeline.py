"""Orchestration: run a judge over every proposition, aggregate side-aware
practitioner views + deduped cross-document contradictions.

Shared by the CLI and the Streamlit app. The `judge` argument is any
``judge(proposition, bundle) -> Judgement`` callable (stub or an LLM judge).
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Callable, Optional

from . import report
from .models import Bundle, Judgement, Proposition


def analyze(bundle: Bundle, propositions: list[Proposition],
            judge: Callable[[Proposition, Bundle], Judgement], *,
            side: Optional[str] = None, progress=None) -> dict:
    judgements: list[Judgement] = []
    for i, p in enumerate(propositions, 1):
        if progress:
            progress(i, len(propositions), p.id)
        judgements.append(judge(p, bundle))

    props_by_id = {p.id: p for p in propositions}
    backend = judgements[0].backend if judgements else ""
    return {
        "judgements": [asdict(j) for j in judgements],
        "readiness": report.trial_readiness(judgements, side=side),
        "cross_exam": report.cross_exam_points(judgements, props_by_id, side=side),
        "gaps": report.gaps_to_fill(judgements, props_by_id, side=side),
        "load_bearing": report.load_bearing(judgements, props_by_id),
        "contradictions": _dedup_contradictions(judgements),
        "props": {pid: asdict(pr) for pid, pr in props_by_id.items()},
        "side": side,
        "backend": backend,
    }


def _dedup_contradictions(judgements: list[Judgement]) -> list[dict]:
    seen: dict = {}
    for j in judgements:
        for c in j.contradictions:
            key = frozenset({c.ref_a, c.ref_b})
            if key not in seen:
                seen[key] = {"ref_a": c.ref_a, "ref_b": c.ref_b, "note": c.note}
    return list(seen.values())
