"""Bake-off: score each judge against the labelled self-test GOLD.

Validates the scorer itself offline (the stub must hit 100%). With an API key,
compares the real judges (long-context / RAG / argument / numeric).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import ingest, pleadings
from .judges import available, base, get_judge

_SELFTEST = Path(__file__).resolve().parents[1] / "data" / "selftest" / "bundle"


def _doc_of(anchor: str) -> str:
    return anchor.split("¶")[0].strip()


def score_judge(name, judge, bundle, propositions, gold) -> dict:
    j = {p.id: judge(p, bundle) for p in propositions}
    n = len(propositions) or 1
    correct = sum(1 for pid, jd in j.items() if gold.get(pid, {}).get("verdict") == jd.verdict)

    # detects a genuine cross-document contradiction (two different doc ids)
    detects = any(
        any(_doc_of(c.ref_a) and _doc_of(c.ref_b) and _doc_of(c.ref_a) != _doc_of(c.ref_b)
            for c in jd.contradictions)
        for jd in j.values()
    )

    gold_gaps = [pid for pid, g in gold.items() if g.get("verdict") == "NOT_ADDRESSED"]
    gaps_correct = sum(1 for pid in gold_gaps
                       if j.get(pid) and j[pid].verdict == "NOT_ADDRESSED")
    support_fp = sum(1 for pid, jd in j.items()
                     if jd.verdict == "SUPPORTED" and gold.get(pid, {}).get("verdict") != "SUPPORTED")
    anchored = all(
        all(e.quote and e.doc_id and e.para and base.verbatim_ok(e.quote, bundle, e.doc_id)
            for e in jd.evidence)
        for jd in j.values()
    )
    practitioner = (any(jd.contradictions for jd in j.values())
                    and any(e for jd in j.values() for e in jd.evidence))
    backend = next(iter(j.values())).backend if j else ""
    return {
        "name": name, "verdict_accuracy": round(correct / n, 2), "detects_P2_D2": detects,
        "gaps_correct": gaps_correct, "gaps_total": len(gold_gaps), "support_false_pos": support_fp,
        "anchored_verbatim": anchored, "practitioner_output": practitioner, "backend": backend,
    }


def run_bakeoff(judge_names: Optional[list[str]] = None, *,
                force_stub: bool = False, model: Optional[str] = None, key=None) -> list[dict]:
    """Score judges against a labelled answer key. With no *key*, uses the synthetic
    self-test (validates the scorer); pass an ``answer_key.AnswerKey`` for the real
    CMS bundle."""
    if key is None:
        from data.selftest.propositions import GOLD
        bundle = ingest.load_bundle(str(_SELFTEST))
        props = pleadings.seed_propositions()
        gold = GOLD
    else:
        bundle = ingest.load_bundle(key.bundle_dir)
        props = key.propositions
        gold = key.gold
    names = judge_names or available()
    rows = []
    for name in names:
        try:
            judge = get_judge(name, force_stub=force_stub, model=model, key=key)
            rows.append(score_judge(name, judge, bundle, props, gold=gold))
        except Exception as exc:  # a judge that errors shouldn't sink the grid
            rows.append({"name": name, "error": str(exc)})
    return rows


def render_bakeoff(rows: list[dict]) -> str:
    head = f"{'judge':<12} {'acc':>5} {'P2↔D2':>6} {'gaps':>5} {'supFP':>6} {'anchored':>9} {'pract':>6}  backend"
    out = ["Bake-off — judges vs GOLD answer key", "=" * len(head), head, "-" * len(head)]
    for r in rows:
        if "error" in r:
            out.append(f"{r['name']:<12}  ERROR: {r['error']}")
            continue
        out.append(
            f"{r['name']:<12} {r['verdict_accuracy']:>5} {('yes' if r['detects_P2_D2'] else 'no'):>6} "
            f"{(str(r['gaps_correct'])+'/'+str(r.get('gaps_total', 2))):>5} {r['support_false_pos']:>6} "
            f"{('yes' if r['anchored_verbatim'] else 'no'):>9} "
            f"{('yes' if r['practitioner_output'] else 'no'):>6}  {r['backend']}"
        )
    return "\n".join(out)
