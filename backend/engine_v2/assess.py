"""Phase 2 — per-proposition structured assessment.

For each proposition: take its pleading claim and the top-K evidence the graph
linked to it, run the general contradiction classifier and a lexical support
score over them, and decide the verdict + legal overlay + the single best
verbatim controlling quote. Offline, this is a deterministic lexical-coverage
scorer; with a key, Claude (``claude-haiku-4-5``) adds a self-confidence signal.
Calibration + the VERIFY flag are delegated to ``safety``.
"""
from __future__ import annotations

from . import safety
from .contradiction import classify
from .lexical import best_quote, coverage_search, similarity, verbatim_ok
from .llm import LLM, MODEL_PER_CLAIM
from .models import Assessment, Bundle, ClaimNode, Graph

SUPPORT = 0.55
ENGAGE = 0.30

# mechanism -> overlay, highest priority first
_OVERLAY_PRIORITY = ["SUPERSEDED", "CONTRACTUALLY_BARRED", "CAPPED",
                     "CAUSATION_PROBLEM", "BURDEN_PROBLEM", "NONE"]


def _overlay_for(mechanism: str, finding_rel: str, has_pct: bool) -> str:
    if mechanism == "supersession" or finding_rel == "supersedes":
        return "SUPERSEDED"
    if mechanism == "contractual-allocation" or finding_rel == "legal_bar":
        return "CONTRACTUALLY_BARRED"
    if mechanism == "contractual-cap" or finding_rel == "caps":
        return "CAPPED"
    if mechanism == "numeric-disjoint" and has_pct:
        return "CAUSATION_PROBLEM"
    return "NONE"


def _pick_overlay(overlays: list[str]) -> str:
    for o in _OVERLAY_PRIORITY:
        if o in overlays:
            return o
    return "NONE"


def _llm_self_conf(claim: ClaimNode, candidates, llm: LLM) -> float | None:
    if not llm.available():
        return None
    ev_lines = "\n".join(f"- [{ev.anchor}] {ev.text}" for ev, _ in candidates[:6])
    out = llm.structured(
        instruction=(
            "Assess whether the bundle SUPPORTS, CONTRADICTS, does NOT address, "
            "or leaves UNVERIFIED the pleaded claim. Give your confidence in [0,1].\n\n"
            f"CLAIM: {claim.text}\nEVIDENCE:\n{ev_lines}"
        ),
        schema={
            "type": "object", "additionalProperties": False,
            "properties": {
                "verdict": {"type": "string", "enum": list(safety.VERDICTS)},
                "confidence": {"type": "number"},
            },
            "required": ["verdict", "confidence"],
        },
        model=MODEL_PER_CLAIM, max_tokens=200,
    )
    if out and isinstance(out.get("confidence"), (int, float)):
        return float(out["confidence"])
    return None


def assess(graph: Graph, claims: list[ClaimNode], bundle: Bundle,
           propositions: list[dict], *, llm: LLM, offline: bool = True,
           pleading_tab: str = "02") -> dict[str, Assessment]:
    claim_by_prop: dict[str, ClaimNode] = {}
    for c in claims:
        claim_by_prop.setdefault(c.prop_id, c)
    party = {d.id: d.party for d in bundle.docs}

    results: dict[str, Assessment] = {}
    for prop in propositions:
        pid = prop["id"]
        claim = claim_by_prop.get(pid)
        if claim is None:  # should not happen — coverage guarantees a claim
            results[pid] = Assessment(pid, "UNVERIFIED", "NONE", "", "", 0.0, True,
                                      ["no_claim_extracted"])
            continue

        candidates = graph.links.get(claim.id, [])
        supports, contras, votes, overlays = [], [], [], []
        for ev, _emb in candidates:
            lex = similarity(claim.text, ev.text)
            find = classify(claim.text, ev.text,
                            evidence_party=party.get(ev.doc_id, "neutral"), llm=llm)
            if find.is_contradiction:
                has_pct = "%" in claim.text or "%" in ev.text
                overlays.append(_overlay_for(find.mechanism, find.rel, has_pct))
                contras.append((ev, find, lex))
                votes.append("CONTRADICTED")
            else:
                supports.append((ev, lex))
                votes.append("SUPPORTED" if lex >= ENGAGE else "NOT_ADDRESSED")

        supports.sort(key=lambda r: (-r[1], -r[0].source_strength, r[0].anchor))
        contras.sort(key=lambda r: (-r[1].hard, -r[0].source_strength, -r[2], r[0].anchor))
        best_support = supports[0][1] if supports else 0.0
        # A precise deterministic surfacer (numeric/supersession/allocation/negation)
        # is trustworthy and flips the point. An LLM-only "contradicts" must be ON-POINT
        # (retrieved with real similarity) to count, and strong corroboration beats it —
        # this is what stops the engine crying "contradicted" over genuinely supported points.
        det_hard = [c for c in contras if c[1].hard and c[1].deterministic]
        relevant_contras = [c for c in contras if c[2] >= ENGAGE]
        hard_contras = det_hard

        coverage = None
        if det_hard:
            verdict = "CONTRADICTED"
            ev, _f, _ = det_hard[0]
        elif best_support >= SUPPORT:
            verdict = "SUPPORTED"
            ev = supports[0][0]
        elif relevant_contras:
            verdict = "CONTRADICTED"
            ev, _f, _ = relevant_contras[0]
        elif best_support >= ENGAGE:
            verdict = "UNVERIFIED"
            ev = supports[0][0]
        else:
            verdict = "NOT_ADDRESSED"
            ev = None
            coverage = coverage_search(claim.text, bundle, exclude_tab=pleading_tab)

        # controlling quote (verbatim substring of the cited paragraph)
        if ev is not None:
            quote = best_quote(claim.text, ev.text)
            anchor = ev.anchor
            if not verbatim_ok(quote, ev.text):      # drop a non-verbatim quote
                quote, anchor = "", ""
        else:
            quote, anchor = "", ""

        # evidence list + single-source
        used = contras if verdict == "CONTRADICTED" else supports
        ev_anchors = [(e.doc_id, e.para) for e, *_ in used[:3]]
        if verdict == "CONTRADICTED":
            distinct = len({e.doc_id for e, _f, _l in contras})
        else:
            distinct = len({e.doc_id for e, lex in supports if lex >= ENGAGE})
        single_source = distinct <= 1
        ambiguous = bool(supports and contras and supports[0][1] >= 0.4)

        overlay = _pick_overlay(overlays + ["NONE"])
        if verdict == "SUPPORTED" and overlay not in ("CAPPED", "CONTRACTUALLY_BARRED"):
            overlay = "NONE"        # don't paint a supersession/causation overlay on a supported point
        llm_conf = _llm_self_conf(claim, candidates, llm) if not offline else None
        cov_max = coverage["max_similarity"] if coverage else 0.0

        confidence = safety.calibrate(
            verdict=verdict, best_support=best_support, votes=votes,
            distinct_sources=distinct, llm_self_conf=llm_conf,
            quote_verbatim=(quote != "" or verdict in ("NOT_ADDRESSED", "UNVERIFIED")),
            coverage_max=cov_max, decisive=bool(hard_contras),
        )
        verify, reasons = safety.verify_flags(
            verdict=verdict, confidence=confidence, single_source=single_source,
            best_support=best_support, ambiguous=ambiguous,
            llm_low=(llm.available() and llm_conf is not None and llm_conf < 0.4),
            coverage_max=cov_max,
        )

        results[pid] = Assessment(
            prop_id=pid, verdict=verdict, legal_risk=overlay, quote=quote,
            anchor=anchor, confidence=confidence, verify=verify, reasons=reasons,
            evidence=ev_anchors, single_source=single_source, coverage=coverage,
        )
    return results
