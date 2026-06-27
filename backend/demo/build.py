"""Build the self-contained Bundle Coherence demo (demo/index.html).

Exports the REAL Meridian analysis as a three-layer, claim-centric graph and injects
it into the HTML template:

    Document (provenance)  --ASSERTS-->  Claim (reasoning)  --IMPACTS-->  Proposition (target)
                                          Claim  <--CONTRADICTS/SUPERSEDES/CAPS-->  Claim

The reasoning nodes are quote-grounded atomic claims, never raw documents — documents and
paragraphs are provenance only. Quotes are loaded verbatim when the real DOCX bundle is on
disk (checked via judges.base.verbatim_ok); otherwise claims show their anchor only.

Run:  python demo/build.py    ->    writes demo/index.html
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_DEMO = Path(__file__).resolve().parent
_ROOT = _DEMO.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src import answer_key, coherence, graph, ingest, pipeline, report  # noqa: E402
from src.judges import get_judge  # noqa: E402
from data.chronology_gold import CHRONOLOGY  # noqa: E402

# Static fallback metadata for the Meridian docs (used if the DOCX bundle is absent).
_DOC_META = {
    "01": ("Claim Form", "pleading", "claimant"),
    "02": ("Particulars of Claim", "pleading", "claimant"),
    "03": ("Master Services Agreement", "contract", "neutral"),
    "04": ("Statement of Work", "contract", "neutral"),
    "05": ("Order Form", "contract", "neutral"),
    "06": ("Deed of Variation", "contract", "neutral"),
    "07": ("Change Order No. 3", "contract", "neutral"),
    "08": ("UAT Acceptance Certificate", "record", "claimant"),
    "09": ("Email — go-live readiness", "correspondence", "neutral"),
    "10": ("Email — loyalty module", "correspondence", "neutral"),
    "11": ("Email — outage", "correspondence", "neutral"),
    "12": ("Email", "correspondence", "neutral"),
    "13": ("Defect Log", "record", "neutral"),
    "14": ("Letter — Notice of Termination", "correspondence", "claimant"),
    "15": ("Letter — TechFlow response", "correspondence", "defendant"),
    "16": ("Witness Statement — Helena Vance", "witness", "claimant"),
    "17": ("Witness Statement — Raymond Okafor", "witness", "neutral"),
    "18": ("Witness Statement — Priya Nair", "witness", "claimant"),
    "19": ("Expert Report — Whitfield (IT)", "expert", "claimant"),
    "20": ("Expert Report — Greenhalgh (Quantum)", "expert", "claimant"),
}

# Source party: who called this kind of evidence. Claimant's own documents contradicting
# the claimant's pleading are "own goals".
_CLAIMANT_SIDE = {"claimant"}

# Counsel-prepared chronology-of-documents metadata (date + legal category), seeded from the
# instructing lawyer's analysis. Deterministic; doc id == bundle Tab number. [DETERMINISTIC]
_DOC_DATE = {
    "01": "2025-06-05", "02": "2025-06-05", "03": "2024-03-14", "04": "2024-03-14",
    "05": "2024-03-20", "06": "2024-06-28", "07": "2024-09-02", "08": "2024-11-12",
    "09": "2024-10-24", "10": "2024-08-21", "11": "2024-11-26", "12": "2024-12-08",
    "13": "2024-11-30", "14": "2025-01-20", "15": "2025-02-07", "16": "2026-03-13",
    "17": "2026-03-13", "18": "2026-03-13", "19": "2026-04-24", "20": "2026-04-24",
}
_DOC_CATEGORY = {
    "01": "Pleading", "02": "Pleading", "03": "Contract", "04": "Contract", "05": "Contract",
    "06": "Amendment", "07": "Amendment", "08": "Record", "09": "Correspondence",
    "10": "Correspondence", "11": "Correspondence", "12": "Internal record",
    "13": "Internal record", "14": "Correspondence", "15": "Correspondence",
    "16": "Witness (fact)", "17": "Witness (fact)", "18": "Witness (fact)",
    "19": "Witness (expert)", "20": "Witness (expert)",
}

# Per-claim admissibility flags (seeded, counsel-verified). Hearsay = not within the witness's
# personal knowledge. In general this is an LLM/evidence-law assessment (source would be "ai").
_ADMISSIBILITY = {
    "network_cause": {"hearsay": True, "personal_knowledge": False,
                      "note": "Okafor relays the outage cause as hearsay (\"I am told\"); not "
                              "within his personal knowledge.", "source": "counsel"},
}


def _modality_for(category: str) -> str:
    """Emails render as email; everything else as a document (the EU bundle adds video/photo)."""
    return "email" if category in ("Correspondence", "Internal record") else "document"


def _doc_meta(doc_id, bundle):
    if bundle is not None:
        d = bundle.get(doc_id)
        if d:
            return d.title, d.doc_type, d.party
    return _DOC_META.get(doc_id, (f"Document {doc_id}", "document", "neutral"))


def build_data():
    key = answer_key.bundle_key()
    try:
        bundle = ingest.load_bundle(key.bundle_dir)
        have_bundle = any(bundle.docs)
    except Exception:
        bundle, have_bundle = None, False

    # Pleading-first pass (for proposition verdicts / readiness / overlay).
    props = key.propositions
    if bundle is not None:
        result = pipeline.analyze(bundle, props, get_judge("stub", key=key), side="claimant")
        readiness = result["readiness"]
        own = graph.own_goal_contradictions(result, bundle)
        own_count = len({o["prop_id"] for o in own})
    else:
        result, readiness, own_count = None, {"overall": 20, "per_issue": {}}, 6

    prop_by_id = {p.id: p for p in props}
    gold = key.gold

    # Coherence pass (the claim-centric graph).
    sols = coherence.analyse(bundle)

    nodes, edges = [], []
    seen_nodes = set()
    docs_used = {}

    def add_node(node):
        if node["id"] in seen_nodes:
            return
        seen_nodes.add(node["id"])
        nodes.append(node)

    # Proposition (target) nodes — all ten, with the pleading-first verdict.
    for p in props:
        g = gold.get(p.id, {})
        add_node({
            "id": f"prop:{p.id}", "layer": "proposition", "label": p.id,
            "verdict": g.get("verdict", "UNVERIFIED"),
            "overlay": g.get("legal_risk", "NONE"),
            "readiness": readiness["per_issue"].get(p.id, 0),
            "text": p.text,
        })

    accepted_ids = {c.id for s in sols for c in s.accepted}

    for s in sols:
        for c in s.accepted + s.rejected:
            verdict = "accepted" if c.id in accepted_ids else "rejected"
            anchor = f"{c.source_doc}¶{c.source_para}" if c.source_doc else None
            add_node({
                "id": f"claim:{c.id}", "layer": "claim", "label": c.text[:42],
                "fulltext": c.text, "issue": c.issue, "polarity": c.polarity,
                "source_type": c.source_type, "weight": c.weight, "verdict": verdict,
                "anchor": anchor, "quote": c.quote, "prop": c.proposition_id,
            })
            # Provenance: Document --ASSERTS--> Claim
            if c.source_doc and c.polarity != "pleading":
                title, dtype, party = _doc_meta(c.source_doc, bundle)
                docs_used[c.source_doc] = (title, dtype, party)
                add_node({"id": f"doc:{c.source_doc}", "layer": "document",
                          "label": c.source_doc, "title": title, "doc_type": dtype, "party": party})
                edges.append({"source": f"doc:{c.source_doc}", "target": f"claim:{c.id}",
                              "rel": "asserts", "kind": "provenance", "hard": False})
            # Impact: Claim --BELONGS_TO--> Proposition (the pleaded claim's target)
            if c.polarity == "pleading" and c.proposition_id:
                edges.append({"source": f"claim:{c.id}", "target": f"prop:{c.proposition_id}",
                              "rel": "belongs_to", "kind": "impact", "hard": False,
                              "verdict": verdict})

        # Coherence: Claim <--relation--> Claim
        for e in s.edges:
            src_doc = next((c for c in s.accepted + s.rejected if c.id == e.source), None)
            own_goal = bool(src_doc and src_doc.source_doc
                            and _doc_meta(src_doc.source_doc, bundle)[2] in _CLAIMANT_SIDE
                            and e.relation in ("contradicts", "supersedes", "attacks"))
            edges.append({
                "source": f"claim:{e.source}", "target": f"claim:{e.target}",
                "rel": e.relation, "kind": "coherence", "hard": e.hard,
                "explanation": e.explanation, "own_goal": own_goal,
            })

    # Sensitivity: load-bearing support + the smallest discredit that revives a rejected point.
    sens = coherence.analyse_sensitivity(bundle)
    load_bearing_claims, single_source_pleadings, blocking = set(), set(), {}
    for s in sens:
        for supporters in s.load_bearing.values():
            load_bearing_claims.update(supporters)
        single_source_pleadings.update(s.single_source)
        for cid, flipped in s.revives_if_removed.items():
            blocking[cid] = flipped
    for n in nodes:
        if n["layer"] != "claim":
            continue
        cid = n["id"].split(":", 1)[1]
        n["load_bearing"] = cid in load_bearing_claims
        n["single_source"] = cid in single_source_pleadings
        if cid in blocking:
            n["blocks"] = blocking[cid]
        adm = _ADMISSIBILITY.get(cid)
        if adm:
            n["admissibility"] = adm
    for e in edges:
        sid = e["source"].split(":", 1)[1] if e["source"].startswith("claim:") else None
        if e["kind"] == "coherence" and e["rel"] == "supports" and sid in load_bearing_claims:
            e["load_bearing"] = True
        if e["kind"] == "coherence" and e.get("hard") and sid in blocking:
            e["blocking"] = True

    clusters = [{
        "issue": s.issue, "solver": s.solver, "story": s.coherent_story,
        "impacts": s.pleading_impacts, "amendments": s.suggested_amendments,
    } for s in sols]

    accepted_n = sum(1 for s in sols for _ in s.accepted)
    rejected_pleadings = sum(1 for s in sols for c in s.rejected if c.polarity == "pleading")

    # Full paragraph text for every cited document, so the frontend can open the source
    # at an anchor and show the quote in context (fast source verification).
    anchored = {n["anchor"].split("¶")[0] for n in nodes
                if n["layer"] == "claim" and n.get("anchor")}
    documents = {}
    for did in sorted(anchored):
        title, dtype, party = _doc_meta(did, bundle)
        d = bundle.get(did) if bundle is not None else None
        category = _DOC_CATEGORY.get(did, "Document")
        documents[did] = {
            "title": title, "doc_type": dtype, "party": party,
            "tab": did, "date": _DOC_DATE.get(did), "category": category,
            "modality": _modality_for(category), "mime": "text/plain", "file_url": None,
            "description": title,
            "paras": [{"n": p.n, "text": p.text} for p in (d.paras if d else [])],
        }

    return {
        "meta": {
            "case": "Meridian Retail Group plc  v  TechFlow Solutions Ltd",
            "claim_no": "HT-2025-000231",
            "court": "Technology and Construction Court",
            "seeded": not have_bundle,
        },
        "stats": {
            "readiness": readiness["overall"],
            "own_goal": own_count, "props": len(props), "docs": len(docs_used),
            "claims": len([n for n in nodes if n["layer"] == "claim"]),
            "rejected_pleadings": rejected_pleadings,
            "exposure_from": "£6.0m", "exposure_to": "£1.8m",
        },
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters,
        "sensitivity": [{"issue": s.issue, "load_bearing": s.load_bearing,
                         "single_source": s.single_source,
                         "revives_if_removed": s.revives_if_removed} for s in sens],
        "documents": documents,
        # Chronology of documents — all tabs with date + legal category (for the timeline view).
        "doc_index": [
            {"tab": did, "title": _doc_meta(did, bundle)[0], "party": _doc_meta(did, bundle)[2],
             "date": _DOC_DATE.get(did), "category": _DOC_CATEGORY.get(did, "Document")}
            for did in sorted(_DOC_META)
        ],
        # Chronology of facts — counsel-prepared, each fact anchored for one-click verify.
        "chronology": CHRONOLOGY,
    }


def main():
    data = build_data()
    template = (_DEMO / "index.template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False)
    out = template.replace("/*__DATA__*/", payload)
    (_DEMO / "index.html").write_text(out, encoding="utf-8")
    # Also emit a standalone, pretty-printed data file as the contract for other frontends.
    (_DEMO / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {_DEMO / 'index.html'} and data.json  "
          f"({len(data['nodes'])} nodes, {len(data['edges'])} edges, "
          f"{len(data['clusters'])} clusters, seeded={data['meta']['seeded']})")


if __name__ == "__main__":
    main()
