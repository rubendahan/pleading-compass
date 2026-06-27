"""Build the augmented EXOTIC AppData (murky EU case + planted traps) -> demo/data_eu_traps.json.

Takes the real-engine output for *Brightmarket v Cobalt* (``demo/eu_case_build.build_data``,
which runs the actual coherence solver) and overlays the seven deliberately treacherous
allegations (P15..P21) from ``data/eu_traps_gold.py``, mapping the engine-agnostic gold
into the frontend's AppData shape per ``demo/BACKEND-OUTPUT-SPEC.md``:

  * one proposition node per trap (verdict / overlay / readiness; ``source:"ai"`` when the
    gold asks for human verification — the margin TrustBadge then reads "AI · verify");
  * one pleading claim per trap (anchored at the Particulars-of-Claim paragraph ¶24..¶30,
    quote = the verbatim pleaded text), with ``belongs_to`` impact edge;
  * operative bundle claims (the controlling document) with a HARD ``contradicts`` /
    ``supersedes`` coherence edge onto the pleaded claim — so ``controllingEvidence()``
    surfaces the document that defeats the pleading, not the decoy;
  * decoy bundle claims (the superficially-supportive document) with a SOFT edge, so the
    decoy is visible but out-ranked;
  * ``own_goal:true`` on edges sourced from the claimant's own material (e.g. P17's own
    25-October email, P21's own DPIA);
  * trap documents (tabs 35..46) added to the ``documents`` map, doc 02 extended with the
    trap pleadings, and a handful of trap chronology facts.

Run:  python demo/eu_traps_build.py    ->    writes demo/data_eu_traps.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_DEMO = Path(__file__).resolve().parent
_ROOT = _DEMO.parent
for _p in (str(_ROOT), str(_DEMO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import eu_case_build  # noqa: E402  (sibling script in demo/)
from data import eu_traps_gold as T  # noqa: E402


_CLAIMANT_SIDE = {"claimant"}
_ADVERSE = {"contradicts", "supersedes", "attacks"}

# Per-document source strength (BACKEND-OUTPUT-SPEC §3.5 convention).
_DOC_SOURCE_TYPE = {
    "35": "legal_clause", "36": "defect_log", "37": "contemporaneous_email",
    "38": "record", "39": "signed_contract", "40": "record", "41": "defect_log",
    "42": "record", "43": "signed_contract", "44": "record", "45": "expert_report",
    "46": "legal_clause", "14": "admission",
}
_WEIGHT = {
    "legal_clause": 5.0, "signed_contract": 5.0, "acceptance_certificate": 5.0,
    "expert_report": 4.0, "admission": 4.0, "change_order": 4.0,
    "contemporaneous_email": 3.0, "defect_log": 3.0, "record": 3.0,
    "witness_statement": 2.0, "pleading": 1.0, "absence": 1.0,
}
# Per-allegation trial readiness from (verdict, confidence band): the more confident the
# engine is that a pleaded point is CONTRADICTED, the LOWER its trial readiness.
_READINESS = {
    ("SUPPORTED", "high"): 100, ("SUPPORTED", "medium"): 85, ("SUPPORTED", "low"): 70,
    ("CONTRADICTED", "high"): 5, ("CONTRADICTED", "medium"): 15, ("CONTRADICTED", "low"): 25,
    ("UNVERIFIED", "high"): 35, ("UNVERIFIED", "medium"): 30, ("UNVERIFIED", "low"): 25,
    ("NOT_ADDRESSED", "high"): 20, ("NOT_ADDRESSED", "medium"): 15, ("NOT_ADDRESSED", "low"): 10,
}


def _source_type(doc: str) -> str:
    return _DOC_SOURCE_TYPE.get(doc, "record")


def _operative_relation(g: dict) -> tuple[str, bool]:
    """Coherence relation from an operative claim onto the pleaded claim.

    CONTRADICTED -> a HARD ``supersedes`` (when the overlay is SUPERSEDED) or
    ``contradicts``; UNVERIFIED / NOT_ADDRESSED -> a SOFT ``qualifies``."""
    if g["verdict"] == "CONTRADICTED":
        return ("supersedes", True) if g["legal_risk"] == "SUPERSEDED" else ("contradicts", True)
    return ("qualifies", False)


def _decoy_relation(g: dict) -> str:
    """A CONTRADICTED trap's decoy superficially SUPPORTS the (wrong) pleading; an
    ambiguous trap's decoy ATTACKS it (a red herring pulling the other way)."""
    return "supports" if g["verdict"] == "CONTRADICTED" else "attacks"


def build_overlay(base: dict, bundle: dict) -> None:
    """Mutate ``base`` AppData in place, adding trap nodes/edges/clusters/documents."""
    nodes, edges, clusters = base["nodes"], base["edges"], base["clusters"]
    docmap = base.setdefault("documents", {})
    existing_ids = {n["id"] for n in nodes}

    def add_doc_node(doc: str) -> None:
        nid = f"doc:{doc}"
        if nid in existing_ids:
            return
        existing_ids.add(nid)
        m = bundle.get(doc, {})
        nodes.append({
            "id": nid, "layer": "document", "label": doc,
            "title": m.get("title", f"Document {doc}"),
            "doc_type": m.get("doc_type", "record"), "party": m.get("party", "neutral"),
            "date": m.get("date"), "category": m.get("category"),
            "tab": doc, "modality": m.get("modality"),
        })

    def add_bundle_claim(cid: str, doc: str, para: int, issue: str,
                         load_bearing: bool) -> str:
        st = _source_type(doc)
        quote = T.QUOTES.get((doc, para)) or T.para_text(bundle, doc, para)
        nodes.append({
            "id": f"claim:{cid}", "layer": "claim", "label": (quote or doc)[:42],
            "fulltext": quote, "issue": issue, "polarity": "bundle",
            "source_type": st, "weight": _WEIGHT.get(st, 3.0), "verdict": "accepted",
            "anchor": f"{doc}¶{para}", "quote": quote, "prop": None,
            "load_bearing": load_bearing, "single_source": False,
        })
        add_doc_node(doc)
        edges.append({"source": f"doc:{doc}", "target": f"claim:{cid}",
                      "rel": "asserts", "kind": "provenance", "hard": False})
        return f"claim:{cid}"

    # Extend the Particulars of Claim (doc 02) with the trap pleadings ¶24..¶30.
    if "02" in docmap:
        have = {p["n"] for p in docmap["02"]["paras"]}
        for n, txt in sorted(T.TRAP_PLEADED_PARAS.items()):
            if n not in have:
                docmap["02"]["paras"].append({"n": n, "text": txt})

    text_by_id = {tp["id"]: tp["text"] for tp in T.TRAP_PROPOSITIONS}
    pleaded_by_id = {tp["id"]: tp["pleaded_at"] for tp in T.TRAP_PROPOSITIONS}

    for tp in T.TRAP_PROPOSITIONS:
        pid = tp["id"]
        g = T.TRAP_GOLD[pid]
        issue = g["issue"]
        ptext = text_by_id[pid]
        pdoc, ppara = pleaded_by_id[pid]

        # Proposition (target) node — verify -> source:"ai" (margin "AI · verify" badge).
        pnode = {
            "id": f"prop:{pid}", "layer": "proposition", "label": pid,
            "verdict": g["verdict"], "overlay": g["legal_risk"],
            "readiness": _READINESS[(g["verdict"], g["confidence_band"])],
            "acts": g.get("acts", []), "text": ptext,
        }
        if g["verify"]:
            pnode["source"] = "ai"
        nodes.append(pnode)
        existing_ids.add(pnode["id"])

        # Pleading claim — quote = the verbatim pleaded paragraph; rejected iff CONTRADICTED.
        plead_quote = T.para_text(bundle, pdoc, ppara)
        plead_verdict = "rejected" if g["verdict"] == "CONTRADICTED" else "accepted"
        pclaim = f"{pid}_plead"
        nodes.append({
            "id": f"claim:{pclaim}", "layer": "claim", "label": ptext[:42],
            "fulltext": ptext, "issue": issue, "polarity": "pleading",
            "source_type": "pleading", "weight": 1.0, "verdict": plead_verdict,
            "anchor": f"{pdoc}¶{ppara}", "quote": plead_quote, "prop": pid,
            "load_bearing": False, "single_source": False,
        })
        edges.append({"source": f"claim:{pclaim}", "target": f"prop:{pid}",
                      "rel": "belongs_to", "kind": "impact", "hard": False,
                      "verdict": plead_verdict})

        # Operative (controlling) evidence: HARD contradicts/supersedes onto the pleading.
        rel, hard = _operative_relation(g)
        for i, (doc, para) in enumerate(g["operative_evidence"]):
            cid = f"{pid}_op{i}"
            add_bundle_claim(cid, doc, para, issue, load_bearing=(i == 0))
            party = bundle.get(doc, {}).get("party")
            own_goal = party in _CLAIMANT_SIDE and rel in _ADVERSE
            edge = {"source": f"claim:{cid}", "target": f"claim:{pclaim}",
                    "rel": rel, "kind": "coherence", "hard": hard,
                    "explanation": g["rationale"], "own_goal": own_goal}
            if hard and i == 0:
                edge["blocking"] = True
            edges.append(edge)

        # Decoy evidence: SOFT edge — visible but out-ranked by the operative claim.
        drel = _decoy_relation(g)
        for i, (doc, para) in enumerate(g["decoy_evidence"]):
            cid = f"{pid}_decoy{i}"
            add_bundle_claim(cid, doc, para, issue, load_bearing=False)
            edges.append({
                "source": f"claim:{cid}", "target": f"claim:{pclaim}",
                "rel": drel, "kind": "coherence", "hard": False,
                "explanation": "Superficially on point, but the controlling evidence is the "
                               "operative document, not this one.",
                "own_goal": False,
            })

        clusters.append({
            "issue": issue, "solver": "trap_oracle",
            "story": [g["rationale"]],
            "impacts": [f"{pid}: {g['verdict']} [legal overlay: {g['legal_risk']}] - "
                        f"{g['rationale']}"],
            "amendments": [g.get("amendment", "Lawyer review required.")],
        })

    # Add the trap documents (tabs 35..46) to the documents map.
    for doc, meta in T.TRAP_DOCS.items():
        docmap[doc] = {
            "title": meta["title"], "doc_type": meta["doc_type"], "party": meta["party"],
            "date": meta["date"], "category": meta["category"], "tab": doc,
            "modality": meta["modality"], "mime": meta["modality"],
            "paras": [{"n": n, "text": t} for n, t in meta["paras"]],
        }


def trap_chronology(start: int) -> list[dict]:
    return [
        {"n": start + 1, "date": "2023-11-30",
         "event": "India sub-processor de-listed and removed from the register; no production "
                  "data routed to it since.",
         "evidence": [{"tab": "39", "para": 2}],
         "remarks": "Breaks the pleaded India-transfer chain (P18).", "source": "ai"},
        {"n": start + 2, "date": "2025-10-11",
         "event": "Analytics-dashboard outage ends after ~30 hours; the public storefront was "
                  "unaffected.",
         "evidence": [{"tab": "36", "para": 2}, {"tab": "36", "para": 4}],
         "remarks": "Pleaded 30 days / EUR 4.5m is a unit/scale trap (P16).", "source": "ai"},
        {"n": start + 3, "date": "2025-10-12",
         "event": "Misconfiguration remediated the same day it was ticketed (SEC-1187).",
         "evidence": [{"tab": "38", "para": 2}],
         "remarks": "Contradicts 'ignored / failed to remediate' (P17).", "source": "ai"},
        {"n": start + 4, "date": "2025-10-25",
         "event": "Post-breach follow-up email — mis-pleaded as a 25 September pre-breach warning.",
         "evidence": [{"tab": "37", "para": 1}],
         "remarks": "Date trap underlying P17; the Claimant's own email.", "source": "ai"},
    ]


def recompute_stats(base: dict) -> None:
    nodes, edges = base["nodes"], base["edges"]
    props = [n for n in nodes if n["layer"] == "proposition"]
    claims = [n for n in nodes if n["layer"] == "claim"]
    docs = [n for n in nodes if n["layer"] == "document"]
    supported = sum(1 for n in props if n["verdict"] == "SUPPORTED")
    base["stats"].update({
        "readiness": round(100 * supported / max(len(props), 1)),
        "own_goal": sum(1 for e in edges if e.get("own_goal")),
        "props": len(props), "docs": len(docs), "claims": len(claims),
        "rejected_pleadings": sum(1 for n in claims
                                  if n["polarity"] == "pleading" and n["verdict"] == "rejected"),
        # Headline rises with the planted EUR 4.5m outage claim; defensible figure unchanged.
        "exposure_from": "€11.4m", "exposure_to": "€0.9m",
    })


def build_data() -> dict:
    base = eu_case_build.build_data()
    _, bundle = T.compose()

    build_overlay(base, bundle)

    base.setdefault("chronology", [])
    base["chronology"].extend(trap_chronology(len(base["chronology"])))

    recompute_stats(base)

    base["meta"]["traps"] = True
    base["meta"]["theme"] = ("B2B SaaS analytics platform / GDPR dispute (EU law) — "
                             "with seven planted adversarial 'traps' for the verifier")
    return base


def main() -> None:
    data = build_data()
    out = _DEMO / "data_eu_traps.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    dist = Counter(n["verdict"] for n in data["nodes"] if n["layer"] == "proposition")
    hard_contra = sum(1 for e in data["edges"]
                      if e["kind"] == "coherence" and e["rel"] in ("contradicts", "supersedes")
                      and e.get("hard"))
    own_goals = sum(1 for e in data["edges"] if e.get("own_goal"))
    trap_props = sum(1 for n in data["nodes"]
                     if n["layer"] == "proposition" and n["label"] in T.TRAP_GOLD)

    print(f"wrote {out}  ({len(data['nodes'])} nodes, {len(data['edges'])} edges, "
          f"{len(data['clusters'])} clusters, {len(data['documents'])} documents, "
          f"{len(data['chronology'])} chronology events)")
    print(f"trap propositions overlaid: {trap_props}   verdict distribution: {dict(sorted(dist.items()))}")
    print(f"hard contradictions/supersessions: {hard_contra}   own-goal edges: {own_goals}   "
          f"readiness: {data['stats']['readiness']}/100")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
