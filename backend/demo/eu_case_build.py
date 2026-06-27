"""Build the SECOND litigation test case as AppData -> demo/data_eu_case.json.

A harder, more ambiguous dispute (*Brightmarket Retail GmbH v Cobalt Cloud Analytics
Ltd*) grounded in REAL EU legislation, in the SAME contract as the Meridian demo
(demo/build.py -> demo/data.json). It runs the real backend: the fixtures in
``data/eu_case_gold.py`` are fed to the actual coherence primitives
(``src.coherence._build_claim`` + the brute-force ``solve_cluster`` + the deterministic
``sensitivity`` sweep), so accepted/rejected, load-bearing and revive-if-removed are all
decided by the engine — not hard-coded here. The node/edge/cluster assembly mirrors
``demo/build.py``; this script adds the newer optional fields the frontend now expects
(per-document ``date``/``category``/``tab``/``modality``, a top-level ``chronology``, and
per-claim ``admissibility``).

Run:  python demo/eu_case_build.py    ->    writes demo/data_eu_case.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_DEMO = Path(__file__).resolve().parent
_ROOT = _DEMO.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data import eu_case_gold as G  # noqa: E402
from src import coherence  # noqa: E402
from src.coherence import (CoherenceCluster, CoherenceEdge, _build_claim,  # noqa: E402
                           sensitivity, solve_cluster)

# Claimant-side parties: a claimant's own document undermining its pleaded case is an
# "own goal" (same rule as demo/build.py).
_CLAIMANT_SIDE = {"claimant"}

# Documentary source types carry no first-hand/hearsay axis (they are records, not oral
# testimony); witness / expert claims do.
_DOCUMENTARY = {"legal_clause", "admission", "defect_log", "change_order",
                "contemporaneous_email", "signed_contract", "acceptance_certificate"}


def _doc_meta(doc_id, bundle):
    """(title, doc_type, party) for a doc — from the loaded bundle, with a static fallback."""
    if bundle is not None:
        d = bundle.get(doc_id)
        if d:
            return d.title, d.doc_type, d.party
    t = G.DOC_META.get(doc_id)
    return (t[0], t[1], t[2]) if t else (f"Document {doc_id}", "document", "neutral")


def _admissibility(claim):
    """Per-claim admissibility overlay {hearsay, personal_knowledge, note, source}."""
    src = claim.source_doc
    if claim.id in G.HEARSAY_CLAIMS:
        return {"hearsay": True, "personal_knowledge": False, "source": src,
                "note": "Witness relays what others told them ('I am told…') — hearsay; no "
                        "personal knowledge; weight reduced."}
    st = claim.source_type
    if st == "witness_statement":
        return {"hearsay": False, "personal_knowledge": True, "source": src,
                "note": "First-hand witness recollection."}
    if st == "expert_report":
        return {"hearsay": False, "personal_knowledge": True, "source": src,
                "note": "Independent expert opinion within the expert's expertise."}
    if st == "absence":
        return {"hearsay": False, "personal_knowledge": None, "source": None,
                "note": "No evidence in the bundle (absence) — burden / evidence gap."}
    if claim.polarity == "pleading":
        return {"hearsay": False, "personal_knowledge": None, "source": src,
                "note": "Pleaded allegation — to be proved."}
    if st in _DOCUMENTARY:
        return {"hearsay": False, "personal_knowledge": None, "source": src,
                "note": "Contemporaneous documentary record."}
    return {"hearsay": False, "personal_knowledge": None, "source": src, "note": ""}


def build_clusters(bundle):
    """Build the coherence clusters from the case recipes, using the REAL engine's
    claim/edge constructors and this case's GOLD / PLEADED_AT."""
    clusters = []
    for recipe in G.RECIPES:
        claims = [_build_claim(c, recipe["issue"], G.GOLD, G.PLEADED_AT, bundle)
                  for c in recipe["claims"]]
        edges = [CoherenceEdge(e["source"], e["target"], e["relation"], e["hard"],
                               e.get("explanation", ""), e.get("rule", ""))
                 for e in recipe["edges"]]
        clusters.append(CoherenceCluster(
            issue=recipe["issue"], claims=claims, edges=edges,
            meta={"story": recipe["story"], "amendments": recipe["amendments"], "gold": G.GOLD}))
    return clusters


def build_data():
    bundle = G.bundle()
    props = list(G.PROPOSITIONS)
    gold = G.GOLD

    clusters = build_clusters(bundle)
    sols = [solve_cluster(c) for c in clusters]
    sens = [sensitivity(c) for c in clusters]

    nodes, edges = [], []
    seen_nodes = set()
    docs_used = {}

    def add_node(node):
        if node["id"] in seen_nodes:
            return
        seen_nodes.add(node["id"])
        nodes.append(node)

    # Proposition (target) nodes — verdict/overlay come straight from the gold oracle.
    for p in props:
        g = gold.get(p.id, {})
        add_node({
            "id": f"prop:{p.id}", "layer": "proposition", "label": p.id,
            "verdict": g.get("verdict", "UNVERIFIED"),
            "overlay": g.get("legal_risk", "NONE"),
            "readiness": 100 if g.get("verdict") == "SUPPORTED" else 0,
            "acts": g.get("acts", []),
            "text": p.text,
        })

    accepted_ids = {c.id for s in sols for c in s.accepted}
    claim_prop = {}  # claim id -> proposition id (for own-goal stat)

    for s in sols:
        for c in s.accepted + s.rejected:
            claim_prop[c.id] = c.proposition_id
            verdict = "accepted" if c.id in accepted_ids else "rejected"
            anchor = f"{c.source_doc}¶{c.source_para}" if c.source_doc else None
            add_node({
                "id": f"claim:{c.id}", "layer": "claim", "label": c.text[:42],
                "fulltext": c.text, "issue": c.issue, "polarity": c.polarity,
                "source_type": c.source_type, "weight": c.weight, "verdict": verdict,
                "anchor": anchor, "quote": c.quote, "prop": c.proposition_id,
                "admissibility": _admissibility(c),
            })
            # Provenance: Document --asserts--> Claim
            if c.source_doc and c.polarity != "pleading":
                title, dtype, party = _doc_meta(c.source_doc, bundle)
                docs_used[c.source_doc] = (title, dtype, party)
                add_node({"id": f"doc:{c.source_doc}", "layer": "document",
                          "label": c.source_doc, "title": title, "doc_type": dtype,
                          "party": party})
                edges.append({"source": f"doc:{c.source_doc}", "target": f"claim:{c.id}",
                              "rel": "asserts", "kind": "provenance", "hard": False})
            # Impact: pleaded Claim --belongs_to--> Proposition
            if c.polarity == "pleading" and c.proposition_id:
                edges.append({"source": f"claim:{c.id}", "target": f"prop:{c.proposition_id}",
                              "rel": "belongs_to", "kind": "impact", "hard": False,
                              "verdict": verdict})

        # Coherence: Claim <--relation--> Claim (own-goal when claimant's own doc attacks)
        for e in s.edges:
            src = next((c for c in s.accepted + s.rejected if c.id == e.source), None)
            own_goal = bool(src and src.source_doc
                            and _doc_meta(src.source_doc, bundle)[2] in _CLAIMANT_SIDE
                            and e.relation in ("contradicts", "supersedes", "attacks"))
            edges.append({
                "source": f"claim:{e.source}", "target": f"claim:{e.target}",
                "rel": e.relation, "kind": "coherence", "hard": e.hard,
                "explanation": e.explanation, "own_goal": own_goal,
            })

    # Sensitivity: load-bearing support + the smallest discredit that revives a point.
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
    for e in edges:
        sid = e["source"].split(":", 1)[1] if e["source"].startswith("claim:") else None
        if e["kind"] == "coherence" and e["rel"] == "supports" and sid in load_bearing_claims:
            e["load_bearing"] = True
        if e["kind"] == "coherence" and e.get("hard") and sid in blocking:
            e["blocking"] = True

    clusters_out = [{
        "issue": s.issue, "solver": s.solver, "story": s.coherent_story,
        "impacts": s.pleading_impacts, "amendments": s.suggested_amendments,
    } for s in sols]

    rejected_pleadings = sum(1 for s in sols for c in s.rejected if c.polarity == "pleading")

    # Distinct propositions sunk by an own-goal coherence edge.
    own_props = {claim_prop.get(e["target"].split(":", 1)[1])
                 for e in edges if e.get("own_goal")}
    own_props.discard(None)

    # Full paragraph text + the newer per-document fields for every cited document.
    anchored = {n["anchor"].split("¶")[0] for n in nodes
                if n["layer"] == "claim" and n.get("anchor")}
    documents = {}
    for did in sorted(anchored):
        title, dtype, party = _doc_meta(did, bundle)
        meta = G.DOC_META.get(did)
        date = meta[3] if meta else None
        category = meta[4] if meta else None
        modality = meta[5] if meta else None
        d = bundle.get(did) if bundle is not None else None
        documents[did] = {
            "title": title, "doc_type": dtype, "party": party,
            "date": date, "category": category, "tab": did, "modality": modality,
            "mime": modality,
            "paras": [{"n": p.n, "text": p.text} for p in (d.paras if d else [])],
        }

    # Annotate the document NODES with the same per-document fields.
    for n in nodes:
        if n["layer"] == "document":
            meta = G.DOC_META.get(n["label"])
            if meta:
                n["date"], n["category"], n["tab"], n["modality"] = meta[3], meta[4], n["label"], meta[5]

    verdict_dist = Counter(gold.get(p.id, {}).get("verdict", "UNVERIFIED") for p in props)
    supported = verdict_dist.get("SUPPORTED", 0)

    # Real EU acts cited, cross-checked against the demo/data_eu.json Cellar library.
    eu_lib_ids = set()
    try:
        eu_lib = json.loads((_DEMO / "data_eu.json").read_text(encoding="utf-8"))
        eu_lib_ids = {n["id"] for n in eu_lib.get("nodes", [])}
    except Exception:
        pass
    eu_acts = []
    for celex, info in G.EU_ACTS.items():
        eu_acts.append({"celex": celex, "title": info["title"], "short": info["short"],
                        "articles": info["arts"], "in_data_eu": celex in eu_lib_ids})

    return {
        "meta": {
            "case": G.CASE,
            "claim_no": G.CLAIM_NO,
            "court": G.COURT,
            "seeded": False,
            "synthetic": True,
            "theme": "B2B SaaS analytics platform / GDPR data-processing dispute (EU law)",
            "eu_acts": eu_acts,
        },
        "stats": {
            "readiness": round(100 * supported / max(len(props), 1)),
            "own_goal": len(own_props), "props": len(props), "docs": len(docs_used),
            "claims": len([n for n in nodes if n["layer"] == "claim"]),
            "rejected_pleadings": rejected_pleadings,
            "exposure_from": "€6.9m", "exposure_to": "€0.9m",
        },
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters_out,
        "sensitivity": [{"issue": s.issue, "load_bearing": s.load_bearing,
                         "single_source": s.single_source,
                         "revives_if_removed": s.revives_if_removed} for s in sens],
        "documents": documents,
        "chronology": G.CHRONOLOGY,
    }


def main():
    data = build_data()
    out = _DEMO / "data_eu_case.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    dist = Counter(n["verdict"] for n in data["nodes"] if n["layer"] == "proposition")
    cross_contra = sum(1 for e in data["edges"]
                       if e["kind"] == "coherence" and e["rel"] in ("contradicts", "supersedes"))
    hearsay = sum(1 for n in data["nodes"]
                  if n["layer"] == "claim" and n.get("admissibility", {}).get("hearsay"))
    overlays = sum(1 for n in data["nodes"]
                   if n["layer"] == "proposition" and n.get("acts"))

    print(f"wrote {out}  ({len(data['nodes'])} nodes, {len(data['edges'])} edges, "
          f"{len(data['clusters'])} clusters, {len(data['documents'])} documents, "
          f"{len(data['chronology'])} chronology events)")
    print("verdict distribution:", dict(sorted(dist.items())))
    print(f"own-goal props: {data['stats']['own_goal']}   "
          f"cross-doc contradictions/supersessions: {cross_contra}   "
          f"hearsay-flagged claims: {hearsay}   propositions citing a real EU act: {overlays}")
    cited = data["meta"]["eu_acts"]
    print(f"real EU acts cited: {len(cited)} "
          f"({sum(a['in_data_eu'] for a in cited)} present in demo/data_eu.json)")
    for a in cited:
        print(f"  - {a['celex']}  {a['title']}  [{'in data_eu.json' if a['in_data_eu'] else 'real Cellar CELEX'}]")


if __name__ == "__main__":
    main()
